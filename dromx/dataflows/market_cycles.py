"""Macro cycle phase detection — 经济周期相位判断（增长 × 通胀 双轴）

借鉴 FinceptTerminal 的 BusinessCycleAnalyzer 思路（expansion / peak /
contraction / trough 四相位打分），但实现完全独立：数据从 FRED 实时拉取，
而不是要求调用方手动填指标。核心是美林投资时钟式的双轴判断：

    增长(Industrial Production / GDP) 与 通胀(CPI) 的同比趋势
    → 四象限 → 每相位的资产与行业配置含义

数据（全部来自 FRED，key 走现有 ``FRED_API_KEY`` 配置）：
- 增长代理：INDPRO（月度工业产出，比季度 GDP 及时）为主，GDPC1 辅助
- 通胀代理：CPIAUCSL（CPI，月度）
- 辅助确认：T10Y2Y（10Y-2Y 利差，衰退预警）、UNRATE（失业率）

输出：结构化相位判断 + 证据 + 行业配置建议，供 market / industry 分析师
挂载使用（也注册为 assistant 工具）。任何序列拉取失败都降级：缺增长或缺
通胀则返回"数据不足"判定，绝不臆测。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

# FRED 序列与代理说明
_GROWTH_SERIES = "INDPRO"        # 工业产出指数（月度）
_GROWTH_BACKUP = "GDPC1"         # 实际 GDP（季度）
_INFLATION_SERIES = "CPIAUCSL"   # CPI（月度）
_CONFIRM_SERIES = {
    "curve": "T10Y2Y",           # 10Y-2Y 利差
    "unemployment": "UNRATE",     # 失业率
}

# 判断阈值（同比 %）
_GROWTH_UP = 1.0     # 增长同比 > 1% 视为扩张
_INFLATION_UP = 3.0  # 通胀同比 > 3% 视为高通胀（用核心趋势）

_PHASE_META = {
    "reflation": {   # 复苏：增长↑ 通胀↓
        "label": "复苏 (Reflation)",
        "cn": "复苏",
        "regime": "增长回升、通胀回落 —— 经济修复初期",
        "assets": "权益偏周期成长；债券可持有；商品谨慎",
        "sectors_favor": ["消费成长", "科技", "工业", "可选消费"],
        "sectors_avoid": ["公用事业", "必需消费"],
        "equity_strategy": "加仓周期成长，银行与利率敏感板块受益于收益率曲线陡峭化",
        "risk": "中高 —— 权益风险偏好回升",
    },
    "overheat": {    # 过热：增长↑ 通胀↑
        "label": "过热 (Overheat)",
        "cn": "过热",
        "regime": "增长高位、通胀上行 —— 政策收紧风险升温",
        "assets": "商品与能源占优；权益偏资源/价值；债券承压（利率上行）",
        "sectors_favor": ["能源", "材料", "工业", "银行"],
        "sectors_avoid": ["长久期成长", "高估值消费"],
        "equity_strategy": "转向价值与上游资源，降低成长股久期暴露",
        "risk": "高 —— 央行加息与估值压缩风险",
    },
    "stagflation": {  # 滞胀：增长↓ 通胀↑
        "label": "滞胀 (Stagflation)",
        "cn": "滞胀",
        "regime": "增长停滞、通胀高企 —— 最不利组合，政策两难",
        "assets": "现金与黄金占优；债券与股票均承压",
        "sectors_favor": ["能源", "黄金/贵金属", "必需消费"],
        "sectors_avoid": ["金融（利率上升 + 信用风险）", "高杠杆成长"],
        "equity_strategy": "防御 + 抗通胀资产（能源/黄金/现金），降低总仓位",
        "risk": "极高 —— 股债双杀风险",
    },
    "recession": {   # 衰退：增长↓ 通胀↓
        "label": "衰退 (Recession)",
        "cn": "衰退",
        "regime": "增长收缩、通胀回落 —— 央行转向宽松",
        "assets": "利率债与黄金占优；权益防御",
        "sectors_favor": ["公用事业", "医疗", "必需消费"],
        "sectors_avoid": ["周期工业", "材料", "可选消费"],
        "equity_strategy": "防御型股票 + 长久期债券；为复苏埋伏周期反转",
        "risk": "低 —— 资本保全优先",
    },
}


def _fetch_fred_series(series_id: str, curr_date: str, look_back_days: int = 1100) -> pd.Series | None:
    """拉取一条 FRED 序列为带日期索引的 Series（失败返回 None，调用方降级）。

    直接走 fred 模块的 ``_request``，避免走 get_macro_data 的 markdown 格式化。
    """
    try:
        from .fred import _request
        end_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = (end_dt - timedelta(days=look_back_days)).strftime("%Y-%m-%d")
        obs = _request(
            "series/observations",
            {
                "series_id": series_id,
                "observation_start": start_date,
                "observation_end": curr_date,
                "sort_order": "asc",
            },
        ).get("observations", [])
        points = [
            (o["date"], o["value"])
            for o in obs
            if o.get("value") not in (".", None, "")
        ]
        if not points:
            return None
        s = pd.Series(
            [float(v) for _, v in points],
            index=pd.to_datetime([d for d, _ in points]),
        )
        return s.sort_index()
    except Exception as exc:  # noqa: BLE001 — 宏观数据尽力而为，失败降级
        logger.warning("market_cycles: fetch %s failed: %s", series_id, exc)
        return None


def _yoy(series: pd.Series | None, months: int = 12) -> float | None:
    """序列同比变化率（%）。取最新值与 12 个月前比较，返回百分比。"""
    if series is None or len(series) < 2:
        return None
    try:
        latest = float(series.iloc[-1])
        past = series.asof(series.index[-1] - pd.DateOffset(months=months))
        if pd.isna(past) or past == 0:
            return None
        return (latest / past - 1.0) * 100.0
    except Exception:  # noqa: BLE001
        return None


def _trend(series: pd.Series | None, window: int = 6) -> str | None:
    """近 window 期趋势：'rising' / 'falling' / 'flat'（线性斜率，带相对容差）。"""
    if series is None or len(series) < 3:
        return None
    recent = series.iloc[-window:].astype(float)
    x = list(range(len(recent)))
    y = recent.tolist()
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    denom = sum((x[i] - mean_x) ** 2 for i in range(n)) or 1.0
    slope = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / denom
    # 相对容差：斜率绝对值小于序列量级的 0.5% 视为 flat
    scale = max(abs(min(y)), abs(max(y)), 1e-12)
    rel = abs(slope) / scale
    if rel > 0.005:
        return "rising" if slope > 0 else "falling"
    return "flat"


def detect_cycle_phase(curr_date: str) -> dict:
    """检测当前经济周期相位。

    Args:
        curr_date: 分析日期 yyyy-mm-dd（FRED 不会返回晚于该日的数据）。

    Returns:
        dict: phase / confidence / evidence / sector_advice / raw_indicators。
        数据不足时 phase 为 None 并给出原因。
    """
    growth = _fetch_fred_series(_GROWTH_SERIES, curr_date)
    gdp = _fetch_fred_series(_GROWTH_BACKUP, curr_date)
    inflation = _fetch_fred_series(_INFLATION_SERIES, curr_date)

    growth_yoy = _yoy(growth)
    gdp_yoy = _yoy(gdp)
    infl_yoy = _yoy(inflation)
    infl_trend = _trend(inflation)

    # 增长判定：工业产出为主，GDP 为辅（GDP 更平滑，用于交叉验证）
    growth_up = growth_yoy is not None and growth_yoy > _GROWTH_UP
    if growth_yoy is None and gdp_yoy is not None:
        growth_up = gdp_yoy > _GROWTH_UP

    # 通胀判定：同比 > 阈值；趋势向上作为同方向确认（仅当已接近阈值时）
    infl_up = infl_yoy is not None and infl_yoy > _INFLATION_UP
    if infl_trend == "rising" and infl_yoy is not None and 2.5 < infl_yoy <= _INFLATION_UP:
        infl_up = True

    if growth_yoy is None and gdp_yoy is None:
        return {
            "phase": None,
            "phase_cn": "数据不足",
            "confidence": 0.0,
            "reason": "无法取得增长数据（INDPRO / GDPC1 均失败）。",
            "raw_indicators": {},
        }
    if infl_yoy is None:
        return {
            "phase": None,
            "phase_cn": "数据不足",
            "confidence": 0.0,
            "reason": "无法取得通胀数据（CPIAUCSL 失败）。",
            "raw_indicators": {},
        }

    # 四象限映射
    if growth_up and not infl_up:
        phase = "reflation"
    elif growth_up and infl_up:
        phase = "overheat"
    elif not growth_up and infl_up:
        phase = "stagflation"
    else:
        phase = "recession"

    # 辅助确认：收益率曲线倒挂 + 增长下滑 → 衰退置信度上升
    curve = _fetch_fred_series(_CONFIRM_SERIES["curve"], curr_date)
    curve_val = float(curve.iloc[-1]) if (curve is not None and len(curve) and not pd.isna(curve.iloc[-1])) else None
    unemp = _fetch_fred_series(_CONFIRM_SERIES["unemployment"], curr_date)
    unemp_val = float(unemp.iloc[-1]) if (unemp is not None and len(unemp) and not pd.isna(unemp.iloc[-1])) else None

    confidence = 0.6
    notes: list[str] = []
    if curve_val is not None:
        if curve_val < 0 and phase in ("recession", "stagflation"):
            confidence = min(0.9, confidence + 0.2)
            notes.append(f"收益率曲线倒挂（10Y-2Y = {curve_val:.2f}%）与收缩相位一致")
        elif curve_val >= 0 and phase in ("reflation", "overheat"):
            confidence = min(0.9, confidence + 0.1)
            notes.append(f"收益率曲线陡峭（10Y-2Y = {curve_val:.2f}%）支持扩张相位")
        else:
            notes.append(f"收益率曲线 10Y-2Y = {curve_val:.2f}%（与相位存在张力）")
    if unemp_val is not None:
        if phase == "recession" and unemp_val > 5.0:
            confidence = min(0.9, confidence + 0.1)
            notes.append(f"失业率 {unemp_val:.1f}% 偏高，支持衰退判断")
        elif phase in ("reflation", "overheat") and unemp_val < 4.5:
            confidence = min(0.9, confidence + 0.1)
            notes.append(f"失业率 {unemp_val:.1f}% 低位，支持扩张判断")

    meta = _PHASE_META[phase]

    raw = {
        "industrial_production_yoy_pct": round(growth_yoy, 2) if growth_yoy is not None else None,
        "gdp_yoy_pct": round(gdp_yoy, 2) if gdp_yoy is not None else None,
        "cpi_yoy_pct": round(infl_yoy, 2) if infl_yoy is not None else None,
        "inflation_trend": infl_trend,
        "growth_up": bool(growth_up),
        "inflation_up": bool(infl_up),
        "curve_10y2y": round(curve_val, 2) if curve_val is not None else None,
        "unemployment_pct": round(unemp_val, 2) if unemp_val is not None else None,
    }

    return {
        "phase": phase,
        "phase_cn": meta["cn"],
        "phase_label": meta["label"],
        "confidence": round(confidence, 2),
        "regime": meta["regime"],
        "assets": meta["assets"],
        "sectors_favor": meta["sectors_favor"],
        "sectors_avoid": meta["sectors_avoid"],
        "equity_strategy": meta["equity_strategy"],
        "risk": meta["risk"],
        "evidence_notes": notes,
        "raw_indicators": raw,
    }


def build_cycle_report(curr_date: str) -> str:
    """把相位检测格式化为分析师可读的报告文本。"""
    r = detect_cycle_phase(curr_date)
    if r.get("phase") is None:
        return (
            f"MACRO_CYCLE_UNAVAILABLE: 经济周期判断无法完成"
            f"（{r.get('reason', '数据不足')}）。报告数据不可用，不要臆测相位。"
        )

    raw = r["raw_indicators"]
    lines = [
        f"# 经济周期相位: {r['phase_cn']} ({r['phase']}) — 置信度 {r['confidence']:.0%}",
        "",
        f"- 判断: {r['regime']}",
        f"- 资产配置: {r['assets']}",
        f"- 权益策略: {r['equity_strategy']}",
        f"- 风险水平: {r['risk']}",
        f"- 利好的行业: {', '.join(r['sectors_favor'])}",
        f"- 回避的行业: {', '.join(r['sectors_avoid'])}",
        "",
        "## 证据（FRED 同比）",
        f"- 工业产出同比: {raw['industrial_production_yoy_pct'] if raw['industrial_production_yoy_pct'] is not None else 'N/A'}%"
        f"（GDP 同比: {raw['gdp_yoy_pct'] if raw['gdp_yoy_pct'] is not None else 'N/A'}%）",
        f"- CPI 同比: {raw['cpi_yoy_pct'] if raw['cpi_yoy_pct'] is not None else 'N/A'}%（趋势: {raw['inflation_trend'] or 'N/A'}）",
        f"- 10Y-2Y 利差: {raw['curve_10y2y'] if raw['curve_10y2y'] is not None else 'N/A'}",
        f"- 失业率: {raw['unemployment_pct'] if raw['unemployment_pct'] is not None else 'N/A'}%",
    ]
    if r["evidence_notes"]:
        lines.append("")
        lines.append("## 交叉验证")
        lines.extend(f"- {n}" for n in r["evidence_notes"])
    lines.append("")
    lines.append("# NOTE: 周期判断基于美国 FRED 数据（INDPRO/CPI/利差/失业率），")
    lines.append("# 用于判断全球风险偏好方向；A股/港股的具体行业映射请结合本地市场数据。")
    return "\n".join(lines)
