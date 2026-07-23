"""Structured analyst reports (regime, sentiment, market, news, fundamentals,
industry) sharing a directional spine + scenario distribution, and their renders."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ._shared import _NULLISH_FLOAT, _coerce_str_list, _conf_cn, _dir_cn


# ---------------------------------------------------------------------------
# Regime Detection (pre-analysis market-state node)
# ---------------------------------------------------------------------------


class TrendDirection(str, Enum):
    """Coarse trend direction of the instrument's recent price action."""

    UPTREND = "Uptrend"
    DOWNTREND = "Downtrend"
    SIDEWAYS = "Sideways"


class VolatilityLevel(str, Enum):
    """Coarse volatility regime, judged from ATR / recent range vs price."""

    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"


class RegimeReport(BaseModel):
    """Market-state classification produced before the analyst team runs.

    A lightweight, deterministic-input read of "what environment are we in"
    so downstream analysts can weight their lenses accordingly: trend-following
    setups favour technicals, range-bound/low-conviction tapes favour
    fundamentals, and high-volatility tapes warrant wider risk discussion.
    The classification is grounded in the verified market snapshot (OHLCV +
    moving averages + ATR + RSI), not free model recall.
    """

    trend_direction: TrendDirection = Field(
        description=(
            "Recent trend direction. Uptrend when price holds above rising "
            "medium/long moving averages; Downtrend when below falling ones; "
            "Sideways when price oscillates around flat averages."
        ),
    )
    volatility_level: VolatilityLevel = Field(
        description=(
            "Volatility regime judged from ATR and recent high-low range "
            "relative to price. High when ATR/range is elevated vs the trailing "
            "norm; Low when unusually compressed; Normal otherwise."
        ),
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description=(
            "Confidence in the regime read, based on how cleanly the snapshot "
            "supports it. Use 'low' when signals are mixed or the snapshot is "
            "sparse (e.g. a newly listed name with little history)."
        ),
    )
    analyst_weighting_hint: str = Field(
        description=(
            "One or two sentences of guidance for the downstream analyst team "
            "on how to weight their lenses in THIS regime — e.g. 'Trending tape: "
            "give technical momentum signals primary weight and treat mean-"
            "reversion setups skeptically' or 'Choppy, high-vol tape: lean on "
            "fundamentals and valuation, widen risk tolerances, discount short-"
            "term technical breakouts'."
        ),
    )
    narrative: str = Field(
        description=(
            "Concise evidence-based explanation of the regime call, citing the "
            "specific snapshot values (which moving averages, ATR level, RSI, "
            "recent range) that drove the trend and volatility classification."
        ),
    )


def render_regime_report(report: RegimeReport) -> str:
    """Render a RegimeReport to the markdown shape the rest of the system expects."""
    return "\n".join([
        f"**市场状态：** **{report.trend_direction.value} / "
        f"{report.volatility_level.value} volatility** "
        f"（置信度：{report.confidence.capitalize()}）",
        "",
        f"**分析师权重指引：** {report.analyst_weighting_hint}",
        "",
        report.narrative,
    ])


# ---------------------------------------------------------------------------
# Sentiment Analyst
# ---------------------------------------------------------------------------


class SentimentBand(str, Enum):
    """Discrete sentiment direction produced by the Sentiment Analyst.

    Six tiers keep the signal granular enough to be actionable while remaining
    small enough for every provider to map reliably from its JSON output.
    """

    BULLISH = "Bullish"
    MILDLY_BULLISH = "Mildly Bullish"
    NEUTRAL = "Neutral"
    MIXED = "Mixed"
    MILDLY_BEARISH = "Mildly Bearish"
    BEARISH = "Bearish"


