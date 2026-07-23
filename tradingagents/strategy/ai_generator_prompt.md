# 策略开发指南 (TradingAgents 选股引擎)

本文档是 AI 生成选股策略代码的完整参考。每个策略是一个独立的 Python 文件，
只 `import polars as pl`，声明 `META` 元数据 + 一个 `filter(df, params) -> pl.Expr`
过滤函数。策略在**全市场当日快照 + 按需计算的技术指标**上运行（免费数据，无付费依赖）。

## 1. 文件结构模板

```python
"""策略简短描述"""
import polars as pl

META = {
    "id": "ai_myidea",                 # 英文ID, 唯一; AI 生成必须以 ai_ 开头
    "name": "策略中文名",               # 显示名称
    "description": "一句话说明策略逻辑",
    "markets": ["HK", "US", "CN"],     # 适用市场; 只写策略真正适用的
    "tags": ["标签1", "标签2"],

    # 基础过滤 (Stage 1, 引擎统一处理; 可选)
    "basic_filter": {
        "price_min": 1,                # 最低收盘价
        "price_max": None,             # 最高收盘价 (None = 不限)
        "amount_min": None,            # 最小成交额
        "turnover_min": None,          # 最小换手率 (小数, 0.03 = 3%)
        "market_cap_min": None,        # 最小总市值
    },

    # 策略参数 (只把用户可能调节的阈值放这里, 公式常数不必参数化)
    "params": [
        {"id": "rsi_max", "label": "RSI上限", "type": "float",
         "default": 30.0, "min": 10.0, "max": 50.0, "step": 1.0},
    ],

    # 评分权重 (排序用, 权重总和 = 1.0)
    "scoring": {"change_pct": 0.4, "vol_ratio_5d": 0.3, "momentum_5d": 0.3},

    "order_by": "score",
    "descending": True,
    "limit": 50,
}

ENTRY_SIGNALS = []                     # 买入信号列 (回测/监控用)
EXIT_SIGNALS = ["signal_ma20_breakdown"]
STOP_LOSS = -0.05                      # 止损 (负数)
MAX_HOLD_DAYS = 15                     # 最长持有天数

def filter(df: pl.DataFrame, params: dict) -> pl.Expr:
    """返回 Polars 布尔表达式 (用 & | 组合)。"""
    rsi_max = params.get("rsi_max", 30.0)
    return (
        (pl.col("rsi_14") < rsi_max)
        & (pl.col("close") > pl.col("open"))
    )
```

## 2. 单位约定（重要）

比率类字段一律为**小数**（0.05 表示 5%），**不是**百分数：
`change_pct`, `turnover_rate`, `momentum_5d/20d/60d`, `annual_vol_20d`, `amplitude`。
所以"涨幅大于 3%"写 `pl.col("change_pct") > 0.03`。

## 3. 可用列（数据适配器已计算，可直接引用）

### 快照 + 价格
| 列名 | 说明 |
|------|------|
| symbol | 代码 (如 00700.HK / AAPL / 600519.SS) |
| name | 名称 |
| open, high, low, close, volume | 当日 OHLCV |
| prev_close | 昨收 |
| change_pct | 涨跌幅 (小数) |
| amplitude | 振幅 (小数) |
| amount | 成交额 |
| turnover_rate | 换手率 (小数) |
| vol_ratio | 快照量比 |
| pe | 市盈率 |
| change_60d | 60日涨幅 (小数) |
| market_cap | 总市值 |

### 均线 / 技术指标
| 列名 | 说明 |
|------|------|
| ma5, ma10, ma20, ma60 | 简单移动均线 |
| rsi_14 | RSI 相对强弱 |
| macd_dif, macd_dea, macd_hist | MACD DIF / DEA / 柱 |
| boll, boll_upper, boll_lower | 布林带中/上/下轨 |
| atr_14 | 平均真实波幅 |

### 量能 / 动量 / 波动
| 列名 | 说明 |
|------|------|
| vol_ratio_5d | 5日量比 (volume / 5日均量) |
| momentum_5d, momentum_20d, momentum_60d | N日涨幅 (小数) |
| annual_vol_20d | 20日年化波动率 (小数) |
| high_60d, low_60d | 60日最高/最低价 |

## 4. 信号列（布尔值，必须用 `.fill_null(False)`）

| 列名 | 说明 |
|------|------|
| signal_ma_golden_5_20 / signal_ma_dead_5_20 | MA5 上穿 / 下穿 MA20 |
| signal_macd_golden / signal_macd_dead | MACD 金叉 / 死叉 |
| signal_ma20_breakout / signal_ma20_breakdown | 突破 / 跌破 MA20 |
| signal_n_day_high / signal_n_day_low | 60日新高 / 新低 |
| signal_boll_breakout_upper / signal_boll_breakdown_lower | 突破 / 跌破布林轨 |
| signal_volume_surge | 放量 (5日量比 ≥ 2) |

## 5. 不可用的数据

以下**不在** DataFrame 中，策略里**不能**引用：
- 财务数据 (PE 除外 / PB / ROE / 净利润 / 营收 / 资产负债)
- 概念 / 行业板块 / 资金流向 / 人气排名
- 盘中分时 / 五档盘口
- A股涨跌停列 (signal_limit_up / consecutive_limit_ups) — 仅 CN 市场且当前未接入，
  非 CN 策略绝不引用。

## 6. 规则（铁律）

1. `filter()` 必须返回 `pl.Expr`（用 `&` `|` 组合布尔表达式）。
2. 信号列必须用 `.fill_null(False)`。
3. 用户可能调节的阈值放 `params`；公式常数不必参数化。
4. `scoring` 权重总和 = 1.0，且键必须是上面列出的可用列。
5. **只 `import polars as pl`**，禁止 import 其他任何模块。
6. 禁止 `open()` / `exec()` / `eval()` / `os` / `sys` / `subprocess` / 文件系统访问。
7. 只生成**这一个** .py 文件，绝不多文件、绝不修改项目源码。
8. `markets` 只写策略真正适用的市场（涨跌停逻辑只能 CN）。
