---
name: next-session-catalyst
description: Read next-session direction from pre-market proxies (futures/ADR/sector overnight) + scheduled catalysts — the lead signal for "tonight/tomorrow up/down".
version: 1.0.0
analyst: news
tags: [catalyst, next-session, pre-market, overnight, lead-signal]
regimes: [volatile, bearish, uptrend, downtrend]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Next-Session Catalyst

## When to Apply
The call needs the NEXT-session direction (tonight/tomorrow), not just backward news flow. Pre-market proxies (index futures, ADR premium, same-sector overnight, scheduled catalysts) are the lead signal. The news block is backward by default; this skill forces a forward 1-2 session look.

## Procedure
1. **Scheduled catalysts.** From `get_news(ticker, start, end)` + `get_global_news(date, 7, 10)`: any scheduled catalyst in the next 1-2 sessions (earnings, ex-div, FOMC, data print, product launch, regulatory deadline)? Name it + date + the binary (beat/miss, cut/no-cut).
2. **Pre-market proxies (daily-close proxy — precise pre-market isn't in this build, say so).**
   - Index futures: `get_stock_data("^NDX"/"^GSPC"/"^HSI", ...)` most-recent session return as the overnight risk-on/off proxy.
   - ADR / cross-market: US name with Asian listing → Asian listing's latest session leads; HK/KR name → US futures lead. State the proxy.
   - Same-sector overnight: cohort's latest returns (see the sector-overnight-flow skill).
3. **Direction read.** Synthesize: scheduled catalyst + proxy sign + sector overnight. Positive + catalyst → next-session up probable; negative + no catalyst → down; mixed → unclear.
4. **Horizon discipline.** This is a 1-2 session tactical read. Do NOT extend it to the medium-term thesis (set by fundamentals/regime). State the horizon explicitly and keep it separate.

## Pitfalls
- Daily-close proxies are NOT precise pre-market/after-hours prints — say so, don't claim a pre-market level you don't have.
- A scheduled catalyst can cut both ways (earnings beat vs miss) — give the binary, don't predict the outcome.
- Next-session signal can conflict with the medium-term thesis; that's normal (tactical vs structural) — state both, don't force them to agree.

## Output
State: (1) scheduled catalysts in next 1-2 sessions + expected direction, (2) pre-market proxies (futures/ADR/sector overnight) + their sign, (3) next-session direction read + confidence, (4) horizon explicitly 1-2 sessions, kept distinct from the medium-term thesis.
