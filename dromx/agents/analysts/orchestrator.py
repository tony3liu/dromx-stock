"""Orchestrator — dynamic analyst + skill selection (v0.4 PRD §4.1).

Sits between the Regime Analyst and the parallel analysts. Reads the regime
classification + instrument type + historical scorecard weights + past
lessons, and decides for THIS run: which analysts, at what depth, with which
skills mounted. Writes the rendered plan to ``state["orchestration_plan"]``;
each analyst node parses it to decide whether to run or noop out.

Single structured LLM call — the orchestrator itself needs no tools (PRD §4.1).
Falls back to free-text via ``invoke_structured_or_freetext``. When
``force_all_analysts=true`` (or ``auto_select_analysts=false``) the LLM is
skipped and a deterministic full plan is written. When ``agent_loop.enabled``
is false the node is not wired in at all (setup.py v0.3 branch).
"""

from __future__ import annotations

from dromx.agents.schemas import (
    OrchestrationPlan,
    render_orchestration_plan,
)
from dromx.core.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)
from dromx.core.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

_ALL_KEYS = ["market", "sentiment", "news", "fundamentals", "industry"]


def _force_all_plan() -> OrchestrationPlan:
    """Deterministic full-panel plan used when auto-select is off."""
    return OrchestrationPlan(
        analysts=[
            {"key": k, "depth": "standard", "priority": i + 1, "skills": []}
            for i, k in enumerate(_ALL_KEYS)
        ],
        skip_research_layer=False,
        reasoning="force_all_analysts=true — running the full analyst panel.",
    )


def create_orchestrator(llm):
    """Create the Orchestrator node (single structured call, no agent loop)."""
    structured_llm = bind_structured(llm, OrchestrationPlan, "Orchestrator")

    def orchestrator_node(state):
        from dromx.dataflows.config import get_config
        from dromx.core.signal_tracker import (
            AnalystScorecard,
            extract_trend,
        )

        cfg = get_config()
        orch_cfg = cfg.get("orchestration") or {}

        # force_all / auto-select off → deterministic full plan, no LLM call
        if orch_cfg.get("force_all_analysts") or not orch_cfg.get("auto_select_analysts", True):
            return {"orchestration_plan": render_orchestration_plan(_force_all_plan())}

        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        instrument_type = state.get("instrument_type", "equity")
        regime_report = state.get("regime_report", "")
        past_context = state.get("past_context", "")

        # Scorecard context: which lenses have been right/wrong in this regime.
        scorecard_block = ""
        try:
            sc = AnalystScorecard(cfg)
            trend = extract_trend(regime_report)
            summary = sc.summary(trend)
            weights = sc.accuracy_weights(trend)
            if summary:
                scorecard_block += f"\n## Historical analyst hit-rates in this regime\n{summary}\n"
            weak = [k for k, v in (weights or {}).items() if v <= 0.7]
            if weak:
                scorecard_block += (
                    f"Lenses with a weak hit-rate here: {', '.join(weak)} — "
                    f"deprioritise or skip only if their lens is also inapplicable.\n"
                )
        except Exception:  # noqa: BLE001 — scorecard is best-effort, never block
            scorecard_block = ""

        past_block = f"\n## Lessons from prior runs\n{past_context}\n" if past_context else ""

        # Available skills so the LLM only lists real names, not invented ones.
        available_skills_block = ""
        try:
            from dromx.skills import SkillLoader
            loader = SkillLoader(cfg)
            by_analyst = {
                ak: [s.name for s in ss] for ak, ss in loader.load_all().items() if ss
            }
            if by_analyst:
                lines = [f"  - {ak}: {', '.join(names)}" for ak, names in by_analyst.items()]
                available_skills_block = (
                    "\n## Available skills (only list names from this set)\n"
                    + "\n".join(lines) + "\n"
                )
        except Exception:  # noqa: BLE001 — skills are best-effort, never block
            available_skills_block = ""

        prompt = f"""You are the Orchestrator. Decide, for THIS run, which analysts to run, at what depth, and with which skills mounted.

{instrument_context}
{regime_context}
## Instrument type
{instrument_type}

## Regime report
{regime_report}
{scorecard_block}{past_block}{available_skills_block}
## Your job
Pick the analysts that add incremental value for THIS instrument + regime:
- **Leveraged / inverse ETF** → skip ``fundamentals`` (its 'fundamentals' are the underlying index path, not a company — the ``leveraged-etf-decay`` skill under market covers the right framework).
- **Crisis / high-volatility regime** → MUST include ``market`` and ``news`` (price action + catalysts move a crisis tape).
- **Calm / clearly-trending regime** → you may run a thinner panel (e.g. market + fundamentals for a slow-grind value name).
- Do NOT skip an analyst just for a weak historical hit-rate — only skip when its lens is genuinely inapplicable to this instrument (e.g. fundamentals for an ETF).
- ``skills``: list skill names to mount for each analyst, ONLY from the "Available skills" set above (overrides auto-selection). Leave empty to let the SkillSelector auto-pick from the run context. Do NOT invent skill names not in that set.

Output the OrchestrationPlan: analysts (key/depth/priority/skills), skip_research_layer (True only when the setup is clear enough to skip Growth/Risk and go straight to PM), and a one-line reasoning.
{get_language_instruction()}"""

        plan_text = invoke_structured_or_freetext(
            structured_llm, llm, prompt, render_orchestration_plan,
            "Orchestrator", schema=OrchestrationPlan,
        )
        return {"orchestration_plan": plan_text}

    return orchestrator_node
