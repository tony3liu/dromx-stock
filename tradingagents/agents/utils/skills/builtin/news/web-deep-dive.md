---
name: web-deep-dive
description: When the fetched data is thin or a specific URL needs full text, use web_read to pull the page via the headless browser. Fill data gaps on demand.
version: 1.0.0
analyst: news
tags: [browser, web, deep-dive, fill-gap]
regimes: [volatile, bearish, uptrend, downtrend, sideways]
instruments: [equity, etf]
markets: [US, HK, KR, CN]
---

# Web Deep-Dive (fill data gaps)

## When to Apply
The fetched data is thin (a ~200-char news snippet, no filing detail, a missing data page) AND a URL is available — from the news block's `Link:` lines, an SEC EDGAR URL, the company's investor page, or a source you know. The other tools cover price / financials / news; this reads a SPECIFIC URL's full text when they don't. The data tools return "unavailable" for a reason; this is the on-demand fallback, not a replacement.

## Procedure
1. **Name the gap.** What specific fact is missing? (full article body, filing detail, a data page the tools don't cover). Don't browse randomly — have a question first.
2. **Find the URL.** From the news block's `Link:` lines (already fetched), an SEC EDGAR URL, the company investor page, or a known data source. Tag `[data]` (from the block) or `[knowledge]` (you know it).
3. **Read it.** Call `web_read(url)` to pull the full page text. Needs the browser enabled — if it returns "browser unavailable", say so and fall back to the snippet; do NOT fabricate the missing fact.
4. **Extract only the answer.** Pull the fact that fills the gap + cite the URL. Don't dump the whole page into the report.

## Pitfalls
- Don't browse speculatively — each `web_read` is slow (headless Chromium) and needs the browser. Have a specific question + URL first; one read per gap.
- The browser needs `enable_browser` + the agent-browser CLI; if unavailable, degrade to the snippet, don't invent.
- `web_read` reads a URL you give it — it does not search the web. If you don't have a URL, say "no URL available" and rely on the fetched data.

## Output
State: (1) the gap you filled, (2) the URL read, (3) the extracted fact (cited), (4) "browser unavailable, used snippet" if it failed.
