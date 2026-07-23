"""Portfolio Manager: synthesises the risk-analyst debate into the final decision.

Uses LangChain's ``with_structured_output`` so the LLM produces a typed
``PortfolioDecision`` directly, in a single call.  The result is rendered
back to markdown for storage in ``final_trade_decision`` so memory log,
CLI display, and saved reports continue to consume the same shape they do
today.  When a provider does not expose structured output, the agent falls
back gracefully to free-text generation.
"""

from __future__ import annotations

from langchain_core.tools import tool

from dromx.agents.schemas import PortfolioDecision, render_pm_decision
from dromx.agents.utils.agent_utils import (
    get_fundamentals,
    get_framework_note_from_state,
    get_instrument_context_from_state,
    get_language_instruction,
    get_market_context_from_state,
    get_news,
    get_numeric_discipline,
    get_regime_context_from_state,
    get_source_freshness_discipline,
    get_stock_data,
)
from dromx.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


@tool
def position_simulate(
    shares: float,
    cost_basis: float,
    current_price: float,
    target_price: float = 0.0,
    stop_price: float = 0.0,
) -> str:
    """Simulate an EXISTING position's P&L and trim sensitivity. Pass the
    user's shares + cost basis (from the position context) + the current
    price (from the snapshot), plus optional target / stop. Returns unrealized
    P&L, P&L at target/stop, risk-to-stop, and P&L locked per 1% trimmed —
    the numbers to decide trim size / stop for a holding (not a flat entry).
    Does NOT re-derive the sizing anchor (that's the risk-consensus Kelly
    figure) — use this for the P&L math, then size the trim from the anchor.
    """
    if shares <= 0 or cost_basis <= 0 or current_price <= 0:
        return "invalid: shares, cost_basis, current_price must be > 0"
    unrealized = (current_price - cost_basis) * shares
    unrealized_pct = (current_price / cost_basis - 1.0) * 100.0
    lines = [
        f"## Position simulate (shares={shares:g}, cost={cost_basis:g}, current={current_price:g})",
        f"- **Unrealized P&L:** {unrealized:+,.2f} ({unrealized_pct:+.1f}%)",
        f"- **Per 1% trimmed at current:** {unrealized / 100.0:+,.2f} P&L locked",
    ]
    if target_price > 0:
        tgt_pnl = (target_price - cost_basis) * shares
        lines.append(
            f"- **P&L if price → target {target_price:g}:** {tgt_pnl:+,.2f} "
            f"({(target_price / current_price - 1) * 100:+.1f}% move)"
        )
    if stop_price > 0:
        stop_pnl = (stop_price - cost_basis) * shares
        lines.append(
            f"- **P&L if price → stop {stop_price:g}:** {stop_pnl:+,.2f} "
            f"({(stop_price / current_price - 1) * 100:+.1f}% move)"
        )
        lines.append(f"- **Risk to stop:** {(stop_price - current_price) * shares:+,.2f}")
    return "\n".join(lines)


