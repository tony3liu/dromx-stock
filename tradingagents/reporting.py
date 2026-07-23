"""Reusable report-tree writer shared by the CLI and the programmatic API.

Writes a run's per-section markdown (analysts, research, trading, risk,
portfolio) plus a consolidated ``complete_report.md`` under ``save_path``. The
CLI and ``TradingAgentsGraph.save_reports`` both call this, so a headless / API
run produces the same on-disk report tree a CLI run does.
"""

from datetime import datetime
from pathlib import Path


def _extract_line(text: str, marker: str) -> str:
    """First line containing ``marker``, stripped; '' if none."""
    for line in (text or "").splitlines():
        if marker in line:
            return line.strip()
    return ""


def _premarket_call_card(final_state: dict) -> str:
    """One-look summary card for the top of the report.

    Pulls the expected-open + transmission-status lines out of the overnight
    block and the PM decision's first line, so a trader sees the call without
    scrolling to §0.7 / §5. Deterministic string extraction over fields we
    render ourselves (never re-runs the LLM). Empty when neither block is
    present, so a single-name / no-transmission run is unchanged.
    """
    lines: list[str] = []
    ov = final_state.get("overnight_transmission") or ""
    if ov:
        struct = _extract_line(ov, "**结构:**")
        expopen = _extract_line(ov, "**期望开盘:**")
        status = _extract_line(ov, "**传导状态:**")
        if expopen or status:
            lines.append("## 盘前 Call（摘要）")
            if struct:
                lines.append(struct)
            if expopen:
                lines.append(expopen)
            if status:
                lines.append(status)
    pat = final_state.get("pattern_discovery") or ""
    if pat:
        verdict = _extract_line(pat, "**精度统计**")
        evo = _extract_line(pat, "**演变**")
        if verdict or evo:
            if not lines:
                lines.append("## 盘前 Call（摘要）")
            if verdict:
                lines.append(verdict)
            if evo:
                lines.append(evo)
    ff = final_state.get("foreign_flow") or ""
    if ff:
        own = _extract_line(ff, "**当前外资持股")
        consec = _extract_line(ff, "**连续净")
        if own or consec:
            if not lines:
                lines.append("## 盘前 Call（摘要）")
            if own:
                lines.append(own)
            if consec:
                lines.append(consec)
    dec = final_state.get("final_trade_decision") or ""
    if dec:
        first = next((ln.strip() for ln in dec.splitlines() if ln.strip()), "")
        if first:
            if not lines:
                lines.append("## 盘前 Call（摘要）")
            first = first.lstrip("#- ").strip()
            if first:
                lines.append(f"- **决策：** {first}")
    return "\n".join(lines)


