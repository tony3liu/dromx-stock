"""Data tools — 数据工具（复用现有 dataflows）

自注册工具：在模块级别调用 `registry.register()`。
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from dromx.assistant.registry import registry, tool_error, tool_result
from dromx.dataflows.interface import route_to_vendor

logger = logging.getLogger(__name__)


def _get_stock_data(args: dict) -> str:
    """获取股票 OHLCV 数据"""
    symbol = args.get("symbol", "")
    start_date = args.get("start_date", "")
    end_date = args.get("end_date", "")
    if not symbol or not start_date or not end_date:
        return tool_error("Missing required params: symbol, start_date, end_date")
    try:
        result = route_to_vendor("get_stock_data", symbol, start_date, end_date)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get stock data: {e}")


def _get_news(args: dict) -> str:
    """获取股票新闻"""
    ticker = args.get("ticker", "")
    start_date = args.get("start_date", "")
    end_date = args.get("end_date", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        result = route_to_vendor("get_news", ticker, start_date, end_date)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get news: {e}")


def _get_global_news(args: dict) -> str:
    """获取全球新闻"""
    curr_date = args.get("curr_date", "")
    look_back_days = args.get("look_back_days")
    limit = args.get("limit")
    try:
        result = route_to_vendor("get_global_news", curr_date, look_back_days, limit)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get global news: {e}")


def _get_indicators(args: dict) -> str:
    """获取技术指标"""
    symbol = args.get("symbol", "")
    indicator = args.get("indicator", "")
    curr_date = args.get("curr_date", "")
    if not symbol or not indicator:
        return tool_error("Missing required params: symbol, indicator")
    try:
        result = route_to_vendor("get_indicators", symbol, indicator, curr_date)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get indicators: {e}")


def _get_fundamentals(args: dict) -> str:
    """获取基本面数据"""
    ticker = args.get("ticker", "")
    curr_date = args.get("curr_date", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        result = route_to_vendor("get_fundamentals", ticker, curr_date)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get fundamentals: {e}")


def _get_insider_transactions(args: dict) -> str:
    """获取内部人交易"""
    ticker = args.get("ticker", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        result = route_to_vendor("get_insider_transactions", ticker)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get insider transactions: {e}")


def _get_macro_data(args: dict) -> str:
    """获取宏观数据"""
    try:
        result = route_to_vendor("get_macro_indicators")
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get macro data: {e}")


def _get_prediction_markets(args: dict) -> str:
    """获取预测市场数据"""
    try:
        result = route_to_vendor("get_prediction_markets")
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get prediction markets: {e}")


# 注册工具
registry.register(
    name="get_stock_data",
    toolset="data",
    schema={
        "description": "获取股票 OHLCV 历史数据",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "股票代码，如 AAPL, 600519.SS"},
                "start_date": {"type": "string", "description": "开始日期，yyyy-mm-dd"},
                "end_date": {"type": "string", "description": "结束日期，yyyy-mm-dd"},
            },
            "required": ["symbol", "start_date", "end_date"],
        },
    },
    handler=_get_stock_data,
    description="获取股票 OHLCV 历史数据",
)

registry.register(
    name="get_news",
    toolset="data",
    schema={
        "description": "获取股票相关新闻",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "start_date": {"type": "string", "description": "开始日期，yyyy-mm-dd"},
                "end_date": {"type": "string", "description": "结束日期，yyyy-mm-dd"},
            },
            "required": ["ticker"],
        },
    },
    handler=_get_news,
    description="获取股票相关新闻",
)

registry.register(
    name="get_global_news",
    toolset="data",
    schema={
        "description": "获取全球宏观新闻",
        "parameters": {
            "type": "object",
            "properties": {
                "curr_date": {"type": "string", "description": "当前日期，yyyy-mm-dd"},
                "look_back_days": {"type": "integer", "description": "回看天数"},
                "limit": {"type": "integer", "description": "最大条数"},
            },
        },
    },
    handler=_get_global_news,
    description="获取全球宏观新闻",
)

registry.register(
    name="get_indicators",
    toolset="data",
    schema={
        "description": "获取股票技术指标",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "股票代码"},
                "indicator": {"type": "string", "description": "指标名称，如 ma, macd, rsi"},
                "curr_date": {"type": "string", "description": "当前日期，yyyy-mm-dd"},
            },
            "required": ["symbol", "indicator"],
        },
    },
    handler=_get_indicators,
    description="获取股票技术指标",
)

registry.register(
    name="get_fundamentals",
    toolset="data",
    schema={
        "description": "获取公司基本面数据",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "curr_date": {"type": "string", "description": "当前日期，yyyy-mm-dd"},
            },
            "required": ["ticker"],
        },
    },
    handler=_get_fundamentals,
    description="获取公司基本面数据",
)

registry.register(
    name="get_insider_transactions",
    toolset="data",
    schema={
        "description": "获取内部人交易数据",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
            },
            "required": ["ticker"],
        },
    },
    handler=_get_insider_transactions,
    description="获取内部人交易数据",
)

registry.register(
    name="get_macro_data",
    toolset="data",
    schema={
        "description": "获取宏观经济数据（利率、通胀、就业等）",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=_get_macro_data,
    description="获取宏观经济数据",
)

registry.register(
    name="get_prediction_markets",
    toolset="data",
    schema={
        "description": "获取预测市场数据（事件概率）",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=_get_prediction_markets,
    description="获取预测市场数据",
)
