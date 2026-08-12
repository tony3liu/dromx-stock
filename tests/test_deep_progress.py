"""P-C（work 平台集成）：深研 section 进度上报打通测试。零成本——mock run_analysis_once，不跑真管线/LLM。

验证：
1. _run_deep_analysis 传了 on_progress 时，深研过程经 on_progress 上报 deep_start + deep_section；
   未传 on_progress 时行为不变（向后兼容）。
2. planner 的工作线程 + 队列桥接：dispatch 里的 on_progress 回调事件被 planner 生成器 yield 出来。
"""

import json
from unittest.mock import patch


def _fake_run_analysis_once(ticker, trade_date, analysts, depth, *, on_section=None, should_stop=None, **kw):
    """假管线：逐 section 回调 on_section，返回 (final_state, rating)。不跑真 LLM。"""
    sections = [
        ("market_report", "Market", "# 行情\n看涨"),
        ("fundamentals_report", "Fundamentals", "# 基本面\n稳健"),
    ]
    if on_section:
        for key, label, md in sections:
            on_section(key, label, md)
    final_state = {k: v for k, v, _ in [(s[0], s[2], None) for s in sections]}
    final_state["final_trade_decision"] = "观望"
    return final_state, "Hold"


def test_deep_analysis_reports_progress_when_callback_given():
    """传 on_progress → 收到 deep_start + 每个 section 的 deep_section。"""
    from dromx.tools.analysis import _run_deep_analysis

    events = []
    with patch("webapp.backend.runner.run_analysis_once", _fake_run_analysis_once), \
         patch("webapp.backend.runner.PIPELINE_NODES", ["Market", "Fundamentals"], create=True):
        out = _run_deep_analysis({"ticker": "NBIS", "date": "2026-08-12"}, on_progress=events.append)

    types = [e["type"] for e in events]
    # task#47：末尾多一个 deep_usage（run 结束上报真实 token/tool usage）
    assert types == ["deep_start", "deep_section", "deep_section", "deep_usage"], types
    assert events[0]["ticker"] == "NBIS"
    assert events[1]["key"] == "market_report" and events[1]["label"] == "Market"
    assert "行情" in events[1]["markdown"]
    assert events[-1]["type"] == "deep_usage" and "usage" in events[-1]  # 真实 usage 上报
    # 工具正常返回结果（进度上报不影响主流程）
    payload = json.loads(out)
    assert payload.get("rating") == "Hold" or payload.get("data", {}).get("rating") == "Hold"


def test_deep_analysis_no_callback_backward_compatible():
    """不传 on_progress → 不报错、行为不变（向后兼容直接调用/CLI）。"""
    from dromx.tools.analysis import _run_deep_analysis

    with patch("webapp.backend.runner.run_analysis_once", _fake_run_analysis_once), \
         patch("webapp.backend.runner.PIPELINE_NODES", ["Market"], create=True):
        out = _run_deep_analysis({"ticker": "NBIS"})  # 无 on_progress
    assert "error" not in json.loads(out) or json.loads(out).get("data") is not None


def test_registry_dispatch_forwards_on_progress():
    """registry.dispatch 把 on_progress 透传给声明了该参的 handler（planner 队列桥接依赖此契约）。"""
    from dromx.tools.registry import registry

    def _fake_tool(args, on_progress=None, **kw):
        if on_progress:
            on_progress({"type": "deep_start", "nodes": ["a"]})
            on_progress({"type": "deep_section", "key": "market_report", "label": "Market", "markdown": "x"})
        return json.dumps({"ok": True})

    registry.register(
        name="__pc_fake_tool",
        toolset="analysis",
        schema={"name": "__pc_fake_tool", "description": "test", "parameters": {}},
        handler=_fake_tool,
    )
    got = []
    result = registry.dispatch("__pc_fake_tool", {}, on_progress=got.append)
    assert [e["type"] for e in got] == ["deep_start", "deep_section"]
    assert json.loads(result)["ok"] is True


def test_registry_dispatch_omits_on_progress_for_plain_handler():
    """handler 未声明 on_progress → dispatch 过滤掉，不打爆签名（向后兼容）。"""
    from dromx.tools.registry import registry

    def _plain(args):
        return json.dumps({"ok": True})

    registry.register(
        name="__pc_plain_tool",
        toolset="analysis",
        schema={"name": "__pc_plain_tool", "description": "test", "parameters": {}},
        handler=_plain,
    )
    # 传 on_progress 也不报错（被 dispatch 过滤）
    result = registry.dispatch("__pc_plain_tool", {}, on_progress=lambda e: None)
    assert json.loads(result)["ok"] is True
