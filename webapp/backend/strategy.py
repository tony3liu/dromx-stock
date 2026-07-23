"""Strategy screening API (v0.4.0) — HTTP glue over the strategy engine.

Endpoints (PRD §2.1.2 / §4.2):
  GET    /api/strategies              list strategies (optionally per market)
  GET    /api/strategies/{id}         strategy detail + param schema
  POST   /api/strategies/{id}/run     run a screen, return the hit list
  POST   /api/strategies/generate     AI-generate a strategy from a prompt
  DELETE /api/strategies/{id}         delete a custom/AI strategy

The engine is built lazily per market (mirrors main.py's ``_get_qa_llm``) and
cached, so the first screen for a market pays the universe fetch and everything
after that day is served from the DataAdapter's parquet cache. Screening is a
bounded, best-effort read — errors surface as HTTP 4xx/5xx, never crash the app.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict
from datetime import date
from pathlib import Path

import polars as pl
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dromx.strategy.data_adapter import DataAdapter
from dromx.strategy.engine import StrategyEngine
from webapp.backend import auth

logger = logging.getLogger("dromx.web.strategy")

_BUILTIN_DIR = Path(__file__).resolve().parents[2] / "dromx" / "strategy" / "builtin"
_USER_DIRS = {
    "custom": Path.home() / ".dromx" / "strategies" / "custom",
    "ai": Path.home() / ".dromx" / "strategies" / "ai",
}
_MARKETS = ("hk", "us", "cn")

# Per-market engine cache (built lazily). Each engine loads builtin + user dirs
# and is gated to strategies that apply to that market.
_engines: dict[str, StrategyEngine] = {}
_adapter = DataAdapter()


def _strategy_dirs() -> list[Path]:
    for d in _USER_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    return [_BUILTIN_DIR, *_USER_DIRS.values()]


def _get_engine(market: str) -> StrategyEngine:
    market = (market or "hk").lower()
    if market not in _MARKETS:
        raise HTTPException(status_code=400, detail=f"未知市场: {market} (支持 hk/us/cn)")
    if market not in _engines:
        loader = _make_loader(market)
        _engines[market] = StrategyEngine(loader, _strategy_dirs(), market=market)
    return _engines[market]


def _make_loader(market: str):
    """Build the enriched-frame loader for a market (DataAdapter.load_universe)."""
    def loader(as_of: date) -> pl.DataFrame:
        # Generic default prefilter: only names that actually moved today, so the
        # expensive stage-2 indicator compute stays bounded. Strategies still get
        # the full computed frame for the shortlisted candidates.
        return _adapter.load_universe(
            market, as_of, prefilter=pl.col("change_pct").abs() > 0.02
        )
    return loader


def _reload_all_engines() -> None:
    for eng in _engines.values():
        eng.reload()


# ---------------------------------------------------------------------------
# Detail serialization
# ---------------------------------------------------------------------------


def _strategy_detail(s) -> dict:
    return {
        "id": s.meta["id"],
        "name": s.meta.get("name", ""),
        "description": s.meta.get("description", ""),
        "markets": s.meta.get("markets", []),
        "tags": s.meta.get("tags", []),
        "source": s.source,
        "params": s.meta.get("params", []),
        "params_defaults": {p["id"]: p.get("default") for p in s.meta.get("params", [])},
        "scoring": s.meta.get("scoring", {}),
        "basic_filter": s.basic_filter,
        "entry_signals": s.entry_signals,
        "exit_signals": s.exit_signals,
        "stop_loss": s.stop_loss,
        "max_hold_days": s.max_hold_days,
        "limit": s.meta.get("limit", 50),
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    market: str = "hk"
    as_of: str | None = None       # YYYY-MM-DD; defaults to today
    pool: list[str] | None = None  # limit to these symbols
    params: dict | None = None


class GenerateRequest(BaseModel):
    prompt: str
    save: bool = False             # persist to ~/.dromx/strategies/ai/ when valid


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
def list_strategies(market: str = "hk", _: None = Depends(auth.require_auth)) -> dict:
    """List strategies available for a market (builtin + custom + AI)."""
    eng = _get_engine(market)
    strategies = [_strategy_detail(eng.get(m["id"])) for m in eng.list_strategies()]
    return {"market": market, "strategies": strategies, "load_errors": eng.load_errors()}


@router.get("/{strategy_id}")
def get_strategy(strategy_id: str, market: str = "hk",
                 _: None = Depends(auth.require_auth)) -> dict:
    eng = _get_engine(market)
    try:
        return _strategy_detail(eng.get(strategy_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{strategy_id}/run")
def run_strategy(strategy_id: str, req: RunRequest,
                 _: None = Depends(auth.require_auth)) -> dict:
    """Execute a screen and return the hit list."""
    eng = _get_engine(req.market)
    if not eng.has(strategy_id):
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 在 {req.market} 市场不可用")
    as_of = _parse_date(req.as_of)
    try:
        result = eng.run(strategy_id, as_of, pool=req.pool, params=req.params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return asdict(result)


@router.post("/generate")
def generate_strategy(req: GenerateRequest, _: None = Depends(auth.require_auth)) -> dict:
    """AI-generate a strategy from a natural-language prompt (optionally save it)."""
    from dromx.strategy.ai_generator import AIStrategyGenerator

    result = AIStrategyGenerator(_qa_llm()).generate(req.prompt)
    if req.save and result.get("valid"):
        sid = (result.get("meta") or {}).get("id", "")
        if not re.fullmatch(r"ai_[A-Za-z0-9_-]+", sid):
            raise HTTPException(status_code=400, detail="AI 策略 id 必须形如 ai_xxx（字母/数字/下划线/短横线）")
        path = _USER_DIRS["ai"]
        path.mkdir(parents=True, exist_ok=True)
        target = path / f"{sid}.py"
        target.write_text(result["code"], encoding="utf-8")
        _reload_all_engines()
        result["saved_path"] = str(target)
    return result


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: str, market: str = "hk",
                    _: None = Depends(auth.require_auth)) -> dict:
    """Delete a custom/AI strategy (builtin strategies cannot be deleted)."""
    eng = _get_engine(market)
    try:
        s = eng.get(strategy_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if s.source == "builtin":
        raise HTTPException(status_code=403, detail="内置策略不可删除")
    if s.file_path and s.file_path.exists():
        s.file_path.unlink()
    _reload_all_engines()
    return {"ok": True, "id": strategy_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(s: str | None) -> date:
    if not s:
        return date.today()
    try:
        return date.fromisoformat(s.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {s} (应为 YYYY-MM-DD)") from e


def _qa_llm():
    """Reuse the app's lazily-built quick LLM for AI strategy generation."""
    from webapp.backend import main

    return main._get_qa_llm()
