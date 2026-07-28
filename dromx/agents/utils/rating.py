"""Backward compatibility: re-export from dromx.core.rating

v0.5.0 架构升级：`agents/utils/rating.py` 已迁移到 `dromx/core/rating.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.core.rating import parse_rating

__all__ = ["parse_rating"]
