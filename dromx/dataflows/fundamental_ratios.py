"""Fundamental ratio analysis — 基本面比率分析（CFA 级，跨 vendor 解析）

背景：DromX 的三表数据流（get_income_statement / get_balance_sheet /
get_cashflow）已覆盖 SEC(英文) / yfinance(英文) / 东财(中文) / 新浪(中文)，
但返回的是原始 CSV 文本，分析师 LLM 只能逐行读。本模块把三表解析成结构化
数字，直接计算 CFA 级财务比率：

- 盈利能力：ROE / ROA / ROIC / 毛利率 / 净利率 / 营业利润率
- 流动性：流动比率 / 速动比率 / 现金比率
- 偿债：资产负债率 / 权益乘数 / D/E
- 效率：总资产周转率 / 存货周转率 / 应收账款周转率
- DuPont 三因子与五因子分解（解释 ROE 的来源）
- 现金流质量：OCF/NI、自由现金流

设计要点：
- 输入三表 CSV 文本（含 ``#`` 注释头，行名在 index，列为报告期）
- 行名别名表同时覆盖英文（US-GAAP tag / yfinance 变体）与中文（东财/新浪）
- 取「最晚一期且不晚于 curr_date」的数据，与现有三表流的 look-ahead 保护一致
- 全部为纯计算，无外部依赖（仅 pandas）
"""

from __future__ import annotations

import io
import logging

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 行名别名表：{逻辑字段: [英文别名..., 中文别名...]}，按优先级排列
# ---------------------------------------------------------------------------

_ALIASES: dict[str, list[str]] = {
    "revenue": [
        "Total Revenue", "Revenue", "Revenues", "TotalRevenues", "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "营业总收入", "营业收入", "营业总收入(元)",
    ],
    "cost_of_revenue": [
        "Cost of Revenue", "CostOfRevenue", "CostOfGoodsAndServicesSold",
        "营业成本", "营业总成本",
    ],
    "gross_profit": [
        "Gross Profit", "GrossProfit", "毛利", "营业毛利",
    ],
    "operating_income": [
        "Operating Income", "OperatingIncomeLoss", "OperatingIncome", "EBIT",
        "营业利润",
    ],
    "net_income": [
        "Net Income", "NetIncomeLoss", "NetIncome", "NetIncomeCommonStockholders",
        "净利润", "归属于母公司股东的净利润", "净利润(元)",
    ],
    "interest_expense": [
        "Interest Expense", "InterestExpense", "InterestExpenseNonOperating",
        "财务费用",
    ],
    "depreciation": [
        "Depreciation & Amort.", "DepreciationAmortizationAndAccretionNet",
        "DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
        "Depreciation & Amortization", "折旧与摊销", "固定资产折旧",
    ],
    "total_assets": [
        "Total Assets", "Assets", "TotalAssets", "资产总计", "资产总计(元)",
    ],
    "total_liabilities": [
        "Total Liabilities", "Liabilities", "TotalLiabilities",
        "负债合计", "负债合计(元)",
    ],
    "equity": [
        "Stockholders Equity", "StockholdersEquity", "TotalEquityGrossMinorityInterest",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "股东权益合计", "所有者权益合计", "归属于母公司股东权益合计",
        "所有者权益(或股东权益)合计", "股东权益(或所有者权益)合计",
    ],
    "current_assets": [
        "Current Assets", "AssetsCurrent", "流动资产合计",
    ],
    "current_liabilities": [
        "Current Liabilities", "LiabilitiesCurrent", "流动负债合计",
    ],
    "cash": [
        "Cash & Equivalents", "CashAndCashEquivalentsAtCarryingValue",
        "Cash", "CashAndCashEquivalents", "货币资金",
    ],
    "inventory": [
        "Inventory", "InventoryNet", "存货",
    ],
    "receivables": [
        "Receivables", "AccountsReceivable", "AccountsReceivableNet",
        "应收账款", "应收账款(元)",
    ],
    "operating_cashflow": [
        "Operating Cash Flow", "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        "经营活动产生的现金流量净额",
    ],
    "capex": [
        "CapEx", "PaymentsToAcquirePropertyPlantAndEquipment",
        "Capital Expenditure", "购建固定资产无形资产和其他长期资产支付的现金",
        "购建固定资产、无形资产和其他长期资产所支付的现金", "购建固定资产、无形资产和其他长期资产支付的现金",
    ],
}

# 别名表反转：行名(小写) → 逻辑字段
_ROW_TO_FIELD: dict[str, str] = {}
for _field, _names in _ALIASES.items():
    for _n in _names:
        _ROW_TO_FIELD[_n.strip().lower()] = _field


