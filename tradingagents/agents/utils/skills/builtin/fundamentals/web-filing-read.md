---
name: web-filing-read
description: When statements are thin or a specific filing needs full text, use web_read to pull SEC EDGAR / annual-report pages. Fundamentals-only.
version: 1.0.0
analyst: fundamentals
tags: [browser, web, filing, sec, annual-report]
regimes: [volatile, uptrend, downtrend, sideways]
instruments: [equity]
markets: [US, HK, KR, CN]
---

# Web Filing Read (fundamentals data-gap fill)

## When to Apply
The fetched statements (`get_fundamentals` / `get_income_statement` / ...) are thin or missing a line item, AND a filing URL is available (SEC EDGAR 10-K/10-Q/8-K, the company IR annual report, a prospectus). The data tools cover the standard statements; this reads a SPECIFIC filing's full text when they lack the detail. Fundamentals-only — the news analyst has its own `web-deep-dive` for article full text.

## Procedure
1. **Name the gap.** What specific line item / disclosure is missing? (segment revenue, off-balance-sheet, a footnote, a covenant, a risk factor). Don't browse randomly — have a question.
2. **Find the filing URL.** SEC EDGAR (sec.gov/cgi-bin/browse-edgar), the company IR page, or a URL you know. Tag `[knowledge]`.
3. **Read it.** Call `web_read(url)` to pull the filing's full text. Needs the browser enabled — if it returns "browser unavailable", say so and fall back to the fetched statements, don't fabricate.
4. **Extract only the line item.** Pull the number / disclosure that fills the gap + cite the filing URL + filing date. Don't dump the whole 10-K into the report.

## Pitfalls
- Filings are long — `web_read` returns the full page text; extract ONLY the gap, don't quote pages.
- The browser needs `enable_browser` + the agent-browser CLI; if unavailable, degrade to the fetched statements.
- A filing URL you "know" may be stale (wrong period) — verify the filing date in the text before quoting.

## Output
State: (1) the gap you filled, (2) the filing URL + date, (3) the extracted line item (cited), (4) "browser unavailable, used fetched statements" if it failed.