class SentimentReport(BaseModel):
    """Structured sentiment report produced by the Sentiment Analyst.

    Replaces the previous free-form prose output so downstream consumers
    (dashboards, audit logs, PDF renderers, other agents) can read
    ``overall_band`` and ``overall_score`` without maintaining fragile regex
    fallbacks that drift with every model release. ``narrative`` preserves the
    rich source-by-source analysis; ``render_sentiment_report`` prepends a
    deterministic header so the saved report stays human-readable.
    """

    overall_band: SentimentBand = Field(
        description=(
            "Overall sentiment direction. Exactly one of: "
            "Bullish / Mildly Bullish / Neutral / Mixed / Mildly Bearish / Bearish. "
            "Use Mixed when sources point in clearly different directions. "
            "Use Neutral only when all sources are genuinely silent or non-committal."
        ),
    )
    overall_score: float = Field(
        ge=0.0,
        le=10.0,
        description=(
            "Numeric sentiment intensity on a 0–10 scale. "
            "0 = maximally bearish, 5 = neutral, 10 = maximally bullish. "
            "Guideline for consistency with overall_band: "
            "Bullish ~6.5–10, Mildly Bullish ~5.5–6.4, Neutral/Mixed ~4.5–5.5, "
            "Mildly Bearish ~3.5–4.4, Bearish ~0–3.4. "
            "Only the 0–10 bounds are enforced."
        ),
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description=(
            "Confidence in the assessment based on data quality and sample size. "
            "Use 'low' when one or more sources returned a placeholder or fewer "
            "than 5 data points; 'medium' when data is present but sparse; "
            "'high' when all three sources returned substantive data."
        ),
    )
    narrative: str = Field(
        description=(
            "Full sentiment report covering, in order: "
            "(1) source-by-source breakdown with specific evidence (cite message "
            "counts, ratios, notable posts); "
            "(2) cross-source divergences and alignments; "
            "(3) dominant narrative themes; "
            "(4) catalysts and risks surfaced by the data; "
            "(5) a markdown table summarising key sentiment signals, their "
            "direction, source, and supporting evidence. "
            "Keep it informative and substantive: develop each section thoroughly "
            "with concrete evidence so every point adds new signal for the trader."
        ),
    )


def render_sentiment_report(report: SentimentReport) -> str:
    """Render a SentimentReport to the markdown shape the rest of the system expects.

    The structured header (band + score + confidence) is prepended to the
    narrative so the saved report is both human-readable and machine-parseable
    without regex.
    """
    return "\n".join([
        f"**综合情绪：** **{_dir_cn(report.overall_band.value)}** "
        f"（评分：{report.overall_score:.1f}/10）",
        f"**置信度：** {_conf_cn(report.confidence)}",
        "",
        report.narrative,
    ])


# ---------------------------------------------------------------------------
# Market / News / Fundamentals analysts (structured, pre-fetch pattern)
# ---------------------------------------------------------------------------
#
# These three analysts moved from free-text tool-calling to the same pre-fetch +
# structured-output contract the Sentiment Analyst uses. A shared directional
# spine (direction + confidence + key_evidence + risks + narrative) makes the
# reports machine-readable for the downstream signal/debate layer, while each
# carries one domain-specific field. A common render helper keeps the saved
# markdown uniform.


class AnalystDirection(str, Enum):
    """Directional read shared by the structured analysts (5 tiers)."""

    BULLISH = "Bullish"
    MILDLY_BULLISH = "Mildly Bullish"
    NEUTRAL = "Neutral"
    MILDLY_BEARISH = "Mildly Bearish"
    BEARISH = "Bearish"


_DIRECTION_DESC = (
    "Directional read for this lens. Exactly one of: Bullish / Mildly Bullish / "
    "Neutral / Mildly Bearish / Bearish. Use Neutral only when the evidence is "
    "genuinely balanced or too thin to lean either way."
)


_CONFIDENCE_DESC = (
    "Confidence based on data quality and signal clarity: 'low' when inputs are "
    "sparse or conflicting, 'medium' when present but mixed, 'high' when the "
    "data is rich and points consistently one way."
)


_EVIDENCE_DESC = (
    "3–6 concrete, evidence-backed bullet points that drove the directional "
    "call. Cite specific numbers, levels, dates, or headlines from the data "
    "provided — not generic statements."
)


_RISKS_DESC = (
    "2–4 key risks or caveats that could invalidate this read (data gaps, "
    "conflicting signals, upcoming catalysts, look-ahead limits)."
)


