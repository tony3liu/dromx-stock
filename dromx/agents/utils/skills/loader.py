"""Skill loader — discovers + parses Hermes-format .md skill files.

A skill file is Markdown with a YAML frontmatter block:

    ---
    name: ma50-hunting
    description: Detect institutional MA50 hunting patterns.
    version: 1.0.0
    analyst: market              # analyst key, or a list [market, industry]
    tags: [technical, institutional, ma50]
    regimes: [volatile, bearish] # empty = applies to all regimes
    instruments: [equity, etf]   # empty = all instrument types
    markets: [US, HK, KR]        # empty = all markets
    ---
    # Markdown body: When to Apply / Procedure / Pitfalls / Output

Skills come from two places:
  - Built-in: ``tradingagents/agents/utils/skills/builtin/{analyst}/{name}.md``
    (shipped with the package as package-data).
  - User: ``~/.tradingagents/skills/{analyst}/{name}.md`` (config ``skills.path``).

User skills override built-in skills of the same name. Per-file try/except: a
malformed skill is skipped + warned, never blocks a run. When ``skills.enabled``
is False the loader returns an empty map (skills off = v0.3 behaviour).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_VALID_ANALYSTS = {"market", "sentiment", "news", "fundamentals", "industry"}

# Built-in skills ship inside the package (see pyproject package-data).
_BUILTIN_ROOT = Path(__file__).parent / "builtin"


@dataclass
class Skill:
    """One parsed skill. ``analyst`` is a list so a skill can mount on multiple
    analysts (e.g. semiconductor-cycle on both market and industry)."""

    name: str
    description: str
    version: str
    analyst: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    regimes: list[str] = field(default_factory=list)
    instruments: list[str] = field(default_factory=list)
    markets: list[str] = field(default_factory=list)
    body: str = ""
    source_path: str = ""


def _as_list(v) -> list[str]:
    """Coerce a YAML scalar/list to a list of trimmed non-empty strings."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip()
    return [s] if s else []


def _parse_skill_file(path: Path) -> Skill | None:
    """Parse one .md skill file. Returns None on any failure (skip + warn)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — best-effort, never block
        logger.warning("skill: cannot read %s: %s", path, exc)
        return None

    if not text.startswith("---"):
        logger.warning("skill: %s missing YAML frontmatter (must start with '---')", path)
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        logger.warning("skill: %s malformed frontmatter (no closing '---')", path)
        return None
    fm_str, body = parts[1], parts[2].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_str) or {}
    except yaml.YAMLError as exc:
        logger.warning("skill: %s YAML parse error: %s", path, exc)
        return None
    if not isinstance(fm, dict):
        logger.warning("skill: %s frontmatter is not a mapping", path)
        return None

    name = str(fm.get("name", "")).strip()
    analysts = _as_list(fm.get("analyst"))
    # normalise + validate analyst keys
    analysts = [a.lower() for a in analysts if a.lower() in _VALID_ANALYSTS]
    if not name or not analysts:
        logger.warning("skill: %s missing 'name' or valid 'analyst' (got name=%r, analyst=%r)",
                       path, name, fm.get("analyst"))
        return None

    return Skill(
        name=name,
        description=str(fm.get("description", "")).strip(),
        version=str(fm.get("version", "1.0.0")).strip() or "1.0.0",
        analyst=analysts,
        tags=_as_list(fm.get("tags")),
        regimes=_as_list(fm.get("regimes")),
        instruments=_as_list(fm.get("instruments")),
        markets=_as_list(fm.get("markets")),
        body=body,
        source_path=str(path),
    )


def _scan_dir(root: Path) -> list[Path]:
    """All .md files under root (recursive), sorted for stable order."""
    if not root or not root.exists():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


class SkillLoader:
    """Discover + parse skill files from built-in + user paths (cached)."""

    def __init__(self, config: dict | None = None):
        cfg = (config or {}).get("skills", {}) or {}
        self._enabled = bool(cfg.get("enabled", True))
        user_path = cfg.get("path", "~/.tradingagents/skills/")
        self._user_path = Path(os.path.expanduser(user_path))
        self._cache: dict[str, list[Skill]] | None = None
        self._by_name: dict[str, Skill] | None = None

    def _load_uncached(self) -> dict[str, list[Skill]]:
        if not self._enabled:
            return {}
        by_analyst: dict[str, list[Skill]] = {k: [] for k in _VALID_ANALYSTS}
        by_name: dict[str, Skill] = {}
        # Built-in first; user path scanned second so same-named user skills override.
        for root in (_BUILTIN_ROOT, self._user_path):
            for path in _scan_dir(root):
                skill = _parse_skill_file(path)
                if skill is None:
                    continue
                if skill.name in by_name:
                    # override: drop the earlier (built-in) copy from every analyst bucket
                    prev = by_name[skill.name]
                    for ak in prev.analyst:
                        by_analyst[ak] = [s for s in by_analyst[ak] if s.name != prev.name]
                for ak in skill.analyst:
                    # avoid intra-file dupes if analyst list repeats a key
                    if skill not in by_analyst[ak]:
                        by_analyst[ak].append(skill)
                by_name[skill.name] = skill
        return by_analyst

    def load_all(self) -> dict[str, list[Skill]]:
        """Return ``{analyst_key: [Skill, ...]}`` (cached). Empty if disabled."""
        if self._cache is None:
            self._cache = self._load_uncached()
        return self._cache

    def get_by_name(self, name: str) -> Skill | None:
        """Cross-analyst name lookup (used by the ``request_skill`` tool)."""
        if self._by_name is None:
            self.load_all()
            self._by_name = {
                s.name: s
                for skills in (self._cache or {}).values()
                for s in skills
            }
        return self._by_name.get(name)

    def reload(self) -> None:
        """Drop the cache so the next load re-scans disk (new/edited skills)."""
        self._cache = None
        self._by_name = None
