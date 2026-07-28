"""Backward compatibility: re-export from dromx.skills.request_tool

v0.5.0 架构升级：`agents/utils/skills/request_tool.py` 已迁移到 `dromx/skills/request_tool.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.skills.request_tool import make_request_skill_tool

__all__ = ["make_request_skill_tool"]
