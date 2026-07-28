"""Backward compatibility: re-export from dromx.core.structured

v0.5.0 架构升级：`agents/utils/structured.py` 已迁移到 `dromx/core/structured.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.core.structured import bind_structured, invoke_structured_or_freetext

__all__ = ["bind_structured", "invoke_structured_or_freetext"]
