"""Monitor rules + alert store + monitor engine isolation tests (no network)."""

from unittest import mock

import polars as pl
import pytest


# ---------------------------------------------------------------------------
# monitor_rules: validate / normalize / CRUD
# ---------------------------------------------------------------------------


@pytest.fixture
def rules_mod(tmp_path, monkeypatch):
    from tradingagents.strategy import monitor_rules

    monkeypatch.setattr(monitor_rules, "_RULES_DIR", tmp_path / "monitor_rules")
    return monitor_rules


@pytest.mark.unit
class TestMonitorRules:
    def _price_rule(self):
        return {
            "id": "r_price", "name": "价格告警", "type": "price",
            "scope": "symbols", "symbols": ["00700.HK"],
            "conditions": [{"field": "change_pct", "op": ">", "value": 0.05}],
        }

    def test_valid_price_rule_passes(self, rules_mod):
        rules_mod.validate(rules_mod.normalize(self._price_rule()))

    def test_valid_signal_rule_passes(self, rules_mod):
        r = rules_mod.normalize({
            "id": "r_sig", "name": "金叉", "type": "signal",
            "scope": "all",
            "conditions": [{"field": "signal_macd_golden", "op": "truth"}],
        })
        rules_mod.validate(r)

    def test_strategy_rule_requires_strategy_id(self, rules_mod):
        r = rules_mod.normalize({"id": "r_s", "name": "s", "type": "strategy",
                                 "scope": "all", "market": "hk"})
        with pytest.raises(ValueError, match="strategy_id"):
            rules_mod.validate(r)

    def test_bad_id_rejected(self, rules_mod):
        r = self._price_rule()
        r["id"] = "Bad ID!"
        with pytest.raises(ValueError, match="id"):
            rules_mod.validate(rules_mod.normalize(r))

    def test_threshold_field_not_in_whitelist_rejected(self, rules_mod):
        r = rules_mod.normalize({
            "id": "r_x", "name": "x", "type": "price", "scope": "all",
            "conditions": [{"field": "not_a_field", "op": ">", "value": 1}],
        })
        with pytest.raises(ValueError, match="白名单"):
            rules_mod.validate(r)

    def test_truth_op_requires_signal_field(self, rules_mod):
        r = rules_mod.normalize({
            "id": "r_x", "name": "x", "type": "signal", "scope": "all",
            "conditions": [{"field": "close", "op": "truth"}],
        })
        with pytest.raises(ValueError, match="signal_"):
            rules_mod.validate(r)

    def test_symbols_scope_requires_symbols(self, rules_mod):
        r = self._price_rule()
        r["scope"] = "symbols"
        r["symbols"] = []
        with pytest.raises(ValueError, match="symbols"):
            rules_mod.validate(rules_mod.normalize(r))

    def test_crud_roundtrip(self, rules_mod):
        r = rules_mod.normalize(self._price_rule())
        rules_mod.save_one(r)
        assert rules_mod.load_one("r_price")["name"] == "价格告警"
        assert any(x["id"] == "r_price" for x in rules_mod.load_all())
        assert rules_mod.delete_one("r_price") is True
        assert rules_mod.load_one("r_price") is None

    def test_normalize_fills_defaults(self, rules_mod):
        r = rules_mod.normalize({"id": "r", "name": "n", "type": "price"})
        assert r["enabled"] is True and r["cooldown_seconds"] == 3600
        assert r["logic"] == "and" and r["severity"] == "info"


# ---------------------------------------------------------------------------
# alert_store: append + query + prune
# ---------------------------------------------------------------------------


@pytest.fixture
def store_mod(tmp_path, monkeypatch):
    from webapp.backend import alert_store

    monkeypatch.setattr(alert_store, "_PATH", tmp_path / "alerts.jsonl")
    alert_store._write_count = 0
    return alert_store


@pytest.mark.unit
class TestAlertStore:
    def test_append_and_query_newest_first(self, store_mod):
        store_mod.append({"ts": 100, "rule_id": "a", "source": "price", "symbol": "X"})
        store_mod.append({"ts": 200, "rule_id": "b", "source": "signal", "symbol": "Y"})
        rows = store_mod.query()
        assert [r["ts"] for r in rows] == [200, 100]

    def test_query_filters_by_source(self, store_mod):
        store_mod.append({"ts": 1, "source": "price", "rule_id": "a"})
        store_mod.append({"ts": 2, "source": "signal", "rule_id": "b"})
        assert [r["rule_id"] for r in store_mod.query(source="signal")] == ["b"]

    def test_prune_drops_records_over_max(self, store_mod, monkeypatch):
        monkeypatch.setattr(store_mod, "MAX_RECORDS", 5)
        monkeypatch.setattr(store_mod, "PRUNE_EVERY", 1)
        import time
        now_ms = time.time() * 1000
        for i in range(12):
            store_mod.append({"ts": now_ms + i, "rule_id": str(i), "source": "price"})
        rows = store_mod.query(limit=100)
        assert len(rows) <= 5

    def test_prune_drops_old_records(self, store_mod, monkeypatch):
        monkeypatch.setattr(store_mod, "PRUNE_EVERY", 1)
        import time
        old_ts = (time.time() - 10 * 86400) * 1000  # older than MAX_DAYS=7
        new_ts = time.time() * 1000
        store_mod.append({"ts": old_ts, "rule_id": "old", "source": "price"})
        store_mod.append({"ts": new_ts, "rule_id": "new", "source": "price"})
        ids = [r["rule_id"] for r in store_mod.query(limit=100)]
        assert "new" in ids and "old" not in ids


