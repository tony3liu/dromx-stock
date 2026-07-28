"""Backward compatibility: re-export from dromx.skills.selector

v0.5.0 架构升级：`agents/utils/skills/selector.py` 已迁移到 `dromx/skills/selector.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.skills.selector import SkillSelector

__all__ = ["SkillSelector"]
