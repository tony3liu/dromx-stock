"""Report summarizer — compress a finished analysis state into a compact, Q&A-ready
context.

The full LangGraph state holds 5 analyst reports + several synthesis reports +
the PM decision — easily >10K tokens. The interactive Q&A only needs the salient
parts. This module extracts a structured summary DETERMINISTICALLY (parse the
rendered headers we already produce + slice the labelled sections), with a plain
truncation fallback when a report took the free-text path. No LLM call — the
summary is selection, not regeneration — so entering Q&A is free.
"""

from __future__ import annotations

import re

from tradingagents.agents.utils.rating import parse_analyst_signal, parse_rating

# (state key, label) for the five analyst lenses.
_ANALYST_LENSES = (
    ("market_report", "Technical"),
    ("sentiment_report", "Sentiment"),
    ("news_report", "News / macro"),
    ("fundamentals_report", "Fundamentals"),
    ("industry_report", "Industry / supply chain"),
)

# Sections worth keeping verbatim-ish (sliced) from a structured analyst report.
_SECTION_HEADERS = (
    "Key Evidence", "Risks", "Scenarios", "Valuation View", "Macro Backdrop",
    "Indicator Read-out", "Industry Read", "Key dependency", "Disruption risk",
)


def _slice_section(text: str, header: str, max_chars: int = 600) -> str:
    """Return the body under a ``**<header>:**`` marker, trimmed, or ''."""
    # Match "**Header:**" or "**Header**" then capture up to the next bold header
    # or a blank-line gap.
    m = re.search(rf"\*\*{re.escape(header)}[:：]?\*\*\s*(.*?)(?=\n\*\*[A-Z]|\n## |\Z)",
                  text, re.DOTALL)
    if not m:
        return ""
    body = m.group(1).strip()
    return body[:max_chars].rstrip()


def summarize_report(text: str, *, max_chars: int = 900) -> dict:
    """Summarize one analyst report into {direction, confidence, highlights}.

    Deterministic: pull the (direction, confidence) header and the most useful
    labelled sections (evidence / scenarios / domain view). Falls back to a head
    truncation when the report is free-text (no parseable structure).
    """
    if not text:
        return {"direction": None, "confidence": None, "highlights": ""}
    direction, confidence = parse_analyst_signal(text)
    parts = []
    for header in _SECTION_HEADERS:
        body = _slice_section(text, header, max_chars=400)
        if body:
            parts.append(f"{header}: {body}")
    highlights = "\n".join(parts)
    if not highlights:
        # Free-text fallback: keep the head, it still carries the gist.
        highlights = text[:max_chars].rstrip()
    else:
        highlights = highlights[: max_chars * 2]
    return {"direction": direction, "confidence": confidence, "highlights": highlights}


def summarize_state(final_state: dict) -> dict:
    """Compress a finished analysis state into a Q&A-ready summary dict.

    Returns:
      {
        "analysts": {label: {direction, confidence, highlights}},
        "signal_aggregation", "event_impact", "key_question",
        "risk_consensus", "forecast_report": <trimmed str>,
        "regime", "pm_decision", "pm_rating", "instrument_context",
      }
    Synthesis blocks are already concise, so they are passed through trimmed.
    """
    analysts = {}
    for key, label in _ANALYST_LENSES:
        rep = final_state.get(key) or ""
        if rep:
            analysts[label] = summarize_report(rep)

    def trim(key, n=1800):
        v = final_state.get(key) or ""
        return v[:n].rstrip()

    pm = final_state.get("final_trade_decision") or ""
    return {
        "analysts": analysts,
        "regime": trim("regime_report", 1200),
        "signal_aggregation": trim("signal_aggregation", 1500),
        "event_impact": trim("event_impact", 1200),
        "key_question": trim("key_question", 1500),
        "risk_consensus": trim("risk_consensus", 1500),
        "forecast_report": trim("forecast_report", 2000),
        "portfolio_context": trim("portfolio_context", 1200),
        "pm_decision": pm[:2500].rstrip(),
        "pm_rating": parse_rating(pm) if pm else None,
        "instrument_context": (final_state.get("instrument_context") or "")[:400],
    }


def render_summary_for_prompt(summary: dict) -> str:
    """Render the summary dict into a compact prompt block."""
    lines = []
    ic = summary.get("instrument_context")
    if ic:
        lines.append(f"Instrument: {ic}")
    if summary.get("pm_rating"):
        lines.append(f"PM rating: {summary['pm_rating']}")
    if summary.get("regime"):
        lines.append(f"\n## Market regime\n{summary['regime']}")
    lines.append("\n## Analyst summaries")
    for label, s in summary.get("analysts", {}).items():
        d = s.get("direction") or "—"
        c = (s.get("confidence") or "—")
        lines.append(f"\n### {label} ({d}, confidence {c})\n{s.get('highlights', '')}")
    for key, label in (
        ("signal_aggregation", "Fused signal"),
        ("event_impact", "Event impact"),
        ("key_question", "Key question"),
        ("risk_consensus", "Risk consensus"),
        ("forecast_report", "Forecast (time horizons)"),
        ("portfolio_context", "Portfolio context"),
        ("pm_decision", "PM decision"),
    ):
        if summary.get(key):
            lines.append(f"\n## {label}\n{summary[key]}")
    return "\n".join(lines)
