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


class AIScreenRequest(BaseModel):
    prompt: str
    market: str = "cn"
    as_of: str | None = None
    review_top_n: int = 8          # AI 研判前 N 只（一次 LLM 调用，控制成本）


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


@router.post("/ai-screen")
def ai_screen(req: AIScreenRequest, _: None = Depends(auth.require_auth)) -> dict:
    """自然语言选股（P0 三层架构）：

    ① LLM 意图解析 → 生成筛选策略代码（AST 安全校验，落盘 ai/ 目录可复用）
    ② 机器全市场快筛（现有 strategy engine + 快照缓存）
    ③ LLM 批量研判 top N：逐票输出入选逻辑 / 风险 / 观察点
    """
    from dromx.strategy.ai_generator import AIStrategyGenerator

    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt required")

    llm = _qa_llm()

    # ① 意图 → 策略代码
    gen = AIStrategyGenerator(llm).generate(prompt)
    if not gen.get("valid"):
        raise HTTPException(status_code=422, detail=gen.get("error") or "策略生成失败，请换个描述试试")
    meta = gen["meta"]
    sid = meta.get("id", "")
    if not re.fullmatch(r"ai_[A-Za-z0-9_-]+", sid):
        raise HTTPException(status_code=400, detail=f"AI 策略 id 非法: {sid}")

    # 策略落盘（同名覆盖即更新）并热加载
    target = _USER_DIRS["ai"] / f"{sid}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(gen["code"], encoding="utf-8")
    _reload_all_engines()

    # ② 机器快筛
    eng = _get_engine(req.market)
    if not eng.has(sid):
        raise HTTPException(status_code=500, detail=f"策略 {sid} 加载失败（见策略列表错误信息）")
    as_of = _parse_date(req.as_of)
    result = eng.run(sid, as_of)

    # ③ LLM 批量研判 top N（一次调用）
    top_n = max(1, min(int(req.review_top_n), 20))
    reviews = _review_hits(llm, prompt, meta, result.rows[:top_n], req.market)

    return {
        "prompt": prompt,
        "strategy": {
            "id": sid,
            "name": meta.get("name", ""),
            "description": meta.get("description", ""),
        },
        "as_of": result.as_of,
        "market": result.market,
        "total": result.total,
        "elapsed_ms": result.elapsed_ms,
        "rows": result.rows,
        "reviews": reviews,
    }


def _review_hits(llm, prompt: str, meta: dict, rows: list[dict], market: str) -> dict:
    """对命中 top N 逐票生成 AI 点评；失败返回 {}（不阻塞主结果）。"""
    if not rows:
        return {}
    try:
        lines = []
        for r in rows:
            lines.append(
                f"- {r.get('symbol')} {r.get('name') or ''}: 现价{r.get('close')}, "
                f"涨跌幅{_fmt_pct(r.get('change_pct'))}, 换手{_fmt_pct(r.get('turnover_rate'))}, "
                f"RSI14={r.get('rsi_14')}, 量比5d={r.get('vol_ratio_5d')}, 评分={r.get('score')}"
            )
        table = "\n".join(lines)
        market_cn = {"cn": "A股", "hk": "港股", "us": "美股"}.get(market, market)
        msg = (
            f"用户的选股意图：「{prompt}」（市场：{market_cn}）\n"
            f"AI 生成的策略「{meta.get('name', '')}」：{meta.get('description', '')}\n\n"
            f"按评分排序的命中标的：\n{table}\n\n"
            "你是资深选股研究员。逐票点评（每只 2-3 句）：为什么它符合用户意图、"
            "主要风险、一个关键观察点（价位/信号/事件）。不要编造数据，只基于给定指标和常识。\n"
            "严格输出 JSON 数组，不要输出其他内容："
            '[{"symbol": "代码", "comment": "点评..."}]'
        )
        resp = llm.invoke(msg)
        text = getattr(resp, "content", None) or str(resp)
        import json as _json

        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return {}
        items = _json.loads(text[start : end + 1])
        return {
            str(i.get("symbol")): str(i.get("comment", ""))
            for i in items
            if isinstance(i, dict) and i.get("symbol")
        }
    except Exception as e:  # noqa: BLE001 — 点评失败不影响筛选结果
        logger.warning("ai_screen review failed: %s", e)
        return {}


def _fmt_pct(v) -> str:
    try:
        return f"{float(v) * 100:.2f}%"
    except (TypeError, ValueError):
        return "—"


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
