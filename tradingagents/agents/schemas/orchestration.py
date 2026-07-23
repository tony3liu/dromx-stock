"""Orchestrator structured output — the dynamic analysis plan (v0.4).

The Orchestrator sits between the Regime Analyst and the parallel analysts.
It reads the regime classification + instrument type + historical scorecard
weights and decides, for THIS run, which analysts to run, at what depth, and
with which skills mounted. The plan is written to ``state["orchestration_plan"]``
(rendered markdown) and each analyst node reads it to decide whether to run or
noop out (a static graph can't be re-compiled at runtime, so unused analysts
short-circuit instead of being removed from the graph — see setup.py).

Single structured LLM call, no agent loop — the orchestrator itself needs no
tools (PRD §4.1). Falls back to free-text via ``invoke_structured_or_freetext``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AnalystKey = Literal["market", "sentiment", "news", "fundamentals", "industry"]
DepthTier = Literal["standard", "deep"]


class AnalystAssignment(BaseModel):
    """One analyst the Orchestrator wants to run this pass.

    ``skills`` are skill names to auto-load for this analyst (the SkillSelector
    honours them as an explicit override of its rule-engine selection). Empty
    list = rule-engine auto-select (or none, if skills are disabled).
    """

    key: AnalystKey = Field(
        description="Which analyst to run: market / sentiment / news / fundamentals / industry.",
    )
    depth: DepthTier = Field(
        default="standard",
        description="standard = one agent-loop pass; deep = allow more iterations / deeper dig.",
    )
    priority: int = Field(
        default=1,
        ge=1,
        description="Relative priority, 1 = highest. Higher-priority analysts run first conceptually.",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Skill names to mount for this analyst (overrides auto-selection). Empty = auto.",
    )


class OrchestrationPlan(BaseModel):
    """The Orchestrator's run-specific analysis plan."""

    analysts: list[AnalystAssignment] = Field(
        description=(
            "The analysts to run this pass. Omit an analyst to skip it (e.g. skip "
            "fundamentals for a leveraged ETF — its 'fundamentals' are the underlying "
            "index, not a company). Must include market + news for a crisis/volatile regime."
        ),
    )
    skip_research_layer: bool = Field(
        default=False,
        description="True = the setup is clear enough to skip the Growth/Risk research layer and go straight to PM.",
    )
    reasoning: str = Field(
        description="One or two sentences: why THIS plan for THIS instrument + regime.",
    )


def render_orchestration_plan(plan: OrchestrationPlan) -> str:
    """Render the plan to the markdown shape the report tree + state expect.

    Downstream analyst nodes parse the ``**Selected analysts:**`` line to decide
    whether to noop, so the format is stable and machine-readable.
    """
    keys = ",".join(a.key for a in plan.analysts)
    lines = [
        "**分析编排计划**",
        "",
        f"**选中分析师:** {keys}",
        "",
        "| 分析师 | 深度 | 优先级 | 挂载 skills |",
        "|---|---|---|---|",
    ]
    for a in plan.analysts:
        skill_list = ", ".join(a.skills) if a.skills else "—"
        lines.append(f"| {a.key} | {a.depth} | {a.priority} | {skill_list} |")
    lines.extend([
        "",
        f"**跳过研究层:** {'是' if plan.skip_research_layer else '否'}",
        "",
        f"**理由:** {plan.reasoning}",
    ])
    return "\n".join(lines)


def selected_analyst_keys(plan_markdown: str) -> set[str]:
    """Parse the ``**Selected analysts:**`` line back into a set of keys.

    Analyst nodes call this to decide whether to noop. Returns the full set
    when the line is absent (v0.3 path / no orchestration), so an absent plan
    never accidentally skips an analyst.
    """
    if not plan_markdown:
        return {"market", "sentiment", "news", "fundamentals", "industry"}
    for line in plan_markdown.splitlines():
        low = line.lower()
        if low.startswith("**选中分析师") or low.startswith("**selected analysts"):
            # The header reads ``**选中分析师:** market,news`` — the colon sits
            # inside the bold wrap, so splitting on ``:`` leaves the closing
            # ``**`` glued to the first key. Strip every ``*`` then split.
            rest = line.split(":", 1)[-1].replace("*", "").strip()
            keys = {k.strip() for k in rest.split(",") if k.strip()}
            return keys
    return {"market", "sentiment", "news", "fundamentals", "industry"}


def orchestrator_skills_for(plan_markdown: str, analyst_key: str) -> list[str]:
    """Parse the skills column for one analyst from the rendered plan table.

    The plan's table row reads ``| news | deep | 2 | adr-shelf-offering, ... |``;
    this pulls the 4th column for the row whose first cell is ``analyst_key``.
    Returns [] when the plan/row is absent or the cell is "—" — so the caller
    falls back to the SkillSelector's rule-engine auto-select.
    """
    if not plan_markdown:
        return []
    for line in plan_markdown.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == analyst_key:
            skills_cell = cells[3]
            if skills_cell and skills_cell != "—":
                return [s.strip() for s in skills_cell.split(",") if s.strip()]
    return []
