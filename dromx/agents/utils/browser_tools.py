"""Backward compatibility: re-export from dromx.browser.tools

v0.5.0 架构升级：`agents/utils/browser_tools.py` 已迁移到 `dromx/browser/tools.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.browser.tools import web_read, web_search

__all__ = ["web_read", "web_search"]
