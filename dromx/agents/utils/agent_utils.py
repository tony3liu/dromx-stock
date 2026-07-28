"""Backward compatibility: re-export from dromx.core.agent_utils

v0.5.0 架构升级：`agents/utils/agent_utils.py` 已迁移到 `dromx/core/agent_utils.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.core.agent_utils import build_instrument_context, resolve_instrument_identity

__all__ = ["build_instrument_context", "resolve_instrument_identity"]
