"""Data tools — 数据工具（复用现有 dataflows）

自注册工具：在模块级别调用 `registry.register()`。
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from dromx.dataflows.interface import route_to_vendor
from dromx.tools.registry import registry, tool_error, tool_result

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


def _fetch_stocktwits(args: dict) -> str:
    """获取 StockTwits 消息"""
    ticker = args.get("ticker", "")
    limit = args.get("limit", 30)
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        from dromx.dataflows.stocktwits import fetch_stocktwits_messages
        result = fetch_stocktwits_messages(ticker, limit=limit)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to fetch stocktwits: {e}")


def _fetch_reddit(args: dict) -> str:
    """获取 Reddit 帖子"""
    ticker = args.get("ticker", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        from dromx.dataflows.reddit import fetch_reddit_posts
        result = fetch_reddit_posts(ticker)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to fetch reddit: {e}")


def _fetch_x_posts(args: dict) -> str:
    """获取 X (Twitter) 帖子"""
    ticker = args.get("ticker", "")
    limit = args.get("limit", 30)
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        from dromx.dataflows.x_twitter import fetch_x_posts
        result = fetch_x_posts(ticker, limit=limit)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to fetch x posts: {e}")


def _get_verified_market_snapshot(args: dict) -> str:
    """获取验证过的市场快照"""
    symbol = args.get("symbol", "")
    curr_date = args.get("curr_date", "")
    look_back_days = args.get("look_back_days", 30)
    if not symbol or not curr_date:
        return tool_error("Missing required params: symbol, curr_date")
    try:
        from dromx.dataflows.market_data_validator import build_verified_market_snapshot
        result = build_verified_market_snapshot(symbol, curr_date, look_back_days)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get verified market snapshot: {e}")


# ---------------------------------------------------------------------------
# 金十 MCP：商品/外汇行情 + 财经日历（需要 jin10_token）
# ---------------------------------------------------------------------------

def _has_jin10_token() -> bool:
    import os
    return any(
        os.environ.get(n, "").strip()
        for n in ("jin10_token", "JIN10_BEARER_TOKEN", "JIN10_TOKEN")
    )


def _get_commodity_quote(args: dict) -> str:
    """商品/外汇实时报价（金十）"""
    code = args.get("code", "")
    if not code:
        return tool_error("Missing required param: code")
    try:
        from dromx.dataflows.jin10 import get_quote
        return tool_result({"data": get_quote(code)})
    except Exception as e:
        return tool_error(f"Failed to get quote: {e}")


def _get_commodity_kline(args: dict) -> str:
    """商品/外汇分钟级 K 线（金十）"""
    code = args.get("code", "")
    if not code:
        return tool_error("Missing required param: code")
    try:
        from dromx.dataflows.jin10 import get_kline
        return tool_result({"data": get_kline(code, int(args.get("count", 30)))})
    except Exception as e:
        return tool_error(f"Failed to get kline: {e}")


def _get_economic_calendar(args: dict) -> str:
    """财经日历（金十）"""
    try:
        from dromx.dataflows.jin10 import get_calendar
        items = get_calendar()
        if not items:
            return tool_error("财经日历暂无数据")
        # 按公布时间倒序（最新/即将公布的在前），保留星级和多空影响字段
        items.sort(key=lambda x: str(x.get("pub_time") or ""), reverse=True)
        return tool_result({"data": items[:50], "count": len(items)})
    except Exception as e:
        return tool_error(f"Failed to get calendar: {e}")


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

registry.register(
    name="fetch_stocktwits",
    toolset="data",
    schema={
        "description": "获取 StockTwits 消息（散户情绪）",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "limit": {"type": "integer", "description": "最大条数，默认 30"},
            },
            "required": ["ticker"],
        },
    },
    handler=_fetch_stocktwits,
    description="获取 StockTwits 消息",
)

registry.register(
    name="fetch_reddit",
    toolset="data",
    schema={
        "description": "获取 Reddit 帖子（散户情绪）",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
            },
            "required": ["ticker"],
        },
    },
    handler=_fetch_reddit,
    description="获取 Reddit 帖子",
)

registry.register(
    name="fetch_x_posts",
    toolset="data",
    schema={
        "description": "获取 X (Twitter) 帖子（散户情绪）",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "limit": {"type": "integer", "description": "最大条数，默认 30"},
            },
            "required": ["ticker"],
        },
    },
    handler=_fetch_x_posts,
    description="获取 X (Twitter) 帖子",
)

registry.register(
    name="get_verified_market_snapshot",
    toolset="data",
    schema={
        "description": "获取验证过的市场快照（精确价格/指标/历史对比）",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "股票代码"},
                "curr_date": {"type": "string", "description": "当前日期，yyyy-mm-dd"},
                "look_back_days": {"type": "integer", "description": "回看天数，默认 30"},
            },
            "required": ["symbol", "curr_date"],
        },
    },
    handler=_get_verified_market_snapshot,
    description="获取验证过的市场快照",
)

registry.register(
    name="get_commodity_quote",
    toolset="data",
    schema={
        "description": "获取全球指数/商品/外汇的实时报价（金十数据）。支持：指数（KS11韩国KOSPI、DJI道指、SPX标普、000001上证、000300沪深300、399006创业板指、FTSE等）、商品（XAUUSD黄金、XAGUSD白银、USOIL WTI原油、UKOIL布油、COPPER铜）、外汇（EURUSD、USDJPY等）。不支持个股——个股行情请用 get_stock_data。",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "品种代码：XAUUSD黄金 / XAGUSD白银 / USOIL原油 / KS11韩国KOSPI / SPX标普 / 000300沪深300 等"},
            },
            "required": ["code"],
        },
    },
    handler=_get_commodity_quote,
    check_fn=_has_jin10_token,
    description="黄金/原油/外汇实时报价（金十）",
)

registry.register(
    name="get_commodity_kline",
    toolset="data",
    schema={
        "description": "获取黄金/白银/原油/外汇等品种的分钟级 K 线（金十数据）。代码同 get_commodity_quote。",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "品种代码，如 XAUUSD"},
                "count": {"type": "integer", "description": "K 线条数，默认 30，最大 200"},
            },
            "required": ["code"],
        },
    },
    handler=_get_commodity_kline,
    check_fn=_has_jin10_token,
    description="黄金/原油/外汇分钟级 K 线（金十）",
)

registry.register(
    name="get_economic_calendar",
    toolset="data",
    schema={
        "description": "获取财经日历：各国重要经济数据和事件（非农、CPI、GDP、央行利率决议等）的公布时间。当用户问『最近有什么重要数据/事件』『非农什么时候公布』时调用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=_get_economic_calendar,
    check_fn=_has_jin10_token,
    description="财经日历（非农/CPI/央行决议公布时间）",
)


# ---------------------------------------------------------------------------
# P0 新增：高级技术指标 / 基本面比率 / 估值模型 / 三表
# 思路借鉴 FinceptTerminal（AGPL）的指标/估值/比率类型，代码为重新实现。
# ---------------------------------------------------------------------------

def _get_advanced_indicators(args: dict) -> str:
    """高级技术指标（60+：ichimoku/adx/vortex/psar/kama/mfi/obv 等）"""
    symbol = args.get("symbol", "")
    indicators = args.get("indicators", "")
    curr_date = args.get("curr_date", "")
    if not symbol:
        return tool_error("Missing required param: symbol")
    try:
        from dromx.dataflows.advanced_indicators import compute_advanced_indicators
        from dromx.dataflows.stockstats_utils import load_ohlcv
        ind_list = [i.strip() for i in indicators.split(",") if i.strip()] if indicators else None
        ohlcv = load_ohlcv(symbol, curr_date or str(__import__("datetime").date.today()))
        if ohlcv is None or ohlcv.empty:
            return tool_error(f"No OHLCV data for {symbol}")
        result = compute_advanced_indicators(ohlcv, ind_list)
        return tool_result({"symbol": symbol, "indicators": result})
    except Exception as e:
        return tool_error(f"Failed to compute advanced indicators: {e}")


def _get_fundamental_ratios(args: dict) -> str:
    """CFA 级基本面比率（DuPont/ROE/流动性/偿债/效率）"""
    ticker = args.get("ticker", "")
    curr_date = args.get("curr_date", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        from dromx.dataflows.fundamental_ratios import build_fundamental_ratios
        report = build_fundamental_ratios(ticker, curr_date or str(__import__("datetime").date.today()))
        return tool_result({"ticker": ticker, "report": report})
    except Exception as e:
        return tool_error(f"Failed to build fundamental ratios: {e}")


def _run_valuation(args: dict) -> str:
    """估值模型（倍数法 + 可选 DCF/DDM 假设驱动）

    原则：估值依赖输入假设，本工具不臆造每股指标。自动获取的是市价；
    每股指标(eps/bvps/sps)或目标倍数由调用方提供，缺失则输出可用的部分
    并明确提示缺少什么。"""
    ticker = args.get("ticker", "")
    curr_date = args.get("curr_date", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        from dromx.dataflows.stockstats_utils import load_ohlcv
        from dromx.dataflows.valuation import (
            MultipleValuationInputs,
            multiple_valuation,
            valuation_summary,
        )

        today = curr_date or str(__import__("datetime").date.today())
        ohlcv = load_ohlcv(ticker, today)
        if ohlcv is None or ohlcv.empty:
            return tool_error(f"No OHLCV data for {ticker}")
        price = float(ohlcv["Close"].iloc[-1])

        m = MultipleValuationInputs(
            eps=args.get("eps"),
            bvps=args.get("bvps"),
            sps=args.get("sps"),
            ebitda_per_share=args.get("ebitda_per_share"),
            net_debt_per_share=args.get("net_debt_per_share"),
            pe_target=args.get("pe_target"),
            pb_target=args.get("pb_target"),
            ps_target=args.get("ps_target"),
            ev_ebitda_target=args.get("ev_ebitda_target"),
        )
        mult = multiple_valuation(m)
        return tool_result(valuation_summary(price, {}, mult))
    except Exception as e:
        return tool_error(f"Failed to run valuation: {e}")


def _get_balance_sheet(args: dict) -> str:
    """资产负债表（三表之一，供基本面分析）"""
    ticker = args.get("ticker", "")
    curr_date = args.get("curr_date", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        result = route_to_vendor("get_balance_sheet", ticker, "quarterly", curr_date or None)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get balance sheet: {e}")


def _get_income_statement(args: dict) -> str:
    """利润表（三表之一）"""
    ticker = args.get("ticker", "")
    curr_date = args.get("curr_date", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        result = route_to_vendor("get_income_statement", ticker, "quarterly", curr_date or None)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get income statement: {e}")


def _get_cashflow(args: dict) -> str:
    """现金流量表（三表之一）"""
    ticker = args.get("ticker", "")
    curr_date = args.get("curr_date", "")
    if not ticker:
        return tool_error("Missing required param: ticker")
    try:
        result = route_to_vendor("get_cashflow", ticker, "quarterly", curr_date or None)
        return tool_result({"data": result})
    except Exception as e:
        return tool_error(f"Failed to get cashflow: {e}")


registry.register(
    name="get_advanced_indicators",
    toolset="data",
    schema={
        "description": "计算高级技术指标（60+ 个）：趋势类(ichimoku/adx/vortex/psar/aroon/stc/kst/dpo/trix/mass_index)、动量类(kama/ppo/pvo/roc/tsi/awesome_oscillator/ultimate_oscillator/stoch_rsi/williams_r/cci)、波动类(atr/keltner_channel/donchian_channel/ulcer_index)、量能类(obv/adi/cmf/mfi/force_index/eom/vpt/nvi/vwap)。指标名逗号分隔；不填则全算。当用户问趋势结构、量价配合、超买超卖时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "股票代码，如 AAPL, 600519.SS"},
                "indicators": {"type": "string", "description": "逗号分隔的指标名，如 ichimoku,adx,mfi；空=全部"},
                "curr_date": {"type": "string", "description": "分析日期 yyyy-mm-dd，默认今天"},
            },
            "required": ["symbol"],
        },
    },
    handler=_get_advanced_indicators,
    description="高级技术指标（ichimoku/adx/vortex/psar/kama/obv 等 60+）",
)

registry.register(
    name="get_fundamental_ratios",
    toolset="data",
    schema={
        "description": "计算 CFA 级基本面比率：盈利能力(ROE/ROA/ROIC/毛利率/净利率/营业利润率)、DuPont 三因子五因子分解、流动性(流动/速动/现金比率)、偿债(资产负债率/D/E)、效率(资产/存货/应收周转)、现金流质量(OCF/NI、FCF)、估值倍数(PE/PB/PS)。跨 SEC/东财/新浪/腾讯自动取最近一期三表。当用户问公司财务健康、ROE 高低、财报质量时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "curr_date": {"type": "string", "description": "分析日期 yyyy-mm-dd，默认今天"},
            },
            "required": ["ticker"],
        },
    },
    handler=_get_fundamental_ratios,
    description="CFA 级基本面比率（DuPont/ROE/流动性/偿债/效率）",
)

registry.register(
    name="run_valuation",
    toolset="data",
    schema={
        "description": "运行估值模型（倍数法 + 可选每股指标/目标倍数）：输入股票代码与目标倍数或每股指标(eps/bvps/sps)，输出各模型内在价值估计与市价对比。工具不臆造每股指标——请先从 get_fundamentals / get_fundamental_ratios 或三表取得真实每股数据再传入。当用户问『值多少钱』『贵不贵』『合理估值』时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "curr_date": {"type": "string", "description": "分析日期 yyyy-mm-dd"},
                "eps": {"type": "number", "description": "每股收益（可选）"},
                "bvps": {"type": "number", "description": "每股净资产（可选）"},
                "sps": {"type": "number", "description": "每股营收（可选）"},
                "ebitda_per_share": {"type": "number", "description": "每股 EBITDA（可选）"},
                "net_debt_per_share": {"type": "number", "description": "每股净债务（可选）"},
                "pe_target": {"type": "number", "description": "目标 PE 倍数（可选）"},
                "pb_target": {"type": "number", "description": "目标 PB 倍数（可选）"},
                "ps_target": {"type": "number", "description": "目标 PS 倍数（可选）"},
                "ev_ebitda_target": {"type": "number", "description": "目标 EV/EBITDA 倍数（可选）"},
            },
            "required": ["ticker"],
        },
    },
    handler=_run_valuation,
    description="估值模型（倍数法/DCF 框架，内在价值 vs 市价）",
)

registry.register(
    name="get_balance_sheet",
    toolset="data",
    schema={
        "description": "资产负债表（最近 6 期，跨 SEC/东财/新浪/腾讯）",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "curr_date": {"type": "string", "description": "分析日期 yyyy-mm-dd"},
            },
            "required": ["ticker"],
        },
    },
    handler=_get_balance_sheet,
    description="资产负债表（三表之一）",
)

registry.register(
    name="get_income_statement",
    toolset="data",
    schema={
        "description": "利润表（最近 6 期，跨 SEC/东财/新浪/腾讯）",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "curr_date": {"type": "string", "description": "分析日期 yyyy-mm-dd"},
            },
            "required": ["ticker"],
        },
    },
    handler=_get_income_statement,
    description="利润表（三表之一）",
)

registry.register(
    name="get_cashflow",
    toolset="data",
    schema={
        "description": "现金流量表（最近 6 期，跨 SEC/东财/新浪/腾讯）",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "股票代码"},
                "curr_date": {"type": "string", "description": "分析日期 yyyy-mm-dd"},
            },
            "required": ["ticker"],
        },
    },
    handler=_get_cashflow,
    description="现金流量表（三表之一）",
)

# ---------------------------------------------------------------------------
# LangChain @tool 层（供 dromx/agents 分析图 bind_tools / .func 使用）
# 重构时这层一度丢失，导致 core/agent_utils 导入断裂 —— 勿再删除。
# ---------------------------------------------------------------------------
from .lc_tools import (  # noqa: E402
    fetch_reddit_tool,
    fetch_stocktwits_tool,
    fetch_x_posts_tool,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_global_news,
    get_income_statement,
    get_indicators,
    get_insider_transactions,
    get_macro_indicators,
    get_news,
    get_prediction_markets,
    get_stock_data,
    get_verified_market_snapshot,
)

__all__ = [
    "fetch_reddit_tool",
    "fetch_stocktwits_tool",
    "fetch_x_posts_tool",
    "get_balance_sheet",
    "get_cashflow",
    "get_fundamentals",
    "get_global_news",
    "get_income_statement",
    "get_indicators",
    "get_insider_transactions",
    "get_macro_indicators",
    "get_news",
    "get_prediction_markets",
    "get_stock_data",
    "get_verified_market_snapshot",
]