class Scenario(BaseModel):
    """One leg of an analyst's probabilistic view (bear / base / bull).

    Replacing a single point-estimate direction with an explicit distribution is
    the difference between "I'm bullish" and "60% base case +12%, 25% bull +25%,
    15% bear −18%". It lets the downstream aggregator compute an expected value
    and a payoff skew, and it forces the analyst to name what would have to
    happen for each leg — the trigger — rather than asserting a single outcome.
    """

    label: Literal["bear", "base", "bull"] = Field(
        description="Which leg of the distribution: 'bear', 'base', or 'bull'.",
    )
    probability: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Probability of this leg as a fraction in [0, 1]. The three legs "
            "should sum to roughly 1.0 (the aggregator normalises, so small "
            "rounding is fine)."
        ),
    )
    magnitude_pct: float = Field(
        description=(
            "Expected price move for this leg, in percent, signed: e.g. +12 for "
            "a 12% gain (base/bull) or -18 for an 18% drop (bear). Measured over "
            "the analyst's stated horizon."
        ),
    )
    trigger: str = Field(
        description=(
            "The concrete, observable condition that would put this leg in play "
            "(e.g. 'data-center revenue beats the whisper number', 'a weekly "
            "close below the 50-day SMA', 'CapEx guidance cut'). One sentence."
        ),
    )

    @field_validator("magnitude_pct", mode="before")
    @classmethod
    def _magnitude_nullish_to_zero(cls, v):
        """Coerce a percent/placeholder string so a sloppy fill never errors.

        '+12%' -> 12.0; 'N/A' -> 0.0; real numbers pass through.
        """
        if isinstance(v, str):
            s = v.strip().rstrip("%").strip()
            if s.lower() in _NULLISH_FLOAT or s == "":
                return 0.0
            try:
                return float(s)
            except ValueError:
                return 0.0
        return v

    @field_validator("probability", mode="before")
    @classmethod
    def _probability_coerce(cls, v):
        """Strip placeholders/percent signs, then fold a percent to a fraction.

        '55%' -> 0.55; 55 -> 0.55; 0.55 -> 0.55; 'N/A' -> 0.0. Done in a single
        validator so the strip-then-fold order is deterministic (Pydantic runs
        multiple before-validators bottom-up, which made two split validators
        race).
        """
        if isinstance(v, str):
            s = v.strip().rstrip("%").strip()
            if s.lower() in _NULLISH_FLOAT or s == "":
                return 0.0
            try:
                v = float(s)
            except ValueError:
                return 0.0
        try:
            f = float(v)
        except (TypeError, ValueError):
            return v
        return f / 100.0 if f > 1.0 else f


_SCENARIOS_DESC = (
    "A 3-leg probability distribution for the price over your stated horizon: "
    "exactly one 'bear', one 'base', and one 'bull' Scenario. Probabilities "
    "should sum to roughly 1.0. This is the core of the modern read — give the "
    "distribution, not just a direction."
)


class MarketReport(BaseModel):
    """Structured technical/market-analysis report (pre-fetched indicators)."""

    direction: AnalystDirection = Field(description=_DIRECTION_DESC)
    direction_short_term: AnalystDirection = Field(
        description=(
            "Directional read over the SHORT term (roughly 1–5 trading days): "
            "what the near-term momentum, overbought/oversold readings, and the "
            "latest candles imply. Same 5-tier scale."
        ),
    )
    direction_medium_term: AnalystDirection = Field(
        description=(
            "Directional read over the MEDIUM term (roughly 1–3 months): what the "
            "moving-average stack and broader trend structure imply. Same 5-tier "
            "scale. It is normal for this to differ from the short-term read."
        ),
    )
    confidence: Literal["low", "medium", "high"] = Field(description=_CONFIDENCE_DESC)
    scenarios: list[Scenario] = Field(default_factory=list, description=_SCENARIOS_DESC)
    indicator_readout: str = Field(
        description=(
            "Interpretation of the verified indicator snapshot: trend (moving "
            "averages), momentum (RSI/MACD), volatility (ATR/Bollinger), and "
            "what they say together. Reference the actual values provided."
        ),
    )
    @field_validator("key_evidence", "risks", mode="before")
    @classmethod
    def _coerce_str_list_field(cls, v):
        return _coerce_str_list(v)

    key_evidence: list[str] = Field(description=_EVIDENCE_DESC)
    risks: list[str] = Field(description=_RISKS_DESC)
    narrative: str = Field(
        description=(
            "Full technical narrative for the trader: trend structure, key "
            "support/resistance levels grounded in the snapshot, momentum and "
            "volatility context, how the short-term and medium-term reads differ, "
            "and a markdown summary table of the indicators and their signals."
        ),
    )


