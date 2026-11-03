---
name: intrinsic-valuation
description: Estimate intrinsic value with DCF (FCFF/FCFE), DDM (Gordon/two-stage/H-model), residual income and target-multiple methods; always report assumptions and sensitivity.
version: 1.0.0
analyst: fundamentals
tags: [fundamental, valuation, dcf, ddm, intrinsic-value, multiples]
regimes: []
instruments: [equity]
markets: [US, HK, CN]
---

# Intrinsic Valuation

## When to Apply
The question is "what is this stock worth?" — fair value, intrinsic value, over/under-valued, price target, or "is the current price justified?". Do NOT apply when the user only wants technical timing; valuation answers value, not timing.

## Procedure
1. **Gather inputs first.** Call `get_fundamental_ratios(ticker, curr_date)` for margins/ROE/leverage; call `get_fundamentals(ticker, curr_date)` for EPS/PE/market cap; pull statements via `get_income_statement` / `get_balance_sheet` / `get_cashflow` when you need exact line items (revenue, net income, equity, net debt, shares outstanding).
2. **Compute per-share inputs from REAL numbers.** Derive EPS = net income / shares outstanding; BVPS = equity / shares; SPS = revenue / shares. If shares outstanding is unknown, get it from the fundamentals snapshot or the balance sheet (issued shares) — do not guess.
3. **Multiples (quick read).** Call `run_valuation(ticker, eps=…, bvps=…, sps=…, pe_target=…, pb_target=…, ps_target=…)`. Use peer/historical multiples as the target — state where the target comes from.
4. **DCF (primary when cash flows are stable).** Base FCF = operating cash flow − capex (from the cash-flow statement). Growth: use consensus/analyst growth for the explicit period, a conservative terminal growth ≤ nominal GDP growth (2-3% US, ~3-4% CN). Discount rate: WACC ≈ 8-12% depending on beta/leverage; note your pick and why.
5. **DDM (when dividends are material).** Gordon for stable payers; two-stage for growers. Use payout ratio × ROE to sanity-check sustainable growth = ROE × retention.
6. **Residual income** as a cross-check when book value is meaningful (banks, insurers).
7. **Synthesize.** Range across methods; compare to market price. If price < low end → undervalued; > high end → overvalued; inside → fairly valued. State conviction.

## Pitfalls
- NEVER invent EPS/BVPS/shares — pull them from statements. A valuation with fabricated inputs is worse than no valuation.
- Terminal value dominates DCF (often 60-80% of EV) — state terminal growth and show the terminal-value share; high share = low confidence in the estimate.
- WACC and growth are assumptions, not facts. Always disclose them and do a simple sensitivity (e.g. ±1% growth / ±1% discount rate).
- The tool only computes what you pass it; empty results mean missing inputs, not "no value".
- Do not present a single point price target — always a range.

## Output
State: (1) per-share inputs used and their source, (2) each method's value estimate, (3) assumptions (WACC, growth, terminal, target multiples) and a sensitivity note, (4) the intrinsic-value range vs market price, (5) verdict (under/fair/over-valued) with confidence.
