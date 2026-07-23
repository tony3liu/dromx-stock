"""Monitor rule model + file CRUD (v0.4.0 Phase 2).

A monitor rule declares WHAT to watch and HOW to alert. Adapted from TickFlow's
``monitor_rules.py`` but trimmed to the V1 scope (PRD §2.4.1):

  - type: "price"    — threshold comparison on a snapshot field (close/change_pct/…)
  - type: "signal"   — a boolean technical signal fires (signal_macd_golden/…)
  - type: "strategy" — a screening strategy's hit-pool changes (new_entry/dropped)

Dropped from TickFlow (out of V1 scope): "market" (index moves, V2), "ladder"
(A-share limit-up seal monitoring).

Rules persist one-JSON-per-file under ``~/.tradingagents/monitor_rules/`` (mirrors
store.py's single-file, no-database approach). The condition field whitelist is
the set of columns the strategy DataAdapter produces, so a rule can only ever
reference a field the monitor engine can actually evaluate.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_RULES_DIR = Path(os.path.expanduser("~")) / ".tradingagents" / "monitor_rules"

ID_RE = re.compile(r"^[a-z0-9_]{1,40}$")
RULE_TYPES = {"price", "signal", "strategy"}
SCOPES = {"symbols", "all"}
LOGICS = {"and", "or"}
DIRECTIONS = {"entry", "exit", "both"}
SEVERITIES = {"info", "warn", "critical"}
OPS = {">", ">=", "<", "<=", "==", "!="}

# Threshold-comparable numeric fields (subset of DataAdapter output columns).
ALLOWED_FIELDS: frozenset[str] = frozenset({
    "open", "high", "low", "close", "volume", "amount",
    "prev_close", "change_pct", "amplitude", "turnover_rate", "vol_ratio",
    "pe", "change_60d", "market_cap",
    "ma5", "ma10", "ma20", "ma60",
    "rsi_14", "macd_dif", "macd_dea", "macd_hist",
    "boll", "boll_upper", "boll_lower", "atr_14",
    "vol_ratio_5d", "momentum_5d", "momentum_20d", "momentum_60d",
    "high_60d", "low_60d", "annual_vol_20d",
})

# Boolean signal columns (op == "truth").
_SIGNAL_PREFIX = "signal_"


def _dir() -> Path:
    _RULES_DIR.mkdir(parents=True, exist_ok=True)
    return _RULES_DIR


def _path(rule_id: str) -> Path:
    return _dir() / f"{rule_id}.json"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def load_all() -> list[dict]:
    """Load all monitor rules. Corrupt files are skipped (best-effort)."""
    out: list[dict] = []
    for f in sorted(_dir().glob("*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            logger.warning("monitor rule load failed %s: %s", f.name, e)
    return out


def load_one(rule_id: str) -> dict | None:
    p = _path(rule_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning("monitor rule load failed %s: %s", rule_id, e)
        return None


def save_one(rule: dict) -> None:
    _path(rule["id"]).write_text(
        json.dumps(rule, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def delete_one(rule_id: str) -> bool:
    p = _path(rule_id)
    if p.exists():
        p.unlink()
        return True
    return False


# ---------------------------------------------------------------------------
# Validation + normalization
# ---------------------------------------------------------------------------


def _is_signal_field(field: str) -> bool:
    return field.startswith(_SIGNAL_PREFIX)


def validate(rule: dict) -> None:
    """Validate a rule; raise ValueError (with a Chinese message) if invalid."""
    rid = rule.get("id", "")
    if not isinstance(rid, str) or not ID_RE.match(rid):
        raise ValueError(f"规则 id 非法(仅小写字母数字下划线,1-40字符): {rid!r}")
    if not isinstance(rule.get("name"), str) or not rule["name"].strip():
        raise ValueError("规则 name 不能为空")
    rtype = rule.get("type")
    if rtype not in RULE_TYPES:
        raise ValueError(f"type 必须是 {sorted(RULE_TYPES)} 之一")

    if rtype == "strategy":
        if not rule.get("strategy_id"):
            raise ValueError("strategy 类型规则必须指定 strategy_id")
        if rule.get("direction", "entry") not in DIRECTIONS:
            raise ValueError(f"direction 必须是 {sorted(DIRECTIONS)} 之一")
        if not rule.get("market"):
            raise ValueError("strategy 类型规则必须指定 market (hk/us/cn)")
    else:
        conds = rule.get("conditions")
        if not isinstance(conds, list) or not conds:
            raise ValueError("price/signal 类型规则的 conditions 不能为空")
        if len(conds) > 8:
            raise ValueError("conditions 最多 8 条")
        if rule.get("logic", "and") not in LOGICS:
            raise ValueError(f"logic 必须是 {sorted(LOGICS)} 之一")
        for i, c in enumerate(conds):
            if not isinstance(c, dict):
                raise ValueError(f"第 {i+1} 个条件格式错误")
            field = c.get("field", "")
            op = c.get("op", "")
            if op == "truth":
                if not _is_signal_field(field):
                    raise ValueError(
                        f"第 {i+1} 个条件: op=truth 时 field 必须是信号列(signal_ 前缀): {field!r}")
            elif op in OPS:
                if field not in ALLOWED_FIELDS:
                    raise ValueError(f"第 {i+1} 个条件: 阈值字段 {field!r} 不在白名单")
                if not isinstance(c.get("value"), (int, float)):
                    raise ValueError(f"第 {i+1} 个条件: value 必须是数字")
            else:
                raise ValueError(f"第 {i+1} 个条件: op {op!r} 非法(应为 truth 或 {sorted(OPS)})")

    scope = rule.get("scope", "symbols")
    if scope not in SCOPES:
        raise ValueError(f"scope 必须是 {sorted(SCOPES)} 之一")
    if scope == "symbols" and not rule.get("symbols"):
        raise ValueError("scope=symbols 时 symbols 不能为空")

    if rule.get("severity", "info") not in SEVERITIES:
        raise ValueError(f"severity 必须是 {sorted(SEVERITIES)} 之一")
    cd = rule.get("cooldown_seconds", 3600)
    if not isinstance(cd, int) or cd < 0:
        raise ValueError("cooldown_seconds 必须是非负整数")


def normalize(rule: dict) -> dict:
    """Fill defaults; return a normalized copy (does not validate)."""
    r = dict(rule)
    r.setdefault("enabled", True)
    r.setdefault("scope", "symbols")
    r.setdefault("symbols", [])
    r.setdefault("market", "hk")
    r.setdefault("strategy_id", None)
    r.setdefault("direction", "entry")
    r.setdefault("conditions", [])
    r.setdefault("logic", "and")
    r.setdefault("cooldown_seconds", 3600)
    r.setdefault("severity", "info")
    r.setdefault("message", "")
    r.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    return r