# ---------------------------------------------------------------------------
# CSV 解析
# ---------------------------------------------------------------------------


def parse_statement_csv(text: str) -> pd.DataFrame:
    """解析三表 CSV 文本为 DataFrame（index=行名, 列=报告期）。

    处理：跳过 ``#`` 注释头；第一列 index 名可能为 ``Unnamed: 0``。
    """
    if not text or not text.strip():
        return pd.DataFrame()
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO("\n".join(lines)), index_col=0)
    df.columns = [str(c) for c in df.columns]
    return df.apply(pd.to_numeric, errors="coerce")


def _get(df: pd.DataFrame, field: str) -> float | None:
    """按逻辑字段名取最新一期数值（跨中英文行名）。

    vendor 列序并不统一（yfinance/东财/新浪最新在前，SEC 按报告期排序），
    因此按列名解析日期取最大日期列；解析失败的列（如 TTM/年度列）保持
    原顺序排在日期列之后（不反转），避免把 TTM 误当最新季度。
    同一字段多行命中的取第一行（别名优先级）。"""
    if df.empty:
        return None

    cols = list(df.columns)
    parsed = [pd.to_datetime(str(c), errors="coerce") for c in cols]
    # 可解析日期的列按日期降序；非日期列保持原顺序（排在日期列之后）
    dated_idx = [i for i, p in enumerate(parsed) if not pd.isna(p)]
    undated_idx = [i for i, p in enumerate(parsed) if pd.isna(p)]
    dated_sorted = sorted(dated_idx, key=lambda i: parsed[i], reverse=True)
    col_order = dated_sorted + undated_idx

    for row_name in df.index:
        key = str(row_name).strip().lower()
        if _ROW_TO_FIELD.get(key) != field:
            continue
        row = df.loc[row_name] if row_name not in df.index.duplicated() else df.loc[[row_name]].iloc[0]
        for col_idx in col_order:
            v = row.iloc[col_idx]
            if pd.notna(v):
                return float(v)
    return None


# ---------------------------------------------------------------------------
# 比率计算（纯函数）
# ---------------------------------------------------------------------------


def _div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def compute_ratios(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame | None = None,
    price: float | None = None,
    shares_outstanding: float | None = None,
) -> dict[str, object]:
    """从三表 DataFrame 计算全套财务比率。

    Args:
        income / balance: 利润表 / 资产负债表（index=行名, 列=报告期）。
        cashflow: 现金流量表（可选，用于现金流质量）。
        price: 当前价格（可选，用于 PE/PB/PS）。
        shares_outstanding: 总股本（可选，用于每股指标）。

    Returns:
        {字段: 值} 字典。比率输出为小数（0.15 = 15%），缺失为 None。
    """
    rev = _get(income, "revenue")
    cost = _get(income, "cost_of_revenue")
    gp = _get(income, "gross_profit")
    oi = _get(income, "operating_income")
    ni = _get(income, "net_income")
    iexp = _get(income, "interest_expense")

    assets = _get(balance, "total_assets")
    liab = _get(balance, "total_liabilities")
    eq = _get(balance, "equity")
    ca = _get(balance, "current_assets")
    cl = _get(balance, "current_liabilities")
    cash = _get(balance, "cash")
    inv = _get(balance, "inventory")
    recv = _get(balance, "receivables")

    ocf = _get(cashflow, "operating_cashflow") if cashflow is not None else None
    capex = _get(cashflow, "capex") if cashflow is not None else None

    # 毛利率：优先毛利行，缺失时营收-营业成本推导（任一缺失则 None，不崩溃）
    gross = _div(gp, rev) if gp is not None else (_div((rev - cost), rev) if (rev is not None and cost is not None) else None)

    # 利润率
    net_margin = _div(ni, rev)
    op_margin = _div(oi, rev)

    # ROE / ROA / ROIC（ROIC 用 NOPAT=营业利润 简化，分母=总资产-现金）
    roe = _div(ni, eq)
    roa = _div(ni, assets)
    nopat = oi  # 简化：未做税调整，注释说明
    roic = _div(nopat, assets - cash if (assets is not None and cash is not None) else assets)

    # 资产周转与杠杆
    asset_turnover = _div(rev, assets)
    equity_multiplier = _div(assets, eq)

    # DuPont 五因子：税负负担=NI/EBT, 利息负担=EBT/EBIT(=oi), 营业利润率=EBIT/Rev
    # 利息费用方向不统一（多数记正，部分记负），取绝对值后加回净利得 EBT 近似
    ebt = (ni + abs(iexp)) if (ni is not None and iexp is not None) else None
    tax_burden = _div(ni, ebt)
    interest_burden = _div(ebt, oi)

    # 流动性
    current_ratio = _div(ca, cl)
    quick_assets = (ca - inv) if (ca is not None and inv is not None) else None
    quick_ratio = _div(quick_assets, cl)
    cash_ratio = _div(cash, cl)

    # 偿债
    debt_to_assets = _div(liab, assets)
    debt_to_equity = _div(liab, eq)

    # 效率
    inv_turnover = _div(cost if cost is not None else rev, inv)
    recv_turnover = _div(rev, recv)

    # 现金流
    fcf = (ocf - capex) if (ocf is not None and capex is not None) else None
    earnings_quality = _div(ocf, ni)

    # 估值倍数（需价格/股本）
    market_cap = (price * shares_outstanding) if (price is not None and shares_outstanding) else None
    pe = _div(price, _div(ni, shares_outstanding)) if shares_outstanding else None
    pb = _div(market_cap, eq)
    ps = _div(market_cap, rev)

    return {
        "revenue": rev,
        "net_income": ni,
        # 盈利
        "gross_margin": gross,
        "net_margin": net_margin,
        "op_margin": op_margin,
        "roe": roe,
        "roa": roa,
        "roic": roic,
        # DuPont
        "dupont": {
            "net_margin": net_margin,
            "op_margin": op_margin,
            "asset_turnover": asset_turnover,
            "equity_multiplier": equity_multiplier,
            "tax_burden": tax_burden,
            "interest_burden": interest_burden,
        },
        # 流动性
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "cash_ratio": cash_ratio,
        # 偿债
        "debt_to_assets": debt_to_assets,
        "debt_to_equity": debt_to_equity,
        # 效率
        "asset_turnover": asset_turnover,
        "inventory_turnover": inv_turnover,
        "receivables_turnover": recv_turnover,
        # 现金流
        "operating_cashflow": ocf,
        "capex": capex,
        "free_cashflow": fcf,
        "earnings_quality": earnings_quality,
        # 估值
        "pe": pe,
        "pb": pb,
        "ps": ps,
    }


