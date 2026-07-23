"""Persistence for web runs: one JSON file per analysis under ~/.tradingagents/web_runs/.

Single-machine, no database. Each run stores its metadata + the engine's
``final_state`` (the 14 markdown report sections) so the history list and any
later report view / Q&A can reload it without re-running the pipeline.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_RUNS_DIR = Path(os.path.expanduser("~")) / ".tradingagents" / "web_runs"

# The engine's report sections, in pipeline order, with display labels. Mirrors
# cli/main.py REPORT_SECTIONS so the web layer stays in lockstep with the engine.
REPORT_SECTIONS: list[tuple[str, str]] = [
    ("regime_report", "Market Regime"),
    ("market_context", "Move Cross-Validation"),
    ("portfolio_context", "Portfolio Context"),
    ("overnight_transmission", "Overnight Transmission"),
    ("pattern_discovery", "Pattern Discovery (Forensics)"),
    ("foreign_flow", "Foreign Flow (Naver)"),
    ("market_report", "Technical / Market"),
    ("sentiment_report", "Sentiment"),
    ("news_report", "News & Macro"),
    ("fundamentals_report", "Fundamentals"),
    ("industry_report", "Industry & Supply Chain"),
    ("signal_aggregation", "Aggregated Signal"),
    ("event_impact", "Event Impact"),
    ("key_question", "Key Question"),
    ("investment_plan", "Research Manager"),
    ("trader_investment_plan", "Trader Plan"),
    ("risk_consensus", "Risk Consensus"),
    ("forecast_report", "Forecast (T+1/5/20/60)"),
    ("final_trade_decision", "Portfolio Manager Decision"),
]


def _runs_dir() -> Path:
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return _RUNS_DIR


def _run_path(run_id: str) -> Path:
    return _runs_dir() / f"{run_id}.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_run(run: dict) -> None:
    """Atomically write a run record (temp file + replace)."""
    path = _run_path(run["id"])
    fd, tmp = tempfile.mkstemp(dir=str(_runs_dir()), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(run, f, ensure_ascii=False, default=str)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_run(run_id: str) -> dict | None:
    path = _run_path(run_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def delete_run(run_id: str) -> bool:
    """Delete a run's on-disk record. Returns True if a file was removed.

    Best-effort: a missing file (already gone) returns False, not an error, so
    a double-delete from the UI is idempotent.
    """
    path = _run_path(run_id)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False



def list_runs() -> list[dict]:
    """Return run summaries (no heavy final_state), newest first."""
    out = []
    for p in _runs_dir().glob("*.json"):
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        out.append({
            "id": r.get("id"),
            "ticker": r.get("ticker"),
            "trade_date": r.get("trade_date"),
            "status": r.get("status"),
            "rating": r.get("rating"),
            "created_at": r.get("created_at"),
            "finished_at": r.get("finished_at"),
        })
    out.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return out


def reap_stale_runs() -> int:
    """Mark any ``running`` record as ``interrupted``.

    A run is an in-memory background thread; when the server process exits the
    thread dies but its on-disk record is frozen at ``running``. On the next
    startup those records are necessarily orphaned, so we flip them to
    ``interrupted`` — otherwise the UI would replay them as a fake ``complete``
    (empty report) or spin on a skeleton forever. Returns the count reaped.
    """
    n = 0
    for p in _runs_dir().glob("*.json"):
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if r.get("status") == "running":
            r["status"] = "interrupted"
            r["finished_at"] = now_iso()
            r["error"] = "后端重启导致该分析中断，请重新发起。"
            save_run(r)
            n += 1
    return n

