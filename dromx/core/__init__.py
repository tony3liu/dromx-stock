"""DromX Core — Agent 基础设施

从 `agents/utils/` 提取的 agent 基础设施：
- `agent_loop.py` — ReAct 循环
- `memory.py` — Memory
- `structured.py` — Structured output helpers
- `agent_states.py` — Agent states
- `agent_utils.py` — Agent utils
- `signal_tracker.py` — Signal tracker
- `rating.py` — Rating
- `report_summarizer.py` — Report summarizer
"""

from .agent_loop import build_analyst_react_invoker, build_analyst_loop_invoker
from .memory import TradingMemoryLog
from .structured import bind_structured, invoke_structured_or_freetext
from .agent_states import AgentState
from .agent_utils import build_instrument_context, resolve_instrument_identity
from .signal_tracker import AnalystScorecard
from .rating import parse_rating
from .report_summarizer import summarize_state

__all__ = [
    "build_analyst_react_invoker",
    "build_analyst_loop_invoker",
    "TradingMemoryLog",
    "bind_structured",
    "invoke_structured_or_freetext",
    "AgentState",
    "build_instrument_context",
    "resolve_instrument_identity",
    "AnalystScorecard",
    "parse_rating",
    "summarize_state",
]
