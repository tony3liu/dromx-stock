---
name: advanced-technicals
description: Apply advanced technical indicators (ichimoku/adx/vortex/psar/kama/mfi/obv/atr/keltner/donchian/ulcer 等 60+) to confirm trend structure and volume-price alignment beyond basic rsi/macd/ma.
version: 1.0.0
analyst: market
tags: [technical, trend, momentum, volume, volatility, ichimoku, adx, vwap]
regimes: [volatile, uptrend, downtrend, bearish, bullish]
instruments: [equity, etf]
markets: [US, HK, CN, KR, JP]
---

# Advanced Technicals

## When to Apply
The question is about trend structure, momentum strength, overbought/oversold, or volume-price alignment — and basic indicators (rsi/macd/sma) alone are not conclusive. Use for: "is the trend intact?", "is this a breakout or a bull trap?", "is volume confirming the move?", "is the stock overbought?"

## Procedure
1. **Fetch OHLCV first.** Call `get_stock_data(symbol, start, end)` for ~6 months (or use the verified snapshot's recent closes) so indicators have enough history to warm up.
2. **Compute the panel.** Call `get_advanced_indicators(symbol, "ichimoku,adx,vortex,psar,aroon,kama,mfi,obv,cmf,atr,keltner_channel,donchian_channel,ulcer_index,vwap", curr_date)`.
3. **Trend structure.** Ichimoku cloud (price vs senkou A/B) + ADX (trend strength, >25 = trending) + PSAR direction + Aroon (new highs/lows frequency).
4. **Momentum.** KAMA adaptive MA (price above/below), MFI (overbought >80 / oversold <20), StochRSI, ROC, PPO histogram sign.
5. **Volume-price.** OBV slope vs price (divergence = warning), CMF (>0 inflow / <0 outflow), VWAP (institutional reference line).
6. **Volatility context.** ATR as % of price (position sizing, stop placement), Keltner/Donchian channel position (breakout zones), Ulcer Index (drawdown persistence).

## Pitfalls
- Indicators computed on too-short history produce garbage — always fetch ≥120 trading days.
- Ichimoku senkou lines are shifted forward by 26 periods; read the CURRENT cloud value vs price, not the shifted historical line.
- ADX < 20-25 means "no trend" — do not force a trend read in a range.
- OBV/CMF diverge in late trends; a single day's divergence is noise, look for 3+ days.
- ATR as % of price above ~8% implies wide stops — reflect that in position sizing advice.

## Output
State plainly: (1) trend regime + strength (ADX), (2) momentum verdict, (3) volume-price alignment (bullish/bearish/neutral), (4) volatility level and its sizing implication, (5) confidence.
