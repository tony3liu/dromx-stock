"""Key Question node schema + render (attention allocation)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Key Question (post-aggregation attention-allocation node)
# ---------------------------------------------------------------------------
#
# A junior analyst spreads attention evenly across every lens; a senior one
# first finds the ONE question whose answer decides the call and spends the
# debate there. This node runs after the Signal Aggregator (so it sees all four
# reports, the fused signal, and the regime) and names the 1–2 questions the
# whole thesis hinges on, plus what data would resolve each. The debate and the
# managers then center on these instead of re-deriving them or arguing evenly.


class KeyQuestion(BaseModel):
    """One pivotal, currently-unresolved question the decision hinges on."""

    question: str = Field(
        description=(
            "The pivotal question, phrased so its answer would actually move the "
            "rating — e.g. 'Does data-center revenue re-accelerate next quarter?' "
            "not 'Is the company doing well?'."
        ),
    )
    why_it_matters: str = Field(
        description=(
            "One or two sentences: why THIS question dominates the others — what "
            "swings if the answer flips. Tie it to the analysts' disagreement or "
            "the biggest expectation gap."
        ),
    )
    what_would_answer_it: str = Field(
        description=(
            "The concrete, observable evidence that would resolve it (a specific "
            "data point, filing, print, or price level) — so the debate can hunt "
            "for it rather than speculate."
        ),
    )


class KeyQuestionReport(BaseModel):
    """The 1–2 questions that decide this call, ranked most-pivotal first."""

    key_questions: list[KeyQuestion] = Field(
        description=(
            "One or two questions, the single most decision-relevant first. "
            "Prefer one sharp question over two diffuse ones; add a second only "
            "if it is genuinely independent and nearly as pivotal."
        ),
    )
    focus_directive: str = Field(
        description=(
            "One sentence telling the debate where to concentrate its effort — "
            "the senior-analyst instruction to spend 70% of the analysis on the "
            "question that matters, not to cover every lens evenly."
        ),
    )


def render_key_question_report(report: KeyQuestionReport) -> str:
    """Render a KeyQuestionReport to the markdown shape stored in state."""
    parts = ["**关键问题（决定这笔判断的真正胜负手）：**"]
    for i, kq in enumerate(report.key_questions, 1):
        parts.extend([
            "",
            f"{i}. **{kq.question}**",
            f"   - *为何重要：* {kq.why_it_matters}",
            f"   - *什么能回答它：* {kq.what_would_answer_it}",
        ])
    if report.focus_directive:
        parts.extend(["", f"**聚焦：** {report.focus_directive}"])
    return "\n".join(parts)