def write_report_tree(final_state: dict, ticker: str, save_path) -> Path:
    """Save a completed run's reports to ``save_path``; return the complete-report path."""
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    sections = []

    # 0. Market regime (pre-analysis classification)
    if final_state.get("regime_report"):
        regime_dir = save_path / "0_regime"
        regime_dir.mkdir(exist_ok=True)
        (regime_dir / "regime.md").write_text(final_state["regime_report"], encoding="utf-8")
        sections.append(f"## 市场状态\n\n{final_state['regime_report']}")

    # 0.5 Pre-trade portfolio context (how this name fits the current book)
    if final_state.get("portfolio_context"):
        regime_dir = save_path / "0_regime"
        regime_dir.mkdir(exist_ok=True)
        (regime_dir / "portfolio_context.md").write_text(
            final_state["portfolio_context"], encoding="utf-8"
        )
        sections.append(f"## 组合上下文\n\n{final_state['portfolio_context']}")

    # 0.6 Move cross-validation (market vs sector vs idiosyncratic)
    if final_state.get("market_context"):
        regime_dir = save_path / "0_regime"
        regime_dir.mkdir(exist_ok=True)
        (regime_dir / "market_context.md").write_text(
            final_state["market_context"], encoding="utf-8"
        )
        sections.append(f"## 异动归因\n\n{final_state['market_context']}")

    # 0.7 Overnight transmission (cross-market lead: US → underlying → listing open)
    if final_state.get("overnight_transmission"):
        regime_dir = save_path / "0_regime"
        regime_dir.mkdir(exist_ok=True)
        (regime_dir / "overnight_transmission.md").write_text(
            final_state["overnight_transmission"], encoding="utf-8"
        )
        sections.append(
            f"## 隔夜传导\n\n{final_state['overnight_transmission']}"
        )

    # 0.8 Pattern discovery (anomaly-driven reverse anchor search — forensics)
    if final_state.get("pattern_discovery"):
        regime_dir = save_path / "0_regime"
        regime_dir.mkdir(exist_ok=True)
        (regime_dir / "pattern_discovery.md").write_text(
            final_state["pattern_discovery"], encoding="utf-8"
        )
        sections.append(
            f"## 取证发现\n\n{final_state['pattern_discovery']}"
        )

    # 0.9 Foreign flow (chip-face: Naver foreign ownership + net trading)
    if final_state.get("foreign_flow"):
        regime_dir = save_path / "0_regime"
        regime_dir.mkdir(exist_ok=True)
        (regime_dir / "foreign_flow.md").write_text(
            final_state["foreign_flow"], encoding="utf-8"
        )
        sections.append(
            f"## 外资筹码\n\n{final_state['foreign_flow']}"
        )

    # 1. Analysts
    analysts_dir = save_path / "1_analysts"
    analyst_parts = []
    if final_state.get("market_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "market.md").write_text(final_state["market_report"], encoding="utf-8")
        analyst_parts.append(("技术面分析师", final_state["market_report"]))
    if final_state.get("sentiment_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "sentiment.md").write_text(final_state["sentiment_report"], encoding="utf-8")
        analyst_parts.append(("情绪面分析师", final_state["sentiment_report"]))
    if final_state.get("news_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "news.md").write_text(final_state["news_report"], encoding="utf-8")
        analyst_parts.append(("新闻面分析师", final_state["news_report"]))
    if final_state.get("fundamentals_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "fundamentals.md").write_text(final_state["fundamentals_report"], encoding="utf-8")
        analyst_parts.append(("基本面分析师", final_state["fundamentals_report"]))
    if final_state.get("industry_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "industry.md").write_text(final_state["industry_report"], encoding="utf-8")
        analyst_parts.append(("行业链分析师", final_state["industry_report"]))
    if analyst_parts:
        content = "\n\n".join(f"### {name}\n{text}" for name, text in analyst_parts)
        sections.append(f"## 一、分析师团队报告\n\n{content}")

    # 1.5 Aggregated signal (deterministic fusion of the analyst signals)
    if final_state.get("signal_aggregation"):
        signal_dir = save_path / "1_analysts"
        signal_dir.mkdir(exist_ok=True)
        (signal_dir / "signal_aggregation.md").write_text(
            final_state["signal_aggregation"], encoding="utf-8"
        )
        sections.append(
            f"## 一.5 融合信号\n\n{final_state['signal_aggregation']}"
        )

    # 1.6 Key question(s) — the pivotal decision driver(s) the call hinges on
    if final_state.get("key_question"):
        kq_dir = save_path / "1_analysts"
        kq_dir.mkdir(exist_ok=True)
        (kq_dir / "key_question.md").write_text(
            final_state["key_question"], encoding="utf-8"
        )
        sections.append(
            f"## 一.6 关键问题\n\n{final_state['key_question']}"
        )

    # 1.7 Event impact (premise-shift detector)
    if final_state.get("event_impact"):
        ei_dir = save_path / "1_analysts"
        ei_dir.mkdir(exist_ok=True)
        (ei_dir / "event_impact.md").write_text(
            final_state["event_impact"], encoding="utf-8"
        )
        sections.append(
            f"## 一.7 事件冲击\n\n{final_state['event_impact']}"
        )

    # 2. Research — two independent parallel reports (no debate) + manager plan
    research_parts = []
    research_dir = save_path / "2_research"
    if final_state.get("growth_report"):
        research_dir.mkdir(exist_ok=True)
        (research_dir / "growth.md").write_text(final_state["growth_report"], encoding="utf-8")
        research_parts.append(("增长与质量分析师", final_state["growth_report"]))
    if final_state.get("risk_report"):
        research_dir.mkdir(exist_ok=True)
        (research_dir / "risk.md").write_text(final_state["risk_report"], encoding="utf-8")
        research_parts.append(("估值与风险分析师", final_state["risk_report"]))
    if final_state.get("investment_plan"):
        research_dir.mkdir(exist_ok=True)
        (research_dir / "manager.md").write_text(final_state["investment_plan"], encoding="utf-8")
        research_parts.append(("研究经理", final_state["investment_plan"]))
    if research_parts:
        content = "\n\n".join(f"### {name}\n{text}" for name, text in research_parts)
        sections.append(f"## 二、研究团队结论\n\n{content}")

    # 3. Trading
    if final_state.get("trader_investment_plan"):
        trading_dir = save_path / "3_trading"
        trading_dir.mkdir(exist_ok=True)
        (trading_dir / "trader.md").write_text(final_state["trader_investment_plan"], encoding="utf-8")
        sections.append(f"## 三、交易团队方案\n\n### 交易员\n{final_state['trader_investment_plan']}")

    # 4. Risk Management — three independent parallel reports (no debate)
    risk_dir = save_path / "4_risk"
    risk_parts = []
    if final_state.get("reward_risk_report"):
        risk_dir.mkdir(exist_ok=True)
        (risk_dir / "reward.md").write_text(final_state["reward_risk_report"], encoding="utf-8")
        risk_parts.append(("仓位与收益专家", final_state["reward_risk_report"]))
    if final_state.get("tailrisk_report"):
        risk_dir.mkdir(exist_ok=True)
        (risk_dir / "tailrisk.md").write_text(final_state["tailrisk_report"], encoding="utf-8")
        risk_parts.append(("尾部风险与回撤专家", final_state["tailrisk_report"]))
    if final_state.get("regime_risk_report"):
        risk_dir.mkdir(exist_ok=True)
        (risk_dir / "regime_risk.md").write_text(final_state["regime_risk_report"], encoding="utf-8")
        risk_parts.append(("环境与宏观背景专家", final_state["regime_risk_report"]))
    if risk_parts:
        content = "\n\n".join(f"### {name}\n{text}" for name, text in risk_parts)
        sections.append(f"## 四、风险管理团队报告\n\n{content}")

    # 4.5 Risk Consensus (unified stop framework reconciled from the three reports)
    if final_state.get("risk_consensus"):
        risk_dir.mkdir(exist_ok=True)
        (risk_dir / "risk_consensus.md").write_text(
            final_state["risk_consensus"], encoding="utf-8"
        )
        sections.append(
            f"## 四.5 风险共识\n\n{final_state['risk_consensus']}"
        )

    # 4.6 Forecast (time-layered T+1/T+5/T+20/T+60 prediction)
    if final_state.get("forecast_report"):
        forecast_dir = save_path / "4_risk"
        forecast_dir.mkdir(exist_ok=True)
        (forecast_dir / "forecast.md").write_text(
            final_state["forecast_report"], encoding="utf-8"
        )
        sections.append(
            f"## 四.6 时间轴预测\n\n{final_state['forecast_report']}"
        )

    # 5. Portfolio Manager
    if final_state.get("final_trade_decision"):
        portfolio_dir = save_path / "5_portfolio"
        portfolio_dir.mkdir(exist_ok=True)
        (portfolio_dir / "decision.md").write_text(final_state["final_trade_decision"], encoding="utf-8")
        sections.append(f"## 五、投资组合经理决策\n\n### 投资组合经理\n{final_state['final_trade_decision']}")

    # Pre-market call card (one-look summary at the very top)
    card = _premarket_call_card(final_state)
    if card:
        sections.insert(0, card)

    # Write consolidated report
    header = f"# 交易分析报告：{ticker}\n\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    (save_path / "complete_report.md").write_text(header + "\n\n".join(sections), encoding="utf-8")
    return save_path / "complete_report.md"
