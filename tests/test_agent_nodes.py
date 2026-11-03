"""Node-level integration tests for the core agent nodes (mock LLM, no network).

Each structured LLM node follows the same contract:
    create_<node>(llm) -> node(state) -> {state_key: rendered_markdown}
where the LLM call goes through invoke_structured_or_freetext. We fake the LLM so
`with_structured_output(Schema).invoke(...)` returns a known schema instance, then
assert the node writes the expected state key with the rendered (Chinese) scaffold.

Pre-fetch nodes (regime/market/news/fundamentals/industry) also hit data vendors;
we monkeypatch those to placeholder strings so the tests are deterministic and
never touch the network. The deterministic Signal Aggregator uses no LLM — it is
driven purely by the rendered analyst reports we place in state.

These are the regression net for the schemas/ split and future refactors: they
prove each node still wires its inputs to the right rendered output key.
"""

from unittest.mock import MagicMock

import pytest

from dromx.agents import schemas as S


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def structured_llm(instance):
    """A MagicMock LLM whose with_structured_output(...).invoke(...) returns `instance`."""
    structured = MagicMock()
    structured.invoke.return_value = instance
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm


def _scn(label, p, m):
    return S.Scenario(label=label, probability=p, magnitude_pct=m, trigger="t")


BASE_STATE = {
    "company_of_interest": "NVDA",
    "trade_date": "2026-06-27",
    "instrument_context": "",
    "regime_report": "**市场状态：** **Uptrend / High volatility** （置信度：Medium）",
    "market_report": "**技术面观点：** **看涨 Bullish** （置信度：高 High）",
    "sentiment_report": "**综合情绪：** **温和看涨 Mildly Bullish** （评分：6.0/10）",
    "news_report": "**新闻面观点：** **中性 Neutral** （置信度：中 Medium）",
    "fundamentals_report": "**基本面观点：** **看涨 Bullish** （置信度：高 High）",
    "industry_report": "**行业链观点：** **看涨 Bullish** （置信度：中 Medium）",
    "signal_aggregation": "**融合信号：** **看涨 Bullish** （加权分 +1.30，一致性：Strong）",
    "event_impact": "**事件冲击：** 3/10 —— 前提无变化",
}


# --------------------------------------------------------------------------- #
# synthesis nodes (state in, no external fetch)
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_key_question_node_writes_rendered_report():
    from dromx.agents.analysts.key_question import create_key_question_analyst

    report = S.KeyQuestionReport(
        key_questions=[S.KeyQuestion(question="Q?", why_it_matters="w", what_would_answer_it="a")],
        focus_directive="focus here",
    )
    node = create_key_question_analyst(structured_llm(report))
    out = node(dict(BASE_STATE))
    assert set(out) == {"key_question"}
    assert "关键问题" in out["key_question"]
    assert "focus here" in out["key_question"]


@pytest.mark.unit
def test_event_impact_node_writes_rendered_report():
    from dromx.agents.analysts.event_impact import create_event_impact_assessor

    report = S.EventImpactReport(
        impact_score=8, affected_dimensions=["fundamentals: dilution"],
        recommend_reanalysis=True, assessment="A capital raise re-rates the structure.",
    )
    node = create_event_impact_assessor(structured_llm(report))
    out = node(dict(BASE_STATE))
    assert set(out) == {"event_impact"}
    assert "事件冲击：** 8/10" in out["event_impact"]
    assert "重新审视前提" in out["event_impact"]


@pytest.mark.unit
def test_forecast_node_writes_rendered_report():
    from dromx.agents.analysts.forecast_synthesizer import create_forecast_synthesizer

    report = S.ForecastReport(
        horizons=[
            S.ForecastHorizon(horizon=h, price_range="1-2", direction="Bullish",
                              most_likely="m", key_trigger_or_calendar="k",
                              falsification="f", confidence="high")
            for h in ("T+1", "T+5", "T+20", "T+60")
        ],
        fused_expected_path="up then sideways",
    )
    node = create_forecast_synthesizer(structured_llm(report))
    out = node(dict(BASE_STATE))
    assert set(out) == {"forecast_report"}
    assert "时间轴预测" in out["forecast_report"]
    assert "T+60" in out["forecast_report"]


# --------------------------------------------------------------------------- #
# deterministic node (no LLM) — driven by the rendered analyst reports in state
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_signal_aggregator_node_fuses_reports():
    from dromx.agents.analysts.signal_aggregator import create_signal_aggregator

    node = create_signal_aggregator()  # no LLM
    out = node(dict(BASE_STATE))
    assert "signal_aggregation" in out and "analysis_depth" in out
    assert "融合信号" in out["signal_aggregation"]
    # each lens surfaces a row in the table (lens labels are the English keys)
    assert "Technical" in out["signal_aggregation"]


# --------------------------------------------------------------------------- #
# pre-fetch nodes (monkeypatch the vendor fetchers to placeholders)
# --------------------------------------------------------------------------- #

