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

import re
from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dromx.strategy.ai_screen import (
    AI_STRATEGY_DIR,
    _adapter,  # noqa: F401 — 供 scheduler.py 经 strategy_api._adapter 复用
    get_engine as _get_engine_core,
    reload_engines,
)
from dromx.strategy.engine import StrategyEngine
from webapp.backend import auth

# scheduler.py 引用 ``strategy_api._adapter`` 做监控/预热；复用 ai_screen 的单例
# 实例（同一 DataAdapter，避免重复创建与缓存分叉）。

# 引擎缓存统一在 dromx.strategy.ai_screen（投研助手工具与 web 端点共用）
_MARKETS = ("hk", "us", "cn")


def _get_engine(market: str) -> StrategyEngine:
    market = (market or "hk").lower()
    if market not in _MARKETS:
        raise HTTPException(status_code=400, detail=f"未知市场: {market} (支持 hk/us/cn)")
    try:
        return _get_engine_core(market)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _reload_all_engines() -> None:
    reload_engines()


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


class AIScreenRequest(BaseModel):
    prompt: str
    market: str = "cn"
    as_of: str | None = None
    review_top_n: int = 8          # AI 研判前 N 只（一次 LLM 调用，控制成本）
    refine_from: str | None = None  # 多轮澄清：基于此 AI 策略 id 修订
    feedback: str | None = None     # 多轮澄清：用户补充要求


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


# 注意：/history 必须声明在 /{strategy_id} 之前，否则会被路径参数吞掉
@router.get("/history")
def screen_history(limit: int = 20, _: None = Depends(auth.require_auth)) -> dict:
    """选股历史（摘要，新→旧）"""
    from dromx.strategy.screen_history import list_recent

    return {"history": list_recent(max(1, min(limit, 50)))}


@router.get("/history/{history_id}")
def screen_history_detail(history_id: str, _: None = Depends(auth.require_auth)) -> dict:
    """选股历史详情（含命中行与 AI 研判）"""
    from dromx.strategy.screen_history import get

    record = get(history_id)
    if record is None:
        raise HTTPException(status_code=404, detail="history not found")
    return record


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
        path = AI_STRATEGY_DIR
        path.mkdir(parents=True, exist_ok=True)
        target = path / f"{sid}.py"
        target.write_text(result["code"], encoding="utf-8")
        _reload_all_engines()
        result["saved_path"] = str(target)
    return result


@router.post("/ai-screen")
def ai_screen(req: AIScreenRequest, _: None = Depends(auth.require_auth)) -> dict:
    """自然语言选股（三层架构 + P1 多轮澄清）：

    ① LLM 意图解析 → 生成筛选策略代码（AST 安全校验，落盘可复用）
    ② 机器全市场快筛（strategy engine + 快照缓存）
    ③ LLM 批量研判 top N：逐票输出入选逻辑 / 风险 / 观察点

    多轮澄清：传 refine_from（已有 AI 策略 id）+ feedback（补充要求），
    LLM 会基于原策略修订后重跑。
    """
    from dromx.strategy.ai_screen import run_ai_screen

    try:
        return run_ai_screen(
            llm=_qa_llm(),
            prompt=req.prompt,
            market=req.market,
            as_of=_parse_date(req.as_of),
            review_top_n=req.review_top_n,
            refine_from=req.refine_from,
            feedback=req.feedback,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


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
