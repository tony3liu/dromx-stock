"""Backward compatibility: re-export from dromx.core.agent_loop

v0.5.0 架构升级：`agents/utils/agent_loop.py` 已迁移到 `dromx/core/agent_loop.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.core.agent_loop import (
    build_analyst_react_invoker,
    build_analyst_loop_invoker,
    extract_market,
)

__all__ = [
    "build_analyst_react_invoker",
    "build_analyst_loop_invoker",
    "extract_market",
]
