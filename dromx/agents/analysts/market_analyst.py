"""Market (technical) analyst — pre-fetch + structured output.

Rewritten from the old tool-calling design (where the LLM picked up to 8
indicators and called get_stock_data / get_indicators in a loop) to the
pre-fetch + structured pattern the Sentiment Analyst established. The node now:

  1. Pre-fetches the deterministic verified market snapshot — the same
     ground-truth OHLCV + 11-indicator block the old prompt told the model to
     trust — plus the recent OHLCV CSV for context.
  2. Makes a single structured LLM call returning a ``MarketReport``.

This removes the tool-calling loop, which (a) lets the analyst run as a parallel
fan-out node without contending on the shared ``messages`` channel, (b) makes
the output machine-readable (direction + confidence + evidence) for the debate
layer, and (c) follows the review's §5.1 advice — give the model a fixed,
computed indicator set to interpret rather than having it role-play indicator
selection.
"""

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from dromx.agents.schemas import MarketReport, render_market_report
from dromx.core.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_pattern_discovery_from_state,
    get_foreign_flow_from_state,
    get_indicators,
    get_regime_context_from_state,
    get_source_freshness_discipline,
    get_stock_data,
    get_verified_market_snapshot,
)
from dromx.core.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def _seven_days_back(trade_date: str) -> str:
    from datetime import datetime, timedelta

    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")


def create_market_analyst(llm):
    """Create the market-analyst node (pre-fetch + structured)."""
    structured_llm = bind_structured(llm, MarketReport, "Market Analyst")

    def market_analyst_node(state):
        ticker = state["company_of_interest"]
        curr_date = state["trade_date"]
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        pattern_block = get_pattern_discovery_from_state(state)
        foreign_block = get_foreign_flow_from_state(state)

        # Pre-fetch ground-truth data. All four fetchers degrade to a
        # placeholder string on failure (see _safe_fetch) so the node never
        # aborts the run; they are independent network calls, so run in parallel.
        from dromx.graph.prefetch import parallel_prefetch
        blocks = parallel_prefetch(
            {
                "snapshot": lambda: _safe_fetch(
                    lambda: get_verified_market_snapshot.func(ticker, curr_date, 30),
                    "verified snapshot",
                ),
                "price_csv": lambda: _safe_fetch(
                    lambda: get_stock_data.func(ticker, _seven_days_back(curr_date), curr_date),
                    "price history",
                ),
                "peer_block": lambda: _build_peer_block(ticker, curr_date),
                "etf_block": lambda: _build_etf_block(ticker, curr_date, llm=llm),
            },
            max_workers=4,
            label="market prefetch",
        )
        snapshot = blocks["snapshot"]
        price_csv = blocks["price_csv"]
        peer_block = blocks["peer_block"]
        etf_block = blocks["etf_block"]

        system_message = _build_system_message(
            ticker=ticker,
            curr_date=curr_date,
            snapshot=snapshot,
            price_csv=price_csv,
            regime_context=regime_context,
            peer_block=peer_block,
            etf_block=etf_block,
            pattern_block=pattern_block,
            foreign_block=foreign_block,
        )

        from dromx.dataflows.config import get_config
        cfg = get_config()
        agent_cfg = cfg.get("agent_loop") or {}
        per_analyst = (agent_cfg.get("per_analyst") or {}).get("market", {}) or {}
        loop_enabled = (
            bool(agent_cfg.get("enabled", False))
            and bool(per_analyst.get("enabled", True))
        )

        if loop_enabled:
            from dromx.core.agent_loop import build_analyst_loop_invoker
            report_text = build_analyst_loop_invoker(
                llm=llm, cfg=cfg, state=state, analyst_key="market",
                tools=[get_stock_data, get_indicators, get_verified_market_snapshot],
                schema=MarketReport, render=render_market_report,
                agent_name="Market Analyst", system_message=system_message,
                instruction=(
                    f"Produce the technical analysis report for {ticker} as of {curr_date}. "
                    f"Use the available tools to verify or deepen any claim you cannot ground "
                    f"in the provided data, then fill the structured fields. Do not call a "
                    f"tool more than once for the same data."
                ),
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a technical market analyst. Today's date is {current_date};"
                        " treat it as 'now'. {instrument_context}\n{system_message}",
                    ),
                ]
            )
            prompt = prompt.partial(system_message=system_message)
            prompt = prompt.partial(current_date=curr_date)
            prompt = prompt.partial(instrument_context=instrument_context)
            formatted_messages = prompt.format_messages()
            report_text = invoke_structured_or_freetext(
                structured_llm, llm, formatted_messages, render_market_report,
                "Market Analyst", schema=MarketReport,
            )

        return {
            "messages": [AIMessage(content=report_text)],
            "market_report": report_text,
        }

    return market_analyst_node