class NewsReport(BaseModel):
    """Structured news/macro-analysis report (pre-fetched headlines + macro)."""

    direction: AnalystDirection = Field(description=_DIRECTION_DESC)
    confidence: Literal["low", "medium", "high"] = Field(description=_CONFIDENCE_DESC)
    scenarios: list[Scenario] = Field(default_factory=list, description=_SCENARIOS_DESC)
    game_changer: bool = Field(
        default=False,
        description=(
            "True if the news window contains an event that MATERIALLY changes "
            "the investment premise — a capital raise / dilution, M&A, a "
            "regulatory action, a management change, a guidance reset, a covenant "
            "or default event. Flag it even if it does NOT change your directional "
            "read: a thesis can survive directionally while its premises shift. "
            "Ordinary price moves, routine coverage, and sentiment swings are NOT "
            "game-changers."
        ),
    )
    game_changer_note: str = Field(
        default="",
        description=(
            "If game_changer is True, one or two sentences naming the specific "
            "event and what premise it changes (e.g. 'a $29B ADR raise dilutes "
            "per-share value and re-rates the capital structure'). Empty when "
            "game_changer is False."
        ),
    )
    macro_backdrop: str = Field(
        description=(
            "The macro/sector backdrop relevant to this name: rates, inflation, "
            "sector rotation, geopolitical or regulatory headlines from the "
            "provided news and macro data. State if the backdrop is a tailwind "
            "or headwind."
        ),
    )
    @field_validator("key_evidence", "risks", mode="before")
    @classmethod
    def _coerce_str_list_field(cls, v):
        return _coerce_str_list(v)

    key_evidence: list[str] = Field(description=_EVIDENCE_DESC)
    risks: list[str] = Field(description=_RISKS_DESC)
    narrative: str = Field(
        description=(
            "Full news narrative: company-specific developments, the macro "
            "backdrop, catalysts on the horizon, and a markdown summary table "
            "of key headlines with their likely market impact."
        ),
    )


class FundamentalsReport(BaseModel):
    """Structured fundamentals report (pre-fetched statements + overview)."""

    direction: AnalystDirection = Field(description=_DIRECTION_DESC)
    confidence: Literal["low", "medium", "high"] = Field(description=_CONFIDENCE_DESC)
    scenarios: list[Scenario] = Field(default_factory=list, description=_SCENARIOS_DESC)
    valuation_view: str = Field(
        description=(
            "Valuation and financial-health assessment grounded in the provided "
            "statements/overview: profitability and margins, growth trajectory "
            "(accelerating vs deteriorating), balance-sheet strength, and "
            "whether valuation looks rich, fair, or cheap given the numbers."
        ),
    )
    @field_validator("key_evidence", "risks", mode="before")
    @classmethod
    def _coerce_str_list_field(cls, v):
        return _coerce_str_list(v)

    key_evidence: list[str] = Field(description=_EVIDENCE_DESC)
    risks: list[str] = Field(description=_RISKS_DESC)
    narrative: str = Field(
        description=(
            "Full fundamental narrative: revenue/earnings trends, margin and "
            "cash-flow analysis, balance-sheet review, valuation framing, and a "
            "markdown summary table of the key financial metrics."
        ),
    )


class IndustryPhase(str, Enum):
    """Where the industry sits in its cycle."""

    EXPANSION = "Expansion"
    PEAK = "Peak"
    CONTRACTION = "Contraction"
    TROUGH = "Trough"
    UNCLEAR = "Unclear"


class MoatTrend(str, Enum):
    """Direction of the name's competitive moat within its industry."""

    WIDENING = "Widening"
    STABLE = "Stable"
    NARROWING = "Narrowing"
    UNCLEAR = "Unclear"