# ---------------------------------------------------------------------------
# 顶层入口：拉取三表 → 计算 → 格式化文本
# ---------------------------------------------------------------------------


def _parse_statement_text(text: str, label: str) -> pd.DataFrame:
    """容错解析：vendor 可能返回异常文本（"Error retrieving..."）。"""
    if not text or text.strip().startswith("Error"):
        logger.warning("fundamental_ratios: %s unavailable (%r)", label, (text or "")[:80])
        return pd.DataFrame()
    return parse_statement_csv(text)


def _parse_shares(text: str):
    """解析快照文本中的总股本，支持千分位与 K/M/B 后缀。

    匹配 ``Total Shares ... <值>``；值形如 1,234,567,890 / 1234.5M / 1.23B。
    解析失败返回 None（调用方降级）。"""
    import re as _re
    m = _re.search(r"Total Shares[^\d]*([\d.,]+\s*[KMB]?)", text, _re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).replace(",", "").strip().upper()
    mult = 1.0
    if raw.endswith("K"):
        mult, raw = 1e3, raw[:-1]
    elif raw.endswith("M"):
        mult, raw = 1e6, raw[:-1]
    elif raw.endswith("B"):
        mult, raw = 1e9, raw[:-1]
    try:
        return float(raw) * mult
    except ValueError:
        return None


