"""Structured-output Pydantic schemas for agents (split into a package by domain).

Re-exports every symbol so ``from dromx.agents.schemas import X`` keeps
working exactly as before the split. See the per-domain submodules for the
definitions.
"""

from ._shared import (
    _NULLISH_FLOAT, _coerce_optional_float,
    _DIRECTION_CN, _CONF_CN, _dir_cn, _conf_cn,
)
from .rating import PortfolioRating, TraderAction
from .research import ResearchPlan, render_research_plan
from .trader import TraderProposal, render_trader_proposal
from .pm import PriceDriver, PortfolioDecision, render_pm_decision
from .analysts import (
    TrendDirection, VolatilityLevel, RegimeReport, render_regime_report,
    SentimentBand, SentimentReport, render_sentiment_report,
    AnalystDirection, Scenario,
    MarketReport, NewsReport, FundamentalsReport,
    IndustryPhase, MoatTrend, IndustryReport,
    render_market_report, render_news_report, render_fundamentals_report, render_industry_report,
    _render_scenarios, _render_analyst_report,
)
from .aggregation import (
    AnalystSignal, SignalAggregation, _consensus_band, render_signal_aggregation,
)
from .key_question import KeyQuestion, KeyQuestionReport, render_key_question_report
from .risk import RiskConsensusReport, render_risk_consensus
from .event import EventImpactReport, render_event_impact
from .forecast import ForecastHorizon, ForecastReport, render_forecast_report
from .orchestration import (
    AnalystAssignment,
    OrchestrationPlan,
    orchestrator_skills_for,
    render_orchestration_plan,
    selected_analyst_keys,
)
from .depth import DepthDecision, render_depth_decision

__all__ = [
    "PortfolioRating", "TraderAction",
    "ResearchPlan", "render_research_plan",
    "TraderProposal", "render_trader_proposal",
    "PriceDriver", "PortfolioDecision", "render_pm_decision",
    "TrendDirection", "VolatilityLevel", "RegimeReport", "render_regime_report",
    "SentimentBand", "SentimentReport", "render_sentiment_report",
    "AnalystDirection", "Scenario",
    "MarketReport", "NewsReport", "FundamentalsReport",
    "IndustryPhase", "MoatTrend", "IndustryReport",
    "render_market_report", "render_news_report", "render_fundamentals_report", "render_industry_report",
    "AnalystSignal", "SignalAggregation", "render_signal_aggregation",
    "KeyQuestion", "KeyQuestionReport", "render_key_question_report",
    "RiskConsensusReport", "render_risk_consensus",
    "EventImpactReport", "render_event_impact",
    "ForecastHorizon", "ForecastReport", "render_forecast_report",
    "AnalystAssignment", "OrchestrationPlan", "render_orchestration_plan",
    "selected_analyst_keys", "orchestrator_skills_for",
    "DepthDecision", "render_depth_decision",
]
