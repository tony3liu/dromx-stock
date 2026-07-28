"""News / macro analyst — pre-fetch + structured output.

Rewritten from tool-calling to the pre-fetch + structured pattern. The node
pre-fetches four context blocks (ticker news, global/macro news, FRED macro
indicators, and live prediction-market probabilities), then makes a single
structured LLM call returning a ``NewsReport``. No tool-calling loop, so the
analyst can run as a parallel fan-out node and emits machine-readable output.

Each fetcher degrades to a placeholder string on failure, so a missing macro
series or an empty news window never aborts the run.
"""

import logging
import re

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from dromx.agents.schemas import NewsReport, render_news_report
from dromx.core.agent_utils import (
    get_global_news,
    get_instrument_context_from_state,
    get_language_instruction,
    get_macro_indicators,
    get_market_context_from_state,
    get_news,
    get_overnight_transmission_from_state,
    get_prediction_markets,
    get_regime_context_from_state,
    get_source_freshness_discipline,
)
from dromx.core.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

logger = logging.getLogger(__name__)

# FRED series the macro block grounds its commentary in (label -> indicator key).
_MACRO_INDICATORS = [
    ("CPI", "cpi"),
    ("Core PCE", "core_pce"),
    ("Unemployment", "unemployment"),
    ("Fed Funds Rate", "fed_funds_rate"),
    ("10Y Treasury", "10y_treasury"),
    ("Yield Curve", "yield_curve"),
]


def _seven_days_back(trade_date: str) -> str:
    from datetime import datetime, timedelta

    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")


def _safe(fn, label: str) -> str:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — degrade, don't crash the pipeline
        logger.warning("News analyst: %s unavailable: %s", label, exc)
        return f"<{label} unavailable: {type(exc).__name__}>"


# Browser article-reading is gated + bounded: only the first few links are read
# (full-page reads are slow), and only when enable_browser is on.
_MAX_ARTICLES = 3
_LINK_RE = re.compile(r"^Link:\s*(https?://\S+)", re.MULTILINE)


def _extract_news_urls(news_block: str, limit: int = _MAX_ARTICLES) -> list[str]:
    """Pull the first ``limit`` distinct article URLs from a rendered news block.

    The news vendors render one ``Link: <url>`` line per article (google_news,
    eastmoney_news). Returns [] when none / not a string.
    """
    if not isinstance(news_block, str):
        return []
    seen: list[str] = []
    for m in _LINK_RE.finditer(news_block):
        url = m.group(1).strip()
        if url not in seen:
            seen.append(url)
        if len(seen) >= limit:
            break
    return seen


def _maybe_enrich_with_articles(news_block: str) -> str:
    """Append full article bodies to the news block when browser reading is on.

    Gated by config ``enable_browser`` (default off). Reads the top few article
    URLs via the headless browser and appends their text. Fully best-effort:
    any failure (browser missing, page error) is skipped, so the news block is
    at worst unchanged — never blocks the pipeline.
    """
    try:
        from dromx.dataflows.config import get_config

        if not get_config().get("enable_browser"):
            return news_block
    except Exception:  # noqa: BLE001
        return news_block

    urls = _extract_news_urls(news_block)
    if not urls:
        return news_block

    try:
        from dromx.browser import read_article
    except Exception:  # noqa: BLE001 — module import shouldn't ever block news
        return news_block

    bodies = []
    for url in urls:
        body = _safe(lambda u=url: read_article(u), f"article {url[:60]}")
        if body and not body.startswith("<"):  # skip "<... failed/unavailable>"
            bodies.append(f"URL: {url}\n{body}")
    if not bodies:
        return news_block
    return news_block + "\n\n### Full article bodies (browser-read)\n" + "\n\n---\n\n".join(bodies)


