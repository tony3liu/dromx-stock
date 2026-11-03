"""Notification system isolation tests (mocked adapters, tmp config, no network).

Covers config merge/persistence, channel gating in ``alert()``, secret
redaction, and the never-raise contract.
"""

from unittest import mock

import pytest


@pytest.fixture
def notify_mod(tmp_path, monkeypatch):
    from webapp.backend import notify

    monkeypatch.setattr(notify, "_CONFIG_PATH", tmp_path / "notify.json")
    return notify


@pytest.mark.unit
class TestNotifyConfig:
    def test_defaults_when_no_file(self, notify_mod):
        cfg = notify_mod.load_config()
        assert cfg["system"]["enabled"] is True
        assert cfg["feishu"]["webhook_url"] == ""

    def test_save_merges_and_persists(self, notify_mod):
        notify_mod.save_config({"feishu": {"webhook_url": "https://x"}})
        cfg = notify_mod.load_config()
        assert cfg["feishu"]["webhook_url"] == "https://x"
        # System default preserved through the merge.
        assert cfg["system"]["enabled"] is True

    def test_partial_update_keeps_other_channel(self, notify_mod):
        notify_mod.save_config({"feishu": {"webhook_url": "https://a", "secret": "s"}})
        notify_mod.save_config({"system": {"enabled": False}})
        cfg = notify_mod.load_config()
        assert cfg["feishu"]["webhook_url"] == "https://a"
        assert cfg["system"]["enabled"] is False


@pytest.mark.unit
class TestAlertDispatch:
    def test_system_channel_called_when_enabled(self, notify_mod):
        with mock.patch.object(notify_mod.notify_adapter, "notify", return_value=True) as m:
            results = notify_mod.alert("t", "b", channels=["system"])
        m.assert_called_once()
        assert results["system"] is True

    def test_system_skipped_when_disabled(self, notify_mod):
        notify_mod.save_config({"system": {"enabled": False}})
        with mock.patch.object(notify_mod.notify_adapter, "notify") as m:
            results = notify_mod.alert("t", "b", channels=["system"])
        m.assert_not_called()
        assert "system" not in results

    def test_feishu_skipped_when_url_absent(self, notify_mod):
        with mock.patch.object(notify_mod.webhook_adapter, "send_feishu") as m:
            results = notify_mod.alert("t", "b", channels=["feishu"])
        m.assert_not_called()
        assert "feishu" not in results

    def test_feishu_card_used_when_subtitle_present(self, notify_mod):
        notify_mod.save_config({"feishu": {
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/x"}})
        with mock.patch.object(notify_mod.webhook_adapter, "send_feishu_card",
                               return_value=True) as card, \
             mock.patch.object(notify_mod.webhook_adapter, "send_feishu") as text:
            results = notify_mod.alert("t", "body", channels=["feishu"],
                                       card_subtitle="NVDA · Buy")
        card.assert_called_once()
        text.assert_not_called()
        assert results["feishu"] is True

    def test_alert_never_raises_on_adapter_error(self, notify_mod):
        notify_mod.save_config({"feishu": {
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/x"}})
        with mock.patch.object(notify_mod.webhook_adapter, "send_feishu",
                               side_effect=RuntimeError("boom")):
            # send_feishu itself is guarded, but even if it raised, alert must
            # not propagate. We assert no exception escapes.
            try:
                notify_mod.alert("t", "b", channels=["feishu"])
            except Exception as e:  # noqa: BLE001
                pytest.fail(f"alert raised: {e}")


@pytest.mark.unit
class TestChannelStatus:
    def test_status_reports_feishu_configured(self, notify_mod):
        notify_mod.save_config({"feishu": {
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/x"}})
        st = notify_mod.channel_status()
        assert st["feishu"]["configured"] is True

    def test_status_no_secret_leak(self, notify_mod):
        notify_mod.save_config({"feishu": {
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/x",
            "secret": "topsecret"}})
        st = notify_mod.channel_status()
        # channel_status returns no secret field at all.
        assert "secret" not in st["feishu"]