def build_fundamental_ratios(ticker: str, curr_date: str) -> str:
    """拉取三表并输出格式化比率报告（供 assistant / 分析师调用）。

    Args:
        ticker: 股票代码（A股/港股/美股均可，由 vendor 链自动路由）。
        curr_date: 当前分析日期 YYYY-MM-DD（防止未来数据）。
    """
    from .interface import route_to_vendor

    income = _parse_statement_text(
        route_to_vendor("get_income_statement", ticker, "quarterly", curr_date), "income"
    )
    balance = _parse_statement_text(
        route_to_vendor("get_balance_sheet", ticker, "quarterly", curr_date), "balance"
    )
    cashflow = _parse_statement_text(
        route_to_vendor("get_cashflow", ticker, "quarterly", curr_date), "cashflow"
    )

    if income.empty and balance.empty:
        return (
            f"NO_FUNDAMENTAL_DATA: no income statement or balance sheet for '{ticker}' "
            f"on/before {curr_date} from any configured vendor. Report that the data is "
            f"unavailable rather than estimating values."
        )

    # 尝试自动补市价与总股本（估值倍数用）：快照给股本，行情给价格。
    # 失败则倍数为 N/A，不阻断比率报告。
    price = None
    shares = None
    try:
        snap = route_to_vendor("get_fundamentals", ticker, curr_date)
        shares = _parse_shares(str(snap))
    except Exception as _exc:  # noqa: BLE001 — 估值增强失败不阻断
        logger.warning("fundamental_ratios: share count unavailable for %s: %s", ticker, _exc)
    if shares:
        try:
            from .stockstats_utils import load_ohlcv
            ohlcv = load_ohlcv(ticker, curr_date or str(__import__("datetime").date.today()))
            if ohlcv is not None and not ohlcv.empty and "Close" in ohlcv.columns:
                price = float(ohlcv["Close"].iloc[-1])
        except Exception as _exc:  # noqa: BLE001 — 市价失败不阻断
            logger.warning("fundamental_ratios: price unavailable for %s: %s", ticker, _exc)

    ratios = compute_ratios(income, balance, cashflow, price=price, shares_outstanding=shares)

    def _fmt(v, suffix: str = "", nd: int = 2) -> str:
        return f"{v:.{nd}f}{suffix}" if v is not None else "N/A"

    def _pct_fmt(v) -> str:
        return _fmt(v * 100, "%", 2) if v is not None else "N/A"

    dupont = ratios.get("dupont", {})

    lines: list[str] = []
    lines.append(f"# Fundamental Ratios for {ticker} (as of {curr_date})")
    lines.append("")
    lines.append("## 盈利能力")
    lines.append(f"- 毛利率: {_pct_fmt(ratios['gross_margin'])}")
    lines.append(f"- 净利率: {_pct_fmt(ratios['net_margin'])}")
    lines.append(f"- 营业利润率: {_pct_fmt(ratios['op_margin'])}")
    lines.append(f"- ROE: {_pct_fmt(ratios['roe'])}")
    lines.append(f"- ROA: {_pct_fmt(ratios['roa'])}")
    lines.append(f"- ROIC: {_pct_fmt(ratios['roic'])}")
    lines.append("")
    lines.append("## DuPont 分解（解释 ROE 来源）")
    lines.append(f"- 三因子: 净利率 {_pct_fmt(dupont.get('net_margin'))} × 总资产周转率 {_fmt(dupont.get('asset_turnover'), nd=3)} × 权益乘数 {_fmt(dupont.get('equity_multiplier'), nd=2)}")
    lines.append(f"- 五因子补充: 税负负担 {_fmt(dupont.get('tax_burden'), nd=2)} · 利息负担 {_fmt(dupont.get('interest_burden'), nd=2)} · 营业利润率 {_pct_fmt(dupont.get('op_margin'))}")
    lines.append("")
    lines.append("## 流动性")
    lines.append(f"- 流动比率: {_fmt(ratios['current_ratio'])}")
    lines.append(f"- 速动比率: {_fmt(ratios['quick_ratio'])}")
    lines.append(f"- 现金比率: {_fmt(ratios['cash_ratio'])}")
    lines.append("")
    lines.append("## 偿债")
    lines.append(f"- 资产负债率: {_pct_fmt(ratios['debt_to_assets'])}")
    lines.append(f"- D/E: {_fmt(ratios['debt_to_equity'])}")
    lines.append("")
    lines.append("## 效率")
    lines.append(f"- 总资产周转率: {_fmt(ratios['asset_turnover'], nd=3)}")
    lines.append(f"- 存货周转率: {_fmt(ratios['inventory_turnover'], nd=2)}")
    lines.append(f"- 应收账款周转率: {_fmt(ratios['receivables_turnover'], nd=2)}")
    lines.append("")
    lines.append("## 现金流")
    lines.append(f"- 经营现金流: {_fmt(ratios['operating_cashflow'])}")
    lines.append(f"- 资本开支: {_fmt(ratios['capex'])}")
    lines.append(f"- 自由现金流: {_fmt(ratios['free_cashflow'])}")
    lines.append(f"- 盈利质量(OCF/NI): {_fmt(ratios['earnings_quality'])}")
    lines.append("")
    lines.append("## 估值倍数")
    lines.append(f"- PE: {_fmt(ratios['pe'])}")
    lines.append(f"- PB: {_fmt(ratios['pb'])}")
    lines.append(f"- PS: {_fmt(ratios['ps'])}")
    lines.append("")
    lines.append("# NOTE: 数值取最近一期已披露财报（不晚于分析日期），货币单位为财报披露币种。")
    lines.append("# 'N/A' = 该期数据缺失或除数为零。ROIC 以营业利润近似 NOPAT，未做税调整。")
    lines.append("# 请勿臆测填补 N/A；对缺失项说明原因即可。")
    return "\n".join(lines)