class IndustryReport(BaseModel):
    """Structured industry / supply-chain report (the missing sector lens).

    Answers the question no other analyst asks — "what is happening to the
    INDUSTRY?" — covering cycle position, competitive structure, supply-chain
    dependencies, and disruption risk. Because hard sector data (market share,
    capex trackers, supply-chain databases) is not available from the project's
    free vendors, this report leans on the fetched signals (sector news, peer
    financials, the name's own classification) PLUS the model's domain knowledge.
    Every claim must be tagged as derived-from-data or model-knowledge so the
    desk can weight it honestly.
    """

    direction: AnalystDirection = Field(description=_DIRECTION_DESC)
    confidence: Literal["low", "medium", "high"] = Field(description=_CONFIDENCE_DESC)
    scenarios: list[Scenario] = Field(default_factory=list, description=_SCENARIOS_DESC)
    industry_phase: IndustryPhase = Field(
        description=(
            "Where the industry is in its cycle: Expansion / Peak / Contraction "
            "/ Trough / Unclear. Judge from demand trend, capex behaviour, and "
            "pricing — state whether this read is from the data or your knowledge."
        ),
    )
    competitive_moat: MoatTrend = Field(
        description=(
            "Is THIS name's competitive moat Widening / Stable / Narrowing / "
            "Unclear within its industry — structural (share, technology lead, "
            "switching costs), not just a cyclical swing."
        ),
    )
    key_dependency: str = Field(
        description=(
            "The single most important upstream supplier or downstream customer "
            "dependency that could make or break the thesis (e.g. customer "
            "concentration, a sole-source input, a capacity bottleneck). One to "
            "two sentences."
        ),
    )
    disruption_risk: str = Field(
        description=(
            "The most credible technology / substitution / regulatory force that "
            "could erode the industry position over the horizon, and how near it "
            "is. One to two sentences."
        ),
    )
    competition_matrix: str = Field(
        default="",
        description=(
            "A markdown horizontal comparison table of the direct competitors "
            "(this name + its peers) when peer financials are available. Rows = "
            "each player; columns = the dimensions that decide the race (e.g. "
            "product/tech status, market share, positioning strength, key "
            "metric). Tag each cell [data] (from peer financials/news) or "
            "[knowledge] (from training). Empty when no peers are configured or "
            "the name has no clear competitive set."
        ),
    )
    @field_validator("key_evidence", "risks", mode="before")
    @classmethod
    def _coerce_str_list_field(cls, v):
        return _coerce_str_list(v)

    key_evidence: list[str] = Field(
        description=(
            _EVIDENCE_DESC
            + " CRITICAL: tag each point as [data] (from the fetched news / peer "
            "financials / classification) or [knowledge] (from your own training "
            "/ domain knowledge), so the desk can weight verifiable facts above "
            "model recall."
        ),
    )
    risks: list[str] = Field(description=_RISKS_DESC)
    narrative: str = Field(
        description=(
            "Full industry narrative: cycle position, competitive structure and "
            "share dynamics, supply-chain map (key upstream/downstream), "
            "technology roadmap and disruption, and how the regime interacts with "
            "the cycle. Keep the [data] vs [knowledge] tagging in the prose, and "
            "end with a markdown table of the key industry signals."
        ),
    )


def _render_scenarios(scenarios: list) -> list[str]:
    """Render the bear/base/bull distribution as a deterministic markdown table.

    The row format (``| Bull | 25% | +25% | trigger |``) is exactly what
    ``dromx.agents.utils.rating.parse_scenarios`` re-parses, so the
    aggregator can recover the distribution and compute EV + skew. Returns an
    empty list when no scenarios were provided (free-text fallback), so the
    caller simply omits the section.
    """
    if not scenarios:
        return []
    from dromx.agents.utils.rating import (
        scenarios_expected_value,
        scenarios_skew_label,
    )

    # Order bear → base → bull for readability regardless of fill order.
    order = {"bear": 0, "base": 1, "bull": 2}
    ordered = sorted(scenarios, key=lambda s: order.get(s.label, 1))
    pairs = [(s.probability, s.magnitude_pct) for s in ordered]
    ev = scenarios_expected_value(pairs)
    skew = scenarios_skew_label(pairs)
    rows = ["", "**情景（按概率加权）：**",
            "| 情景 | 概率 | 幅度 | 触发条件 |",
            "|---|---:|---:|---|"]
    for s in ordered:
        rows.append(
            f"| {s.label.capitalize()} | {s.probability * 100:.0f}% | "
            f"{s.magnitude_pct:+.0f}% | {s.trigger} |"
        )
    if ev is not None:
        rows.append(f"\n*期望值 ≈ {ev:+.1f}% · 收益偏度 {skew}。*")
    return rows


