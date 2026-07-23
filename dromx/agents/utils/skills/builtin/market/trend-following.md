---
name: trend-following
description: Read the MA stack + slopes + cross structure for the trend regime — the baseline technical framework.
version: 1.0.0
analyst: market
tags: [technical, trend, moving-average, breakout]
regimes: [uptrend, downtrend, sideways]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Trend-Following Framework

## When to Apply
The baseline technical read for any name: price vs the MA stack (10 EMA / 50 SMA / 200 SMA), slopes, cross structure. This is the default lens; oversold-bounce / volatility-regime skills layer on top when the regime calls for it.

## Procedure
1. **MA stack.** `get_verified_market_snapshot(ticker, date, 30)` gives 10 EMA / 50 SMA / 200 SMA + RSI + MACD + ATR + Bollinger. Place price vs each: above all = uptrend; below 10EMA but above 50SMA = pullback in uptrend; below 50SMA but above 200SMA = correction; below all = downtrend.
2. **Slopes.** `get_stock_data(ticker, start, end)` ~60 days. Are 10EMA/50SMA/200SMA rising or falling? Rising 50SMA + price above = healthy uptrend; falling 50SMA + price below = downtrend. Slope > level.
3. **Cross structure.** Golden cross (50SMA > 200SMA, rising) = structural bull; death cross (50SMA < 200SMA, falling) = structural bear. Recent cross = transition; old = entrenched.
4. **Break vs false break.** A close beyond a key MA (50/200) is a break; 2+ closes confirm. A single wick + reclaim = false break (liquidity grab). `get_indicators` for volume: high-volume break = real, low-volume = suspect.
5. **Trend vs mean-reversion call.** Clean trend (MA stack aligned + slopes) → follow the trend, don't fade. Sideways/choppy (MA stack tangled + flat slopes) → mean-revert the edges. State which the structure implies.

## Pitfalls
- MA crosses lag — they confirm a trend change after it happens, don't predict. Lead with slope + price-vs-stack, cross is confirmation.
- In high-volatility regimes the MA stack whipsaws — switch to the volatility-regime skill (ATR-based, wider stops) rather than forcing tight MA levels.
- A break below 50SMA in an uptrend is a pullback, not a reversal — check 200SMA + slope before calling a reversal.

## Output
State: (1) price vs MA stack, (2) slopes, (3) cross structure + age, (4) break vs false-break at key MAs, (5) trend vs mean-reversion regime call + direction.
