"""Scheduled jobs (v0.4.0 Phase 2) — APScheduler over the existing engines.

A thin scheduler that runs three kinds of job on a cron/interval, using the
pieces Phase 1 already built. Uses ``BackgroundScheduler`` (thread pool) rather
than AsyncIOScheduler because the work it dispatches is synchronous/blocking
(``runner.start_run`` spawns its own thread; ``engine.run`` is sync) and we don't
want to contend with uvicorn's event loop.

Job kinds (PRD §2.3.1):
  - analysis: run the full pipeline on a ticker (notify on complete)
  - screen:   run a screening strategy for a market → notify the hit list
  - warmup:   pre-warm a market's universe cache (DataAdapter.load_universe)

Plus one internal job when monitoring is enabled: monitor_poll, which loads the
enabled rules, evaluates them against the current snapshot, and fires alerts.

Jobs persist to ``~/.tradingagents/jobs.json``. Everything is gated by config
(``scheduler.enabled`` / ``monitor.enabled``, both default False) so a normal
deployment that never opts in is completely unaffected.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger("tradingagents.web.scheduler")

_JOBS_PATH = Path(os.path.expanduser("~")) / ".tradingagents" / "jobs.json"
_LOCK = threading.Lock()

JOB_KINDS = {"analysis", "screen", "warmup"}

# Lazily-built singletons.
_scheduler = None          # BackgroundScheduler
_monitor_engine = None     # tradingagents.strategy.monitor.MonitorEngine


# ---------------------------------------------------------------------------
# Config (env override for the nested scheduler/monitor blocks)
# ---------------------------------------------------------------------------


def _cfg() -> dict:
    from tradingagents.default_config import DEFAULT_CONFIG

    sched = dict(DEFAULT_CONFIG.get("scheduler", {}))
    mon = dict(DEFAULT_CONFIG.get("monitor", {}))
    # Nested env overrides (the flat _ENV_OVERRIDES mechanism can't reach these).
    if os.getenv("TRADINGAGENTS_SCHEDULER_ENABLED"):
        sched["enabled"] = os.environ["TRADINGAGENTS_SCHEDULER_ENABLED"].lower() in ("1", "true", "yes", "on")
    if os.getenv("TRADINGAGENTS_SCHEDULER_TIMEZONE"):
        sched["timezone"] = os.environ["TRADINGAGENTS_SCHEDULER_TIMEZONE"]
    if os.getenv("TRADINGAGENTS_MONITOR_ENABLED"):
        mon["enabled"] = os.environ["TRADINGAGENTS_MONITOR_ENABLED"].lower() in ("1", "true", "yes", "on")
    if os.getenv("TRADINGAGENTS_MONITOR_POLL_SECONDS"):
        try:
            mon["poll_interval_seconds"] = int(os.environ["TRADINGAGENTS_MONITOR_POLL_SECONDS"])
        except ValueError:
            pass
    return {"scheduler": sched, "monitor": mon}


# ---------------------------------------------------------------------------
# Jobs persistence + CRUD
# ---------------------------------------------------------------------------


def load_jobs() -> list[dict]:
    with _LOCK:
        if not _JOBS_PATH.exists():
            return []
        try:
            return json.loads(_JOBS_PATH.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            logger.warning("jobs read failed: %s", e)
            return []


def _save_jobs(jobs: list[dict]) -> None:
    _JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _JOBS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _JOBS_PATH)


def get_job(job_id: str) -> dict | None:
    return next((j for j in load_jobs() if j.get("id") == job_id), None)


def upsert_job(job: dict) -> dict:
    """Validate + persist a job, then (re)register it with a running scheduler."""
    validate_job(job)
    with _LOCK:
        jobs = json.loads(_JOBS_PATH.read_text(encoding="utf-8")) if _JOBS_PATH.exists() else []
        jobs = [j for j in jobs if j.get("id") != job["id"]]
        jobs.append(job)
        _save_jobs(jobs)
    if _scheduler is not None:
        _register_job(job)
    return job


def delete_job(job_id: str) -> bool:
    with _LOCK:
        jobs = json.loads(_JOBS_PATH.read_text(encoding="utf-8")) if _JOBS_PATH.exists() else []
        n = len(jobs)
        jobs = [j for j in jobs if j.get("id") != job_id]
        _save_jobs(jobs)
    if _scheduler is not None:
        try:
            _scheduler.remove_job(job_id)
        except Exception:  # noqa: BLE001 — job may not be registered
            pass
    return len(jobs) < n


def validate_job(job: dict) -> None:
    import re

    jid = job.get("id", "")
    if not isinstance(jid, str) or not re.fullmatch(r"[a-z0-9_-]{1,40}", jid):
        raise ValueError("job id 非法(仅小写字母/数字/下划线/短横线,1-40字符)")
    if job.get("kind") not in JOB_KINDS:
        raise ValueError(f"kind 必须是 {sorted(JOB_KINDS)} 之一")
    if not job.get("cron"):
        raise ValueError("必须指定 cron 表达式(5 字段: 分 时 日 月 周)")
    _parse_cron(job["cron"])  # raises on malformed
    kind = job["kind"]
    params = job.get("params", {})
    if kind == "analysis" and not params.get("ticker"):
        raise ValueError("analysis 任务必须指定 params.ticker")
    if kind == "screen" and not params.get("strategy_id"):
        raise ValueError("screen 任务必须指定 params.strategy_id")


def _parse_cron(cron: str):
    """Turn a 5-field cron string into a CronTrigger (raises if malformed)."""
    from apscheduler.triggers.cron import CronTrigger

    parts = cron.split()
    if len(parts) != 5:
        raise ValueError("cron 必须是 5 字段: 分 时 日 月 周")
    minute, hour, dom, month, dow = parts
    return CronTrigger(minute=minute, hour=hour, day=dom, month=month,
                       day_of_week=dow, timezone=_cfg()["scheduler"]["timezone"])


# ---------------------------------------------------------------------------
# Job execution
# ---------------------------------------------------------------------------


def run_job(job_id: str) -> dict:
    """Execute a job now (manual trigger). Returns a small status dict."""
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"未知任务: {job_id}")
    return _dispatch(job)


def _dispatch(job: dict) -> dict:
    kind = job.get("kind")
    params = job.get("params", {})
    try:
        if kind == "analysis":
            return _run_analysis_job(params)
        if kind == "screen":
            return _run_screen_job(params)
        if kind == "warmup":
            return _run_warmup_job(params)
    except Exception as e:  # noqa: BLE001 — a job failure must not kill the scheduler
        logger.warning("job %s (%s) failed: %s", job.get("id"), kind, e)
        _notify_job_failure(job, e)
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": f"unknown kind {kind}"}


def _run_analysis_job(params: dict) -> dict:
    from datetime import date

    from webapp.backend import runner

    ticker = params["ticker"].strip()
    trade_date = params.get("trade_date") or date.today().isoformat()
    analysts = params.get("analysts") or ["market", "social", "news", "fundamentals", "industry"]
    run_id = runner.start_run(
        ticker=ticker, trade_date=trade_date, analysts=[a.lower() for a in analysts],
        depth=int(params.get("depth", 1)), on_complete_notify=True,
    )
    logger.info("scheduled analysis started: %s (run %s)", ticker, run_id)
    return {"ok": True, "run_id": run_id}


def _run_screen_job(params: dict) -> dict:
    from datetime import date

    from webapp.backend import notify, strategy as strategy_api

    sid = params["strategy_id"]
    market = params.get("market", "hk")
    eng = strategy_api._get_engine(market)
    result = eng.run(sid, date.today())
    if result.total:
        top = result.rows[: min(10, result.total)]
        lines = [f"{r.get('name') or r['symbol']} ({r['symbol']})" for r in top]
        notify.alert(
            f"选股 · {sid} 命中 {result.total} 只",
            "命中标的:\n" + "\n".join(lines),
            card_subtitle=f"策略 {sid} · {market} · {date.today().isoformat()}",
        )
    logger.info("scheduled screen %s (%s): %d hits", sid, market, result.total)
    return {"ok": True, "total": result.total}


def _run_warmup_job(params: dict) -> dict:
    from datetime import date

    from webapp.backend import strategy as strategy_api

    market = params.get("market", "hk")
    df = strategy_api._adapter.load_universe(market, date.today())
    logger.info("scheduled warmup %s: %d rows cached", market, df.height)
    return {"ok": True, "rows": df.height}


def _notify_job_failure(job: dict, exc: Exception) -> None:
    try:
        from webapp.backend import notify

        notify.alert(f"定时任务失败 · {job.get('id')}", f"{type(exc).__name__}: {exc}",
                     channels=["feishu"])
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Monitor poll (internal job)
# ---------------------------------------------------------------------------


def _get_monitor_engine():
    global _monitor_engine
    if _monitor_engine is None:
        from tradingagents.strategy.monitor import MonitorEngine
        from webapp.backend import alert_store, notify, strategy as strategy_api

        def _handler(ev: dict) -> None:
            alert_store.append(ev)
            notify.alert(ev.get("rule_name") or "监控告警", ev.get("message", ""))

        eng = MonitorEngine(alert_handler=_handler)
        # strategy-type rules need the screening engine (default market from cfg).
        try:
            market = _cfg()["monitor"]["market"]
            eng.set_strategy_engine(strategy_api._get_engine(market))
        except Exception as e:  # noqa: BLE001
            logger.warning("monitor: strategy engine unavailable: %s", e)
        _monitor_engine = eng
    return _monitor_engine


def monitor_poll() -> dict:
    """One monitoring cycle: reload rules, screen the market, evaluate, alert."""
    from datetime import date

    from tradingagents.strategy import monitor_rules
    from webapp.backend import strategy as strategy_api

    rules = [r for r in monitor_rules.load_all() if r.get("enabled", True)]
    if not rules:
        return {"ok": True, "rules": 0, "events": 0}
    eng = _get_monitor_engine()
    eng.set_rules(rules)
    market = _cfg()["monitor"]["market"]
    try:
        df = strategy_api._adapter.load_universe(market, date.today())
    except Exception as e:  # noqa: BLE001
        logger.warning("monitor poll: universe load failed: %s", e)
        return {"ok": False, "error": str(e)}
    events = eng.evaluate(df)
    logger.info("monitor poll: %d rules → %d events", len(rules), len(events))
    return {"ok": True, "rules": len(rules), "events": len(events)}


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


def _register_job(job: dict) -> None:
    if _scheduler is None or not job.get("enabled", True):
        return
    try:
        _scheduler.add_job(
            _dispatch, trigger=_parse_cron(job["cron"]), args=[job],
            id=job["id"], replace_existing=True, misfire_grace_time=300,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("failed to register job %s: %s", job.get("id"), e)


def start() -> bool:
    """Start the scheduler if enabled. Registers all jobs + monitor poll. Idempotent."""
    global _scheduler
    cfg = _cfg()
    if not cfg["scheduler"]["enabled"] and not cfg["monitor"]["enabled"]:
        logger.info("scheduler + monitor both disabled — not starting")
        return False
    if _scheduler is not None:
        return True

    from apscheduler.schedulers.background import BackgroundScheduler

    _scheduler = BackgroundScheduler(timezone=cfg["scheduler"]["timezone"])

    if cfg["scheduler"]["enabled"]:
        for job in load_jobs():
            _register_job(job)

    if cfg["monitor"]["enabled"]:
        from apscheduler.triggers.interval import IntervalTrigger

        _scheduler.add_job(
            monitor_poll, trigger=IntervalTrigger(
                seconds=int(cfg["monitor"]["poll_interval_seconds"])),
            id="_monitor_poll", replace_existing=True, misfire_grace_time=30,
        )

    _scheduler.start()
    logger.info("scheduler started (jobs=%d, monitor=%s)",
                len(load_jobs()) if cfg["scheduler"]["enabled"] else 0,
                cfg["monitor"]["enabled"])
    return True


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:  # noqa: BLE001
            pass
        _scheduler = None
