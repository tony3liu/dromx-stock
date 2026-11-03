"""Strategy backtest harness (PRD §6 P0).

Backtests the AI DECISION PROCESS itself: on each historical trading day in a
window it re-runs the full pipeline (look-ahead-safe — the engine only sees data
up to that ``trade_date``), scores the day's rating against the realized forward
return, and rolls the sequence into an equity curve + standard metrics.

This is the EXPENSIVE feature — every day is a full multi-agent LLM run — so the
harness is built defensively:
  * hard cap on days per backtest (``MAX_DAYS``); the API rejects bigger windows;
  * SERIAL execution via the runner's single-flight semaphore (one heavy run at
    a time on this box);
  * a checkpoint written after EVERY day, so a killed / restarted backtest
    resumes from where it stopped instead of paying for finished days again;
  * the per-day analysis call is INJECTED (``run_day``) so the whole harness —
    enumeration, caching, scoring, equity curve, resume, cap — is unit-testable
    with a cheap stub and never spends real tokens in tests.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import date as _date
from pathlib import Path
from typing import Callable

logger = logging.getLogger("dromx.web.backtest")

MAX_DAYS = 50  # hard ceiling on full-pipeline runs per backtest (cost guard)
_NOISE = 0.01  # ±1% band: a directional call needs a real move to be confirmed

_DIR = {"buy": 1, "overweight": 1, "hold": 0, "neutral": 0, "underweight": -1, "sell": -1}

_BT_DIR = Path(os.path.expanduser("~")) / ".dromx" / "backtests"
_REGISTRY: dict[str, dict] = {}   # id -> live status dict (progress polling)
_LOCK = threading.Lock()


# --- persistence -------------------------------------------------------------

def _bt_dir() -> Path:
    _BT_DIR.mkdir(parents=True, exist_ok=True)
    return _BT_DIR


def _bt_path(bt_id: str) -> Path:
    return _bt_dir() / f"{bt_id}.json"


def save_backtest(bt: dict) -> None:
    path = _bt_path(bt["id"])
    fd, tmp = tempfile.mkstemp(dir=str(_bt_dir()), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(bt, f, ensure_ascii=False, default=str)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_backtest(bt_id: str) -> dict | None:
    with _LOCK:
        if bt_id in _REGISTRY:
            return dict(_REGISTRY[bt_id])
    path = _bt_path(bt_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def list_backtests() -> list[dict]:
    out = []
    for p in _bt_dir().glob("*.json"):
        try:
            with open(p, encoding="utf-8") as f:
                b = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        out.append({k: b.get(k) for k in
                    ("id", "ticker", "start_date", "end_date", "status",
                     "created_at", "finished_at", "metrics")})
    out.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return out


# --- trading-day enumeration + returns (prices only) -------------------------

def _closes(ticker: str, curr_date: str) -> list[tuple[str, float]]:
    """(date, close) list up to ``curr_date`` via the engine data layer."""
    from dromx.dataflows.stockstats_utils import load_ohlcv

    df = load_ohlcv(ticker, curr_date)
    if df is None or getattr(df, "empty", True):
        return []
    cols = {c.lower(): c for c in df.columns}
    dcol, ccol = cols.get("date"), cols.get("close")
    if ccol is None:
        return []
    out = []
    for _, row in df.iterrows():
        d = str(row[dcol])[:10] if dcol else ""
        try:
            out.append((d, float(row[ccol])))
        except (TypeError, ValueError):
            continue
    return out


def trading_days(ticker: str, start: str, end: str) -> list[str]:
    """Trading days in [start, end] for which the name has a close."""
    today = _date.today().isoformat()
    return [d for d, _ in _closes(ticker, today) if d and start <= d <= end]


def _forward_return(closes: list[tuple[str, float]], day: str, holding: int
                    ) -> tuple[float | None, int]:
    """Close-to-close return starting at ``day`` over ``holding`` trading days."""
    idx = next((i for i, (d, _) in enumerate(closes) if d == day), None)
    if idx is None:
        return None, 0
    entry = closes[idx][1]
    j = min(idx + holding, len(closes) - 1)
    if j <= idx or entry <= 0:
        return None, 0
    return (closes[j][1] - entry) / entry, j - idx


def _score(direction: int | None, raw: float | None) -> bool | None:
    if direction is None or raw is None:
        return None
    if direction == 0:
        return abs(raw) < _NOISE
    if abs(raw) < _NOISE:
        return False
    return (raw > 0) == (direction > 0)


# --- metrics over the per-day strategy returns -------------------------------

def _metrics(day_rows: list[dict]) -> dict:
    import math

    scored = [r for r in day_rows if r.get("correct") is not None]
    # strategy return per day = direction * forward return (flat on Hold).
    strat = [r["direction"] * r["raw_return"]
             for r in day_rows
             if r.get("direction") not in (None, 0) and r.get("raw_return") is not None]
    hits = sum(1 for r in scored if r["correct"])

    equity, peak, mdd = 1.0, 1.0, 0.0
    for s in strat:
        equity *= 1 + s
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1)

    def sharpe(xs):
        if len(xs) < 2:
            return None
        m = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
        return round(m / sd, 3) if sd > 1e-12 else None

    gains = sum(x for x in strat if x > 0)
    losses = -sum(x for x in strat if x < 0)
    wins = [x for x in strat if x > 0]

    return {
        "days_scored": len(scored),
        "hit_rate": round(hits / len(scored), 3) if scored else None,
        "cumulative_return_pct": round((equity - 1) * 100, 2) if strat else None,
        "max_drawdown_pct": round(mdd * 100, 2) if strat else None,
        "sharpe": sharpe(strat),
        "win_rate": round(len(wins) / len(strat), 3) if strat else None,
        "profit_factor": (round(gains / losses, 2) if losses > 1e-12
                          else (None if gains <= 1e-12 else math.inf)),
        "trades": len(strat),
    }


# --- the harness -------------------------------------------------------------

def run_backtest(
    bt_id: str,
    ticker: str,
    start_date: str,
    end_date: str,
    analysts: list[str],
    depth: int,
    holding_days: int,
    run_day: Callable[[str, str], str | None],
    *,
    reuse_rating: Callable[[str, str], str | None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    """Execute the backtest, checkpointing after each day. Returns the final record.

    ``run_day(ticker, day) -> rating`` does the expensive full-pipeline analysis
    (injected — a stub in tests). ``reuse_rating(ticker, day) -> rating|None``
    lets the caller supply an already-computed rating (from a prior run/backtest)
    to skip paying for that day. ``should_stop`` aborts gracefully between days.
    """
    days = trading_days(ticker, start_date, end_date)
    if len(days) > MAX_DAYS:
        days = days[:MAX_DAYS]
    closes = _closes(ticker, _date.today().isoformat())

    # resume: keep already-scored days from a prior checkpoint.
    existing = load_backtest(bt_id) or {}
    done_by_day = {r["date"]: r for r in existing.get("days", []) if r.get("rating")}

    rows: list[dict] = []
    for i, day in enumerate(days):
        if should_stop and should_stop():
            break

        rating = None
        if day in done_by_day:
            rating = done_by_day[day]["rating"]          # resume: already paid
        elif reuse_rating:
            rating = reuse_rating(ticker, day)           # reuse a live run's rating
        if rating is None:
            rating = run_day(ticker, day)                # PAY: full pipeline

        raw, held = _forward_return(closes, day, holding_days)
        direction = _DIR.get((rating or "").strip().lower())
        rows.append({
            "date": day, "rating": rating, "direction": direction,
            "raw_return": raw, "held_days": held,
            "correct": _score(direction, raw),
        })

        # checkpoint after EVERY day so a crash/kill resumes for free.
        _write_progress(bt_id, ticker, start_date, end_date, analysts, depth,
                        holding_days, rows, len(days), status="running")

    metrics = _metrics(rows)
    return _write_progress(bt_id, ticker, start_date, end_date, analysts, depth,
                           holding_days, rows, len(days), status="done",
                           metrics=metrics)


def _write_progress(bt_id, ticker, start_date, end_date, analysts, depth,
                    holding_days, rows, total, *, status, metrics=None) -> dict:
    from webapp.backend import store  # reuse now_iso

    existing = load_backtest(bt_id) or {}
    rec = {
        "id": bt_id, "ticker": ticker, "start_date": start_date, "end_date": end_date,
        "analysts": analysts, "depth": depth, "holding_days": holding_days,
        "status": status, "days": rows, "days_total": total, "days_done": len(rows),
        "created_at": existing.get("created_at") or store.now_iso(),
        "finished_at": store.now_iso() if status in ("done", "error") else None,
        "metrics": metrics if metrics is not None else existing.get("metrics"),
    }
    with _LOCK:
        _REGISTRY[bt_id] = rec
    save_backtest(rec)
    return rec


def estimate_days(ticker: str, start_date: str, end_date: str) -> int:
    """How many full-pipeline runs a backtest would cost (before launching)."""
    return min(len(trading_days(ticker, start_date, end_date)), MAX_DAYS)


_STOP: dict[str, bool] = {}


def request_stop(bt_id: str) -> None:
    _STOP[bt_id] = True


def start_backtest(bt_id: str, ticker: str, start_date: str, end_date: str,
                   analysts: list[str], depth: int, holding_days: int) -> None:
    """Launch the backtest on a background thread (serial via runner's semaphore).

    Each day calls the REAL pipeline (runner.run_analysis_once). Days already
    analysed live for this exact (ticker, date) are reused for free; a killed
    backtest resumes from its checkpoint.
    """
    from webapp.backend import runner, store

    # Build a reuse map: latest done run per (ticker, date) → rating (skip paying).
    def reuse_rating(tk: str, day: str) -> str | None:
        for r in store.list_runs():
            if (r.get("status") == "done" and (r.get("ticker") or "").upper() == tk.upper()
                    and (r.get("trade_date") or "") == day and r.get("rating")):
                return r.get("rating")
        return None

    def run_day(tk: str, day: str) -> str | None:
        runner._RUN_SEM.acquire()  # single-flight: one heavy run at a time
        try:
            _merged, rating = runner.run_analysis_once(tk, day, analysts, depth)
            return rating
        except Exception as exc:  # noqa: BLE001 — one bad day shouldn't sink the run
            logger.warning("backtest %s day %s failed: %s", bt_id, day, exc)
            return None
        finally:
            runner._RUN_SEM.release()

    def worker():
        try:
            run_backtest(bt_id, ticker, start_date, end_date, analysts, depth,
                         holding_days, run_day, reuse_rating=reuse_rating,
                         should_stop=lambda: _STOP.get(bt_id, False))
        except Exception:  # noqa: BLE001
            logger.exception("backtest %s crashed", bt_id)
            rec = load_backtest(bt_id) or {"id": bt_id}
            rec["status"] = "error"
            save_backtest(rec)
        finally:
            _STOP.pop(bt_id, None)

    # Write an initial 'running' checkpoint SYNCHRONOUSLY before the thread starts,
    # so a client that polls immediately gets a record (not a 404) while the first
    # day's multi-minute analysis is still running.
    total = estimate_days(ticker, start_date, end_date)
    _write_progress(bt_id, ticker, start_date, end_date, analysts, depth,
                    holding_days, [], total, status="running")
    threading.Thread(target=worker, daemon=True).start()
