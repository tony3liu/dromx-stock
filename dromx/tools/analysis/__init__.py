"""Analysis tools — 分析工具（包装现有流水线/模块）

自注册工具：把现有 DromXGraph / backtest / strategy / hedge / factor / sizing
包装成可调用的 tool。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Annotated

from dromx.tools.registry import registry, tool_error, tool_result

logger = logging.getLogger(__name__)


def _run_deep_analysis(args: dict, llm=None, config=None) -> str:
    """运行深度分析流水线"""
    ticker = args.get("ticker", "")
    date = args.get("date") or datetime.now().strftime("%Y-%m-%d")
    analysts = args.get("analysts") or ["market", "social", "news", "fundamentals", "industry"]
    depth = args.get("depth", 3)

    if not ticker:
        return tool_error("Missing required param: ticker")

    try:
        from webapp.backend.runner import run_analysis_once

        result, rating = run_analysis_once(ticker, date, analysts, depth)
        decision = result.get("final_trade_decision", "")
        return tool_result({
            "ticker": ticker,
            "date": date,
            "rating": rating,
            "decision": decision,
            "sections": {k: v for k, v in result.items() if isinstance(v, str)},
        })
    except Exception as e:
        return tool_error(f"Deep analysis failed: {e}")


def _run_backtest(args: dict, llm=None, config=None) -> str:
    """运行回测"""
    ticker = args.get("ticker", "")
    start_date = args.get("start_date", "")
    end_date = args.get("end_date", "")
    analysts = args.get("analysts") or ["market", "social", "news", "fundamentals", "industry"]
    depth = args.get("depth", 3)
    holding_days = args.get("holding_days", 5)

    if not ticker or not start_date or not end_date:
        return tool_error("Missing required params: ticker, start_date, end_date")

    try:
        from webapp.backend.backtest import run_backtest_once

        result = run_backtest_once(
            ticker, start_date, end_date,
            analysts=analysts, depth=depth, holding_days=holding_days,
        )
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Backtest failed: {e}")


def _run_screener(args: dict, llm=None, config=None) -> str:
    """运行选股策略"""
    strategy_id = args.get("strategy_id", "")
    market = args.get("market", "cn")
    as_of = args.get("as_of")

    if not strategy_id:
        return tool_error("Missing required param: strategy_id")

    try:
        from webapp.backend.strategy import run_strategy

        result = run_strategy(strategy_id, market, as_of)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Screener failed: {e}")


def _run_hedge_analysis(args: dict, llm=None, config=None) -> str:
    """运行对冲分析"""
    try:
        from webapp.backend.hedge import run_hedge_analysis

        result = run_hedge_analysis()
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Hedge analysis failed: {e}")


def _run_factor_analysis(args: dict, llm=None, config=None) -> str:
    """运行因子分析"""
    ticker = args.get("ticker", "")
    if not ticker:
        return tool_error("Missing required param: ticker")

    try:
        from webapp.backend.factor import run_factor_analysis

        result = run_factor_analysis(ticker)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Factor analysis failed: {e}")


def _run_sizing_analysis(args: dict, llm=None, config=None) -> str:
    """运行仓位分析"""
    run_id = args.get("run_id", "")
    if not run_id:
        return tool_error("Missing required param: run_id")

    try:
        from webapp.backend.sizing import run_sizing_analysis

        result = run_sizing_analysis(run_id)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Sizing analysis failed: {e}")


# 注册工具
registry.register(
    name="run_deep_analysis",
    toolset="analysis",
    schema={
        "description": "运行深度分析流水线（19节点多智能体投研）。当用户需要『深度分析一只股票』时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码，如 NVDA, 600519.SS"},
                "date": {"type": "string", "description": "分析日期，yyyy-mm-dd，默认今天"},
                "analysts": {"type": "array", "items": {"type": "string"}, "description": "分析师列表"},
                "depth": {"type": "integer", "description": "分析深度 1-5，默认 3"},
            },
            "required": ["ticker"],
        },
    },
    handler=_run_deep_analysis,
    description="运行深度分析流水线",
)

registry.register(
    name="run_backtest",
    toolset="analysis",
    schema={
        "description": "运行历史回测。当用户需要『回测这只股票的历史表现』时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "start_date": {"type": "string", "description": "开始日期，yyyy-mm-dd"},
                "end_date": {"type": "string", "description": "结束日期，yyyy-mm-dd"},
                "analysts": {"type": "array", "items": {"type": "string"}, "description": "分析师列表"},
                "depth": {"type": "integer", "description": "分析深度 1-5，默认 3"},
                "holding_days": {"type": "integer", "description": "持有天数，默认 5"},
            },
            "required": ["ticker", "start_date", "end_date"],
        },
    },
    handler=_run_backtest,
    description="运行历史回测",
)

registry.register(
    name="run_screener",
    toolset="analysis",
    schema={
        "description": "运行选股策略。当用户需要『筛选股票』或『找股票』时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "strategy_id": {"type": "string", "description": "策略 ID"},
                "market": {"type": "string", "description": "市场：hk/us/cn，默认 cn"},
                "as_of": {"type": "string", "description": "截止日期，yyyy-mm-dd"},
            },
            "required": ["strategy_id"],
        },
    },
    handler=_run_screener,
    description="运行选股策略",
)

registry.register(
    name="run_hedge_analysis",
    toolset="analysis",
    schema={
        "description": "运行跨品种对冲分析。当用户需要『对冲风险』或『看看持仓相关性』时调用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=_run_hedge_analysis,
    description="运行跨品种对冲分析",
)

registry.register(
    name="run_factor_analysis",
    toolset="analysis",
    schema={
        "description": "运行因子暴露分析。当用户需要『分析这只股票的因子暴露』时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
            },
            "required": ["ticker"],
        },
    },
    handler=_run_factor_analysis,
    description="运行因子暴露分析",
)

registry.register(
    name="run_sizing_analysis",
    toolset="analysis",
    schema={
        "description": "运行仓位建议分析。当用户需要『看看该买多少』或『仓位建议』时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "分析 run ID"},
            },
            "required": ["run_id"],
        },
    },
    handler=_run_sizing_analysis,
    description="运行仓位建议分析",
)
