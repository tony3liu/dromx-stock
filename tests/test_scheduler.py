"""Scheduler job CRUD + dispatch isolation tests (mocked runner/engine/notify)."""

from unittest import mock

import pytest


@pytest.fixture
def sched(tmp_path, monkeypatch):
    from webapp.backend import scheduler

    monkeypatch.setattr(scheduler, "_JOBS_PATH", tmp_path / "jobs.json")
    scheduler._scheduler = None
    scheduler._monitor_engine = None
    return scheduler


@pytest.mark.unit
class TestJobCrud:
    def _analysis_job(self):
        return {"id": "j1", "kind": "analysis", "cron": "0 16 * * 1-5",
                "params": {"ticker": "NVDA"}, "enabled": True}

    def test_upsert_and_get(self, sched):
        sched.upsert_job(self._analysis_job())
        assert sched.get_job("j1")["params"]["ticker"] == "NVDA"

    def test_upsert_replaces_same_id(self, sched):
        sched.upsert_job(self._analysis_job())
        j = self._analysis_job()
        j["params"]["ticker"] = "AAPL"
        sched.upsert_job(j)
        jobs = sched.load_jobs()
        assert len(jobs) == 1 and jobs[0]["params"]["ticker"] == "AAPL"

    def test_delete(self, sched):
        sched.upsert_job(self._analysis_job())
        assert sched.delete_job("j1") is True
        assert sched.get_job("j1") is None

    def test_validate_bad_id(self, sched):
        with pytest.raises(ValueError, match="id"):
            sched.validate_job({"id": "Bad!", "kind": "analysis",
                                "cron": "0 16 * * *", "params": {"ticker": "X"}})

    def test_validate_bad_kind(self, sched):
        with pytest.raises(ValueError, match="kind"):
            sched.validate_job({"id": "j", "kind": "nope", "cron": "0 16 * * *"})

    def test_validate_bad_cron(self, sched):
        with pytest.raises(ValueError, match="cron"):
            sched.validate_job({"id": "j", "kind": "warmup", "cron": "not a cron",
                                "params": {}})

    def test_validate_analysis_needs_ticker(self, sched):
        with pytest.raises(ValueError, match="ticker"):
            sched.validate_job({"id": "j", "kind": "analysis",
                                "cron": "0 16 * * *", "params": {}})

    def test_validate_screen_needs_strategy(self, sched):
        with pytest.raises(ValueError, match="strategy_id"):
            sched.validate_job({"id": "j", "kind": "screen",
                                "cron": "0 9 * * *", "params": {}})


@pytest.mark.unit
class TestDispatch:
    def test_analysis_dispatch_calls_runner(self, sched):
        job = {"id": "j", "kind": "analysis", "cron": "0 16 * * *",
               "params": {"ticker": "NVDA"}}
        with mock.patch("webapp.backend.runner.start_run", return_value="rid123") as sr:
            out = sched._dispatch(job)
        sr.assert_called_once()
        assert sr.call_args.kwargs["on_complete_notify"] is True
        assert out["ok"] is True and out["run_id"] == "rid123"

    def test_screen_dispatch_notifies_on_hits(self, sched):
        job = {"id": "j", "kind": "screen", "cron": "0 9 * * *",
               "params": {"strategy_id": "oversold_bounce", "market": "hk"}}
        fake_result = mock.MagicMock()
        fake_result.total = 2
        fake_result.rows = [{"symbol": "00001.HK", "name": "A"},
                            {"symbol": "00002.HK", "name": "B"}]
        fake_engine = mock.MagicMock()
        fake_engine.run.return_value = fake_result
        with mock.patch("webapp.backend.strategy._get_engine", return_value=fake_engine), \
             mock.patch("webapp.backend.notify.alert") as alert:
            out = sched._dispatch(job)
        alert.assert_called_once()
        assert out["ok"] is True and out["total"] == 2

    def test_screen_dispatch_no_notify_when_empty(self, sched):
        job = {"id": "j", "kind": "screen", "cron": "0 9 * * *",
               "params": {"strategy_id": "x", "market": "hk"}}
        fake_result = mock.MagicMock()
        fake_result.total = 0
        fake_result.rows = []
        fake_engine = mock.MagicMock()
        fake_engine.run.return_value = fake_result
        with mock.patch("webapp.backend.strategy._get_engine", return_value=fake_engine), \
             mock.patch("webapp.backend.notify.alert") as alert:
            out = sched._dispatch(job)
        alert.assert_not_called()
        assert out["total"] == 0

    def test_dispatch_failure_notifies_and_returns_error(self, sched):
        job = {"id": "j", "kind": "screen", "cron": "0 9 * * *",
               "params": {"strategy_id": "x", "market": "hk"}}
        with mock.patch("webapp.backend.strategy._get_engine",
                        side_effect=RuntimeError("boom")), \
             mock.patch("webapp.backend.notify.alert") as alert:
            out = sched._dispatch(job)
        assert out["ok"] is False and "boom" in out["error"]
        alert.assert_called_once()  # failure notification

    def test_run_job_unknown_raises(self, sched):
        with pytest.raises(ValueError, match="未知任务"):
            sched.run_job("does_not_exist")


@pytest.mark.unit
class TestMonitorPoll:
    def test_poll_no_rules_returns_zero(self, sched, monkeypatch):
        monkeypatch.setattr("dromx.strategy.monitor_rules.load_all", lambda: [])
        out = sched.monitor_poll()
        assert out["ok"] is True and out["events"] == 0

    def test_poll_evaluates_and_counts(self, sched, monkeypatch):
        import polars as pl

        rule = {"id": "r", "name": "x", "type": "price", "scope": "all",
                "enabled": True,
                "conditions": [{"field": "change_pct", "op": ">", "value": 0.05}]}
        monkeypatch.setattr("dromx.strategy.monitor_rules.load_all", lambda: [rule])
        df = pl.DataFrame({"symbol": ["X"], "name": ["X"], "close": [10.0],
                          "change_pct": [0.08]})
        fake_adapter = mock.MagicMock()
        fake_adapter.load_universe.return_value = df
        monkeypatch.setattr("webapp.backend.strategy._adapter", fake_adapter)
        with mock.patch("webapp.backend.alert_store.append"), \
             mock.patch("webapp.backend.notify.alert"):
            out = sched.monitor_poll()
        assert out["ok"] is True and out["events"] == 1


@pytest.mark.unit
class TestLifecycle:
    def test_start_noop_when_disabled(self, sched, monkeypatch):
        monkeypatch.setattr(sched, "_cfg", lambda: {
            "scheduler": {"enabled": False, "timezone": "UTC"},
            "monitor": {"enabled": False, "poll_interval_seconds": 60, "market": "hk"},
        })
        assert sched.start() is False
        assert sched._scheduler is None

    def test_start_and_shutdown_idempotent(self, sched, monkeypatch):
        monkeypatch.setattr(sched, "_cfg", lambda: {
            "scheduler": {"enabled": True, "timezone": "UTC"},
            "monitor": {"enabled": False, "poll_interval_seconds": 60, "market": "hk"},
        })
        assert sched.start() is True
        assert sched.start() is True  # idempotent
        sched.shutdown()
        assert sched._scheduler is None
        sched.shutdown()  # no-op, no raise
