"""Analyst-accuracy scorecard — signal-level memory keyed by market regime.

The decision-level memory log (``TradingMemoryLog``) records the final
BUY/SELL/HOLD call and a post-hoc reflection. This module adds a finer,
quantitative layer: for every run it records each analyst's directional read
(Bullish … Bearish) alongside the market regime at the time, then — once the
realized return is known — scores each read correct/wrong and accumulates a
hit-rate per ``(analyst lens, trend regime)``.

Two things consume it:
  * the Signal Aggregator up-weights lenses with a strong hit-rate in the
    current regime (and annotates the signal table with the record), so the
    consensus leans on whoever has actually been right in this kind of tape;
  * the Portfolio Manager can be shown the same summary as soft context.

Storage is a single JSON file (``analyst_scorecard_path`` in config). It holds
two parts: ``pending`` runs awaiting an outcome, and ``stats`` — the running
``{correct, wrong, total}`` tally keyed by ``"<lens>|<trend>"``. All writes are
atomic (temp file + ``os.replace``) so a crash mid-write never corrupts it.
Every method is a no-op when no path is configured.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dromx.agents.utils.rating import direction_score, parse_analyst_signal

logger = logging.getLogger(__name__)

# (state key, lens label) — must match the Signal Aggregator's lenses so the
# scorecard and the aggregation talk about the same analysts.
_REPORT_LENSES: tuple[tuple[str, str], ...] = (
    ("market_report", "Technical"),
    ("sentiment_report", "Sentiment"),
    ("news_report", "News"),
    ("fundamentals_report", "Fundamentals"),
    # Industry lens added in v0.4 so the Orchestrator can score/skip the industry
    # analyst too (must mirror signal_aggregator._REPORT_LENSES).
    ("industry_report", "Industry"),
)

# A directional call counts as correct when the realized return agrees in sign
# and clears this magnitude; smaller moves are treated as noise (no score).
_RETURN_NOISE_THRESHOLD = 0.01  # ±1%


def extract_trend(regime_report: str) -> str:
    """Pull the coarse trend label (Uptrend/Downtrend/Sideways) from the regime text.

    Returns ``"Unknown"`` when the regime report is empty or unparseable, so
    stats still accumulate under a stable bucket rather than being dropped.
    """
    if not regime_report:
        return "Unknown"
    low = regime_report.lower()
    for trend in ("uptrend", "downtrend", "sideways"):
        if trend in low:
            return trend.capitalize()
    return "Unknown"


class AnalystScorecard:
    """Persisted directional hit-rate per analyst lens and market regime."""

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        path = cfg.get("analyst_scorecard_path")
        self._path = Path(path).expanduser() if path else None
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    # --- IO helpers ---

    def _load(self) -> dict:
        if not self._path or not self._path.exists():
            return {"pending": [], "stats": {}}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            data.setdefault("pending", [])
            data.setdefault("stats", {})
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Scorecard unreadable (%s); starting fresh", exc)
            return {"pending": [], "stats": {}}

    def _save(self, data: dict) -> None:
        if not self._path:
            return
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)

    # --- Write path ---

    def record_run(self, ticker: str, trade_date: str, final_state: dict) -> None:
        """Append a pending record of each analyst's signal for this run.

        Idempotent on (trade_date, ticker): a re-run for the same key replaces
        the prior pending record rather than duplicating it.
        """
        if not self._path:
            return
        trend = extract_trend(final_state.get("regime_report", ""))
        signals: dict[str, dict] = {}
        for key, lens in _REPORT_LENSES:
            direction, confidence = parse_analyst_signal(final_state.get(key) or "")
            if direction is None:
                continue
            signals[lens] = {"direction": direction, "confidence": confidence}
        if not signals:
            return

        data = self._load()
        data["pending"] = [
            p for p in data["pending"]
            if not (p["ticker"] == ticker and p["trade_date"] == trade_date)
        ]
        data["pending"].append(
            {"ticker": ticker, "trade_date": trade_date, "trend": trend, "signals": signals}
        )
        self._save(data)

    # --- Resolve path ---

    def resolve(self, ticker: str, trade_date: str, raw_return: float) -> None:
        """Score the pending record for (ticker, trade_date) against the outcome.

        Each analyst's signed direction is compared with the sign of
        ``raw_return``; agreements increment ``correct``, disagreements
        ``wrong``. Near-flat outcomes (|return| < threshold) and Neutral reads
        are skipped (counted in neither) to avoid rewarding noise.
        """
        if not self._path:
            return
        data = self._load()
        match = None
        for p in data["pending"]:
            if p["ticker"] == ticker and p["trade_date"] == trade_date:
                match = p
                break
        if match is None:
            return

        if abs(raw_return) >= _RETURN_NOISE_THRESHOLD:
            outcome_sign = 1 if raw_return > 0 else -1
            for lens, sig in match["signals"].items():
                score = direction_score(sig.get("direction"))
                if not score:  # None or 0 (Neutral) — skip
                    continue
                bucket = f"{lens}|{match['trend']}"
                tally = data["stats"].setdefault(bucket, {"correct": 0, "wrong": 0, "total": 0})
                if (score > 0) == (outcome_sign > 0):
                    tally["correct"] += 1
                else:
                    tally["wrong"] += 1
                tally["total"] += 1

        data["pending"] = [
            p for p in data["pending"]
            if not (p["ticker"] == ticker and p["trade_date"] == trade_date)
        ]
        self._save(data)

    # --- Read path ---

    def accuracy_notes(self, trend: str, min_total: int = 3) -> dict[str, str]:
        """Return ``{lens: "Nn/Mm hit in <trend>"}`` for lenses with enough history.

        Only lenses with at least ``min_total`` scored calls in this trend are
        included, so the aggregator does not over-react to a single data point.
        """
        if not self._path:
            return {}
        stats = self._load()["stats"]
        notes: dict[str, str] = {}
        for bucket, tally in stats.items():
            lens, _, bucket_trend = bucket.partition("|")
            if bucket_trend != trend or tally["total"] < min_total:
                continue
            notes[lens] = f"{tally['correct']}/{tally['total']} in {trend}"
        return notes

    def accuracy_weights(self, trend: str, min_total: int = 3) -> dict[str, float]:
        """Return ``{lens: multiplier}`` to scale a lens's aggregation weight.

        Hit-rate ``h`` maps to a multiplier in ``[0.5, 1.5]`` (``0.5 + h``),
        so a 0%-accurate lens is halved and a 100%-accurate lens is 1.5×.
        Lenses below ``min_total`` are omitted (the aggregator leaves them at
        their confidence weight).
        """
        if not self._path:
            return {}
        stats = self._load()["stats"]
        weights: dict[str, float] = {}
        for bucket, tally in stats.items():
            lens, _, bucket_trend = bucket.partition("|")
            if bucket_trend != trend or tally["total"] < min_total:
                continue
            hit_rate = tally["correct"] / tally["total"]
            weights[lens] = 0.5 + hit_rate
        return weights

    def summary(self, trend: str, min_total: int = 1) -> str:
        """Human-readable hit-rate summary for the current trend, or "" if none."""
        if not self._path:
            return ""
        stats = self._load()["stats"]
        rows = []
        for bucket, tally in sorted(stats.items()):
            lens, _, bucket_trend = bucket.partition("|")
            if bucket_trend != trend or tally["total"] < min_total:
                continue
            rows.append(f"- {lens}: {tally['correct']}/{tally['total']} correct in {trend} regimes")
        if not rows:
            return ""
        return "Historical analyst hit-rates in this regime:\n" + "\n".join(rows)
