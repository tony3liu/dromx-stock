"""Sector tools — 板块数据工具

不依赖外部板块 API（akshare / eastmoney 在当前网络环境不可用），
改用「板块成分股映射 + 现有 get_stock_data 数据工具」计算板块表现：

- SECTOR_MAP: 板块名 → 代表性成分股列表（A 股为主，含部分港股/美股）
- get_sector_quote: 获取板块成分股近期行情，计算板块整体表现
- get_capital_flow: 资金流数据暂无可用数据源，返回明确说明
- get_sector_news: 聚合板块代表个股的新闻
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta

import pandas as pd

from dromx.dataflows.interface import route_to_vendor
from dromx.tools.registry import registry, tool_error, tool_result

logger = logging.getLogger(__name__)


# 板块 → 代表性成分股（每板块 8 只以内，控制数据请求量）
# A 股用纯代码（如 603986）或带后缀（600519.SS）均可，由数据层归一化
SECTOR_MAP: dict[str, dict] = {
    "存储": {
        "aliases": ["存储芯片", "内存", "存储器", "DRAM", "NAND"],
        "tickers": ["603986", "000021", "300223", "002049", "688766", "301308", "688008", "300302"],
    },
    "半导体": {
        "aliases": ["芯片", "集成电路", "IC"],
        "tickers": ["688981", "002371", "603501", "300782", "688012", "600584", "688041", "002156"],
    },
    "AI算力": {
        "aliases": ["算力", "人工智能", "AI", "服务器"],
        "tickers": ["000977", "603019", "002230", "300308", "688256", "300502", "000938", "601138"],
    },
    "新能源": {
        "aliases": ["锂电", "电池", "新能源车"],
        "tickers": ["300750", "002594", "300014", "002460", "603799", "300207", "002812", "688006"],
    },
    "光伏": {
        "aliases": ["太阳能"],
        "tickers": ["601012", "300274", "002129", "600438", "688599", "300118", "002459", "600732"],
    },
    "白酒": {
        "aliases": ["食品饮料", "酒类"],
        "tickers": ["600519", "000858", "600809", "000568", "002304", "600779", "603369", "600702"],
    },
    "医药": {
        "aliases": ["生物医药", "医疗"],
        "tickers": ["600276", "300760", "603259", "000661", "300122", "600196", "002821", "300347"],
    },
    "银行": {
        "aliases": [],
        "tickers": ["601398", "601288", "600036", "601988", "601166", "600000", "601328", "600016"],
    },
    "券商": {
        "aliases": ["证券"],
        "tickers": ["600030", "300059", "601688", "600837", "601211", "000776", "600999", "601066"],
    },
    "军工": {
        "aliases": ["国防军工", "航空航天"],
        "tickers": ["600760", "002179", "600893", "000768", "002013", "600862", "300699", "600967"],
    },
    "消费电子": {
        "aliases": ["苹果链", "电子"],
        "tickers": ["002475", "300433", "002241", "601138", "002600", "300115", "603986", "002938"],
    },
    "汽车": {
        "aliases": ["整车", "汽车零部件"],
        "tickers": ["601633", "000625", "600104", "002594", "601238", "000800", "600741", "603596"],
    },
    "有色": {
        "aliases": ["有色金属", "黄金", "稀土"],
        "tickers": ["601899", "600547", "600111", "000630", "600489", "603993", "000975", "002460"],
    },
    "地产": {
        "aliases": ["房地产"],
        "tickers": ["000002", "600048", "001979", "600383", "000069", "601155", "600606", "000961"],
    },
    "煤炭": {
        "aliases": [],
        "tickers": ["601088", "600188", "601225", "600985", "000983", "601699", "600348", "600123"],
    },
    "中概互联网": {
        "aliases": ["互联网", "港股科技"],
        "tickers": ["0700.HK", "9988.HK", "9618.HK", "3690.HK", "9888.HK", "1024.HK", "9999.HK", "2015.HK"],
    },
    "美股科技": {
        "aliases": ["纳指科技", "FAANG"],
        "tickers": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO"],
    },
}


def _find_sector(name: str) -> tuple[str | None, dict | None]:
    """按板块名或别名查找板块配置"""
    name = (name or "").strip()
    if not name:
        return None, None
    for sector, cfg in SECTOR_MAP.items():
        if name == sector or name in cfg["aliases"]:
            return sector, cfg
    # 模糊包含匹配（如 "存储板块" → "存储"）
    for sector, cfg in SECTOR_MAP.items():
        if sector in name or any(a in name for a in cfg["aliases"]):
            return sector, cfg
    return None, None


def _list_sectors(args: dict) -> str:
    """列出支持的板块"""
    sectors = [
        {"name": s, "aliases": cfg["aliases"], "constituents": cfg["tickers"]}
        for s, cfg in SECTOR_MAP.items()
    ]
    return tool_result({"sectors": sectors, "count": len(sectors)})


def _parse_close_series(csv_text: str) -> pd.Series | None:
    """从 CSV 字符串中解析 Close 序列（带日期索引）"""
    try:
        df = pd.read_csv(io.StringIO(csv_text), comment="#")
    except Exception:
        return None
    if "Close" not in df.columns or df.empty:
        return None
    closes = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if closes.empty:
        return None
    return closes


def _fetch_change(symbol: str, days: int) -> dict | None:
    """获取单只股票近 days 天表现；失败返回 None"""
    end = datetime.now()
    start = end - timedelta(days=int(days * 1.6) + 10)  # 预留非交易日余量
    try:
        csv_text = route_to_vendor(
            "get_stock_data", symbol,
            start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
        )
    except Exception as e:
        logger.warning("sector quote: fetch %s failed: %s", symbol, e)
        return None
    closes = _parse_close_series(csv_text)
    if closes is None or len(closes) < 2:
        return None
    latest = float(closes.iloc[-1])
    prev = float(closes.iloc[-2])
    base = float(closes.iloc[max(0, len(closes) - 1 - days)])
    return {
        "symbol": symbol,
        "latest_close": round(latest, 2),
        "daily_change_pct": round((latest / prev - 1) * 100, 2) if prev else None,
        "period_change_pct": round((latest / base - 1) * 100, 2) if base else None,
        "bars": int(len(closes)),
    }


def _get_sector_quote(args: dict) -> str:
    """获取板块行情：成分股表现 + 板块汇总"""
    sector_name = args.get("sector", "")
    days = int(args.get("days", 20))
    days = max(1, min(days, 120))

    sector, cfg = _find_sector(sector_name)
    if not cfg:
        available = "、".join(SECTOR_MAP.keys())
        return tool_error(
            f"未识别的板块: {sector_name!r}。支持的板块: {available}",
            hint="可先调用 list_sectors 查看全部板块",
        )

    results = []
    for ticker in cfg["tickers"]:
        item = _fetch_change(ticker, days)
        if item:
            results.append(item)

    if not results:
        return tool_error(f"板块 {sector} 的成分股数据全部获取失败，请稍后重试")

    period_changes = [r["period_change_pct"] for r in results if r["period_change_pct"] is not None]
    daily_changes = [r["daily_change_pct"] for r in results if r["daily_change_pct"] is not None]
    up = sum(1 for c in daily_changes if c > 0)
    down = sum(1 for c in daily_changes if c < 0)

    summary = {
        "sector": sector,
        "days": days,
        "sample_size": len(results),
        "avg_period_change_pct": round(sum(period_changes) / len(period_changes), 2) if period_changes else None,
        "avg_daily_change_pct": round(sum(daily_changes) / len(daily_changes), 2) if daily_changes else None,
        "up_count": up,
        "down_count": down,
        "breadth_pct": round(up / len(daily_changes) * 100, 1) if daily_changes else None,
    }
    ranked = sorted(results, key=lambda r: r["period_change_pct"] or 0, reverse=True)
    return tool_result({
        "summary": summary,
        "top_gainers": ranked[:3],
        "top_losers": ranked[-3:],
        "constituents": results,
    })


def _get_capital_flow(args: dict) -> str:
    """板块资金流（暂无可用数据源）"""
    sector_name = args.get("sector", "")
    sector, _ = _find_sector(sector_name)
    return tool_error(
        "资金流数据暂不可用：当前环境无法访问东财/akshare 资金流 API。",
        sector=sector or sector_name,
        hint="可改用 get_sector_quote 观察板块涨跌与宽度，间接判断资金动向",
    )


def _get_sector_news(args: dict) -> str:
    """聚合板块代表个股新闻"""
    sector_name = args.get("sector", "")
    days = int(args.get("days", 7))
    days = max(1, min(days, 30))
    per_stock = int(args.get("per_stock", 3))

    sector, cfg = _find_sector(sector_name)
    if not cfg:
        available = "、".join(SECTOR_MAP.keys())
        return tool_error(
            f"未识别的板块: {sector_name!r}。支持的板块: {available}",
            hint="可先调用 list_sectors 查看全部板块",
        )

    end = datetime.now()
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    # 只取前 3 只代表股，控制请求量
    sample = cfg["tickers"][:3]
    all_news: dict[str, str] = {}
    failures: list[str] = []
    for ticker in sample:
        try:
            text = route_to_vendor("get_news", ticker, start_str, end_str)
            if text:
                lines = [ln for ln in str(text).splitlines() if ln.strip()]
                all_news[ticker] = "\n".join(lines[:per_stock])
        except Exception as e:
            logger.warning("sector news: %s failed: %s", ticker, e)
            failures.append(ticker)

    if not all_news:
        return tool_error(f"板块 {sector} 的新闻全部获取失败", failures=failures)

    return tool_result({
        "sector": sector,
        "days": days,
        "sampled_tickers": sample,
        "news_by_ticker": all_news,
        "failures": failures,
    })


# 注册工具
registry.register(
    name="list_sectors",
    toolset="sector",
    schema={
        "description": "列出当前支持的所有板块及其成分股",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=_list_sectors,
    description="列出当前支持的所有板块（存储/半导体/AI算力/新能源/白酒/医药等）",
)

registry.register(
    name="get_sector_quote",
    toolset="sector",
    schema={
        "description": "获取板块行情：成分股近期涨跌幅、板块整体表现、涨跌宽度，可用于判断板块是否见底/见顶",
        "parameters": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "板块名称，如 存储、半导体、AI算力、新能源"},
                "days": {"type": "integer", "description": "回看交易日数，默认 20，最大 120"},
            },
            "required": ["sector"],
        },
    },
    handler=_get_sector_quote,
    description="获取板块行情与涨跌宽度（判断板块强弱的工具）",
)

registry.register(
    name="get_capital_flow",
    toolset="sector",
    schema={
        "description": "获取板块资金流向（当前环境数据源不可用，会返回明确说明）",
        "parameters": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "板块名称"},
            },
            "required": ["sector"],
        },
    },
    handler=_get_capital_flow,
    description="获取板块资金流向（暂不可用）",
)

registry.register(
    name="get_sector_news",
    toolset="sector",
    schema={
        "description": "获取板块近期新闻（聚合板块代表个股的新闻）",
        "parameters": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "板块名称"},
                "days": {"type": "integer", "description": "回看天数，默认 7，最大 30"},
                "per_stock": {"type": "integer", "description": "每只股票最多取几条，默认 3"},
            },
            "required": ["sector"],
        },
    },
    handler=_get_sector_news,
    description="获取板块近期新闻",
)
