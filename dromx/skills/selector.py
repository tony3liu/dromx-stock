"""Skill selector — pick which skills apply to a given analyst + run context.

Rule-engine match on the skill's frontmatter (regimes / instruments / markets)
against the current run's attributes. The Orchestrator can also pass explicit
skill names (from its LLM plan) to override / pre-load the rule-engine result.

The regime match is substring-based on purpose: skills use state words like
``volatile`` / ``bearish`` while the regime_report carries trend labels like
``Uptrend`` / ``Downtrend`` plus volatility phrases. A skill whose ``regimes``
field lists ``volatile`` should fire whenever the regime text mentions
"volatile", and a skill listing ``uptrend`` should fire in an uptrend. Empty
``regimes`` means the skill applies to every regime.
"""

from __future__ import annotations

from .loader import Skill, SkillLoader


class SkillSelector:
    """Pick skills for one analyst given the run's instrument / regime / market."""

    def __init__(self, loader: SkillLoader, config: dict | None = None):
        self._loader = loader
        cfg = (config or {}).get("skills", {}) or {}
        self._max_per_analyst = int(cfg.get("max_per_analyst", 5))
        self._auto_load = bool(cfg.get("auto_load", True))

    def select(
        self,
        analyst_key: str,
        *,
        instrument_type: str = "",
        regime_text: str = "",
        market: str = "",
        explicit: list[str] | None = None,
    ) -> list[Skill]:
        """Return the skills to mount for this analyst.

        ``explicit`` (from the Orchestrator LLM) takes precedence: those names
        load first in order, then rule-engine matches fill up to ``max_per_analyst``.
        """
        all_skills = self._loader.load_all().get(analyst_key, [])
        if not all_skills:
            return []

        out: list[Skill] = []
        seen: set[str] = set()

        # 1) explicit (Orchestrator-specified) — load even if the rule engine wouldn't
        if explicit:
            by_name = {s.name: s for s in all_skills}
            for name in explicit:
                s = by_name.get(name)
                if s is not None and s.name not in seen:
                    out.append(s)
                    seen.add(s.name)

        # 2) rule-engine fill
        if self._auto_load:
            for s in all_skills:
                if len(out) >= self._max_per_analyst:
                    break
                if s.name in seen:
                    continue
                if self._matches(s, instrument_type, regime_text, market):
                    out.append(s)
                    seen.add(s.name)

        return out[: self._max_per_analyst]

    @staticmethod
    def _matches(skill: Skill, instrument_type: str, regime_text: str, market: str) -> bool:
        """Empty frontmatter field = no constraint on that axis (match all)."""
        if skill.instruments and instrument_type:
            if instrument_type.lower() not in [i.lower() for i in skill.instruments]:
                return False
        if skill.regimes and regime_text:
            low = regime_text.lower()
            if not any(r.lower() in low for r in skill.regimes):
                return False
        if skill.markets and market:
            if market.upper() not in [m.upper() for m in skill.markets]:
                return False
        return True
