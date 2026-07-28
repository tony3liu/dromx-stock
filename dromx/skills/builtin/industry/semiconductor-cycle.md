---
name: semiconductor-cycle
description: Place a semi name in its memory/logic/device sub-cycle — spot, ASP, inventory, capex phases.
version: 1.0.0
analyst: [industry, market]
tags: [semiconductor, cycle, memory, dram, nand]
regimes: [volatile, uptrend, downtrend]
instruments: [equity, leveraged_etf, etf]
markets: [US, HK, KR, TW]
---

# Semiconductor Cycle Analysis

## When to Apply
The name is a semiconductor company (memory DRAM/NAND, logic/foundry, equipment, design) or an ETF tracking semis. Semis are deeply cyclical — the cycle phase (shortage / oversupply, inventory build / deplete, capex up / down) dominates the price; company-level analysis is secondary to cycle placement.

## Procedure
1. **Sub-sector classification.** Memory (DRAM/NAND spot-driven), logic/foundry (utilization + node), equipment (book-to-bill leading), design (product cycle). State which — they lead/lag differently.
2. **Cycle phase from news.** `get_news(ticker, start, end)` + `get_global_news(date, 7, 10)` for spot-price / inventory / capex keywords. Spot rising + low inventory + capex just-starting = upcycle early. Spot falling + high inventory + capex peaking = downcycle.
3. **Underlying / peer corroboration.** For a leveraged semi ETF, the overnight-transmission block + peer snapshots (`peer_tickers`) confirm the cycle read across the cohort — a single name moving alone is company-specific, the cohort moving together is cycle.
4. **Historical cycle anchor.** From `get_stock_data(ticker, start, end)` (≥2 years), place the current price vs prior cycle peaks/troughs. A memory name at 0.7x prior-peak sales in a downcycle is a different call from 1.5x in an upcycle.
5. **Foreign flow (Korea/TW semis).** For .KS/.TW semis, the foreign-flow block = foreign money is the dominant holder; foreign accumulation in a downcycle = a bottoming signal.

## Pitfalls
- Treating a spot-price spike as a new cycle — can be a supply shock, not demand.
- Ignoring capex lag: capex decisions land as supply 1.5-2 years later; price often peaks before supply arrives.
- Applying DCF to a cyclical semi without normalising through the cycle — peak earnings at peak multiple = double-counted.

## Output
State: (1) sub-sector, (2) cycle phase (upcycle early / mid / late / downcycle / bottoming), (3) evidence (spot, inventory, capex, peer corroboration), (4) cycle-normalised valuation read, (5) direction + confidence.
