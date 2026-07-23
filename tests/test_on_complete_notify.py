"""on-complete notification hook tests (mocked notify, no engine run)."""

from unittest import mock

import pytest


@pytest.mark.unit
class TestOnCompleteNotify:
    def _handle(self, **kw):
        from webapp.backend import runner

        h = runner.RunHandle("rid", "07709.HK", "2026-06-30", ["market"], 1, **kw)
        h.rating = "Hold"
        return h

    def test_notify_dispatched_with_ticker_rating_subtitle(self):
        from webapp.backend import runner

        handle = self._handle(on_complete_notify=True, strategy_id="oversold_bounce")
        with mock.patch("webapp.backend.notify.alert") as alert:
            runner._notify_on_complete(handle, "**评级**：Hold\n持有观望。")
        alert.assert_called_once()
        _, kwargs = alert.call_args
        args = alert.call_args.args
        assert "07709.HK" in args[0]              # title has ticker
        assert "Hold" in kwargs["card_subtitle"]  # subtitle has rating
        assert "oversold_bounce" in kwargs["card_subtitle"]  # source strategy

    def test_notify_never_raises(self):
        from webapp.backend import runner

        handle = self._handle(on_complete_notify=True)
        with mock.patch("webapp.backend.notify.alert", side_effect=RuntimeError("boom")):
            # Must swallow — a notification failure cannot fail the run.
            runner._notify_on_complete(handle, "decision")

    def test_start_run_threads_new_fields(self):
        from webapp.backend import runner

        captured = {}

        class _T:
            def __init__(self, *a, **k):
                captured["handle"] = k.get("args", a[1] if len(a) > 1 else None)

            def start(self):
                pass

        with mock.patch.object(runner.store, "save_run"), \
             mock.patch.object(runner.threading, "Thread", _T):
            runner.start_run("NVDA", "2026-06-30", ["market"], 1,
                             strategy_id="macd_golden", on_complete_notify=True)
        handle = captured["handle"][0]
        assert handle.strategy_id == "macd_golden"
        assert handle.on_complete_notify is True
