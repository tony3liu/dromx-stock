"""Signal Aggregator — a deterministic node that fuses the analyst signals.

The four structured analysts (Market / Sentiment / News / Fundamentals) each
emit a directional read with a confidence tier. Until now those structured
fields were rendered to markdown and then only consumed as prose by the
bull/bear debate. This node closes that gap: it parses each rendered report
back into a ``(direction, confidence)`` pair, computes a confidence-weighted
consensus, and — crucially — lists the explicit points of disagreement so the
researchers debate the real contested questions instead of re-discovering them.

It is a NON-LLM node (pure post-processing), which keeps it cheap and
deterministic, and it runs as the fan-in point after the parallel analysts and
before the Bull Researcher. When the optional analyst scorecard is available
(phase 3), it up-weights lenses with a strong historical hit-rate in the
current regime; absent that, every present signal is weighted purely by its
self-reported confidence.
"""

from __future__ import annotations

import logging

from tradingagents.agents.schemas import (
    AnalystSignal,
    SignalAggregation,
    _consensus_band,
    render_signal_aggregation,
)
from tradingagents.agents.utils.rating import (
    confidence_weight,
    direction_score,
    parse_analyst_signal,
    parse_scenarios,
    scenarios_expected_value,
    scenarios_skew_label,
)

# (state key, lens label) for each structured analyst report we aggregate.
_REPORT_LENSES: tuple[tuple[str, str], ...] = (
    ("market_report", "Technical"),
    ("sentiment_report", "Sentiment"),
    ("news_report", "News"),
    ("fundamentals_report", "Fundamentals"),
    ("industry_report", "Industry"),
)

logger = logging.getLogger(__name__)


def _agreement_level(scores: list[int]) -> str:
    """Qualitative agreement from the spread of signed direction scores."""
    if len(scores) < 2:
        return "n/a"
    has_bull = any(s > 0 for s in scores)
    has_bear = any(s < 0 for s in scores)
    spread = max(scores) - min(scores)
    if has_bull and has_bear and spread >= 3:
        return "Split"
    if spread <= 1:
        return "Strong"
    return "Moderate"


# Depth tiers for the adaptive-analysis routing. The aggregator picks one based
# on how contested / unusual the setup is; the graph then skips or deepens the
# debate accordingly. The variation in depth is itself a signal — an auto-
# triggered Deep Dive means "this name is not behaving normally, look closer".
DEPTH_QUICK = "Quick Scan"
DEPTH_STANDARD = "Standard"
DEPTH_DEEP = "Deep Dive"


def decide_analysis_depth(
    agreement: str,
    regime_report: str,
    accuracy_weights: dict[str, float] | None = None,
) -> tuple[str, str]:
    """Choose an analysis depth from the signal agreement and the regime.

    Returns ``(depth, reason)``. The reason is logged and shown so a Deep Dive
    reads as an explicit "this is unusual" flag rather than silent extra work.

    - **Deep Dive** when the lenses are Split, the regime is extreme (high
      volatility, especially with a trend that could be reversing), or a lens
      that historically misfires in this regime is carrying weight — the cases a
      senior desk slows down for.
    - **Quick Scan** when the lenses Strongly agree in a calm/normal regime —
      no contest to litigate, so don't spend debate rounds manufacturing one.
    - **Standard** otherwise.
    """
    weights = accuracy_weights or {}
    regime = (regime_report or "").lower()
    # Match the volatility phrase specifically — "high volatility" — not a bare
    # "high", which also appears in "Confidence: High" and would false-positive.
    high_vol = "high volatility" in regime
    downtrend = "downtrend" in regime

    if agreement == "Split":
        return DEPTH_DEEP, "analysts are split — deepening the debate to resolve the contested call"
    if high_vol:
        note = "high-volatility regime"
        if downtrend:
            note += " with a downtrend (reversal risk)"
        return DEPTH_DEEP, f"{note} — widening the risk debate"
    # A lens that has been notably UNreliable here (weight well below 1) is
    # carrying a signal: slow down rather than trust it at face value.
    if weights and min(weights.values(), default=1.0) <= 0.6:
        weak = min(weights, key=weights.get)
        return DEPTH_DEEP, f"the {weak} lens has a weak hit-rate in this regime — verifying before committing"

    if agreement == "Strong" and not high_vol:
        return DEPTH_QUICK, "analysts strongly agree in a calm regime — no contested question to debate"
    return DEPTH_STANDARD, "balanced setup — standard depth"