def _safe_fetch(fn, label: str) -> str:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — degrade, don't crash the pipeline
        return f"<{label} unavailable: {type(exc).__name__}: {exc}>"


def _build_etf_block(ticker: str, curr_date: str, llm=None) -> str:
    """ETF-passthrough block, auto-detected for ANY ticker (zero hardcoded map).

    ``resolve_etf_structure`` reads the fund name + yfinance fields and lets the
    LLM decide whether this is an ETF and what it tracks (leverage, underlying,
    currencies). Config ``etf_underlying_map`` is an OPTIONAL manual override only.
    Non-ETFs yield '' so single-stock analysis is unchanged. Best-effort.
    """
    from dromx.dataflows.config import get_config
    from dromx.dataflows.etf_data import (
        build_etf_passthrough,
        resolve_etf_structure,
    )

    etf_map = get_config().get("etf_underlying_map") or {}
    override = etf_map.get(ticker.upper()) or etf_map.get(ticker) or {}
    try:
        structure = resolve_etf_structure(ticker, curr_date, llm=llm)
        return build_etf_passthrough(
            ticker, curr_date,
            structure=structure,
            underlying=override.get("underlying"),
            underlying_currency=override.get("currency"),
        )
    except Exception:  # noqa: BLE001 — ETF context is best-effort, never abort
        return ""


def _build_peer_block(ticker: str, curr_date: str) -> str:
    """Pre-fetch each peer's verified snapshot for relative-strength context.

    Returns an empty string when no peers are configured (the default), so the
    prompt is unchanged for single-name analysis. Peers that fail to fetch are
    skipped — peer context is best-effort and must never abort the run.
    """
    from dromx.dataflows.config import get_config
    from dromx.graph.prefetch import parallel_prefetch

    peers = [
        p for p in (get_config().get("peer_tickers") or [])
        if p and p.upper() != ticker.upper()
    ]
    if not peers:
        return ""

    # Peer snapshots are independent network calls — fetch in parallel and
    # re-assemble in configured peer order.
    snaps = parallel_prefetch(
        {
            peer: (lambda p=peer: _safe_fetch(
                lambda: get_verified_market_snapshot.func(p, curr_date, 30),
                f"peer snapshot {p}",
            ))
            for peer in peers
        },
        max_workers=4,
        label="market peer snapshots",
    )
    blocks = [
        f"### Peer — {peer}\n<start_of_peer>\n{snaps[peer]}\n<end_of_peer>"
        for peer in peers
    ]
    return (
        "\n## Peer snapshots (for RELATIVE strength — is this name leading or "
        "lagging its peers?)\n" + "\n".join(blocks) + "\n"
    )


