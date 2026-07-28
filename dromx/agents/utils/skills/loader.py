"""Backward compatibility: re-export from dromx.skills.loader

v0.5.0 架构升级：`agents/utils/skills/loader.py` 已迁移到 `dromx/skills/loader.py`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.skills.loader import Skill, SkillLoader

__all__ = ["Skill", "SkillLoader"]