def create_news_analyst(llm):
    """Create the news-analyst node (pre-fetch + structured)."""
    structured_llm = bind_structured(llm, NewsReport, "News Analyst")

    def news_analyst_node(state):
        ticker = state["company_of_interest"]
        curr_date = state["trade_date"]
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        market_context = get_market_context_from_state(state)
        overnight_transmission = get_overnight_transmission_from_state(state)
        start_date = _seven_days_back(curr_date)

        news_block = _safe(lambda: get_news.func(ticker, start_date, curr_date), "ticker news")
        news_block = _maybe_enrich_with_articles(news_block)
        global_block = _safe(lambda: get_global_news.func(curr_date, 7, 10), "global news")
        macro_block = _safe(lambda: _fetch_macro(curr_date), "macro indicators")
        prediction_block = _safe(
            lambda: get_prediction_markets.func("Fed rate cut recession 2026", 8),
            "prediction markets",
        )

        system_message = _build_system_message(
            ticker=ticker,
            start_date=start_date,
            curr_date=curr_date,
            news_block=news_block,
            global_block=global_block,
            macro_block=macro_block,
            prediction_block=prediction_block,
            regime_context=regime_context,
            market_context=market_context,
            overnight_context=overnight_transmission,
        )

        # v0.4 agentic pipeline: agent loop with tools + skills, or v0.3 single call.
        from dromx.dataflows.config import get_config
        cfg = get_config()
        agent_cfg = cfg.get("agent_loop") or {}
        per_analyst = (agent_cfg.get("per_analyst") or {}).get("news", {}) or {}
        loop_enabled = (
            bool(agent_cfg.get("enabled", False))
            and bool(per_analyst.get("enabled", True))
        )

        if loop_enabled:
            report_text = _run_news_agent_loop(
                llm=llm, cfg=cfg, state=state, ticker=ticker, curr_date=curr_date,
                system_message=system_message,
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a news and macroeconomics analyst. Today's date is"
                        " {current_date}; treat it as 'now'. {instrument_context}\n{system_message}",
                    ),
                ]
            )
            prompt = prompt.partial(system_message=system_message)
            prompt = prompt.partial(current_date=curr_date)
            prompt = prompt.partial(instrument_context=instrument_context)
            formatted_messages = prompt.format_messages()
            report_text = invoke_structured_or_freetext(
                structured_llm, llm, formatted_messages, render_news_report, "News Analyst",
            )

        return {
            "messages": [AIMessage(content=report_text)],
            "news_report": report_text,
        }

    return news_analyst_node


def _extract_market(ticker: str) -> str:
    """Coarse market label from the ticker suffix, for skill filtering."""
    t = (ticker or "").upper()
    if t.endswith(".HK"):
        return "HK"
    if t.endswith((".KS", ".KQ")):
        return "KR"
    if t.endswith((".SS", ".SZ")):
        return "CN"
    if t.endswith(".T"):
        return "JP"
    return "US"  # default for US-listed (no suffix) and unrecognised


def _run_news_agent_loop(*, llm, cfg, state, ticker, curr_date, system_message):
    """v0.4 path: react agent with news tools + skills; falls back to v0.3 on any failure."""
    from dromx.agents.schemas import orchestrator_skills_for
    from dromx.core.agent_loop import build_analyst_react_invoker
    from dromx.skills import SkillLoader, SkillSelector
    from dromx.skills.request_tool import make_request_skill_tool

    # Tools the loop can call to verify / deepen claims not grounded in the
    # pre-fetched blocks. The pre-fetch stays (seeds the prompt) so the loop
    # doesn't waste turns re-fetching the baseline.
    from dromx.browser.tools import web_read, web_search
    tools = [
        get_news,
        get_global_news,
        get_macro_indicators,
        get_prediction_markets,
        web_read,  # news core: read article full text from the block's Link: lines
        web_search,  # search when get_news/get_global_news miss (e.g. CXMT pricing)
    ]
    skills_cfg = cfg.get("skills") or {}
    if skills_cfg.get("dynamic_request", True):
        tools = tools + [make_request_skill_tool(SkillLoader(cfg))]

    skills: list = []
    if skills_cfg.get("enabled", True):
        loader = SkillLoader(cfg)
        selector = SkillSelector(loader, cfg)
        explicit = orchestrator_skills_for(state.get("orchestration_plan", ""), "news")
        skills = selector.select(
            "news",
            instrument_type=state.get("instrument_type", "equity"),
            regime_text=state.get("regime_report", ""),
            market=_extract_market(ticker),
            explicit=explicit or None,
        )

    invoker = build_analyst_react_invoker(
        llm=llm,
        tools=tools,
        schema=NewsReport,
        render=render_news_report,
        agent_name="News Analyst",
        system_message=system_message,
        skills=skills,
        instruction=(
            f"Produce the news & macro report for {ticker} as of {curr_date}. Use "
            f"the available tools to verify or deepen any claim you cannot ground "
            f"in the provided data, then fill the structured fields. Do not call a "
            f"tool more than once for the same data."
        ),
        max_iterations=int((cfg.get("agent_loop") or {}).get("analyst_max_iterations", 5)),
    )
    return invoker()


