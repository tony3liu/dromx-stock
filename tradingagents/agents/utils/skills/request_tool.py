"""Dynamic ``request_skill`` tool — let an analyst pull an extra skill mid-loop.

The agent loop's system prompt already carries the auto-selected skills, but an
analyst may spot something mid-analysis ("volume profile shows algorithmic
traces — I want algorithm-trading-detection"). Rather than rebuild the system
prompt (breaks prompt caching) or rebuild the react agent (expensive), this
tool returns the skill body as a ToolMessage so the model sees it in the
conversation and can apply it on the next turn.

Count-limited (default 2) to bound how many skills one analyst can pull in a
run. A skill not in the loader returns a "not found" message listing the
available names so the model can retry or give up cleanly.
"""

from __future__ import annotations

from langchain_core.tools import tool


def make_request_skill_tool(loader, max_loads: int = 2):
    """Build a per-run ``request_skill`` tool backed by ``loader``.

    Returns a fresh ``@tool`` with its own count, so each analyst node gets an
    independent limit (one analyst's dynamic loads don't deplete another's).
    """
    state = {"count": 0}

    @tool
    def request_skill(name: str) -> str:
        """Load an additional methodology skill by name (e.g. 'ma50-hunting').

        Returns the skill body to apply on the next turn. Limited to a few
        loads per run; a non-existent name returns 'not found' plus the
        available skill names so you can retry.
        """
        if state["count"] >= max_loads:
            return (
                f"dynamic skill load limit ({max_loads}) reached — work with "
                f"the skills already in your prompt."
            )
        skill = loader.get_by_name(name)
        if skill is None:
            available = sorted({
                s.name for skills in loader.load_all().values() for s in skills
            })
            return (
                f"skill '{name}' not found. Available: {', '.join(available)}."
            )
        state["count"] += 1
        return (
            f"[SKILL: {skill.name}]\n{skill.description}\n\n{skill.body}"
        )

    return request_skill