def _build_system_message(
    *,
    ticker: str,
    curr_date: str,
    snapshot: str,
    price_csv: str,
    regime_context: str,
    peer_block: str = "",
    etf_block: str = "",
    pattern_block: str = "",
    foreign_block: str = "",
) -> str:
    """Assemble the market-analyst system message with pre-fetched data blocks."""
    return f"""Produce a technical analysis report for {ticker} as of {curr_date}, based on the verified market data already collected for you below.
{regime_context}
## Verified market snapshot (ground truth — treat these numbers as authoritative)
The snapshot is the latest OHLCV row on/before {curr_date} plus a fixed set of computed indicators (10 EMA, 50/200 SMA, RSI, Bollinger bands, MACD line/signal/histogram, ATR). Base every exact numeric claim on these values; do not invent levels, bounces, or percentage moves the data doesn't support.

**Numeric discipline (the report must be internally consistent):**
- The CURRENT PRICE is the snapshot's latest close — use that ONE number everywhere in the report; never quote two or three different "current" prices.
- Any percentage move (e.g. "+128% over 30 days") MUST cite its start date and start price from the price history, and the arithmetic must check out. If you cannot ground both endpoints in the provided data, do not state the figure.
- When you mention a high/low or a "from X to Y" move, the X and Y must come from the snapshot or the price CSV — not from memory.

<start_of_snapshot>
{snapshot}
<end_of_snapshot>

## Recent price history (CSV, for trend/structure context)
<start_of_prices>
{price_csv}
<end_of_prices>
{peer_block}{etf_block}{pattern_block}{foreign_block}
## How to analyze

1. **Trend** — read the moving-average stack (price vs 10 EMA / 50 SMA / 200 SMA) and their slopes. Golden/death-cross structure, dynamic support/resistance.
2. **Momentum** — RSI (overbought/oversold vs 70/30, divergences) and MACD (line vs signal, histogram direction).
3. **Volatility** — ATR level and Bollinger band width: are moves expanding or compressing? Set realistic stop distances from ATR.
4. **Levels** — identify support/resistance grounded in the snapshot's recent highs/lows, not invented round numbers.
5. **Is it already priced in?** — a trend is only tradable if it has room left. Judge whether this move is already crowded/extended (stretched RSI, price far above the MA stack, a parabolic late-stage run) versus early with room to run. The edge is the gap between what the tape has already discounted and what is left — a strong-but-exhausted uptrend can be a worse entry than a basing one.
6. **Synthesize** into a directional read and weight it per the regime guidance above.
7. **Separate the time horizons.** Give a SHORT-term read (≈1–5 trading days: near-term momentum, RSI extremes, latest candles) and a MEDIUM-term read (≈1–3 months: the moving-average stack and broader trend). These can legitimately disagree — e.g. short-term overbought inside a medium-term uptrend — and the trader needs both.
{"8. **Relative strength.** If peer snapshots are provided, note whether this name is leading or lagging its peers (recent returns, momentum) and let that sharpen the directional read." if peer_block else ""}
{"9. **Look through the ETF wrapper.** If an ETF-passthrough block is provided, fold its tracking error and FX exposure into your read: a wide tracking error or an unhedged currency leg means the headline index call is NOT the whole story — say what the holder is really exposed to." if etf_block else ""}
{"10. **Forensics reasoning (if a pattern-discovery block is provided).** The block is COMPUTED EVIDENCE — anomaly days, the pivot-vs-anchor deviation competition, an algorithmic-precision verdict, and an evolution read — NOT your speculation. Reason FROM it: which anchor won and why (quant / retail-stop / option-gamma multi-layer), what motive could drive a pattern at that anchor, and what the evolution (precision trend + break direction) points to. The block is direction-neutral — a Low-pivot win is a short-hunt read, a High-pivot win is a breakout/squeeze read, both is two-way. MARK evidence (the block's numbers) vs speculation (your reasoning) explicitly, like a case report; never present speculation as fact, and do not invent deviation numbers the block does not contain." if pattern_block else ""}

Fill the structured fields: direction (your overall read), direction_short_term, direction_medium_term, confidence, scenarios, indicator_readout, key_evidence (cite actual values), risks, and a full narrative ending with a markdown indicator table.

For `scenarios`, give a 3-leg probability distribution (bear / base / bull) over your medium-term horizon: each leg's probability (summing to ≈1), its signed expected % move, and the concrete trigger that would put it in play. A point direction says "which way"; the distribution says "how much, how likely, and what would change it" — that is what the desk sizes to.
{get_source_freshness_discipline()}
{get_language_instruction()}"""