def _fetch_macro(curr_date: str) -> str:
    """Fetch a compact macro block from FRED across the standard series."""
    parts = []
    for label, key in _MACRO_INDICATORS:
        try:
            parts.append(f"### {label}\n{get_macro_indicators.func(key, curr_date, 90)}")
        except Exception as exc:  # noqa: BLE001 — one series shouldn't sink the block
            parts.append(f"### {label}\n<unavailable: {type(exc).__name__}>")
    return "\n\n".join(parts)


def _build_system_message(
    *,
    ticker: str,
    start_date: str,
    curr_date: str,
    news_block: str,
    global_block: str,
    macro_block: str,
    prediction_block: str,
    regime_context: str,
    market_context: str = "",
    overnight_context: str = "",
) -> str:
    """Assemble the news-analyst system message with pre-fetched data blocks."""
    return f"""Produce a news & macro report for {ticker} covering {start_date} to {curr_date}, based on the data already collected for you below.
{regime_context}{market_context}{overnight_context}
### Ticker-specific news
<start_of_news>
{news_block}
<end_of_news>

### Global / macro headlines
<start_of_global>
{global_block}
<end_of_global>

### Macro indicators (FRED)
<start_of_macro>
{macro_block}
<end_of_macro>

### Prediction markets (live market-implied probabilities)
<start_of_prediction>
{prediction_block}
<end_of_prediction>

## How to analyze

1. **Attribute the move first (if a cross-validation block is present above).** Before attributing any large move to a company-specific story, check the market/sector cross-validation: if the benchmark index and peers moved the same way, the move is largely MARKET / SECTOR driven — do NOT pin it on a single-name catalyst (e.g. an ADR dilution) unless the name moved materially MORE than its index and peers. Only the name-specific RESIDUAL is a company story.
2. **Company-specific developments** — what in the ticker news moves the thesis (earnings, guidance, products, litigation, M&A)? Distinguish events from opinion.
3. **Macro backdrop** — read the FRED series and global headlines: is the rate/inflation/growth environment a tailwind or headwind for this name and its sector?
4. **Forward catalysts** — use the prediction-market probabilities and the news calendar to flag upcoming events that could move the stock.
5. **Surprise vs the consensus, not the headline** — what moves a stock is not whether news is "good" but whether it beats or misses what the market already expects. For each material item, judge it against the consensus / whisper number: the same earnings print is bullish 2% above the whisper and bearish 2% below it. Where you can, state what the market is positioned for and which way the actual data point surprised relative to that bar.
6. **Flag game-changers** — separately from your directional read, scan for any event that materially changes the investment PREMISE: a capital raise / dilution, M&A, a regulatory action, a management change, a guidance reset, a covenant or default. These deserve a flag even when they do not change your direction, because a thesis can stay directionally intact while its premises shift underneath it. Set game_changer=True and name the event in game_changer_note. Do NOT flag ordinary price moves, routine coverage, or sentiment swings.
7. **Synthesize** into a directional read and weight it per the regime guidance above.

Fill the structured fields: direction, confidence, scenarios, game_changer (+ game_changer_note if true), macro_backdrop, key_evidence (cite specific headlines/figures), risks, and a full narrative ending with a markdown table of key headlines and their likely impact.

For `scenarios`, give a 3-leg probability distribution (bear / base / bull) tied to the catalysts and the surprise-vs-consensus read above: each leg's probability (summing to ≈1), its signed expected % move, and the concrete event/data point (e.g. a print beating or missing the whisper number) that would trigger it.
{get_source_freshness_discipline()}
{get_language_instruction()}"""
