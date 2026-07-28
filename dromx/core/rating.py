"""Shared 5-tier rating vocabulary and a deterministic heuristic parser.

The same five-tier scale (Buy, Overweight, Hold, Underweight, Sell) is used by:
- The Research Manager (investment plan recommendation)
- The Portfolio Manager (final position decision)
- The signal processor (rating extracted for downstream consumers)
- The memory log (rating tag stored alongside each decision entry)

Centralising it here avoids drift between those call sites.
"""

from __future__ import annotations

import re

# Canonical, ordered 5-tier scale (most bullish to most bearish).
RATINGS_5_TIER: tuple[str, ...] = (
    "Buy", "Overweight", "Hold", "Underweight", "Sell",
)

_RATING_SET = {r.lower() for r in RATINGS_5_TIER}

# Matches "Rating: X" / "rating - X" / "Rating: **X**" / Chinese "评级：X" —
# tolerates markdown bold wrappers and a half/full-width colon or hyphen.
_RATING_LABEL_RE = re.compile(r"(?:rating|评级).*?[:：\-][\s*]*([A-Za-z]+)", re.IGNORECASE)


def parse_rating(text: str, default: str = "Hold") -> str:
    """Heuristically extract a 5-tier rating from prose text.

    Two-pass strategy:
    1. Look for an explicit "Rating: X" label (tolerant of markdown bold).
    2. Fall back to the first 5-tier rating word found anywhere in the text.

    Returns a Title-cased rating string, or ``default`` if no rating word appears.
    """
    for line in text.splitlines():
        m = _RATING_LABEL_RE.search(line)
        if m and m.group(1).lower() in _RATING_SET:
            return m.group(1).capitalize()

    for line in text.splitlines():
        for word in line.lower().split():
            clean = word.strip("*:.,")
            if clean in _RATING_SET:
                return clean.capitalize()

    return default


# ---------------------------------------------------------------------------
# Structured analyst-signal parsing (consumed by the Signal Aggregator and the
# analyst-accuracy scorecard).
#
# The four structured analysts render a deterministic first-line header:
#   - Market/News/Fundamentals: ``**<Lens> View:** **<Direction>** (Confidence: <Conf>)``
#   - Sentiment:                 ``**Overall Sentiment:** **<Band>** (Score: x/10)``
#                                followed by ``**Confidence:** <Conf>``
# We re-extract direction + confidence from that rendered markdown rather than
# threading the Pydantic objects through the graph, so the aggregator stays a
# pure post-processing step and free-text fallbacks degrade gracefully (a miss
# returns ``None``, which the aggregator treats as "no signal").
# ---------------------------------------------------------------------------

# Directional vocabulary shared by AnalystDirection and SentimentBand, mapped to
# a signed score. "Mixed" (sentiment-only) sits at neutral. Longer phrases are
# listed first so "Mildly Bullish" matches before "Bullish".
_DIRECTION_SCORES: tuple[tuple[str, int], ...] = (
    ("mildly bullish", 1),
    ("mildly bearish", -1),
    ("bullish", 2),
    ("bearish", -2),
    ("neutral", 0),
    ("mixed", 0),
)

# Multilingual aliases → canonical English direction phrase. Needed because the
# structured-output header is always English (enum .value), but when a provider
# intermittently misses structured output the free-text fallback returns prose
# in the configured output language (e.g. Chinese 看涨/看跌). Without these the
# parser returned None for that analyst and the Signal Aggregator showed "—".
# Order matters: qualified phrases ("温和看涨") MUST precede the base form
# ("看涨") since the base is a substring of the qualified one.
_DIRECTION_ALIASES: tuple[tuple[str, str], ...] = (
    # Chinese — mildly first (they contain the base term as a substring)
    ("温和看涨", "Mildly Bullish"),
    ("谨慎看涨", "Mildly Bullish"),
    ("偏多", "Mildly Bullish"),
    ("温和看跌", "Mildly Bearish"),
    ("谨慎看跌", "Mildly Bearish"),
    ("偏空", "Mildly Bearish"),
    ("看涨", "Bullish"),
    ("看多", "Bullish"),
    ("看跌", "Bearish"),
    ("看空", "Bearish"),
    ("中性", "Neutral"),
    ("中立", "Neutral"),
    ("观望", "Neutral"),
    ("混合", "Mixed"),
    ("分化", "Mixed"),
)

_CONFIDENCE_WEIGHTS = {"low": 0.5, "medium": 1.0, "high": 1.5}

# Multilingual confidence aliases → canonical English tier.
_CONFIDENCE_ALIASES: tuple[tuple[str, str], ...] = (
    ("高", "high"),
    ("中", "medium"),
    ("低", "low"),
)

_VIEW_RE = re.compile(
    r"\*\*(?:overall sentiment|综合情绪|[\w/ ]*view|[^*]*观点)[\:：]?\*\*\s*\*\*([^*]+)\*\*",
    re.IGNORECASE,
)
_CONFIDENCE_RE = re.compile(r"confidence[:\s*]*\*{0,2}(low|medium|high)", re.IGNORECASE)
# Chinese confidence, e.g. "置信度：高" / "信心 中" / "置信 低".
_CONFIDENCE_RE_ZH = re.compile(r"(?:置信度|信心|置信)[：:\s*]*\*{0,2}([高中低])")


