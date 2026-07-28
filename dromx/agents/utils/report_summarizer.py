"""Backward compatibility: re-export from dromx.core.report_summarizer

v0.5.0 架构升级：`agents/utils/report_summarizer.py` 已迁移到 `dromx/core/report_summarizer.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.core.report_summarizer import summarize_state

__all__ = ["summarize_state"]