@pytest.mark.unit
def test_regime_node_writes_report(monkeypatch):
    import dromx.agents.analysts.regime_analyst as mod

    monkeypatch.setattr(mod, "build_verified_market_snapshot",
                        lambda *a, **k: "SNAPSHOT: close 100, ATR 5, RSI 55")
    report = S.RegimeReport(
        trend_direction="Uptrend", volatility_level="High", confidence="medium",
        analyst_weighting_hint="favour technicals", narrative="n",
    )
    node = mod.create_regime_analyst(structured_llm(report))
    out = node(dict(BASE_STATE))
    assert out["regime_report"] and "市场状态" in out["regime_report"]
    assert "messages" in out  # regime emits an AIMessage too


@pytest.mark.unit
def test_market_node_writes_report(monkeypatch):
    import dromx.agents.analysts.market_analyst as mod

    # market analyst pre-fetches the verified snapshot (a langchain @tool → .func)
    monkeypatch.setattr(mod.get_verified_market_snapshot, "func",
                        lambda *a, **k: "SNAPSHOT: close 100", raising=False)
    report = S.MarketReport(
        direction="Bullish", direction_short_term="Neutral", direction_medium_term="Bullish",
        confidence="high", scenarios=[_scn("bear", 0.25, -18), _scn("base", 0.5, 8), _scn("bull", 0.25, 25)],
        indicator_readout="RSI 62", key_evidence=["e"], risks=["r"], narrative="n",
    )
    node = mod.create_market_analyst(structured_llm(report))
    out = node(dict(BASE_STATE))
    assert "技术面观点" in out["market_report"]
    assert "分时方向" in out["market_report"]  # short/medium horizon splice


@pytest.mark.unit
def test_news_node_writes_report(monkeypatch):
    import dromx.agents.analysts.news_analyst as mod

    monkeypatch.setattr(mod.get_news, "func", lambda *a, **k: "### [2026-06-24] headline (source: X)", raising=False)
    monkeypatch.setattr(mod.get_global_news, "func", lambda *a, **k: "global news", raising=False)
    monkeypatch.setattr(mod, "_fetch_macro", lambda *a, **k: "macro block")
    monkeypatch.setattr(mod.get_prediction_markets, "func", lambda *a, **k: "prediction block", raising=False)
    report = S.NewsReport(
        direction="Neutral", confidence="medium",
        scenarios=[_scn("bear", 0.3, -10), _scn("base", 0.5, 3), _scn("bull", 0.2, 15)],
        macro_backdrop="neutral backdrop", key_evidence=["e"], risks=["r"], narrative="n",
    )
    node = mod.create_news_analyst(structured_llm(report))
    out = node(dict(BASE_STATE))
    assert "新闻面观点" in out["news_report"]


@pytest.mark.unit
def test_fundamentals_node_writes_report(monkeypatch):
    import dromx.agents.analysts.fundamentals_analyst as mod

    for name in ("get_fundamentals", "get_balance_sheet", "get_income_statement", "get_cashflow"):
        monkeypatch.setattr(getattr(mod, name), "func", lambda *a, **k: "financial block", raising=False)
    report = S.FundamentalsReport(
        direction="Bullish", confidence="high",
        scenarios=[_scn("bear", 0.2, -15), _scn("base", 0.5, 10), _scn("bull", 0.3, 25)],
        valuation_view="fair", key_evidence=["e"], risks=["r"], narrative="n",
    )
    node = mod.create_fundamentals_analyst(structured_llm(report))
    out = node(dict(BASE_STATE))
    assert "基本面观点" in out["fundamentals_report"]


@pytest.mark.unit
def test_industry_node_writes_report(monkeypatch):
    import dromx.agents.analysts.industry_analyst as mod

    monkeypatch.setattr(mod, "resolve_instrument_identity", lambda *a, **k: {"sector": "Tech", "industry": "Semis"})
    monkeypatch.setattr(mod.get_global_news, "func", lambda *a, **k: "sector news", raising=False)
    monkeypatch.setattr(mod.get_news, "func", lambda *a, **k: "name news", raising=False)
    monkeypatch.setattr(mod.get_fundamentals, "func", lambda *a, **k: "peer fin", raising=False)
    report = S.IndustryReport(
        direction="Bullish", confidence="medium",
        scenarios=[_scn("bear", 0.2, -20), _scn("base", 0.5, 8), _scn("bull", 0.3, 30)],
        industry_phase="Expansion", competitive_moat="Widening",
        key_dependency="HBM capacity", disruption_risk="substitution low",
        key_evidence=["[data] e"], risks=["r"], narrative="n",
    )
    node = mod.create_industry_analyst(structured_llm(report))
    out = node(dict(BASE_STATE))
    assert "行业链观点" in out["industry_report"]
    assert "周期阶段" in out["industry_report"]
