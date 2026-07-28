"""Fundamentals analyst — pre-fetch + structured output.

Rewritten from tool-calling to the pre-fetch + structured pattern. The node
pre-fetches the fundamentals overview plus the three financial statements
(income, balance sheet, cash flow), then makes a single structured LLM call
returning a ``FundamentalsReport``. No tool-calling loop, so the analyst runs as
a parallel fan-out node and emits machine-readable output.

Each fetcher degrades to a placeholder string on failure, so a vendor with no
coverage for a given market (e.g. SEC for a HK name) never aborts the run — the
router's NO_DATA sentinel or the placeholder flows into the prompt and the model
is told to flag the gap rather than fabricate numbers.
"""

import logging

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from dromx.agents.schemas import FundamentalsReport, render_fundamentals_report
from dromx.core.agent_utils import (
    get_balance_sheet,
    get_cashflow,
    get_framework_note_from_state,
    get_fundamentals,
    get_income_statement,
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
    get_source_freshness_discipline,
)
from dromx.core.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

logger = logging.getLogger(__name__)


def _safe(fn, label: str) -> str:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — degrade, don't crash the pipeline
        logger.warning("Fundamentals analyst: %s unavailable: %s", label, exc)
        return f"<{label} unavailable: {type(exc).__name__}>"


def _build_peer_block(ticker: str, curr_date: str) -> str:
    """Pre-fetch each peer's fundamentals overview for relative-valuation context.

    Returns an empty string when no peers are configured (the default). Peers
    that fail to fetch are skipped — peer context is best-effort and never
    aborts the run.
    """
    from dromx.dataflows.config import get_config

    peers = [
        p for p in (get_config().get("peer_tickers") or [])
        if p and p.upper() != ticker.upper()
    ]
    if not peers:
        return ""

    blocks = []
    for peer in peers:
        overview = _safe(lambda p=peer: get_fundamentals.func(p, curr_date), f"peer overview {peer}")
        blocks.append(f"### Peer — {peer}\n<start_of_peer>\n{overview}\n<end_of_peer>")
    return (
        "\n### Peer overviews (for RELATIVE valuation — is this name cheap or "
        "expensive vs peers?)\n" + "\n".join(blocks) + "\n"
    )


def create_fundamentals_analyst(llm):
    """Create the fundamentals-analyst node (pre-fetch + structured)."""
    structured_llm = bind_structured(llm, FundamentalsReport, "Fundamentals Analyst")

    def fundamentals_analyst_node(state):
        ticker = state["company_of_interest"]
        curr_date = state["trade_date"]
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        framework_note = get_framework_note_from_state(state)

        overview = _safe(lambda: get_fundamentals.func(ticker, curr_date), "fundamentals overview")
        income = _safe(lambda: get_income_statement.func(ticker, "quarterly", curr_date), "income statement")
        balance = _safe(lambda: get_balance_sheet.func(ticker, "quarterly", curr_date), "balance sheet")
        cashflow = _safe(lambda: get_cashflow.func(ticker, "quarterly", curr_date), "cash flow statement")
        peer_block = _build_peer_block(ticker, curr_date)

        system_message = _build_system_message(
            ticker=ticker,
            curr_date=curr_date,
            overview=overview,
            income=income,
            balance=balance,
            cashflow=cashflow,
            regime_context=regime_context,
            peer_block=peer_block,
        )

        from dromx.dataflows.config import get_config
        cfg = get_config()
        agent_cfg = cfg.get("agent_loop") or {}
        per_analyst = (agent_cfg.get("per_analyst") or {}).get("fundamentals", {}) or {}
        loop_enabled = (
            bool(agent_cfg.get("enabled", False))
            and bool(per_analyst.get("enabled", True))
        )

        if loop_enabled:
            from dromx.core.agent_loop import build_analyst_loop_invoker
            report_text = build_analyst_loop_invoker(
                llm=llm, cfg=cfg, state=state, analyst_key="fundamentals",
                tools=[get_fundamentals, get_income_statement, get_balance_sheet, get_cashflow],
                add_web_read=False,  # fundamentals doesn't read news/article full text
                schema=FundamentalsReport, render=render_fundamentals_report,
                agent_name="Fundamentals Analyst", system_message=system_message,
                instruction=(
                    f"Produce the fundamental analysis report for {ticker} as of {curr_date}. "
                    f"Use the available tools to verify or deepen any figure not grounded in the "
                    f"provided statements, then fill the structured fields. Do not call a tool "
                    f"more than once for the same data."
                ),
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a fundamentals analyst. Today's date is {current_date};"
                        " treat it as 'now'. {instrument_context}\n{system_message}",
                    ),
                ]
            )
            prompt = prompt.partial(system_message=system_message)
            prompt = prompt.partial(current_date=curr_date)
            prompt = prompt.partial(instrument_context=instrument_context)
            formatted_messages = prompt.format_messages()
            report_text = invoke_structured_or_freetext(
                structured_llm, llm, formatted_messages, render_fundamentals_report,
                "Fundamentals Analyst", schema=FundamentalsReport,
            )

        return {
            "messages": [AIMessage(content=report_text)],
            "fundamentals_report": report_text,
        }

    return fundamentals_analyst_node


