"""Re-Analysis node (v0.4 PRD §5.1) — re-examine analysts flagged by Event Impact.

A static LangGraph graph can't route back to an earlier analyst node, so this
forward node does the re-examination: for each analyst key in
``reanalysis_targets``, take its original report + the Event Impact assessment,
and have the LLM produce an updated report that incorporates the premise
shift. Overwrites the ``report_key`` in state so KeyQuestion / PM see the
revised read. Best-effort: a failed re-examination leaves the original intact.

Only runs when ``trigger_reanalysis`` is True (DepthController set it); the
graph routes here via ``route_after_depth_control`` and then on to Key
Question.
"""

from __future__ import annotations

import logging

from dromx.core.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
)

logger = logging.getLogger(__name__)

# analyst key -> state report key (mirrors analyst_execution.ANALYST_NODE_SPECS)
_KEY_TO_REPORT = {
    "market": "market_report",
    "news": "news_report",
    "sentiment": "sentiment_report",
    "fundamentals": "fundamentals_report",
    "industry": "industry_report",
}

# LLMs sometimes write the lens LABEL (Technical/Sentiment/News/...) instead
# of the analyst KEY (market/sentiment/news/...) into reanalysis_targets. Map
# back so the Re-Analysis node still finds the report.
_LENS_TO_KEY = {
    "Technical": "market", "Sentiment": "sentiment", "News": "news",
    "Fundamentals": "fundamentals", "Industry": "industry",
}


def create_re_analysis(llm):
    """Create the Re-Analysis node (one plain LLM call per affected analyst)."""

    def re_analysis_node(state):
        targets = state.get("reanalysis_targets") or []
        if not targets:
            return {}
        event_impact = state.get("event_impact", "")
        ticker = state["company_of_interest"]
        instrument_context = get_instrument_context_from_state(state)

        def _re_examine(key: str) -> tuple[str, str | None]:
            """Re-examine one analyst report; returns (report_key, updated|None)."""
            report_key = _KEY_TO_REPORT.get(key) or _KEY_TO_REPORT.get(_LENS_TO_KEY.get(key, ""))
            if not report_key:
                return "", None
            original = state.get(report_key, "") or ""
            if not original:
                return "", None
            prompt = (
                f"You are re-examining the {key} analyst's report for {ticker} "
                f"after the Event Impact assessor flagged a premise-changing "
                f"event. Update the report to incorporate the premise shift — "
                f"do not discard the original analysis, revise it in light of "
                f"the event.\n"
                f"{instrument_context}\n"
                f"## Event Impact assessment\n{event_impact}\n\n"
                f"## Original {key} analyst report\n{original}\n\n"
                f"Produce the UPDATED {key} report (same format/headers as the "
                f"original), revised to reflect the premise shift. If the event "
                f"doesn't actually change the {key} lens's conclusion, say so "
                f"plainly and keep the original read.\n"
                f"{get_language_instruction()}"
            )
            try:
                resp = llm.invoke(prompt)
                updated = getattr(resp, "content", str(resp))
                if updated and len(updated.strip()) > 50:
                    return report_key, updated
            except Exception as exc:  # noqa: BLE001 — leave the original intact
                logger.warning("Re-Analysis: %s re-examination failed: %s", key, exc)
            return "", None

        # 各 target 互相独立、写不同 report_key —— 线程并行，失败留原文
        updates = {}
        if len(targets) > 1:
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=min(len(targets), 5)) as ex:
                for report_key, updated in ex.map(_re_examine, targets):
                    if report_key and updated:
                        updates[report_key] = updated
        else:
            report_key, updated = _re_examine(targets[0])
            if report_key and updated:
                updates[report_key] = updated
        return updates

    return re_analysis_node