def parse_direction(text: str) -> str | None:
    """Return the canonical direction phrase found in the report header, or None.

    Matches the bolded direction in the rendered header line first; falls back
    to the first directional phrase anywhere in the text, in English then in the
    multilingual aliases (so a non-English free-text fallback still parses).
    Returns the canonical Title-cased English phrase (e.g. ``"Mildly Bullish"``)
    or ``None`` when no directional word is present.
    """
    m = _VIEW_RE.search(text)
    candidates = [m.group(1).strip().lower()] if m else []
    # Fall back to scanning the whole text if the header didn't match cleanly.
    haystack = " ".join(candidates) if candidates else text.lower()
    for phrase, _score in _DIRECTION_SCORES:
        if phrase in haystack:
            return phrase.title()
    # Multilingual fallback (e.g. Chinese free-text when structured output missed).
    # Scan the captured header group if present, else the raw text (not lowered —
    # CJK is case-insensitive but lower() is harmless; we use the raw text so the
    # aliases match regardless).
    alias_haystack = m.group(1) if m else text
    for alias, canonical in _DIRECTION_ALIASES:
        if alias in alias_haystack:
            return canonical
    return None


def parse_confidence(text: str) -> str | None:
    """Return 'low' / 'medium' / 'high' from the report, or None if absent."""
    m = _CONFIDENCE_RE.search(text)
    if m:
        return m.group(1).lower()
    m = _CONFIDENCE_RE_ZH.search(text)
    if m:
        return dict(_CONFIDENCE_ALIASES)[m.group(1)]
    return None


def parse_analyst_signal(text: str) -> tuple[str | None, str | None]:
    """Extract ``(direction, confidence)`` from a rendered analyst report.

    Either element is ``None`` when the corresponding marker is missing, so the
    aggregator and scorecard can decide how to treat an incomplete signal.
    """
    if not text:
        return None, None
    return parse_direction(text), parse_confidence(text)


def direction_score(direction: str | None) -> int | None:
    """Map a direction phrase to its signed score (Bullish +2 … Bearish −2)."""
    if not direction:
        return None
    key = direction.strip().lower()
    for phrase, score in _DIRECTION_SCORES:
        if phrase == key:
            return score
    return None


def confidence_weight(confidence: str | None) -> float:
    """Map a confidence tier to its weight; unknown/None defaults to medium (1.0)."""
    if not confidence:
        return 1.0
    return _CONFIDENCE_WEIGHTS.get(confidence.strip().lower(), 1.0)


# ---------------------------------------------------------------------------
# Scenario-distribution parsing (P1-A).
#
# The structured analysts now express their view as a probability distribution
# (bear / base / bull), rendered as a deterministic markdown table by
# ``schemas._render_scenarios``. The Signal Aggregator re-parses that table back
# into (label, probability, magnitude) triples — the same "parse the rendered
# report" contract used for direction/confidence — and fuses them into a
# portfolio expected value and a payoff-skew read. A free-text fallback (no
# table) parses to an empty list, so the report simply contributes no EV.
# ---------------------------------------------------------------------------

# Matches a rendered scenario row: ``| Bull | 25% | +25% | trigger... |``.
# Captures (label, probability-percent, signed-magnitude-percent).
_SCENARIO_RE = re.compile(
    r"\|\s*(bull|base|bear)\b[^|]*\|\s*([0-9]+(?:\.[0-9]+)?)\s*%?\s*\|"
    r"\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*%?",
    re.IGNORECASE,
)


def parse_scenarios(text: str) -> list[tuple[str, float, float]]:
    """Extract ``(label, probability_fraction, magnitude_pct)`` triples from a report.

    ``probability_fraction`` is in [0, 1] (the rendered percent / 100);
    ``magnitude_pct`` is the signed expected move in percent. Returns an empty
    list when the report has no scenario table (e.g. a free-text fallback).
    """
    if not text:
        return []
    out: list[tuple[str, float, float]] = []
    for m in _SCENARIO_RE.finditer(text):
        try:
            out.append((m.group(1).lower(), float(m.group(2)) / 100.0, float(m.group(3))))
        except (TypeError, ValueError):  # pragma: no cover — regex guarantees numerics
            continue
    return out


def scenarios_expected_value(pairs) -> float | None:
    """Probability-weighted expected percent move, or None if no usable scenarios.

    ``pairs`` is an iterable of ``(probability, magnitude)``. Normalised by total
    probability so it is robust to probabilities that do not sum exactly to 1.
    """
    usable = [(p, m) for p, m in pairs if p is not None and m is not None and p > 0]
    total = sum(p for p, _ in usable)
    if total <= 0:
        return None
    return sum(p * m for p, m in usable) / total