def create_portfolio_manager(llm):
    structured_llm = bind_structured(llm, PortfolioDecision, "Portfolio Manager")

    def portfolio_manager_node(state) -> dict:
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        framework_note = get_framework_note_from_state(state)
        market_context = get_market_context_from_state(state)
        signal_aggregation = state.get("signal_aggregation", "")
        signal_block = (
            f"- Aggregated analyst signal:\n{signal_aggregation}\n"
            if signal_aggregation
            else ""
        )
        key_question = state.get("key_question", "")
        key_question_block = (
            f"- Pivotal question(s) flagged for this call:\n{key_question}\n"
            if key_question
            else ""
        )
        event_impact = state.get("event_impact", "")
        event_impact_block = (
            f"- Event-impact / premise-shift check (if it recommends re-examining "
            f"the premise, address that explicitly before committing):\n{event_impact}\n"
            if event_impact
            else ""
        )
        risk_consensus = state.get("risk_consensus", "")
        risk_consensus_block = (
            f"- Unified risk framework (use this stop/drawdown — it already "
            f"reconciles the three risk analysts; do not re-stitch their levels "
            f"by hand):\n{risk_consensus}\n"
            if risk_consensus
            else ""
        )
        forecast_report = state.get("forecast_report", "")
        forecast_block = (
            f"- Time-horizon forecast (T+1/T+5/T+20/T+60 ranges, triggers, "
            f"falsifications) — use it to set the time horizon and entry/exit "
            f"cadence; check your rating is consistent with the expected path:\n"
            f"{forecast_report}\n"
            if forecast_report
            else ""
        )

        # Three independent risk reports (no debate). Concatenated for the PM as
        # context; the Risk Consensus node above already reconciled them into the
        # unified stop framework consumed via risk_consensus_block.
        risk_reports = "\n\n".join(
            r for r in (
                state.get("reward_risk_report", ""),
                state.get("tailrisk_report", ""),
                state.get("regime_risk_report", ""),
            ) if r
        )
        research_plan = state["investment_plan"]
        trader_plan = state["trader_investment_plan"]

        past_context = state.get("past_context", "")
        lessons_line = (
            f"- Lessons from prior decisions and outcomes:\n{past_context}\n"
            if past_context
            else ""
        )
        portfolio_context = state.get("portfolio_context", "")
        portfolio_block = (
            f"- Pre-trade portfolio interaction (how this name fits what is "
            f"already held — weigh concentration vs diversification before "
            f"sizing):\n{portfolio_context}\n"
            if portfolio_context
            else ""
        )
        position_context = state.get("position_context", "")
        position_block = (
            f"\n**The user's CURRENT position in this name:**\n{position_context}\n"
            if position_context
            else "\n**The user holds NO position in this name** — frame the call as "
            "a build-from-flat entry decision (enter / wait), not position management.\n"
        )

        # Soft context: how each analyst lens has historically scored in this
        # regime, so the PM knows whom to trust when the lenses disagree.
        scorecard_line = ""
        try:
            from dromx.agents.utils.signal_tracker import (
                AnalystScorecard,
                extract_trend,
            )
            from dromx.dataflows.config import get_config

            summary = AnalystScorecard(get_config()).summary(
                extract_trend(state.get("regime_report", ""))
            )
            if summary:
                scorecard_line = f"- {summary}\n"
        except Exception:  # noqa: BLE001 — best-effort, never block the decision
            scorecard_line = ""

        prompt = f"""As the Portfolio Manager, synthesize the independent risk reports and deliver the final trading decision.

{instrument_context}
{framework_note}{regime_context}{market_context}
{position_block}
**Position-aware decision.** Anchor the call to the user's CURRENT position above:
- Holding an OPEN position → decide add / hold / trim / exit, and reconcile the rating with their entry: reference the unrealized P&L and cost basis, say whether the original thesis still holds, and set actions relative to what they own (e.g. "trim half above $X, stop the rest at $Y") rather than a generic entry.
- FLAT (no position) → an entry-timing call: enter now / scale in / wait for a level, with the trigger.
Never recommend "reduce/take profits" on a name the user does not hold, nor "enter" on one they already own — match the advice to their actual position.

---

**Rating Scale** (use exactly one):
- **Buy**: Strong conviction to enter or add to position
- **Overweight**: Favorable outlook, gradually increase exposure
- **Hold**: Maintain current position, no action needed
- **Underweight**: Reduce exposure, take partial profits
- **Sell**: Exit position or avoid entry

**Context:**
- Research Manager's investment plan: **{research_plan}**
- Trader's transaction proposal: **{trader_plan}**
{key_question_block}{event_impact_block}{signal_block}{scorecard_line}{lessons_line}{portfolio_block}{risk_consensus_block}{forecast_block}
**Independent risk reports (Reward / Tail-Risk / Regime — analysed separately, not a debate):**
{risk_reports}

---

Be decisive and ground every conclusion in specific evidence from the analysts. Weight the final call to the market regime above: in high-volatility regimes prefer wider risk bands and avoid over-precise targets.

When the risk framework above includes a **suggested position size (sizing anchor)**, treat it as your quantitative starting point for sizing in the executive_summary — it is a fractional-Kelly figure derived from the fused scenario distribution and the consolidated stop. You may size below it (regime caution, concentration, conviction) or, rarely, above it, but if you depart from the anchor say why in one phrase. Do not invent a position size that ignores it.

If the fused expected value (from the aggregated signal) and any analyst's independently-computed EV point in different directions, do NOT silently pick one — state the divergence and its cause (usually different probability weights on the same scenarios) in one sentence, then say which you are trusting and why. A system that reports two contradictory EVs without reconciling them is a bug, not an insight.

Fill **key_drivers** with at least 3 weighted price drivers (driver + weight% summing to ~100 + tailwind/headwind/neutral) — the multi-variable decomposition of what actually moves this name (e.g. underlying stock 40% / a pending corporate action 30% / regional market sentiment 20% / FX 10%). A single-variable explanation ("the only thing that matters is X") is almost always wrong; the Key Question names the most CONTESTED unknown, but the price is driven by several factors at once — list them.

Keep time horizons separate, do not blend them. When the time-horizon forecast is provided above, reference it by horizon (the next-session view, the one-week view, the multi-month view) rather than mixing an intraday reaction and a quarterly target into one undifferentiated paragraph.

**A rating MUST bind to ONE primary horizon.** Set `primary_horizon` (T+1 / T+5 / T+20 / T+60) — the rating holds at THIS horizon. The other horizons are conditional views (`t1_view` / `t5_view` / `t20_view`), NOT separate ratings. "Short-term overbought + medium-term uptrend + long-term improving → Buy" is a fallacy — those three don't auto-derive "buy now". Pick the primary horizon the rating is for, state it, and let the others be risks/conditions. `action` is the concrete step tied to the primary horizon + rating (e.g. "scale in on a pullback to $X or a break above $Y"), not a vague "hold". Your `time_horizon` and `primary_horizon` should agree.

Your investment_thesis must close with two explicit elements, because a thesis you cannot disprove is not a thesis:
- **Key question:** the single most important unresolved question this decision hinges on — the one whose answer most determines whether you are right. Anchor this on the pivotal question(s) flagged for this call above, refining it if the risk debate sharpened it.
- **Falsification trigger:** a concrete, observable event or data point that would prove the thesis wrong (e.g. "two consecutive quarters of decelerating data-center revenue", "a weekly close below $X", "gross margin contracting below Y%"), and how you would change the rating if it occurs. Make it specific enough that a teammate could check it later without your interpretation. **Its timescale must match your time_horizon:** a 3–6 month horizon needs a monthly/weekly-resolution trigger (an earnings print, a weekly close, a multi-week trend), NOT an intraday or next-day move; a multi-week horizon should not hinge on a single day's tick. State the check cadence explicitly (e.g. "re-evaluate after each monthly close").{get_numeric_discipline()}{get_source_freshness_discipline()}{get_language_instruction()}"""

        from dromx.dataflows.config import get_config
        cfg = get_config()
        agent_cfg = cfg.get("agent_loop") or {}
        pm_loop_enabled = bool(agent_cfg.get("enabled", False))

        if pm_loop_enabled:
            from dromx.agents.utils.agent_loop import build_analyst_react_invoker

            def _shift_date(date_str: str, days: int) -> str:
                from datetime import datetime, timedelta
                return (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")

            _REPORT_KEYS = {
                "market": "market_report", "news": "news_report",
                "sentiment": "sentiment_report",
                "fundamentals": "fundamentals_report",
                "industry": "industry_report",
            }

            @tool
            def read_analyst_report(analyst_name: str) -> str:
                """Read the FULL original report of an analyst (market / news / sentiment / fundamentals / industry), not the aggregated summary in the prompt. Use to verify a specific claim against its source report."""
                key = _REPORT_KEYS.get((analyst_name or "").lower().strip())
                if not key:
                    return (
                        f"unknown analyst '{analyst_name}'. Available: "
                        f"{', '.join(sorted(_REPORT_KEYS))}."
                    )
                rep = state.get(key, "") or ""
                return rep if rep else f"<{analyst_name} report is empty>"

            _ticker = state.get("company_of_interest", "")
            _date = state.get("trade_date", "")

            @tool
            def _get_stock_data(
                start_date: str = "",
                end_date: str = "",
            ) -> str:
                """Pull OHLCV price history for the current ticker. start_date/end_date default to a 180-day window ending on trade_date when omitted."""
                s = start_date or _shift_date(_date, -180)
                e = end_date or _date
                return get_stock_data.func(_ticker, s, e)

            @tool
            def _get_fundamentals() -> str:
                """Pull the most recent fundamental data (financials, ratios, etc.) for the current ticker."""
                return get_fundamentals.func(_ticker, _date)

            @tool
            def _get_news(
                start_date: str = "",
                end_date: str = "",
            ) -> str:
                """Pull news for the current ticker. start_date/end_date default to a 7-day window ending on trade_date when omitted."""
                s = start_date or _shift_date(_date, -7)
                e = end_date or _date
                return get_news.func(_ticker, s, e)

            from dromx.agents.utils.browser_tools import web_read, web_search
            tools = [
                read_analyst_report,
                _get_stock_data, _get_fundamentals, _get_news,
                position_simulate,
                web_read,
                web_search,
            ]

            invoker = build_analyst_react_invoker(
                llm=llm, tools=tools, schema=PortfolioDecision,
                render=render_pm_decision, agent_name="Portfolio Manager",
                system_message=prompt, skills=[],
                instruction=(
                    "As Portfolio Manager, synthesize the final trading decision. Use "
                    "read_analyst_report to verify any analyst's specific claim against its "
                    "full original report (the prompt above only carries the aggregated "
                    "summary), and the data tools to pull raw data to cross-check a figure. "
                    "Then fill the structured fields. Do not call a tool more than once for "
                    "the same data."
                ),
                max_iterations=int(agent_cfg.get("pm_max_iterations", 8)),
            )
            final_trade_decision = invoker()
        else:
            final_trade_decision = invoke_structured_or_freetext(
                structured_llm,
                llm,
                prompt,
                render_pm_decision,
                "Portfolio Manager",
                schema=PortfolioDecision,
            )

        return {
            "final_trade_decision": final_trade_decision,
        }

    return portfolio_manager_node
