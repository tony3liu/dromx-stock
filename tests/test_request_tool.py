"""Tests for the dynamic ``request_skill`` tool (v0.4 M2).

The tool lets an analyst pull an extra skill mid-loop. Count-limited per
instance; a non-existent name returns a not-found message listing what's
available so the model can retry cleanly. Not-found calls do NOT consume the
count (only successful loads do).
"""

from __future__ import annotations

from dromx.agents.utils.skills import SkillLoader
from dromx.agents.utils.skills.request_tool import make_request_skill_tool


def _loader():
    return SkillLoader({"skills": {"enabled": True, "path": "~/.dromx/skills/"}})


def test_returns_skill_body():
    rt = make_request_skill_tool(_loader(), max_loads=2)
    out = rt.invoke({"name": "ma50-hunting"})
    assert "[SKILL: ma50-hunting]" in out
    assert "When to Apply" in out


def test_not_found_lists_available():
    out = make_request_skill_tool(_loader(), max_loads=2).invoke({"name": "does-not-exist"})
    assert "not found" in out
    assert "ma50-hunting" in out  # the available-names list


def test_not_found_does_not_consume_count():
    rt = make_request_skill_tool(_loader(), max_loads=1)
    rt.invoke({"name": "does-not-exist"})  # no increment
    assert "[SKILL: ma50-hunting]" in rt.invoke({"name": "ma50-hunting"})  # still within limit


def test_limit_reached_after_max_loads():
    rt = make_request_skill_tool(_loader(), max_loads=1)
    rt.invoke({"name": "ma50-hunting"})  # count=1
    out = rt.invoke({"name": "leveraged-etf-decay"})  # limit hit
    assert "limit" in out.lower()


def test_independent_count_per_instance():
    rt1 = make_request_skill_tool(_loader(), max_loads=1)
    rt2 = make_request_skill_tool(_loader(), max_loads=1)
    rt1.invoke({"name": "ma50-hunting"})  # rt1 exhausted
    assert "[SKILL:" in rt2.invoke({"name": "ma50-hunting"})  # rt2 unaffected
