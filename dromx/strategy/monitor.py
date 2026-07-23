"""Monitor engine (v0.4.0 Phase 2) — evaluate rules against a market snapshot.

Adapted from TickFlow's ``MonitorRuleEngine`` (monitor.py:295), trimmed to the
V1 rule types (price / signal / strategy). Given the enriched full-market
DataFrame (from ``DataAdapter.load_universe``), it evaluates every enabled rule
and returns AlertEvent dicts, deduped by a per-(rule, symbol) cooldown.

Reused verbatim from TickFlow: the condition mask (AND/OR over threshold +
boolean-signal conditions), scope filtering, cooldown dedup. Dropped: ladder
(A-share seal), history_loader (A-share reversal patterns), quote_service push.

price/signal rules → condition match on the snapshot row.
strategy rules → run the screening engine and diff the hit-pool vs last poll
(new_entry / dropped), first poll records the baseline only.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

import polars as pl

logger = logging.getLogger(__name__)

_OP_BUILDERS: dict[str, Callable[[pl.Expr, float], pl.Expr]] = {
    ">": lambda c, v: c > v,
    ">=": lambda c, v: c >= v,
    "<": lambda c, v: c < v,
    "<=": lambda c, v: c <= v,
    "==": lambda c, v: c == v,
    "!=": lambda c, v: c != v,
}

# Field/signal → Chinese label for alert messages.
_FIELD_CN = {
    "close": "收盘价", "change_pct": "涨跌幅", "turnover_rate": "换手率",
    "vol_ratio_5d": "5日量比", "rsi_14": "RSI14", "ma20": "MA20", "ma60": "MA60",
    "momentum_20d": "20日动量", "amount": "成交额",
    "signal_ma_golden_5_20": "MA5上穿MA20", "signal_macd_golden": "MACD金叉",
    "signal_ma20_breakout": "突破MA20", "signal_n_day_high": "60日新高",
    "signal_boll_breakout_upper": "突破布林上轨", "signal_volume_surge": "放量",
}


def _cn(field: str) -> str:
    return _FIELD_CN.get(field, field)


def _build_condition_mask(df: pl.DataFrame, conditions: list[dict], logic: str) -> pl.DataFrame:
    """Filter df to rows matching conditions combined by AND/OR (ported)."""
    cols = set(df.columns)
    parts: list[pl.Expr] = []
    for c in conditions:
        field = c.get("field", "")
        if field not in cols:
            return df.head(0)  # field absent → cannot judge → no hits
        op = c.get("op", "")
        if op == "truth":
            parts.append(pl.col(field).fill_null(False))
        elif op in _OP_BUILDERS:
            parts.append(_OP_BUILDERS[op](pl.col(field), c["value"]))
        else:
            return df.head(0)
    if not parts:
        return df.head(0)
    mask = pl.any_horizontal(parts) if logic == "or" else pl.all_horizontal(parts)
    return df.filter(mask)


class MonitorEngine:
    """Evaluate monitor rules against a snapshot; emit deduped alert events."""

    def __init__(self, alert_handler: Callable[[dict], None] | None = None):
        self._alert_handler = alert_handler
        self._rules: dict[str, dict] = {}
        self._last_fire: dict[tuple[str, str], float] = {}
        self._strategy_engine = None
        # strategy_id → last poll's hit-pool (for new_entry / dropped diff).
        self._strategy_pools: dict[str, set[str]] = {}

    def set_strategy_engine(self, engine) -> None:
        self._strategy_engine = engine

    def set_rules(self, rules: list[dict]) -> None:
        self._rules = {r["id"]: r for r in rules if r.get("enabled", True)}
        logger.info("MonitorEngine: loaded %d enabled rules", len(self._rules))

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, df: pl.DataFrame, *, now: float | None = None) -> list[dict]:
        """Evaluate all rules against the snapshot; return triggered events."""
        if not self._rules or df is None or df.is_empty():
            return []
        now = now if now is not None else time.time()
        events: list[dict] = []
        for rule_id, rule in self._rules.items():
            try:
                events.extend(self._evaluate_rule(df, rule, now))
            except Exception as e:  # noqa: BLE001 — one bad rule must not stop the rest
                logger.warning("rule eval failed %s: %s", rule_id, e)
        return events

    def _evaluate_rule(self, df: pl.DataFrame, rule: dict, now: float) -> list[dict]:
        scoped = self._apply_scope(df, rule)
        if scoped.is_empty():
            return []

        rtype = rule.get("type", "signal")
        # (event_type, symbol, name, price, pct, signals)
        hit_rows: list[tuple[str, str, Any, Any, Any, list[str]]] = []
        if rtype == "strategy":
            hit_rows = self._match_strategy(scoped, rule)
        else:
            for sym, name, price, pct, sigs in self._match_conditions(scoped, rule):
                hit_rows.append((rtype, sym, name, price, pct, sigs))

        if not hit_rows:
            return []

        cooldown = rule.get("cooldown_seconds", 3600)
        severity = rule.get("severity", "info")
        events: list[dict] = []
        for ev_type, sym, name, price, pct, sigs in hit_rows:
            key = (rule["id"], sym)
            last = self._last_fire.get(key)
            if last is not None and (now - last) < cooldown:
                continue
            self._last_fire[key] = now
            message = rule.get("message", "") or self._default_message(
                rule, ev_type, sym, name, pct, price, sigs)
            ev = {
                "ts": int(now * 1000),
                "rule_id": rule["id"],
                "rule_name": rule.get("name", ""),
                "source": rtype,
                "type": ev_type,
                "symbol": sym,
                "name": name or sym,
                "message": message,
                "price": price,
                "change_pct": pct,
                "signals": sigs,
                "severity": severity,
            }
            events.append(ev)
            if self._alert_handler:
                try:
                    self._alert_handler(ev)
                except Exception as e:  # noqa: BLE001
                    logger.warning("alert handler failed: %s", e)
        return events

    @staticmethod
    def _apply_scope(df: pl.DataFrame, rule: dict) -> pl.DataFrame:
        scope = rule.get("scope", "symbols")
        if scope == "all":
            return df
        syms = rule.get("symbols", [])
        if not syms or "symbol" not in df.columns:
            return df.head(0)
        return df.filter(pl.col("symbol").is_in(syms))

    @staticmethod
    def _match_conditions(
        df: pl.DataFrame, rule: dict,
    ) -> list[tuple[str, Any, Any, Any, list[str]]]:
        conditions = rule.get("conditions", [])
        logic = rule.get("logic", "and")
        if not conditions:
            return []
        hit = _build_condition_mask(df, conditions, logic)
        results = []
        for row in hit.iter_rows(named=True):
            sym = row.get("symbol", "")
            name = row.get("name")
            price = row.get("close")
            pct = row.get("change_pct")
            sigs = [c["field"] for c in conditions
                    if c.get("op") == "truth" and row.get(c["field"])]
            results.append((sym, name, price, pct, sigs))
        return results

    def _match_strategy(
        self, df: pl.DataFrame, rule: dict,
    ) -> list[tuple[str, str, Any, Any, Any, list[str]]]:
        """Run the strategy and diff its hit-pool vs the last poll.

        Returns new_entry / dropped events. First poll records the baseline and
        returns nothing (so we don't alert the entire pool on startup).
        """
        if self._strategy_engine is None:
            return []
        sid = rule.get("strategy_id")
        direction = rule.get("direction", "entry")
        if not sid or not self._strategy_engine.has(sid):
            return []

        from datetime import date
        try:
            result = self._strategy_engine.run(sid, date.today(), precomputed=df)
        except Exception as e:  # noqa: BLE001
            logger.warning("strategy %s screen failed: %s", sid, e)
            return []

        current = {r["symbol"] for r in result.rows}
        row_map = {r["symbol"]: r for r in result.rows}
        prev = self._strategy_pools.get(sid)
        self._strategy_pools[sid] = current
        if prev is None:
            return []  # baseline poll — no alerts

        out: list[tuple[str, str, Any, Any, Any, list[str]]] = []
        if direction in ("entry", "both"):
            for sym in sorted(current - prev):
                r = row_map.get(sym, {})
                out.append(("new_entry", sym, r.get("name"), r.get("close"),
                            r.get("change_pct"), []))
        if direction in ("exit", "both"):
            for sym in sorted(prev - current):
                out.append(("dropped", sym, None, None, None, []))
        return out

    @staticmethod
    def _default_message(rule: dict, ev_type: str, sym: str, name: str | None,
                         pct: Any, price: Any, sigs: list[str]) -> str:
        label = name or sym
        rtype = rule.get("type", "signal")
        if rtype == "strategy":
            sname = rule.get("name", rule.get("strategy_id", ""))
            verb = "新入选" if ev_type == "new_entry" else "移出"
            return f"{sname} · {label} {verb}"
        if sigs:
            return f"{label} 触发信号: {'/'.join(_cn(s) for s in sigs)}"
        # threshold rule: summarise the conditions
        conds = rule.get("conditions", [])
        desc = " ".join(
            f"{_cn(c['field'])}{c.get('op','')}{c.get('value','')}" for c in conds
        )
        pct_txt = f" (涨跌 {pct*100:.2f}%)" if isinstance(pct, (int, float)) else ""
        return f"{label} 满足 {desc}{pct_txt}"
