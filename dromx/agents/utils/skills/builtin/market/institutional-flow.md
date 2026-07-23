---
name: institutional-flow
description: Read foreign/mainline money flow (chip-face) alongside price to spot accumulation vs distribution.
version: 1.0.0
analyst: market
tags: [flow, foreign, institutional, chip]
regimes: [volatile, bearish, uptrend, downtrend]
instruments: [equity, etf]
markets: [US, HK, KR]
---

# Institutional / Foreign Flow Analysis

## When to Apply
A foreign-flow (chip) block is present in your context (foreign-ownership % + daily net trading), or volume is anomalous and you need to distinguish accumulation/distribution from noise. Primary use: Korea (.KS) names where Naver gives foreign flow; elsewhere use price+volume as a proxy.

## Procedure
1. **Price vs flow sign.** From `get_stock_data`, identify the recent move direction. From the foreign-flow block, read the consecutive net-sell/buy days + cumulative net. Price up + foreign net-buy = accumulation (healthy). Price up + foreign net-sell = distribution (warn). Price down + foreign net-sell = real exit. Price down + foreign net-buy = absorption (potential reversal).
2. **Ownership % trajectory.** The snapshot foreign-ownership % + cumulative net over 20 days tells you if the level is shifting. A 1pp+ drop in foreign-ownership % over a month is institutional exit regardless of daily noise.
3. **Pattern-discovery block (if present).** Cross-check anomaly days (high-amplitude / z-score days) against the flow sign. An anomaly down-day + foreign net-sell = an institutional-driven move (high signal). Anomaly down-day + foreign flat = retail/options-driven (lower signal for a structural call).
4. **Volume confirmation.** `get_verified_market_snapshot` includes volume — a flow move without volume is suspect; a flow move on >1.5x average volume is meaningful.

## Pitfalls
- One day of foreign net-sell is noise — require a consecutive run (the block flags ≥5 days) before calling distribution.
- Foreign-flow data is Korea-only here; do NOT fabricate foreign-ownership % for US/HK/A-share names. State "flow data unavailable" and fall back to a price+volume proxy.
- Flow sometimes lags price (reported T+1) — do not treat today's flow as confirming today's move.

## Output
State: (1) accumulation / distribution / exit / absorption / unclear, (2) key evidence (consecutive days, cumulative net, ownership % delta, volume), (3) whether the pattern-discovery anomaly days align.
