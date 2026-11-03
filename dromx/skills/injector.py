"""Skill injector — format selected skills into a system-prompt block.

The block goes AFTER the core instructions + pre-fetched data and BEFORE the
tool list, so the model sees ground-truth data first, then the skill playbooks,
then the tools it can call to execute the playbooks (PRD §10.5).

The block is a no-op (returns "") when no skills are selected, so the v0.3
analyst prompt is byte-identical when skills are disabled.
"""

from __future__ import annotations

from .loader import Skill


class SkillInjector:
    """Format a list of skills into the ``[SKILL: ...]`` prompt block."""

    @staticmethod
    def format_skills_block(skills: list[Skill]) -> str:
        if not skills:
            return ""
        parts = [
            "",
            "## Applicable skills (methodology playbooks — apply the relevant ones)",
            "",
        ]
        for s in skills:
            parts.append(f"[SKILL: {s.name}]")
            if s.description:
                parts.append(f"{s.description}")
            parts.append(s.body.rstrip())
            parts.append("")
        return "\n".join(parts)
