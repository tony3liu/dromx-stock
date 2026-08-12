"""OBS-dromx-stock-01：结构化输出宽松挽救测试。零成本——纯函数，不调 LLM。

验证 _recover_from_freetext 在严格校验失败时，先宽松挽救部分结构化数据（补默认字段）
再校验渲染，而非整个丢弃 pretty-print。
"""

import json

from dromx.core.structured import _recover_from_freetext, _coerce_to_schema, _default_for
from dromx.agents.schemas import ForecastReport, render_forecast_report


def _valid_horizon(label):
    return {
        "horizon": label, "price_range": "175-195", "direction": "up",
        "most_likely": "180", "key_trigger_or_calendar": "earnings",
        "falsification": "closes below 170", "confidence": "medium",
    }


def test_default_for_types():
    """类型默认：list→[]、str→""、bool→False、int→0。"""
    from typing import List
    assert _default_for(str) == ""
    assert _default_for(bool) is False
    assert _default_for(int) == 0
    assert _default_for(List[str]) == []
    assert _default_for(list) == []


def test_coerce_fills_missing_required_field():
    """缺失必填字段（fused_expected_path）→ 补默认后可构造。"""
    data = {"horizons": [_valid_horizon(h) for h in ("T+1", "T+5", "T+20", "T+60")]}
    # 缺 fused_expected_path（必填）
    coerced = _coerce_to_schema(data, ForecastReport)
    assert "fused_expected_path" in coerced
    obj = ForecastReport.model_validate(coerced)
    assert obj.fused_expected_path == ""  # 补了默认空串
    assert len(obj.horizons) == 4


def test_recover_salvages_near_valid_json():
    """近合法 JSON（缺 fused_expected_path + scenario_table）→ 挽救为结构化渲染（非 blob）。"""
    blob = json.dumps({
        "horizons": [_valid_horizon(h) for h in ("T+1", "T+5", "T+20", "T+60")],
        # 缺 fused_expected_path（必填）→ 严格校验会报错
    })
    text = f"这是我的预测：\n{blob}\n以上。"
    out = _recover_from_freetext(text, ForecastReport, render_forecast_report, "Forecast Synthesizer")
    assert out is not None
    # 挽救成功 = 走了 render_forecast_report（结构化），不是 _json_to_markdown 的 blob
    # render 输出含 horizon 标签；blob pretty-print 会是 "- **horizons:**" 列表
    assert "T+1" in out or "T+60" in out


def test_recover_strict_valid_still_works():
    """完全合法 JSON → 严格校验直接过（不走挽救）。"""
    blob = json.dumps({
        "horizons": [_valid_horizon(h) for h in ("T+1", "T+5", "T+20", "T+60")],
        "scenario_table": [],
        "fused_expected_path": "tomorrow 175-195 → one week hinges on earnings",
    })
    out = _recover_from_freetext(blob, ForecastReport, render_forecast_report, "Forecast Synthesizer")
    assert out is not None
    assert "175-195" in out or "earnings" in out


def test_recover_non_json_returns_none():
    """无 JSON 的纯文本 → None（调用方保留 prose）。"""
    assert _recover_from_freetext("就是一段没有 json 的话", ForecastReport, render_forecast_report, "X") is None
