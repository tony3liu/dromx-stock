"""选股历史（JSONL 追加 + 滚动修剪）

每次 AI 选股（含多轮澄清）完成后落一条记录到
``~/.dromx/screen_history.jsonl``：意图/反馈链、市场、策略、命中（前 15 只
精简行）+ AI 研判，供前端「历史记录」回看与恢复。

修剪策略（与 alert_store 一致）：最多 MAX_RECORDS 条，每 PRUNE_EVERY 次写入
重写一次文件。读取全量加载、内存过滤。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_PATH = Path(os.path.expanduser("~")) / ".dromx" / "screen_history.jsonl"

MAX_RECORDS = 100
PRUNE_EVERY = 20
_KEEP_ROWS = 15  # 每条记录最多存的命中行数

_lock = threading.Lock()
_write_count = 0

_ROW_FIELDS = ("symbol", "name", "close", "change_pct", "turnover_rate",
               "vol_ratio_5d", "rsi_14", "score")


def _path() -> Path:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    return _PATH


def save(result: dict) -> str | None:
    """把一次 run_ai_screen 结果存为一条历史记录，返回记录 id。

    best-effort：写失败只记日志，不影响主流程。
    """
    global _write_count
    try:
        hid = uuid.uuid4().hex[:12]
        rows = []
        for r in (result.get("rows") or [])[:_KEEP_ROWS]:
            rows.append({k: r.get(k) for k in _ROW_FIELDS})
        record = {
            "id": hid,
            "ts": int(time.time() * 1000),
            "prompt": result.get("prompt", ""),
            "feedback": result.get("feedback"),
            "market": result.get("market", ""),
            "as_of": result.get("as_of", ""),
            "strategy": result.get("strategy") or {},
            "total": result.get("total", 0),
            "elapsed_ms": result.get("elapsed_ms", 0),
            "rows": rows,
            "reviews": result.get("reviews") or {},
        }
        with _lock:
            p = _path()
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            _write_count += 1
            if _write_count >= PRUNE_EVERY:
                _write_count = 0
                _prune_locked(p)
        return hid
    except Exception as e:  # noqa: BLE001
        logger.warning("screen history save failed: %s", e)
        return None


def list_recent(limit: int = 20) -> list[dict]:
    """最近记录（新→旧），摘要形态（不含 rows/reviews）"""
    with _lock:
        rows = _read_all_locked()
    rows.sort(key=lambda r: r.get("ts", 0), reverse=True)
    out = []
    for r in rows[: max(1, limit)]:
        out.append({
            "id": r.get("id"),
            "ts": r.get("ts"),
            "prompt": r.get("prompt"),
            "feedback": r.get("feedback"),
            "market": r.get("market"),
            "as_of": r.get("as_of"),
            "strategy_name": (r.get("strategy") or {}).get("name", ""),
            "strategy_id": (r.get("strategy") or {}).get("id", ""),
            "total": r.get("total", 0),
        })
    return out


def get(hid: str) -> dict | None:
    """按 id 取完整记录（含 rows/reviews）"""
    with _lock:
        rows = _read_all_locked()
    for r in rows:
        if r.get("id") == hid:
            return r
    return None


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
        logger.warning("screen history read failed: %s", e)
    return out


def _prune_locked(p: Path) -> None:
    rows = _read_all_locked()
    if len(rows) <= MAX_RECORDS:
        return
    rows.sort(key=lambda r: r.get("ts", 0))
    rows = rows[-MAX_RECORDS:]
    try:
        tmp = p.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, p)
    except Exception as e:  # noqa: BLE001
        logger.warning("screen history prune failed: %s", e)
