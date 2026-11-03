"""Tests for the v0.4 skill system (loader / selector / injector).

Built-in skills ship inside the package, so these run without any user
``~/.dromx/skills/`` directory. Hermes-format frontmatter (YAML +
Markdown body) must round-trip; cross-analyst mounting (``analyst: [a, b]``)
and the instrument/regime/market filter axes are the core behaviours.
"""

from __future__ import annotations

from dromx.skills import (
    SkillInjector,
    SkillLoader,
    SkillSelector,
)

_TEN = [
    "ma50-hunting", "leveraged-etf-decay", "institutional-flow",
    "adr-shelf-offering", "korea-cross-market", "event-chain-tracing",
    "earnings-deviation", "semiconductor-cycle", "supply-chain-bottleneck",
    "sentiment-contagion",
]


def _loader():
    return SkillLoader({"skills": {
        "enabled": True, "path": "~/.dromx/skills/",
        "max_per_analyst": 5, "auto_load": True,
    }})


def test_load_all_ten_builtin():
    all_s = _loader().load_all()
    names = {s.name for skills in all_s.values() for s in skills}
    for n in _TEN:
        assert n in names, f"missing skill: {n}"
    # v0.4 added later: short-horizon / sector-linkage skills
    assert "oversold-bounce" in names
    assert "sector-overnight-flow" in names
    # v0.4 added: valuation / next-session / trend / volatility
    assert "forward-valuation" in names
    assert "next-session-catalyst" in names
    assert "trend-following" in names
    assert "volatility-regime" in names


def test_cross_mounted_skills():
    loader = _loader()
    assert set(loader.get_by_name("semiconductor-cycle").analyst) == {"industry", "market"}
    assert set(loader.get_by_name("korea-cross-market").analyst) == {"news", "market"}


def test_select_by_instrument_leveraged_etf():
    sel = SkillSelector(_loader(), {"skills": {"max_per_analyst": 5, "auto_load": True}})
    names = {s.name for s in sel.select(
        "market", instrument_type="leveraged_etf", regime_text="volatile", market="HK")}
    assert "leveraged-etf-decay" in names
    assert "ma50-hunting" not in names  # equity/etf only — leveraged_etf excluded


def test_select_by_regime():
    sel = SkillSelector(_loader(), {"skills": {"max_per_analyst": 5, "auto_load": True}})
    names = {s.name for s in sel.select(
        "market", instrument_type="equity", regime_text="high volatility bearish", market="US")}
    assert "ma50-hunting" in names


def test_max_per_analyst_truncates():
    sel = SkillSelector(_loader(), {"skills": {"max_per_analyst": 1, "auto_load": True}})
    assert len(sel.select("market", instrument_type="equity", regime_text="volatile", market="US")) <= 1


def test_explicit_override_loads_first():
    sel = SkillSelector(_loader(), {"skills": {"max_per_analyst": 5, "auto_load": True}})
    out = sel.select("market", instrument_type="equity", regime_text="calm uptrend",
                     market="US", explicit=["ma50-hunting"])
    assert out[0].name == "ma50-hunting"


def test_injector_formats_block():
    sc = _loader().get_by_name("ma50-hunting")
    blk = SkillInjector.format_skills_block([sc])
    assert "[SKILL: ma50-hunting]" in blk
    assert "When to Apply" in blk


def test_injector_empty_is_empty_string():
    assert SkillInjector.format_skills_block([]) == ""


def test_disabled_returns_empty():
    assert SkillLoader({"skills": {"enabled": False}}).load_all() == {}
