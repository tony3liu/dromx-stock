"""Report synthesis + rendering isolation tests (mock LLM, no Chromium/network)."""

from unittest import mock

import pytest


_FINAL_STATE = {
    "regime_report": "**Market Regime:** Uptrend / High volatility",
    "market_report": "**Direction:** Bullish\n**Key Evidence:** RSI 62, price above MA20.",
    "sentiment_report": "**Overall Sentiment:** Bullish",
    "news_report": "**Direction:** Neutral\n无重大事件。",
    "fundamentals_report": "**Direction:** Bullish\n净利率 45%。",
    "industry_report": "**Direction:** Bullish\n行业扩张期。",
    "signal_aggregation": "融合方向 Bullish, EV +4.2%。",
    "risk_consensus": "止损 178（ATR×2）。",
    "forecast_report": "T+1 区间 185-192；T+20 200。",
    "final_trade_decision": "**评级**：Overweight\n**目标价**：210",
}


def _run_rec(with_state=True, report_md=None, report_version=None):
    rec = {"id": "r1", "ticker": "NVDA", "trade_date": "2026-06-30",
           "rating": "Overweight", "final_state": _FINAL_STATE if with_state else {}}
    if report_md is not None:
        rec["report_md"] = report_md
        # Stamp the current version so cache-hit tests reflect a fresh cache.
        from webapp.backend import report as _report
        rec["report_version"] = report_version if report_version is not None else _report._REPORT_VERSION
    return rec


def _llm(content: str):
    llm = mock.MagicMock()
    llm.invoke.return_value = mock.MagicMock(content=content)
    return llm


@pytest.mark.unit
class TestReportSynthesis:
    def test_generates_markdown_and_caches(self, tmp_path, monkeypatch):
        from webapp.backend import report, store

        saved = {}
        monkeypatch.setattr(store, "load_run", lambda rid: _run_rec())
        monkeypatch.setattr(store, "save_run", lambda rec: saved.update(rec))
        long_md = "### 一、执行摘要\n" + "评级 Overweight，目标价 210。" * 24
        llm = _llm(long_md)

        res = report.build_report_markdown("r1", llm)
        assert res is not None
        md, _rec = res
        assert "执行摘要" in md
        llm.invoke.assert_called_once()
        # prompt carries the FULL analysis context (raw section reports, not a
        # compressed summary) + the PM rating
        prompt = llm.invoke.call_args.args[0]
        assert "完整分析底稿" in prompt and "Overweight" in prompt
        # the full market report body must be present (not truncated to highlights)
        assert "RSI 62" in prompt
        # cached back into the record with the current version stamp
        assert saved.get("report_md") == md
        assert saved.get("report_version") == report._REPORT_VERSION

    def test_uses_cache_second_time(self, monkeypatch):
        from webapp.backend import report, store

        monkeypatch.setattr(store, "load_run", lambda rid: _run_rec(report_md="## 缓存报告\n已生成。"))
        llm = _llm("should-not-be-called")
        md, _ = report.build_report_markdown("r1", llm)
        assert "缓存报告" in md
        llm.invoke.assert_not_called()

    def test_stale_version_regenerates(self, monkeypatch):
        """A report cached under an older version must be regenerated, not served."""
        from webapp.backend import report, store

        saved = {}
        monkeypatch.setattr(
            store, "load_run",
            lambda rid: _run_rec(report_md="## 旧的浅层报告\n太浅了。", report_version=0),
        )
        monkeypatch.setattr(store, "save_run", lambda rec: saved.update(rec))
        fresh = "### 一、执行摘要\n" + "全新的深度研报内容。" * 60
        llm = _llm(fresh)
        md, _ = report.build_report_markdown("r1", llm)
        assert "旧的浅层报告" not in md   # stale cache ignored
        assert "执行摘要" in md            # regenerated
        llm.invoke.assert_called_once()
        assert saved.get("report_version") == report._REPORT_VERSION

    def test_llm_failure_falls_back_to_assembly(self, monkeypatch):
        from webapp.backend import report, store

        monkeypatch.setattr(store, "load_run", lambda rid: _run_rec())
        monkeypatch.setattr(store, "save_run", lambda rec: None)
        llm = mock.MagicMock()
        llm.invoke.side_effect = RuntimeError("no key")
        md, _ = report.build_report_markdown("r1", llm)
        # assembly fallback includes the PM decision + section labels
        assert "组合经理决策" in md and "目标价" in md

    def test_too_short_llm_output_falls_back(self, monkeypatch):
        from webapp.backend import report, store

        monkeypatch.setattr(store, "load_run", lambda rid: _run_rec())
        monkeypatch.setattr(store, "save_run", lambda rec: None)
        md, _ = report.build_report_markdown("r1", _llm("太短"))
        assert "组合经理决策" in md  # fell back

    def test_missing_run_returns_none(self, monkeypatch):
        from webapp.backend import report, store

        monkeypatch.setattr(store, "load_run", lambda rid: None)
        assert report.build_report_markdown("nope", _llm("x")) is None


@pytest.mark.unit
class TestReportHtml:
    def test_render_html_has_cover_and_body(self):
        from webapp.backend import report

        html = report.render_html("## 执行摘要\n\n评级 Overweight。",
                                  ticker="NVDA", trade_date="2026-06-30", rating="Overweight")
        assert "NVDA" in html and "执行摘要" in html
        assert "Fraunces" in html          # display font linked
        assert 'class="badge ' in html     # rating badge rendered

    def test_rating_class_colors(self):
        from webapp.backend import report

        assert report._rating_class("Sell") == "bear"
        assert report._rating_class("Hold") == "neutral"
        assert report._rating_class("Overweight") == ""  # green default

    def test_markdown_table_renders(self):
        from webapp.backend import report

        html = report.render_html("| A | B |\n|---|---|\n| 1 | 2 |",
                                  ticker="X", trade_date="", rating=None)
        assert "<table>" in html
