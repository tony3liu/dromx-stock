"""AI 自然语言选股核心（P0/P1 共用层）

三层架构：
  ① LLM 意图解析 → 生成筛选策略代码（AST 安全校验，落盘 ~/.dromx/strategies/ai/）
  ② 机器全市场快筛（StrategyEngine + DataAdapter 快照缓存）
  ③ LLM 批量研判 top N：逐票入选逻辑 / 风险 / 观察点

P1 多轮澄清：`run_ai_screen(..., refine_from=<strategy_id>, feedback="更看重位置低的")`
会加载已有策略代码，连同反馈一起让 LLM 输出修订版，再重跑筛选。

此模块同时持有全进程统一的 per-market 引擎缓存（webapp 端点与投研助手工具共用）。
"""

from __future__ import annotations

import json
import logging
import re
import threading
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from dromx.strategy.data_adapter import DataAdapter
from dromx.strategy.engine import StrategyEngine

logger = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).resolve().parent / "builtin"
AI_STRATEGY_DIR = Path.home() / ".dromx" / "strategies" / "ai"
CUSTOM_STRATEGY_DIR = Path.home() / ".dromx" / "strategies" / "custom"

_MARKETS = ("hk", "us", "cn")

_engines: dict[str, StrategyEngine] = {}
_adapter = DataAdapter()
_lock = threading.Lock()


def _strategy_dirs() -> list[Path]:
    for d in (AI_STRATEGY_DIR, CUSTOM_STRATEGY_DIR):
        d.mkdir(parents=True, exist_ok=True)
    return [_BUILTIN_DIR, CUSTOM_STRATEGY_DIR, AI_STRATEGY_DIR]


def get_engine(market: str) -> StrategyEngine:
    """per-market 引擎缓存（首次构建加载策略目录 + 快照 adapter）"""
    market = (market or "cn").lower()
    if market not in _MARKETS:
        raise ValueError(f"未知市场: {market} (支持 hk/us/cn)")
    with _lock:
        if market not in _engines:
            def loader(as_of: date) -> pl.DataFrame:
                # 默认预筛：只保留当日有波动的标的，控制指标计算量
                return _adapter.load_universe(
                    market, as_of, prefilter=pl.col("change_pct").abs() > 0.02
                )

            _engines[market] = StrategyEngine(loader, _strategy_dirs(), market=market)
    return _engines[market]


def reload_engines() -> None:
    with _lock:
        for eng in _engines.values():
            eng.reload()


def run_ai_screen(
    llm,
    prompt: str,
    market: str = "cn",
    as_of: date | None = None,
    review_top_n: int = 8,
    refine_from: str | None = None,
    feedback: str | None = None,
) -> dict[str, Any]:
    """自然语言选股主入口。

    Args:
        llm: LangChain 风格 LLM（.invoke）
        prompt: 选股意图（首轮）或原始意图（多轮时保留）
        market: cn / hk / us
        as_of: 筛选日期，默认今天
        review_top_n: AI 研判前 N 只
        refine_from: 多轮澄清时，基于此策略 id（ai/ 目录中的代码）修订
        feedback: 多轮澄清的用户补充要求

    Returns:
        {strategy: {id,name,description}, as_of, market, total, elapsed_ms,
         rows, reviews, prompt, feedback?}
    """
    from dromx.strategy.ai_generator import AIStrategyGenerator

    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("prompt required")
    as_of = as_of or date.today()

    # 多轮澄清：加载被修订的策略代码
    base_code = None
    if refine_from:
        base_path = AI_STRATEGY_DIR / f"{refine_from}.py"
        if not base_path.exists():
            raise ValueError(f"策略 {refine_from} 不存在，无法基于它修订")
        base_code = base_path.read_text(encoding="utf-8")

    # ① 意图 → 策略代码
    gen = AIStrategyGenerator(llm).generate(prompt, base_code=base_code, feedback=feedback)
    if not gen.get("valid"):
        raise ValueError(gen.get("error") or "策略生成失败，请换个描述试试")
    meta = gen["meta"]
    sid = meta.get("id", "")
    if not re.fullmatch(r"ai_[A-Za-z0-9_-]+", sid):
        raise ValueError(f"AI 策略 id 非法: {sid}")

    target = AI_STRATEGY_DIR / f"{sid}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(gen["code"], encoding="utf-8")
    reload_engines()

    # ② 机器快筛
    eng = get_engine(market)
    if not eng.has(sid):
        raise ValueError(f"策略 {sid} 加载失败（语法或门控问题）")
    result = eng.run(sid, as_of)

    # ③ LLM 批量研判
    top_n = max(1, min(int(review_top_n), 20))
    reviews = review_hits(llm, prompt, meta, result.rows[:top_n], market, feedback=feedback)

    out = {
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
    if feedback:
        out["feedback"] = feedback
    return out


def review_hits(
    llm, prompt: str, meta: dict, rows: list[dict], market: str,
    feedback: str | None = None,
) -> dict:
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
        market_cn = {"cn": "A股", "hk": "港股", "us": "美股"}.get(market, market)
        refine_note = f"\n用户最新的补充要求：「{feedback}」，点评时优先回应它。" if feedback else ""
        msg = (
            f"用户的选股意图：「{prompt}」（市场：{market_cn}）\n"
            f"AI 生成的策略「{meta.get('name', '')}」：{meta.get('description', '')}\n\n"
            f"按评分排序的命中标的：\n{chr(10).join(lines)}\n{refine_note}\n"
            "你是资深选股研究员。逐票点评（每只 2-3 句）：为什么它符合用户意图、"
            "主要风险、一个关键观察点（价位/信号/事件）。不要编造数据，只基于给定指标和常识。\n"
            "严格输出 JSON 数组，不要输出其他内容："
            '[{"symbol": "代码", "comment": "点评..."}]'
        )
        resp = llm.invoke(msg)
        text = getattr(resp, "content", None) or str(resp)
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return {}
        items = json.loads(text[start : end + 1])
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
