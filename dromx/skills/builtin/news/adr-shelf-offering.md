---
name: adr-shelf-offering
description: Detect ADR / shelf registration / capital-raise / dilution events and assess per-share impact.
version: 1.0.0
analyst: news
tags: [adr, dilution, shelf, capital-raise]
regimes: [volatile, bearish, uptrend, downtrend, sideways]
instruments: [equity]
markets: [US, HK]
---

# ADR / Shelf Offering / Dilution Analysis

## When to Apply
A news item mentions an ADR, shelf registration, follow-on offering, convertible, or capital raise for the name. These re-rate the thesis via dilution even when the direction is unchanged — flag them as game-changers.

## Procedure
1. **Find the raise.** Scan `get_news(ticker, start, end)` for keywords: "shelf", "offering", "ADR", "follow-on", "convertible", "raise", "issue". Note the announced size + date.
2. **Quantify dilution.** Call `get_fundamentals(ticker, date)` for shares-outstanding. Dilution % ≈ new_shares / (existing + new_shares). If the raise size is in $ and the price is known, infer new_shares = raise_$ / price. State the dilution % explicitly.
3. **Insider alignment.** Call `get_insider_transactions(ticker, date)` — insiders selling into a raise = bearish signal; insiders participating in the raise = less bearish.
4. **Historical context.** Has this name raised before? Use `get_news` lookback to find prior raises and their 5-day price reaction. A name that dilutes repeatedly carries a structural short bias.
5. **Use of proceeds.** From the news text: debt repayment / acquisitions / general corporate = dilution without growth (bearish). Growth funding at accretive returns = less bearish.

## Pitfalls
- A filed shelf ≠ an imminent raise — a shelf is an option, not an event. Only flag as a game-changer when an actual offering is launched or strongly telegraphed.
- Dilution % is meaningless without price context — a 5% raise at a 52-week high is different from 5% at a 52-week low.
- Don't fabricate shares-outstanding if `get_fundamentals` returns no data — state "dilution unquantifiable" and flag qualitatively.

## Output
State: (1) dilution % (or "unquantifiable"), (2) use of proceeds, (3) insider alignment, (4) game-changer flag (yes/no) + why, (5) historical raise pattern if any.
