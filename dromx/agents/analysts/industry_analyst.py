"""Industry & Supply-Chain analyst — the missing sector lens (pre-fetch + structured).

The four base analysts all look at the COMPANY (price, statements, sentiment,
news) — none asks "what is happening to the INDUSTRY?". A senior analyst's edge
is understanding the sector's cycle position, competitive structure, supply-chain
dependencies, and disruption risk: whether a moat can persist and what would
make it crack, not just whether the PE is high or low.

Hard sector data (market share, capex trackers, supply-chain databases) is not
available from the project's free vendors, so this analyst pre-fetches what it
CAN — sector/global news, peer financials, and the name's own classification —
and combines it with the model's domain knowledge, REQUIRING every claim to be
tagged [data] or [knowledge] so the desk can weight verifiable facts above model
recall. Same pre-fetch + single structured call pattern as the news analyst (no
tool loop, so it runs as a parallel fan-out analyst).
"""

import logging

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from dromx.agents.schemas import IndustryReport, render_industry_report
from dromx.core.agent_utils import (
    get_fundamentals,
    get_global_news,
    get_instrument_context_from_state,
    get_language_instruction,
    get_news,
    get_regime_context_from_state,
    get_source_freshness_discipline,
    resolve_instrument_identity,
)
from dromx.core.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

logger = logging.getLogger(__name__)


def _seven_days_back(trade_date: str) -> str:
    from datetime import datetime, timedelta

    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")


def _safe(fn, label: str) -> str:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — degrade, don't crash the pipeline
        logger.warning("Industry analyst: %s unavailable: %s", label, exc)
        return f"<{label} unavailable: {type(exc).__name__}>"


def _identity_block(ticker: str) -> str:
    """The name's sector/industry classification, the anchor for the sector read."""
    try:
        ident = resolve_instrument_identity(ticker) or {}
    except Exception:  # noqa: BLE001
        ident = {}
    sector = ident.get("sector") or "Unknown"
    industry = ident.get("industry") or "Unknown"
    name = ident.get("company_name") or ident.get("name") or ticker
    return f"Name: {name}\nSector: {sector}\nIndustry: {industry}"


def _peer_block(ticker: str, curr_date: str) -> str:
    """Peer fundamentals for relative competitive positioning (best-effort)."""
    from dromx.dataflows.config import get_config

    peers = [
        p for p in (get_config().get("peer_tickers") or [])
        if p and p.upper() != ticker.upper()
    ]
    if not peers:
        return "<no peers configured — judge competitive structure from knowledge, tagged [knowledge]>"
    blocks = []
    for peer in peers:
        overview = _safe(lambda p=peer: get_fundamentals.func(p, curr_date), f"peer {peer}")
        blocks.append(f"### Peer — {peer}\n{overview}")
    return "\n".join(blocks)


