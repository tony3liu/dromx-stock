"""Skill system (v0.4) — pluggable analyst methodology playbooks.

A skill decouples the "how to analyze" knowledge from the agent-loop skeleton:
the same Market Analyst mounts different skills for a semiconductor equity
(``ma50-hunting`` + ``semiconductor-cycle``) vs a 2x leveraged ETF
(``leveraged-etf-decay``). Skills are Hermes-format .md files (YAML frontmatter
+ Markdown body) so they are portable across platforms.

Public surface:
  - ``Skill``            — one parsed skill (name / analyst / filters / body)
  - ``SkillLoader``      — discovers + parses built-in + user skill files
  - ``SkillSelector``    — picks skills for an analyst given run context
  - ``SkillInjector``    — formats selected skills into a system-prompt block
  - ``make_request_skill_tool`` — dynamic ``request_skill(name)`` tool (M2)
"""

from .injector import SkillInjector
from .loader import Skill, SkillLoader
from .selector import SkillSelector

__all__ = ["Skill", "SkillLoader", "SkillSelector", "SkillInjector"]
