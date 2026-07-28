"""Backward compatibility: re-export from dromx.core.signal_tracker

v0.5.0 架构升级：`agents/utils/signal_tracker.py` 已迁移到 `dromx/core/signal_tracker.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.core.signal_tracker import AnalystScorecard

__all__ = ["AnalystScorecard"]