def scenarios_skew_label(pairs) -> str:
    """Label the payoff asymmetry from a set of ``(probability, magnitude)`` pairs.

    Compares probability-weighted downside against upside. A distribution whose
    downside meaningfully outweighs its upside is "left-tailed" (size down), and
    vice versa — the asymmetry a senior desk sizes to, not just the direction.
    """
    usable = [(p, m) for p, m in pairs if p is not None and m is not None and p > 0]
    total = sum(p for p, _ in usable)
    if total <= 0:
        return "n/a"
    downside = sum(p * abs(m) for p, m in usable if m < 0) / total
    upside = sum(p * m for p, m in usable if m > 0) / total
    if downside > upside * 1.3:
        return "left-tailed (downside-skewed)"
    if upside > downside * 1.3:
        return "right-tailed (upside-skewed)"
    return "roughly symmetric"


# ---------------------------------------------------------------------------
# Position sizing (P1+-2): map the scenario distribution to a Kelly-based
# suggested position-size range, so the Portfolio Manager has a quantitative
# anchor instead of sizing by feel. We compute the FULL-KELLY fraction that
# maximises expected log-growth over the discrete scenario distribution, then
# return a deliberately conservative fraction of it (quarter-to-half Kelly) as a
# range, hard-capped. Kelly is notoriously aggressive and assumes the
# probabilities are exactly right; fractional Kelly is the standard practitioner
# hedge against estimation error.
# ---------------------------------------------------------------------------

# Cap any single-name suggestion. Full Kelly on a high-edge distribution can
# exceed 100%; a single position should never anchor the PM that high.
_MAX_POSITION_FRACTION = 0.25


def _kelly_growth(f: float, pairs) -> float:
    """Expected log-growth at bet fraction ``f`` over ``(prob, magnitude_pct)`` pairs.

    Returns ``-inf`` if any leg would bankrupt the book at this fraction
    (1 + f*r <= 0), which bounds the search to feasible fractions.
    """
    import math

    total = 0.0
    for p, m in pairs:
        r = m / 100.0
        equity = 1.0 + f * r
        if equity <= 0:
            return float("-inf")
        total += p * math.log(equity)
    return total


def full_kelly_fraction(pairs) -> float | None:
    """Full-Kelly capital fraction maximising expected log-growth over the scenarios.

    ``pairs`` is an iterable of ``(probability, magnitude_pct)`` (magnitude in
    percent, signed). Returns the optimal fraction in [0, ~], or ``None`` when
    there are no usable scenarios or the edge is non-positive (don't bet).
    Solved by a coarse-then-fine scan — the objective is concave in ``f`` so a
    grid refine is robust and dependency-free (no SciPy).
    """
    usable = [
        (p, m) for p, m in pairs
        if p is not None and m is not None and p > 0 and m is not None
    ]
    tot = sum(p for p, _ in usable)
    if tot <= 0:
        return None
    norm = [(p / tot, m) for p, m in usable]

    # No positive edge → Kelly says don't bet.
    if scenarios_expected_value([(p, m) for p, m in norm]) is None:
        return None
    ev = sum(p * (m / 100.0) for p, m in norm)
    if ev <= 0:
        return None

    lo, hi = 0.0, 5.0  # search up to 5x (leverage); we cap later anyway
    best_f = 0.0
    for _ in range(6):  # successive refinement of the bracket around the optimum
        step = (hi - lo) / 50.0
        if step <= 0:
            break
        best_val = float("-inf")
        f = lo
        while f <= hi + 1e-9:
            val = _kelly_growth(f, norm)
            if val > best_val:
                best_val, best_f = val, f
            f += step
        # Tighten the bracket to one step either side of the current optimum.
        lo, hi = max(0.0, best_f - step), best_f + step
    return best_f


def suggest_position_size(pairs, *, max_fraction: float = _MAX_POSITION_FRACTION) -> dict | None:
    """Suggest a position-size range from the scenario distribution.

    Returns ``{"low_pct", "high_pct", "full_kelly_pct", "note"}`` as percentages
    of the book, or ``None`` when there is no positive edge to size (Kelly = 0 →
    "no position warranted").

    The range is quarter-Kelly (low) to half-Kelly (high) — the conservative band
    practitioners use to absorb the fact that the scenario probabilities are
    estimates, not truth — each hard-capped at ``max_fraction``. The PM may
    deviate but must justify departing from this anchor.
    """
    fk = full_kelly_fraction(pairs)
    if fk is None or fk <= 0:
        return None
    quarter = min(fk * 0.25, max_fraction)
    half = min(fk * 0.5, max_fraction)
    capped = (fk * 0.5) > max_fraction
    if capped:
        note = (
            f"fractional Kelly (¼–½) on the fused scenario distribution; full "
            f"Kelly is {fk * 100:.0f}% (a strong one-period edge), so the range is "
            f"CAPPED at the {max_fraction * 100:.0f}% single-name ceiling — treat "
            f"{max_fraction * 100:.0f}% as a not-to-exceed anchor, not a target"
        )
    else:
        note = (
            "fractional Kelly (¼–½) on the fused scenario distribution, "
            f"capped at {max_fraction * 100:.0f}% of book"
        )
    return {
        "low_pct": round(quarter * 100, 1),
        "high_pct": round(half * 100, 1),
        "full_kelly_pct": round(fk * 100, 1),
        "capped": capped,
        "note": note,
    }

