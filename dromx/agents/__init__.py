from .analysts.fundamentals_analyst import create_fundamentals_analyst
from .analysts.event_impact import create_event_impact_assessor
from .analysts.forecast_synthesizer import create_forecast_synthesizer
from .analysts.industry_analyst import create_industry_analyst
from .analysts.key_question import create_key_question_analyst
from .analysts.market_analyst import create_market_analyst
from .analysts.news_analyst import create_news_analyst
from .analysts.depth_controller import create_depth_controller
from .analysts.orchestrator import create_orchestrator
from .analysts.re_analysis import create_re_analysis
from .analysts.regime_analyst import create_regime_analyst
from .analysts.sentiment_analyst import (
    create_sentiment_analyst,
    create_social_media_analyst,  # deprecated alias kept for back-compat
)
from .analysts.signal_aggregator import create_signal_aggregator
from .managers.portfolio_manager import create_portfolio_manager
from .managers.research_manager import create_research_manager
from .researchers.bear_researcher import create_bear_researcher
from .researchers.bull_researcher import create_bull_researcher
from .risk_mgmt.aggressive_debator import create_aggressive_debator
from .risk_mgmt.conservative_debator import create_conservative_debator
from .risk_mgmt.neutral_debator import create_neutral_debator
from .risk_mgmt.risk_consensus import create_risk_consensus
from .trader.trader import create_trader
from dromx.core.agent_states import AgentState, InvestDebateState, RiskDebateState
from dromx.core.agent_utils import create_msg_delete

__all__ = [
    "AgentState",
    "create_msg_delete",
    "InvestDebateState",
    "RiskDebateState",
    "create_bear_researcher",
    "create_bull_researcher",
    "create_research_manager",
    "create_fundamentals_analyst",
    "create_event_impact_assessor",
    "create_forecast_synthesizer",
    "create_industry_analyst",
    "create_key_question_analyst",
    "create_market_analyst",
    "create_neutral_debator",
    "create_news_analyst",
    "create_depth_controller",
    "create_orchestrator",
    "create_re_analysis",
    "create_regime_analyst",
    "create_aggressive_debator",
    "create_portfolio_manager",
    "create_conservative_debator",
    "create_risk_consensus",
    "create_sentiment_analyst",
    "create_signal_aggregator",
    "create_social_media_analyst",  # deprecated; will be removed in a future version
    "create_trader",
]
