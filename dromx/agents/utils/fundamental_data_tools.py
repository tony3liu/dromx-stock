"""Backward compatibility: re-export from dromx.tools.data

v0.5.0 架构升级：`agents/utils/fundamental_data_tools.py` 已迁移到 `dromx/tools/data/`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.tools.data import _get_fundamentals

__all__ = ["_get_fundamentals"]
