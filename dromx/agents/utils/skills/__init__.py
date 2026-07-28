"""Backward compatibility: re-export from dromx.skills

v0.5.0 架构升级：`agents/utils/skills/` 已迁移到 `dromx/skills/`。
此文件保留作为向后兼容的 re-export。
"""

from dromx.skills.injector import SkillInjector
from dromx.skills.loader import Skill, SkillLoader
from dromx.skills.selector import SkillSelector

__all__ = ["Skill", "SkillLoader", "SkillSelector", "SkillInjector"]