def _build_system_message(
    *,
    ticker: str,
    curr_date: str,
    overview: str,
    income: str,
    balance: str,
    cashflow: str,
    regime_context: str,
    peer_block: str = "",
    framework_note: str = "",
) -> str:
    """Assemble the fundamentals-analyst system message with pre-fetched data blocks."""
    return f"""Produce a fundamental analysis report for {ticker} as of {curr_date}, based on the financial data already collected for you below. The statements are point-in-time filtered to on/before {curr_date} (no look-ahead). If a block says "unavailable" or "NO_DATA_AVAILABLE", say so explicitly and do NOT fabricate the missing figures.
{framework_note}{regime_context}
### Fundamentals overview (key indicators)
<start_of_overview>
{overview}
<end_of_overview>

### Income statement
<start_of_income>
{income}
<end_of_income>

### Balance sheet
<start_of_balance>
{balance}
<end_of_balance>

### Cash flow statement
<start_of_cashflow>
{cashflow}
<end_of_cashflow>
{peer_block}
## How to analyze

1. **Profitability & growth** — revenue and earnings trend across the periods shown: accelerating or decelerating? Margins (gross/operating/net) expanding or compressing?
2. **Cash & balance sheet** — operating cash flow vs net income (earnings quality), capex intensity, leverage (debt vs equity, current ratio), liquidity.
3. **Valuation framing** — given the growth/margin/return profile, does the name look rich, fair, or cheap? Use PE / margins / ROE from the overview where present; be explicit about which framework you apply.
4. **Expectation gap (this is where the alpha is)** — do not stop at "is this a good company?". Work backwards from the current valuation: what growth rate and margin trajectory is the market *implying* at this PE / EV-EBITDA? Then state your own estimate. The gap between the market-implied expectation and your estimate — not the absolute quality — is the actual edge. A great company can be a poor investment if expectations are already higher than you can justify, and a mediocre one can be a buy if expectations are too low.
5. **Trend over snapshot** — judge the trajectory across periods (edge-of-improvement vs deterioration), not just the latest number.
6. **Synthesize** into a directional read and weight it per the regime guidance above.
{"7. **Relative valuation.** If peer overviews are provided, compare this name's valuation and growth/margin profile against its peers and state whether it looks cheap or expensive relative to them." if peer_block else ""}

Fill the structured fields: direction, confidence, scenarios, valuation_view, key_evidence (cite actual figures), risks, and a full narrative ending with a markdown table of key financial metrics.

For `scenarios`, give a 3-leg probability distribution (bear / base / bull) anchored to the expectation gap above: each leg's probability (summing to ≈1), its signed expected % move, and the concrete fundamental trigger (e.g. growth re-accelerating vs decelerating, a margin inflection) that would put it in play. The leg probabilities should reflect how far the market-implied expectation sits from your own estimate.
{get_source_freshness_discipline()}
{get_language_instruction()}"""