def create_industry_analyst(llm):
    """Create the industry-analyst node (pre-fetch + structured)."""
    structured_llm = bind_structured(llm, IndustryReport, "Industry Analyst")

    def industry_analyst_node(state):
        ticker = state["company_of_interest"]
        curr_date = state["trade_date"]
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        start_date = _seven_days_back(curr_date)

        identity_block = _identity_block(ticker)
        # The three pre-fetches are independent network calls (each degrades
        # to a placeholder via _safe), so run them in parallel.
        from dromx.graph.prefetch import parallel_prefetch
        blocks = parallel_prefetch(
            {
                "ticker_news": lambda: _safe(lambda: get_news.func(ticker, start_date, curr_date), "ticker news"),
                "global_news": lambda: _safe(lambda: get_global_news.func(curr_date, 7, 10), "global/sector news"),
                "peer_block": lambda: _peer_block(ticker, curr_date),
            },
            max_workers=3,
            label="industry prefetch",
        )
        ticker_news = blocks["ticker_news"]
        global_news = blocks["global_news"]
        peer_block = blocks["peer_block"]

        system_message = f"""Produce an INDUSTRY & SUPPLY-CHAIN report for {ticker} as of {curr_date}. The rest of the team analyses the company; your job is the sector around it: cycle position, competitive structure, supply-chain dependencies, and disruption risk.
{regime_context}
## The name's classification (anchor your sector read here)
{identity_block}

## Ticker-specific news ({start_date} → {curr_date})
<start_of_news>
{ticker_news}
<end_of_news>

## Global / macro headlines (scan for sector-relevant items)
<start_of_global>
{global_news}
<end_of_global>

## Peer financials (for relative competitive positioning)
<start_of_peers>
{peer_block}
<end_of_peers>

## How to analyze

1. **Industry cycle.** Where is this industry — Expansion / Peak / Contraction / Trough? Judge from demand, capex behaviour, and pricing power.
2. **Competitive structure & moat.** Is THIS name's position widening, stable, or narrowing — structurally (share, technology lead, switching costs), not just cyclically? Use the peer financials where they help. When peer financials are available, ALSO fill `competition_matrix`: a markdown table with one row per competitor (this name + each peer) and columns for the dimensions that decide the race (e.g. product/tech status, market share, positioning, key metric). Tag each cell [data]/[knowledge]. Leave it empty only when no peers are configured or there is no clear competitive set.
3. **Supply chain.** Map the key upstream (suppliers, inputs, capacity bottlenecks) and downstream (customer concentration) dependencies. Name the single one that could make or break the thesis.
4. **Disruption.** The most credible technology / substitution / regulatory force that could erode the position, and how near it is.
5. **Regime interaction.** How the current market regime interacts with where the industry sits in its cycle.

CRITICAL — honesty about sources: hard sector data (market share, capex, supply-chain detail) is largely NOT in the fetched data. You may use your own domain knowledge, but you MUST tag every claim: **[data]** when it comes from the news / peer financials / classification above, **[knowledge]** when it comes from your training. Never present model recall as if it were fetched data. Where you are uncertain, lower the confidence and say so.

Fill the structured fields: direction, confidence, scenarios, industry_phase, competitive_moat, key_dependency, disruption_risk, competition_matrix (when peers exist), key_evidence (each tagged [data]/[knowledge]), risks, narrative.
{get_source_freshness_discipline()}
{get_language_instruction()}"""

        from dromx.dataflows.config import get_config
        cfg = get_config()
        agent_cfg = cfg.get("agent_loop") or {}
        per_analyst = (agent_cfg.get("per_analyst") or {}).get("industry", {}) or {}
        loop_enabled = (
            bool(agent_cfg.get("enabled", False))
            and bool(per_analyst.get("enabled", True))
        )

        if loop_enabled:
            from dromx.core.agent_loop import build_analyst_loop_invoker
            report_text = build_analyst_loop_invoker(
                llm=llm, cfg=cfg, state=state, analyst_key="industry",
                tools=[get_news, get_global_news, get_fundamentals],
                schema=IndustryReport, render=render_industry_report,
                agent_name="Industry Analyst", system_message=system_message,
                instruction=(
                    f"Produce the industry & supply-chain report for {ticker} as of {curr_date}. "
                    f"Use the available tools to verify or deepen any claim, then fill the "
                    f"structured fields. Tag every claim [data]/[knowledge]. Do not call a "
                    f"tool more than once for the same data."
                ),
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are an industry and supply-chain analyst. Today's date is"
                        " {current_date}; treat it as 'now'. {instrument_context}\n{system_message}",
                    ),
                ]
            )
            prompt = prompt.partial(system_message=system_message)
            prompt = prompt.partial(current_date=curr_date)
            prompt = prompt.partial(instrument_context=instrument_context)
            formatted_messages = prompt.format_messages()
            report_text = invoke_structured_or_freetext(
                structured_llm, llm, formatted_messages, render_industry_report,
                "Industry Analyst", schema=IndustryReport,
            )

        return {
            "messages": [AIMessage(content=report_text)],
            "industry_report": report_text,
        }

    return industry_analyst_node