def _disagreements(signals: list[AnalystSignal]) -> list[str]:
    """List pairwise disagreements worth debating.

    A pair disagrees when their signed scores sit on opposite sides of neutral
    (one bullish, one bearish), or when one is firmly directional (|score| == 2)
    while the other is neutral. Same-side differences (Bullish vs Mildly
    Bullish) are not flagged — they are not a real contest.
    """
    scored = [s for s in signals if s.score is not None]
    out: list[str] = []
    for i in range(len(scored)):
        for j in range(i + 1, len(scored)):
            a, b = scored[i], scored[j]
            opposite = a.score * b.score < 0
            strong_vs_neutral = (
                (abs(a.score) == 2 and b.score == 0)
                or (abs(b.score) == 2 and a.score == 0)
            )
            if opposite or strong_vs_neutral:
                out.append(
                    f"{a.lens} reads {a.direction} but {b.lens} reads {b.direction}"
                    f" — reconcile which signal the tape is actually confirming."
                )
    return out


def aggregate_signals(
    state,
    *,
    accuracy_notes: dict[str, str] | None = None,
    accuracy_weights: dict[str, float] | None = None,
) -> SignalAggregation:
    """Build the SignalAggregation from the rendered analyst reports in ``state``.

    ``accuracy_notes`` (phase 3) maps a lens label to a short historical
    hit-rate string for the current regime; when present it annotates the
    signal. ``accuracy_weights`` maps a lens to a multiplier (``[0.5, 1.5]``)
    that scales its confidence weight, so lenses that have actually been right
    in this regime carry more of the consensus.
    """
    accuracy_notes = accuracy_notes or {}
    accuracy_weights = accuracy_weights or {}
    signals: list[AnalystSignal] = []
    # (probability, magnitude) pairs across all analysts' scenario legs, each
    # leg's probability scaled by the analyst's confidence×accuracy weight so a
    # high-confidence / historically-accurate analyst shapes more of the fused
    # distribution. Collected here and reduced to EV + skew below.
    fused_pairs: list[tuple[float, float]] = []
    for key, lens in _REPORT_LENSES:
        report = state.get(key) or ""
        direction, confidence = parse_analyst_signal(report)
        score = direction_score(direction)
        weight = confidence_weight(confidence) * accuracy_weights.get(lens, 1.0)
        note = accuracy_notes.get(lens)
        for _label, prob, magnitude in parse_scenarios(report):
            fused_pairs.append((prob * weight, magnitude))
        signals.append(
            AnalystSignal(
                lens=lens,
                direction=direction,
                confidence=confidence,
                score=score,
                weight=weight,
                accuracy_note=note,
            )
        )

    scored = [s for s in signals if s.score is not None]
    total_weight = sum(s.weight for s in scored)
    weighted_score = (
        sum(s.score * s.weight for s in scored) / total_weight if total_weight else 0.0
    )
    consensus = _consensus_band(weighted_score)
    agreement = _agreement_level([s.score for s in scored])
    disagreements = _disagreements(signals)
    expected_value_pct = scenarios_expected_value(fused_pairs)
    payoff_skew = scenarios_skew_label(fused_pairs) if expected_value_pct is not None else None

    return SignalAggregation(
        consensus_direction=consensus,
        weighted_score=weighted_score,
        agreement=agreement,
        signals=signals,
        disagreements=disagreements,
        expected_value_pct=expected_value_pct,
        payoff_skew=payoff_skew,
    )


def create_signal_aggregator():
    """Create the deterministic signal-aggregation node (no LLM).

    Reads the analyst scorecard (when configured) so the consensus up-weights
    lenses that have historically been accurate in the current market regime.
    """

    def signal_aggregator_node(state):
        from tradingagents.agents.utils.signal_tracker import (
            AnalystScorecard,
            extract_trend,
        )
        from tradingagents.dataflows.config import get_config

        notes: dict[str, str] = {}
        weights: dict[str, float] = {}
        try:
            scorecard = AnalystScorecard(get_config())
            trend = extract_trend(state.get("regime_report", ""))
            notes = scorecard.accuracy_notes(trend)
            weights = scorecard.accuracy_weights(trend)
        except Exception:  # noqa: BLE001 — scorecard is best-effort, never block
            notes, weights = {}, {}

        aggregation = aggregate_signals(
            state, accuracy_notes=notes, accuracy_weights=weights
        )

        # Adaptive depth: decide how hard to work this name from how contested /
        # unusual the setup is, and surface the reason so a Deep Dive reads as an
        # explicit "this is unusual" flag.
        depth, reason = decide_analysis_depth(
            aggregation.agreement, state.get("regime_report", ""), weights
        )
        logger.info("Analysis depth: %s — %s", depth, reason)
        rendered = render_signal_aggregation(aggregation)
        rendered += f"\n\n**Analysis depth:** {depth} — {reason}."
        return {
            "signal_aggregation": rendered,
            "analysis_depth": depth,
        }

    return signal_aggregator_node
