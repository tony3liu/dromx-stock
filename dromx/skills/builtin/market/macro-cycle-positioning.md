---
name: macro-cycle-positioning
description: Position the analysis within the current macro cycle (reflation/overheat/stagflation/recession) using FRED growth + inflation, and map it to sector and asset-class tilts.
version: 1.0.0
analyst: [market, industry]
tags: [macro, cycle, sector-rotation, inflation, growth, rates]
regimes: []
instruments: [equity, etf]
markets: [US, HK, CN, KR, JP]
---

# Macro Cycle Positioning

## When to Apply
The question is about the macro environment ("which cycle phase are we in?", "is it a good time for growth vs value?", "what sectors should lead?"), or when a single-name analysis needs a macro overlay (e.g. a bank in a steepening-curve regime, a consumer name in a stagflation scare). Do NOT apply for pure micro/single-stock questions without a macro angle.

## Procedure
1. **Detect the phase.** Call `get_macro_cycle(curr_date)`. It reads FRED INDPRO/GDP (growth) and CPI (inflation) year-over-year, maps to one of four phases, and cross-checks with the 10Y-2Y curve and unemployment.
   - growth ↑ & inflation ↓ → **reflation** (cyclical growth, steep curve)
   - growth ↑ & inflation ↑ → **overheat** (commodities/value, rate pressure)
   - growth ↓ & inflation ↑ → **stagflation** (cash/gold, defensive)
   - growth ↓ & inflation ↓ → **recession** (bonds/gold, quality defensive)
2. **Note the confidence and evidence.** The tool returns confidence 0-1 plus evidence notes (curve inversion, unemployment). Low confidence (<0.5) or missing data → say the phase is uncertain, don't force it.
3. **Map to sectors.** Use the tool's sector lists as a starting frame, then ground them in the actual name: what is the analysed company's sector, its duration/leverage sensitivity, and how does the phase change its earnings trajectory and multiple?
4. **For single-name overlays.** State how the phase tilts the name: e.g. overheat → a bank benefits from steeper curve and higher rates; stagflation → a discretionary consumer name faces margin pressure.
5. **Time horizon.** A cycle phase is a 6-18 month tilt, not a daily signal — combine with the technicals snapshot for timing, don't trade the phase intraday.

## Pitfalls
- FRED data is US-centric; it sets the global risk-appetite direction, but A股/港股 sector mapping needs local context (policy, liquidity, foreign flow). Say so when applying to CN/HK names.
- CPI YoY can be distorted by base effects — cross-check the inflation trend direction, not just the level.
- The tool degrades gracefully when FRED is unavailable; if it returns MACRO_CYCLE_UNAVAILABLE, state that the macro overlay is missing rather than inventing a phase.
- Do not over-rotate: a single name's alpha is mostly idiosyncratic; the cycle is a tilt, not a verdict.

## Output
State: (1) detected phase + confidence, (2) the growth/inflation evidence behind it, (3) the sector/asset tilt implied, (4) how it applies to the analysed name(s), (5) caveats (data missing, US-centric, time horizon).