def _render_analyst_report(report, *, lens: str, domain_label: str, domain_value: str) -> str:
    """Render a structured analyst report to the shared markdown shape.

    ``lens`` names the analyst (e.g. "Technical"), ``domain_label``/``domain_value``
    carry the type-specific field (e.g. "Indicator Read-out" + its text). The
    direction/confidence header is deterministic and machine-parseable; the
    evidence/risks/narrative follow.
    """
    evidence = "\n".join(f"- {e}" for e in report.key_evidence) or "- （无）"
    risks = "\n".join(f"- {r}" for r in report.risks) or "- （无）"
    scenario_block = _render_scenarios(getattr(report, "scenarios", []))
    return "\n".join([
        f"**{lens}观点：** **{_dir_cn(report.direction.value)}** "
        f"（置信度：{_conf_cn(report.confidence)}）",
        "",
        f"**{domain_label}：** {domain_value}",
        *scenario_block,
        "",
        "**关键证据：**",
        evidence,
        "",
        "**风险：**",
        risks,
        "",
        report.narrative,
    ])


def render_market_report(report: MarketReport) -> str:
    base = _render_analyst_report(
        report, lens="技术面", domain_label="指标读数",
        domain_value=report.indicator_readout,
    )
    # Splice a horizon line right after the direction/confidence header so the
    # short- vs medium-term split is visible to readers and downstream parsers.
    horizon = (
        f"**分时方向：** 短期（1–5日）**{_dir_cn(report.direction_short_term.value)}** · "
        f"中期（1–3月）**{_dir_cn(report.direction_medium_term.value)}**"
    )
    lines = base.split("\n")
    # header is line 0, blank is line 1; insert the horizon line after the header
    lines.insert(1, horizon)
    return "\n".join(lines)


def render_news_report(report: NewsReport) -> str:
    base = _render_analyst_report(
        report, lens="新闻面", domain_label="宏观背景",
        domain_value=report.macro_backdrop,
    )
    if report.game_changer:
        # Splice a prominent flag right after the header so downstream readers
        # (and the Event Impact Assessor) can't miss a premise-changing event.
        flag = f"⚠️ **改变格局的事件：** {report.game_changer_note or '新闻窗口内出现了改变投资前提的事件。'}"
        lines = base.split("\n")
        lines.insert(1, flag)
        return "\n".join(lines)
    return base


def render_fundamentals_report(report: FundamentalsReport) -> str:
    return _render_analyst_report(
        report, lens="基本面", domain_label="估值观点",
        domain_value=report.valuation_view,
    )


def render_industry_report(report: IndustryReport) -> str:
    """Render an IndustryReport. Uses the shared analyst shape (so the Signal
    Aggregator can parse the ``Industry View`` header) plus the sector-specific
    cycle / moat / dependency lines spliced after the domain block.
    """
    domain = (
        f"周期阶段 **{report.industry_phase.value}**，护城河 **{report.competitive_moat.value}**"
    )
    base = _render_analyst_report(
        report, lens="行业链", domain_label="行业解读",
        domain_value=domain,
    )
    extra_lines = [
        "",
        f"**关键依赖：** {report.key_dependency}",
        f"**颠覆风险：** {report.disruption_risk}",
    ]
    if report.competition_matrix and report.competition_matrix.strip():
        extra_lines.extend([
            "",
            "**竞争格局横向对比：**",
            report.competition_matrix.strip(),
        ])
    extra = "\n".join(extra_lines)
    # Insert the extra industry lines right after the domain block (which is the
    # 4th line: header, domain, blank, ...). Simplest: append before the narrative
    # by splicing after the domain line.
    lines = base.split("\n")
    # domain line is at index 2 (header=0, blank=1, domain=2)
    insert_at = 3
    out = lines[:insert_at] + extra.split("\n") + lines[insert_at:]
    return "\n".join(out)
