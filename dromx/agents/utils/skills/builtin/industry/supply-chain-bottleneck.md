---
name: supply-chain-bottleneck
description: Identify supply-chain choke points and who captures the scarcity rent.
version: 1.0.0
analyst: industry
tags: [supply-chain, bottleneck, scarcity]
regimes: [volatile, uptrend, downtrend]
instruments: [equity, etf]
markets: [US, HK, KR, TW]
---

# Supply-Chain Bottleneck Analysis

## When to Apply
A component/material is constrained (HBM, substrates, advanced packaging, litho tools, specialty chemicals). The question: who in the chain captures the scarcity rent, and is your ticker upstream (beneficiary) or downstream (margin-squeezed)?

## Procedure
1. **Name the bottleneck.** From `get_news(ticker, start, end)` + `get_global_news`, identify the constrained item + the cause (capacity, geo, tech, qualification).
2. **Map the chain around the bottleneck.** Upstream (the constrained supplier) → midstream (integrators) → downstream (the buyer facing higher input costs). Tag each from news or `[knowledge]`.
3. **Where is the rent captured?** The constrained upstream captures price uplift (margin expansion); downstream buyers eat it (margin compression). Use `get_fundamentals(ticker, date)` for the gross-margin trend — expanding GM = your ticker is upstream of the bottleneck; compressing GM = downstream.
4. **Duration.** Is the bottleneck structural (2-3yr qualification cycles: HBM, advanced nodes) or transient (a fire, a shipping lane)? Structural = multi-quarter thesis; transient = trade, not thesis.
5. **Substitution / relief.** From news: any alternative supplier ramping, any demand-destruction from high prices? A bottleneck relieved in 2 quarters is a fade signal for the upstream beneficiary.

## Pitfalls
- Treating "supply tight" as automatically bullish for your ticker — only if your ticker is the constrained supplier, not the buyer.
- Ignoring demand elasticity: extreme scarcity often kills end-demand, capping the cycle.
- Over-stating duration — most bottlenecks resolve faster than the bull case assumes.

## Output
State: (1) the bottleneck + cause, (2) your ticker's chain position, (3) where the rent is captured (upstream / downstream), (4) structural vs transient, (5) margin evidence, (6) direction + confidence.
