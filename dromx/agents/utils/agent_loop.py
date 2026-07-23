"""Analyst agent-loop factory (v0.4) — the shared skeleton every analyst uses.

v0.3 analysts = pre-fetch + 1 structured call. v0.4 = pre-fetch + a
``create_react_agent`` loop (think → call tool → observe → … → structured
output). The pre-fetch STAYS: it seeds the system prompt with ground-truth
data so the loop doesn't waste turns re-fetching what we already pulled. The
loop is for FOLLOW-UP verification and deepening ("the news mentions a $29B
raise — let me check insider transactions and historical dilution"), not for
fetching the baseline snapshot.

The factory is a single function ``build_analyst_react_invoker`` returning a
zero-arg callable that runs the loop and returns the rendered report string.
The caller (each analyst node) wraps it with state read/write. This keeps the
analyst modules small and the loop logic in one place.

Degradation chain (every run must produce a report, never crash):
  1. provider supports ``with_structured_output`` → react agent with
     ``response_format=Schema`` → ``state["structured_response"]`` → render.
  2. structured_response missing/invalid → take the final AIMessage.content →
     ``invoke_structured_or_freetext`` to recover the schema from free text.
  3. provider lacks structured output → react agent without ``response_format``
     → final AIMessage.content → ``invoke_structured_or_freetext`` (JSON recover).
  4. ``create_react_agent`` itself fails → v0.3 path: single
     ``invoke_structured_or_freetext`` on the full system prompt.

Parallel fan-out safe: the analyst NODE returns only ``{report_key, messages:
[AIMessage(report_text)]}`` — never the react agent's internal messages, which
would collide on the Signal Aggregator's fan-in.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from tradingagents.agents.utils.skills import SkillInjector
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

logger = logging.getLogger(__name__)

# Each loop iteration ≈ 2 graph steps (model node + tool node); the
# response_format call adds 1. recursion_limit is a hard ceiling so a
# runaway loop can never hang the pipeline.
def _recursion_limit(max_iterations: int) -> int:
    # create_react_agent uses ~2 graph steps per loop iteration (model + tool);
    # an analyst with several tools (Market has get_stock_data/get_indicators/
    # get_verified_market_snapshot/web_read/web_search/request_skill) can call
    # 8-10 tools before stopping, so the old max_iter*3+5=20 was hit ("Recursion
    # limit of 20 reached"). 5 per iteration + 10 base gives enough headroom while
    # still bounding a runaway loop.
    return max(16, max_iterations * 5 + 10)


def _build_react_agent(
    llm: Any,
    tools: list,
    prompt: str,
    schema: type[BaseModel] | None,
    agent_name: str,
):
    """Create a react agent, or None if create_react_agent is unavailable.

    ``response_format`` is set only when ``schema`` is given — the caller
    decides (provider lacking structured output passes None so the loop runs
    free-text and ``invoke_structured_or_freetext`` recovers downstream).
    """
    try:
        from langgraph.prebuilt import create_react_agent
    except ImportError as exc:
        logger.warning("%s: langgraph create_react_agent unavailable (%s)", agent_name, exc)
        return None
    kwargs: dict[str, Any] = {"model": llm, "tools": tools, "prompt": prompt}
    if schema is not None:
        # Pass response_format as (system_prompt, schema) — a BARE schema makes
        # generate_structured_response invoke WITHOUT the system prompt, so the
        # LLM never sees get_language_instruction and outputs English even with
        # output_language=中文. The tuple form prepends the prompt as a
        # SystemMessage to the structured-response call (langgraph L482-484).
        kwargs["response_format"] = (prompt, schema)
    try:
        return create_react_agent(**kwargs)
    except Exception as exc:  # noqa: BLE001 — fall back to v0.3 single-call
        logger.warning("%s: create_react_agent build failed (%s); using v0.3 path", agent_name, exc)
        return None


def build_analyst_react_invoker(
    *,
    llm: Any,
    tools: list,
    schema: type[BaseModel] | None = None,
    render: Callable[[BaseModel], str] = lambda x: str(x),
    agent_name: str,
    system_message: str,
    skills: list | None = None,
    instruction: str = "",
    max_iterations: int = 5,
) -> Callable[[], str]:
    """Return a zero-arg callable that runs the analyst's agent loop → report str.

    ``system_message`` is the full v0.3-style prompt (core instructions +
    pre-fetched data blocks). ``skills`` are the SkillInjector-formatted skills
    to append. ``instruction`` is the short user-message that triggers the
    loop (defaults to a generic "begin" if empty).
    """
    skills_block = SkillInjector.format_skills_block(skills or [])
    full_prompt = system_message + ("\n" + skills_block if skills_block else "")
    structured_llm = bind_structured(llm, schema, agent_name) if schema is not None else None
    trigger = instruction or (
        "Begin the analysis. Call the available tools to verify or deepen any "
        "claim you cannot ground in the provided data, then fill the structured "
        "fields. Do not call a tool more than once for the same data."
    )
    limit = _recursion_limit(max_iterations)

    def _invoke() -> str:
        # Decide whether the provider can do structured output at all.
        use_response_format = structured_llm is not None
        schema_for_rf = schema if use_response_format else None
        agent = _build_react_agent(llm, tools, full_prompt, schema_for_rf, agent_name)

        if agent is not None:
            try:
                result = agent.invoke(
                    {"messages": [HumanMessage(content=trigger)]},
                    {"recursion_limit": limit},
                )
            except Exception as exc:  # noqa: BLE001 — fall back to v0.3 single-call
                logger.warning("%s: react agent invoke failed (%s); v0.3 fallback", agent_name, exc)
                result = None

            if result is not None:
                # 1) structured_response path (provider supports response_format).
                # schema=None (freetext, e.g. risk specialists) has no structured_response.
                if schema is not None:
                    sr = result.get("structured_response")
                    if isinstance(sr, schema):
                        return render(sr)
                    if sr is not None:
                        try:
                            return render(schema.model_validate(sr))
                        except Exception:  # noqa: BLE001 — fall through to content recovery
                            logger.warning("%s: structured_response did not validate; recovering from content", agent_name)
                # 2/3) recover schema from the final AIMessage.content, or
                # (schema=None freetext) the react output IS the report.
                msgs = result.get("messages", []) or []
                content = getattr(msgs[-1], "content", "") if msgs else ""
                if content:
                    if schema is None:
                        return content  # freetext agent loop: react output is the report
                    return invoke_structured_or_freetext(
                        structured_llm, llm, [HumanMessage(content=content)],
                        render, agent_name, schema=schema,
                    )

        # 4) full v0.3 fallback. schema=None: plain llm.invoke(prompt) — the
        # original freetext path (e.g. risk specialists before v0.4 agent loop).
        if schema is None:
            resp = llm.invoke(full_prompt + "\n\n" + trigger)
            return getattr(resp, "content", str(resp))
        return invoke_structured_or_freetext(
            structured_llm, llm, [HumanMessage(content=full_prompt + "\n\n" + trigger)],
            render, agent_name, schema=schema,
        )

    return _invoke


def extract_market(ticker: str) -> str:
    """Coarse market label from the ticker suffix, for skill filtering.

    Used by ``build_analyst_loop_invoker`` to pick skills whose ``markets``
    frontmatter matches the listing market. US-listed (no suffix) and any
    unrecognised ticker fall back to ``US``.
    """
    t = (ticker or "").upper()
    if t.endswith(".HK"):
        return "HK"
    if t.endswith((".KS", ".KQ")):
        return "KR"
    if t.endswith((".SS", ".SZ")):
        return "CN"
    if t.endswith(".T"):
        return "JP"
    return "US"


def build_analyst_loop_invoker(
    *,
    llm: Any,
    cfg: dict,
    state: dict,
    analyst_key: str,
    tools: list,
    schema: type[BaseModel],
    render: Callable[[BaseModel], str],
    agent_name: str,
    system_message: str,
    instruction: str,
    skills: list | None = None,
    add_web_read: bool = True,
) -> str:
    """Shared v0.4 helper every analyst calls from its node's loop branch.

    Mounts the auto-selected skills (instrument + regime + market + the
    Orchestrator's explicit picks) and the dynamic ``request_skill`` tool,
    then delegates to ``build_analyst_react_invoker`` (which owns the
    react-agent build + full degrade chain). Returns the rendered report
    string. Caller passes its pre-fetched ``system_message`` (data already
    in the prompt) + the per-analyst ``tools`` list.
    """
    from tradingagents.agents.schemas import orchestrator_skills_for
    from tradingagents.agents.utils.skills import SkillLoader, SkillSelector
    from tradingagents.agents.utils.skills.request_tool import make_request_skill_tool

    skills_cfg = cfg.get("skills") or {}
    tools = list(tools)
    if skills_cfg.get("dynamic_request", True):
        tools = tools + [make_request_skill_tool(SkillLoader(cfg))]
    if add_web_read:
        # Browser: web_read fills data gaps (article / filing / data page full
        # text). Degrades gracefully (error string) if the browser isn't enabled.
        from tradingagents.agents.utils.browser_tools import web_read
        tools = tools + [web_read]
    # web_search (serper.dev API) is a universal data-failure fallback — any
    # analyst can search when its data tools can't get the info (a pending event
    # outcome, a real-time fact). Always added (HTTP API call, not a browser).
    from tradingagents.agents.utils.browser_tools import web_search
    tools = tools + [web_search]

    if skills is None and skills_cfg.get("enabled", True):
        loader = SkillLoader(cfg)
        selector = SkillSelector(loader, cfg)
        explicit = orchestrator_skills_for(state.get("orchestration_plan", ""), analyst_key)
        skills = selector.select(
            analyst_key,
            instrument_type=state.get("instrument_type", "equity"),
            regime_text=state.get("regime_report", ""),
            market=extract_market(state.get("company_of_interest", "")),
            explicit=explicit or None,
        )

    invoker = build_analyst_react_invoker(
        llm=llm,
        tools=tools,
        schema=schema,
        render=render,
        agent_name=agent_name,
        system_message=system_message,
        skills=skills,
        instruction=instruction,
        max_iterations=int((cfg.get("agent_loop") or {}).get("analyst_max_iterations", 5)),
    )
    return invoker()
