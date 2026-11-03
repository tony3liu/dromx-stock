"""User tools — 用户工具（持仓、交易记录、操作复盘）

自注册工具：需要用户数据（持仓、交易记录）。
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from dromx.tools.registry import registry, tool_error, tool_result

logger = logging.getLogger(__name__)


def _get_my_portfolio(args: dict, llm=None, config=None) -> str:
    """获取用户当前持仓"""
    try:
        from webapp.backend.portfolio import get_user_portfolio

        portfolio = get_user_portfolio()
        return tool_result({"data": portfolio})
    except Exception as e:
        return tool_error(f"Failed to get portfolio: {e}")


def _get_my_position(args: dict, llm=None, config=None) -> str:
    """获取用户某只股票的持仓"""
    ticker = args.get("ticker", "")
    if not ticker:
        return tool_error("Missing required param: ticker")

    try:
        from webapp.backend.portfolio import get_user_position

        position = get_user_position(ticker)
        return tool_result({"data": position})
    except Exception as e:
        return tool_error(f"Failed to get position: {e}")


def _analyze_my_operation(args: dict, llm=None, config=None) -> str:
    """分析用户的一笔操作"""
    ticker = args.get("ticker", "")
    operation = args.get("operation", "")  # buy/sell/hold
    price = args.get("price")
    date = args.get("date", "")
    shares = args.get("shares")

    if not ticker or not operation or price is None or not date:
        return tool_error("Missing required params: ticker, operation, price, date")

    try:
        from webapp.backend.portfolio import analyze_operation

        result = analyze_operation(ticker, operation, price, date, shares)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to analyze operation: {e}")


# 注册工具
registry.register(
    name="get_my_portfolio",
    toolset="user",
    schema={
        "description": "获取用户当前持仓。当用户问『我的持仓』或『我的股票』时调用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=_get_my_portfolio,
    description="获取用户当前持仓",
)

registry.register(
    name="get_my_position",
    toolset="user",
    schema={
        "description": "获取用户某只股票的持仓。当用户问『我持有这只股票吗』或『我的成本价是多少』时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
            },
            "required": ["ticker"],
        },
    },
    handler=_get_my_position,
    description="获取用户某只股票的持仓",
)

registry.register(
    name="analyze_my_operation",
    toolset="user",
    schema={
        "description": "分析用户的一笔操作（买/卖/持有）。当用户问『我这笔操作对不对』或『怎么补救』时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "operation": {"type": "string", "description": "操作类型：buy/sell/hold"},
                "price": {"type": "number", "description": "操作价格"},
                "date": {"type": "string", "description": "操作日期，yyyy-mm-dd"},
                "shares": {"type": "number", "description": "股数（可选）"},
            },
            "required": ["ticker", "operation", "price", "date"],
        },
    },
    handler=_analyze_my_operation,
    description="分析用户的一笔操作",
)
