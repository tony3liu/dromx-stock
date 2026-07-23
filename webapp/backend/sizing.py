"""Position sizing over a finished run's fused scenario distribution (PRD §7 P1).

The engine already computes a fractional-Kelly size anchor inside Risk Consensus
(``rating.suggest_position_size``), but it is buried in the report prose — the
user can't plug in their own account size or risk appetite. This module exposes
that same, battle-tested Kelly math as structured data so the webapp can offer
an INTERACTIVE sizer: fused scenario distribution → full/half/quarter Kelly →
concrete position given the user's capital.

Read-only over a stored run: re-parses the analyst scenario tables from
``final_state`` (the same source the Signal Aggregator fuses) and reuses
``rating.full_kelly_fraction`` / ``suggest_position_size``. No new model.
"""

from __future__ import annotations

import logging

from . import store

logger = logging.getLogger(__name__)

# Analyst reports that carry a scenario table (matches risk_consensus._REPORT_KEYS).
_REPORT_KEYS = (
    "market_report", "sentiment_report", "news_report",
    "fundamentals_report", "industry_report",
)

_MAX_POSITION_FRACTION = 0.25  # single-name ceiling (matches rating._MAX_POSITION_FRACTION)


def _fuse_scenarios(pairs: list[tuple[float, float]]) -> list[dict]:
    """Collapse all lenses' legs into a probability-weighted bear/base/bull view.

    Each analyst emits (prob, magnitude) legs; we bucket by sign of magnitude
    into bear/flat/bull, prob-weight the magnitude within each bucket, and
    renormalise the bucket probabilities to sum to 1 — a compact distribution to
    show the user next to the Kelly output.
    """
    buckets = {"bear": [0.0, 0.0], "base": [0.0, 0.0], "bull": [0.0, 0.0]}
    for prob, mag in pairs:
        if prob is None or mag is None or prob <= 0:
            continue
        label = "bull" if mag > 1 else "bear" if mag < -1 else "base"
        buckets[label][0] += prob
        buckets[label][1] += prob * mag
    total_p = sum(b[0] for b in buckets.values())
    if total_p <= 0:
        return []
    out = []
    for label in ("bear", "base", "bull"):
        p, pm = buckets[label]
        if p <= 0:
            continue
        out.append({
            "label": label,
            "probability": round(p / total_p, 4),
            "magnitude_pct": round(pm / p, 2),  # prob-weighted mean move in bucket
        })
    return out


def build_sizing(run_id: str) -> dict | None:
    """Return the sizing model for a run, or ``None`` if the run doesn't exist."""
    from tradingagents.agents.utils.rating import (
        full_kelly_fraction,
        parse_scenarios,
        scenarios_expected_value,
        suggest_position_size,
    )

    rec = store.load_run(run_id)
    if rec is None:
        return None
    state = rec.get("final_state") or {}

    pairs: list[tuple[float, float]] = []
    for key in _REPORT_KEYS:
        for _label, prob, mag in parse_scenarios(state.get(key) or ""):
            pairs.append((prob, mag))

    if not pairs:
        return {
            "run_id": run_id, "ticker": rec.get("ticker"), "rating": rec.get("rating"),
            "has_scenarios": False,
            "scenarios": [], "expected_value_pct": None,
            "full_kelly_pct": None, "sizing": None, "max_fraction_pct": _MAX_POSITION_FRACTION * 100,
        }

    fk = full_kelly_fraction(pairs)
    ev = scenarios_expected_value(pairs)
    sizing = suggest_position_size(pairs)
    return {
        "run_id": run_id,
        "ticker": rec.get("ticker"),
        "rating": rec.get("rating"),
        "has_scenarios": True,
        "scenarios": _fuse_scenarios(pairs),
        "expected_value_pct": round(ev, 2) if ev is not None else None,
        "full_kelly_pct": round(fk * 100, 1) if fk else None,
        "sizing": sizing,  # {low_pct, high_pct, full_kelly_pct, capped, note} or None
        "max_fraction_pct": _MAX_POSITION_FRACTION * 100,
    }
