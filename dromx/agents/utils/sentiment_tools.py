"""Backward compatibility: re-export from dromx.tools.data

v0.5.0 架构升级：`agents/utils/sentiment_tools.py` 已迁移到 `dromx/tools/data/`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.tools.data import _fetch_stocktwits, _fetch_reddit, _fetch_x_posts

__all__ = ["_fetch_stocktwits", "_fetch_reddit", "_fetch_x_posts"]