# ---------------------------------------------------------------------------
# MonitorEngine: condition mask / scope / cooldown / strategy diff
# ---------------------------------------------------------------------------


def _frame():
    return pl.DataFrame({
        "symbol": ["00001.HK", "00002.HK", "00003.HK"],
        "name": ["A", "B", "C"],
        "close": [10.0, 20.0, 30.0],
        "change_pct": [0.08, -0.02, 0.03],
        "rsi_14": [25.0, 55.0, 72.0],
        "signal_macd_golden": [True, False, False],
    })


@pytest.mark.unit
class TestMonitorEngine:
    def test_price_threshold_rule_hits(self):
        from tradingagents.strategy.monitor import MonitorEngine

        eng = MonitorEngine()
        eng.set_rules([{
            "id": "r1", "name": "big move", "type": "price", "scope": "all",
            "conditions": [{"field": "change_pct", "op": ">", "value": 0.05}],
            "cooldown_seconds": 3600,
        }])
        events = eng.evaluate(_frame(), now=1000.0)
        assert [e["symbol"] for e in events] == ["00001.HK"]

    def test_signal_truth_rule_hits(self):
        from tradingagents.strategy.monitor import MonitorEngine

        eng = MonitorEngine()
        eng.set_rules([{
            "id": "r2", "name": "macd", "type": "signal", "scope": "all",
            "conditions": [{"field": "signal_macd_golden", "op": "truth"}],
        }])
        events = eng.evaluate(_frame(), now=1000.0)
        assert [e["symbol"] for e in events] == ["00001.HK"]
        assert "signal_macd_golden" in events[0]["signals"]

    def test_and_or_logic(self):
        from tradingagents.strategy.monitor import MonitorEngine

        eng = MonitorEngine()
        eng.set_rules([{
            "id": "r3", "name": "and", "type": "price", "scope": "all", "logic": "and",
            "conditions": [{"field": "change_pct", "op": ">", "value": 0.0},
                           {"field": "rsi_14", "op": "<", "value": 30}],
        }])
        events = eng.evaluate(_frame(), now=1000.0)
        assert [e["symbol"] for e in events] == ["00001.HK"]

    def test_missing_field_yields_no_hits(self):
        from tradingagents.strategy.monitor import MonitorEngine

        eng = MonitorEngine()
        eng.set_rules([{
            "id": "r4", "name": "x", "type": "price", "scope": "all",
            "conditions": [{"field": "nonexistent", "op": ">", "value": 1}],
        }])
        assert eng.evaluate(_frame(), now=1000.0) == []

    def test_scope_symbols_filters(self):
        from tradingagents.strategy.monitor import MonitorEngine

        eng = MonitorEngine()
        eng.set_rules([{
            "id": "r5", "name": "x", "type": "price",
            "scope": "symbols", "symbols": ["00003.HK"],
            "conditions": [{"field": "change_pct", "op": ">", "value": 0.0}],
        }])
        events = eng.evaluate(_frame(), now=1000.0)
        assert [e["symbol"] for e in events] == ["00003.HK"]

    def test_cooldown_dedup(self):
        from tradingagents.strategy.monitor import MonitorEngine

        eng = MonitorEngine()
        eng.set_rules([{
            "id": "r6", "name": "x", "type": "price", "scope": "all",
            "conditions": [{"field": "change_pct", "op": ">", "value": 0.05}],
            "cooldown_seconds": 3600,
        }])
        assert len(eng.evaluate(_frame(), now=1000.0)) == 1
        # Same rule+symbol within cooldown → no re-fire.
        assert eng.evaluate(_frame(), now=1000.0 + 100) == []
        # After cooldown → fires again.
        assert len(eng.evaluate(_frame(), now=1000.0 + 4000)) == 1

    def test_alert_handler_called(self):
        from tradingagents.strategy.monitor import MonitorEngine

        seen = []
        eng = MonitorEngine(alert_handler=seen.append)
        eng.set_rules([{
            "id": "r7", "name": "x", "type": "price", "scope": "all",
            "conditions": [{"field": "change_pct", "op": ">", "value": 0.05}],
        }])
        eng.evaluate(_frame(), now=1000.0)
        assert len(seen) == 1 and seen[0]["symbol"] == "00001.HK"

    def test_strategy_pool_diff_baseline_then_changes(self):
        from tradingagents.strategy.monitor import MonitorEngine

        # Fake engine whose run() returns a controllable hit list.
        fake = mock.MagicMock()
        fake.has.return_value = True
        pool = [{"symbol": "00001.HK", "name": "A", "close": 10.0, "change_pct": 0.08}]

        def _run(sid, as_of, precomputed=None):
            r = mock.MagicMock()
            r.rows = list(pool)
            return r
        fake.run.side_effect = _run

        eng = MonitorEngine()
        eng.set_strategy_engine(fake)
        eng.set_rules([{
            "id": "r8", "name": "策略池", "type": "strategy", "scope": "all",
            "strategy_id": "oversold_bounce", "market": "hk", "direction": "both",
            "cooldown_seconds": 0,
        }])
        # First poll = baseline, no alerts.
        assert eng.evaluate(_frame(), now=1.0) == []
        # Add a name → new_entry event.
        pool.append({"symbol": "00002.HK", "name": "B", "close": 20.0, "change_pct": 0.03})
        events = eng.evaluate(_frame(), now=2.0)
        assert [(e["type"], e["symbol"]) for e in events] == [("new_entry", "00002.HK")]
        # Remove both → dropped events.
        pool.clear()
        events = eng.evaluate(_frame(), now=3.0)
        assert {e["type"] for e in events} == {"dropped"}
