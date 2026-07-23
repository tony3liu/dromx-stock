"""Q&A agent — answer a follow-up question against a finished analysis.

A single quick-LLM call: it receives the compact report summary (see
``report_summarizer``), the conversation history, and the user's question, and
answers strictly from that context. It does NOT re-run the analyst pipeline. The
rules below (cite specifics, show ATR/leverage math, admit when uncovered, defer
other tickers) come straight from the feature spec.
"""

from __future__ import annotations

from dromx.agents.utils.agent_utils import get_language_instruction
from dromx.agents.utils.report_summarizer import render_summary_for_prompt

_RULES = """## How to answer
1. Answer from the context above first — cite the specific number, level, or section you used.
2. For a calculation ("if X moves +Y%, where does this go?"), use the ATR / leverage / stop figures in the context and SHOW the derivation step by step. If this is a leveraged ETF, apply the leverage multiple (and note daily-reset decay over multi-day horizons).
3. If the question is outside what the analysis covered, say so plainly ("the report doesn't cover this — re-run the analysis to include it"). Do not invent.
4. If the question is about a DIFFERENT ticker than the one analysed, say it needs its own analysis run.
5. Do not re-run the analyst pipeline; answer only from the context.
6. If the user challenges a conclusion, walk through the derivation and state the data limitations honestly.
Keep the answer focused and concrete — a few sentences, not an essay."""


def build_qa_prompt(summary: dict, question: str, history: list[tuple[str, str]]) -> str:
    """Assemble the Q&A prompt from the summary, prior turns, and the question."""
    ctx = render_summary_for_prompt(summary)
    convo = ""
    if history:
        convo_lines = []
        for q, a in history:
            convo_lines.append(f"Q: {q}\nA: {a}")
        convo = "\n\n## Earlier in this conversation\n" + "\n\n".join(convo_lines) + "\n"
    return (
        "You are an investment-research assistant answering follow-up questions "
        "about a completed analysis. Use ONLY the analysis context below.\n\n"
        f"## Analysis context\n{ctx}\n"
        f"{convo}\n"
        f"## User question\n{question}\n\n"
        f"{_RULES}"
        + get_language_instruction()
    )


def answer_question(summary: dict, question: str, history: list[tuple[str, str]], llm) -> str:
    """Return the assistant's answer to ``question`` (one LLM call, no pipeline)."""
    prompt = build_qa_prompt(summary, question, history)
    try:
        resp = llm.invoke(prompt)
        return getattr(resp, "content", str(resp)).strip()
    except Exception as exc:  # noqa: BLE001 — Q&A must never crash the session
        return f"(无法回答：{type(exc).__name__}: {exc})"
