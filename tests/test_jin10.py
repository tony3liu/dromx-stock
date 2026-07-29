"""Jin10 MCP vendor 单元测试（离线，mock call_tool / _post_rpc）。"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

import dromx.dataflows.jin10 as jin10


class TestParsing:
    def test_as_list_envelope(self):
        data = {"data": {"has_more": True, "items": [{"content": "a"}, {"content": "b"}]}}
        assert len(jin10._as_list(data)) == 2

    def test_as_list_bare_list(self):
        assert len(jin10._as_list([{"x": 1}])) == 1

    def test_as_list_garbage(self):
        assert jin10._as_list({"status": 200}) == []
        assert jin10._as_list("nope") == []

    def test_parse_pub_iso_with_tz(self):
        dt = jin10._parse_pub({"time": "2026-07-29T16:11:38+08:00"})
        assert dt == datetime(2026, 7, 29, 16, 11, 38)

    def test_parse_pub_seconds_and_ms(self):
        assert jin10._parse_pub({"time": 1776339120}).year == 2026
        assert jin10._parse_pub({"time": 1776339120000}).year == 2026

    def test_parse_pub_missing(self):
        assert jin10._parse_pub({}) is None


_FLASH = {
    "data": {
        "has_more": True,
        "items": [
            {"content": "【重要】美联储维持利率不变", "time": "2026-07-29T02:00:00+08:00", "url": "https://x"},
            {"content": "港股收评：恒指收涨1.96%", "time": "2026-07-29T16:11:21+08:00", "url": "https://y"},
            {"content": "旧闻一条", "time": "2026-07-01T10:00:00+08:00", "url": "https://z"},
        ],
    }
}


@pytest.mark.unit
class TestGetGlobalNews:
    def test_renders_and_filters_window(self):
        with patch.object(jin10, "call_tool", return_value=_FLASH):
            out = jin10.get_global_news("2026-07-29", look_back_days=1, limit=10)
        assert "金十快讯" in out
        assert "美联储" in out
        assert "【重要】" in out  # important 标记保留
        assert "旧闻一条" not in out  # 超出 look_back 窗口被过滤

    def test_empty_when_all_out_of_window(self):
        flash = {"data": {"items": [_FLASH["data"]["items"][2]]}}
        with patch.object(jin10, "call_tool", return_value=flash):
            out = jin10.get_global_news("2026-07-29", look_back_days=1, limit=10)
        assert "No global news found" in out

    def test_unconfigured_raises(self, monkeypatch):
        for name in ("jin10_token", "JIN10_BEARER_TOKEN", "JIN10_TOKEN"):
            monkeypatch.delenv(name, raising=False)
        with pytest.raises(Exception) as exc:
            jin10._get_token()
        assert "not configured" in str(exc.value)


@pytest.mark.unit
class TestSseParsing:
    def test_parse_sse_basic(self):
        text = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
        assert jin10._parse_sse(text)["result"] == {"ok": True}

    def test_parse_sse_multiline_data(self):
        text = 'data: {"jsonrpc":"2.0",\ndata: "id":1,"result":1}\n\n'
        assert jin10._parse_sse(text)["result"] == 1

    def test_parse_sse_no_message(self):
        with pytest.raises(jin10.Jin10UnreachableError):
            jin10._parse_sse("event: ping\n\n")
