"""Alert history store (v0.4.0 Phase 2) — JSONL append + rolling prune.

Ported from TickFlow's ``alert_store.py``. Each triggered alert event is one JSON
line appended to ``~/.dromx/alerts.jsonl``. Reads load the whole file
(bounded by the prune caps) and filter in memory.

Prune policy (intersection): keep records from the last MAX_DAYS AND at most
MAX_RECORDS. Pruning runs every PRUNE_EVERY writes to avoid rewriting the file on
every append. Thread-safe via a module lock.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_PATH = Path(os.path.expanduser("~")) / ".dromx" / "alerts.jsonl"

MAX_DAYS = 7
MAX_RECORDS = 5000
PRUNE_EVERY = 20

_lock = threading.Lock()
_write_count = 0


def _path() -> Path:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    return _PATH


def append(event: dict) -> None:
    """Append one alert event (should carry ts in ms, rule_id, source, …)."""
    global _write_count
    with _lock:
        p = _path()
        try:
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:  # noqa: BLE001 — history is best-effort
            logger.warning("alert append failed: %s", e)
            return
        _write_count += 1
        if _write_count >= PRUNE_EVERY:
            _write_count = 0
            _prune_locked(p)


def append_many(events: list[dict]) -> None:
    if not events:
        return
    for ev in events:
        append(ev)


def query(limit: int = 200, source: str | None = None,
          rule_id: str | None = None) -> list[dict]:
    """Return alerts newest-first, optionally filtered by source / rule_id."""
    with _lock:
        rows = _read_all_locked()
    if source:
        rows = [r for r in rows if r.get("source") == source]
    if rule_id:
        rows = [r for r in rows if r.get("rule_id") == rule_id]
    rows.sort(key=lambda r: r.get("ts", 0), reverse=True)
    return rows[: max(1, limit)]


def _read_all_locked() -> list[dict]:
    p = _PATH
    if not p.exists():
        return []
    out: list[dict] = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception as e:  # noqa: BLE001
        logger.warning("alert read failed: %s", e)
    return out


def _prune_locked(p: Path) -> None:
    """Rewrite the file keeping records within MAX_DAYS AND MAX_RECORDS."""
    rows = _read_all_locked()
    if not rows:
        return
    cutoff_ms = (time.time() - MAX_DAYS * 86400) * 1000
    rows = [r for r in rows if r.get("ts", 0) >= cutoff_ms]
    rows.sort(key=lambda r: r.get("ts", 0))
    if len(rows) > MAX_RECORDS:
        rows = rows[-MAX_RECORDS:]
    try:
        tmp = p.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, p)
    except Exception as e:  # noqa: BLE001
        logger.warning("alert prune failed: %s", e)
