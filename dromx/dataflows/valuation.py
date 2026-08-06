"""Valuation models — 估值模型（DCF / DDM / 倍数法 / 剩余收益）

灵感来自 FinceptTerminal 的 equity_valuation 目录（FCFF/FCFE DCF、多阶段
DDM、倍数法、剩余收益），但全部按标准估值教材公式重新实现（AGPL 代码不
复制；公式本身为公开财务知识）。

模块定位：**纯计算层**。数据输入由调用方提供（三表、行情、假设），本模块
负责确定性计算，输出可解释的内在价值区间。适合挂载为 fundamentals skill
供分析师按场景选用。

覆盖模型：
1. FCFF DCF：两阶段（显式预测期 + 永续终值），Enterprise Value → Equity Value
2. FCFE DCF：直接到权益价值（股权自由现金流折现）
3. DDM：Gordon 单阶段 / 两阶段 / 三阶段（H 模型）
4. 倍数法：P/E、P/B、P/S、EV/EBITDA 目标倍数
5. 剩余收益：RI = EVA 折现，校验 ROE 与要求回报率的关系

依赖：无外部库（纯 Python 标准库 + typing）。
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _pv(amount: float, rate: float, period: int) -> float:
    """单期现值：amount / (1+rate)^period。rate<=-1 时返回 None 由调用方处理。"""
    if rate <= -1:
        raise ValueError("discount rate must be > -1")
    return amount / (1 + rate) ** period


def _gordon_terminal(fcf: float, growth: float, discount: float) -> float:
    """永续增长终值：fcf*(1+g)/(r-g)。r<=g 时无有限解，抛错提示。"""
    if discount <= growth:
        raise ValueError(f"terminal requires discount rate > growth (r={discount:.4f}, g={growth:.4f})")
    return fcf * (1 + growth) / (discount - growth)


@dataclass
class DCFInputs:
    """FCFF/FCFE 两阶段 DCF 输入。"""

    # 最近一期自由现金流（基准年）
    base_fcf: float
    # 显式预测期（年）
    years: int = 5
    # 预测期增长率（每阶段逐年或恒定）
    growth_rates: list[float] | None = None  # 长度 == years，None = 恒用 high_growth
    high_growth: float = 0.08
    # 永续期
    terminal_growth: float = 0.03
    discount_rate: float = 0.10  # WACC（FCFF）或要求回报率（FCFE）
    # FCFF → 权益价值
    net_debt: float = 0.0  # 净债务 = 总债务 - 现金（FCFF 用）
    shares_outstanding: float | None = None


@dataclass
class DCFResult:
    """两阶段 DCF 结果。"""

    pv_fcf: float = 0.0          # 显式预测期现值
    pv_terminal: float = 0.0     # 终值现值
    enterprise_value: float = 0.0
    equity_value: float = 0.0
    per_share: float | None = None
    terminal_growth: float = 0.0
    terminal_value_ratio: float = 0.0  # 终值占企业价值比例
    warnings: list[str] = field(default_factory=list)


def two_stage_dcf(inp: DCFInputs) -> DCFResult:
    """两阶段 DCF（FCFF 或 FCFE 通用）。

    FCF_t = base * prod(1+g_i)；终值 = Gordon；各期按 discount_rate 折现。
    """
    res = DCFResult()
    growths = inp.growth_rates if inp.growth_rates else [inp.high_growth] * inp.years
    if len(growths) != inp.years:
        raise ValueError(f"growth_rates length {len(growths)} != years {inp.years}")

    fcf = inp.base_fcf
    for t in range(1, inp.years + 1):
        fcf *= 1 + growths[t - 1]
        res.pv_fcf += _pv(fcf, inp.discount_rate, t)

    try:
        tv = _gordon_terminal(fcf, inp.terminal_growth, inp.discount_rate)
    except ValueError as exc:
        res.warnings.append(str(exc))
        res.enterprise_value = res.pv_fcf
        res.equity_value = res.pv_fcf - inp.net_debt
        res.per_share = res.equity_value / inp.shares_outstanding if inp.shares_outstanding else None
        return res

    res.pv_terminal = _pv(tv, inp.discount_rate, inp.years)
    res.enterprise_value = res.pv_fcf + res.pv_terminal
    res.equity_value = res.enterprise_value - inp.net_debt
    res.per_share = res.equity_value / inp.shares_outstanding if inp.shares_outstanding else None
    res.terminal_growth = inp.terminal_growth
    if res.enterprise_value > 0:
        res.terminal_value_ratio = res.pv_terminal / res.enterprise_value
    return res


# ---------------------------------------------------------------------------
# DDM
# ---------------------------------------------------------------------------


def gordon_ddm(dividend_per_share: float, growth: float, required_return: float) -> float | None:
    """Gordon 单阶段 DDM：P0 = D1 / (r - g)。"""
    try:
        return _gordon_terminal(dividend_per_share, growth, required_return)
    except ValueError:
        return None


def two_stage_ddm(
    d0: float,
    high_growth: float,
    high_years: int,
    terminal_growth: float,
    required_return: float,
) -> float | None:
    """两阶段 DDM：高速增长期 + 永续低速期。

    P0 = Σ D_t/(1+r)^t + D_{n+1}/((r-g2)(1+r)^n)
    """
    if required_return <= -1:
        return None
    price = 0.0
    d = d0
    for t in range(1, high_years + 1):
        d *= 1 + high_growth
        price += _pv(d, required_return, t)
    try:
        terminal = _gordon_terminal(d, terminal_growth, required_return)
    except ValueError:
        return None
    price += _pv(terminal, required_return, high_years)
    return price


def h_model_ddm(
    d0: float,
    current_growth: float,
    terminal_growth: float,
    h_years: int,          # 线性衰减期（年）
    required_return: float,
) -> float | None:
    """H 模型（三阶段线性衰减 DDM）。

    P0 = D0 * [(1+g2) + H*(g1-g2)] / (r - g2)，H = h_years/2。
    增长从 g1 线性衰减到 g2。
    """
    if required_return <= terminal_growth:
        return None
    h = h_years / 2
    numerator = d0 * ((1 + terminal_growth) + h * (current_growth - terminal_growth))
    return numerator / (required_return - terminal_growth)


# ---------------------------------------------------------------------------
# 倍数法
# ---------------------------------------------------------------------------


@dataclass
class MultipleValuationInputs:
    eps: float | None = None        # 每股收益
    bvps: float | None = None       # 每股净资产
    sps: float | None = None        # 每股营收
    ev_per_ebitda: float | None = None  # 企业价值/EBITDA
    ebitda_per_share: float | None = None
    net_debt_per_share: float | None = None

    pe_target: float | None = None
    pb_target: float | None = None
    ps_target: float | None = None
    ev_ebitda_target: float | None = None


def multiple_valuation(inp: MultipleValuationInputs) -> dict[str, float | None]:
    """目标倍数法：P = 指标 × 目标倍数。返回各方法估值与输入标记。"""
    out: dict[str, float | None] = {}
    if inp.eps is not None and inp.pe_target is not None:
        out["P/E"] = inp.eps * inp.pe_target
    if inp.bvps is not None and inp.pb_target is not None:
        out["P/B"] = inp.bvps * inp.pb_target
    if inp.sps is not None and inp.ps_target is not None:
        out["P/S"] = inp.sps * inp.ps_target
    if (
        inp.ev_per_ebitda is not None
        and inp.ebitda_per_share is not None
        and inp.net_debt_per_share is not None
    ):
        out["EV/EBITDA"] = inp.ev_per_ebitda * inp.ebitda_per_share - inp.net_debt_per_share
    return out


# ---------------------------------------------------------------------------
# 剩余收益
# ---------------------------------------------------------------------------


def residual_income_valuation(
    book_value_per_share: float,
    roe: float,                 # 预测期 ROE（小数）
    required_return: float,     # r
    terminal_growth: float = 0.0,
    years: int = 5,
    roe_terminal: float | None = None,  # 永续 ROE（默认收敛到 r）
) -> float | None:
    """剩余收益模型（单阶段简化 + 显式预测期）。

    RI_t = (ROE_t - r) * B_{t-1}；B_t = B_{t-1} * (1 + g)，g 由再投资率隐含。
    简化假设 g = (1 - payout) * ROE，这里用固定 g=terminal_growth 作近似。
    """
    if required_return <= -1:
        return None
    roe_term = roe_terminal if roe_terminal is not None else required_return

    price = book_value_per_share
    b = book_value_per_share
    for t in range(1, years + 1):
        # 预测期用给定 ROE，增长 = terminal_growth（近似：留存收益再投资）
        b_prev = b
        ri = (roe - required_return) * b_prev
        price += _pv(ri, required_return, t)
        b = b_prev * (1 + terminal_growth)

    # 终值：永续 RI = (roe_term - r) * B_n / (r - g)
    if required_return > terminal_growth:
        ri_terminal = (roe_term - required_return) * b
        pv_terminal = _pv(ri_terminal / (required_return - terminal_growth), required_return, years)
        price += pv_terminal
    return price


# ---------------------------------------------------------------------------
# 便捷入口：从比率数据构建估值文本
# ---------------------------------------------------------------------------


def valuation_summary(
    price: float,
    per_share: dict[str, float | None],
    multiple_results: dict[str, float | None],
    dcf_result: DCFResult | None = None,
    ddm_value: float | None = None,
) -> str:
    """把各模型结果整理成人类可读的估值汇总文本。"""
    lines: list[str] = ["# Valuation Summary", ""]
    lines.append(f"当前价格: {price:.2f}")

    if dcf_result is not None:
        lines.append("")
        lines.append("## DCF (两阶段)")
        lines.append(f"- 预测期 FCF 现值: {dcf_result.pv_fcf:,.2f}")
        lines.append(f"- 终值现值: {dcf_result.pv_terminal:,.2f}")
        lines.append(f"- 企业价值: {dcf_result.enterprise_value:,.2f}")
        lines.append(f"- 权益价值: {dcf_result.equity_value:,.2f}")
        lines.append(f"- 每股价值: {dcf_result.per_share:.2f}" if dcf_result.per_share is not None else "- 每股价值: N/A")
        lines.append(f"- 终值占比: {dcf_result.terminal_value_ratio * 100:.0f}%")
        for w in dcf_result.warnings:
            lines.append(f"- 警告: {w}")

    if ddm_value is not None:
        lines.append("")
        lines.append(f"## DDM: {ddm_value:.2f}")

    if multiple_results:
        lines.append("")
        lines.append("## 倍数法")
        for name, v in multiple_results.items():
            lines.append(f"- {name}: {v:.2f}" if v is not None else f"- {name}: N/A")

    # 与市价对比的结论
    estimates = [v for v in list(multiple_results.values()) + ([dcf_result.per_share] if dcf_result else []) + ([ddm_value] if ddm_value else []) if v is not None]
    if estimates:
        lo, hi = min(estimates), max(estimates)
        if price < lo:
            verdict = "市场价低于全部模型估计（或被低估）"
        elif price > hi:
            verdict = "市场价高于全部模型估计（或被高估）"
        else:
            verdict = "市场价落在模型估计区间内"
        lines.append("")
        lines.append(f"## 结论: {verdict}（模型区间 {lo:.2f} ~ {hi:.2f}）")

    lines.append("")
    lines.append("# NOTE: 估值为模型输出，依赖输入假设（增长率/折现率/目标倍数）。")
    lines.append("# 假设不同结果差异巨大；请同时披露假设与敏感性。")
    return "\n".join(lines)
