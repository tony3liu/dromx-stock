---
name: forward-valuation
description: Frame valuation on forward earnings + cycle inflection, not trailing PE. Solves the "growth/cyclical looks expensive on trailing PE" trap.
version: 1.0.0
analyst: fundamentals
tags: [valuation, forward-pe, cycle, inflection]
regimes: [volatile, uptrend, downtrend, sideways]
instruments: [equity]
markets: [US, HK, KR, CN]
---

# Forward Valuation / Cycle Inflection

## When to Apply
The name is a growth/cyclical whose earnings are climbing (AI/semis/cycle upturn) or at a cyclical peak (memory/logic top). Trailing/annualized PE misleads: a growth name at 100× trailing may be 30× forward; a cyclical at 8× trailing may be 20× forward (earnings about to halve). Always frame on forward + cycle position, never trailing alone.

## Procedure
1. **Trailing vs forward earnings.** `get_fundamentals(ticker, date)` for latest EPS/PE. `get_income_statement(ticker, "quarterly", date)` for YoY/QoQ revenue + margin trajectory. If EPS is accelerating QoQ, forward PE (next-4Q consensus or your extrapolation) is materially below trailing — state both numbers.
2. **Cycle inflection.** Is the name at an inflection? Up (spot-price cycle up, capex/HBM ramp, AI demand pull) → forward earnings >> trailing, trailing PE OVERSTATES expensiveness. Down (cycle peak, earnings about to halve) → trailing PE UNDERSTATES expensiveness (value trap). Tag [data]/[knowledge].
3. **Implied growth.** From current PE + risk-free, infer the growth the market prices (P/E ≈ 1/(r−g), back-of-envelope). Compare to your forward estimate. The gap (your estimate vs market-implied) is the edge — not the absolute PE.
4. **Vs own history.** Where does the forward PE sit vs the name's historical range (`get_stock_data` ~2y for price, statements for EPS history)? Bottom-of-range + up-inflection = cheap; top + down-inflection = expensive.

## Pitfalls
- Forward EPS needs a consensus or your extrapolation — if you have neither, say "forward unquantifiable" + qualitative, don't fabricate.
- Cycle inflection is [knowledge]-heavy; corroborate with the industry/news blocks.
- A low trailing PE at cycle peak is the classic value trap — never conclude "cheap" on trailing alone for a cyclical.

## Output
State: (1) trailing PE + forward PE (or "unquantifiable"), (2) cycle inflection (up/down/none) + evidence, (3) market-implied growth vs your estimate (the gap), (4) forward PE vs historical range, (5) valuation verdict ON FORWARD (cheap/fair/expensive), not trailing.
