---
name: fundamental-ratios
description: Evaluate financial health via CFA-grade ratios — profitability (ROE/ROA/ROIC/margins), DuPont decomposition, liquidity, solvency, efficiency, cash-flow quality.
version: 1.0.0
analyst: fundamentals
tags: [fundamental, ratios, dupont, roe, balance-sheet, income-statement, cashflow]
regimes: []
instruments: [equity]
markets: [US, HK, CN]
---

# Fundamental Ratios

## When to Apply
The question is about a company's financial health, quality of earnings, leverage, or why ROE is what it is. Also use before valuation: ratios give the raw inputs (margins, asset turnover, leverage) that drive DCF/DDM assumptions.

## Procedure
1. **Pull the ratio panel.** Call `get_fundamental_ratios(ticker, curr_date)`. It fetches the last reported income statement, balance sheet, and cash flow across SEC/Eastmoney/Sina/Tencent (auto-routed per market) and computes the full panel.
2. **Profitability.** ROE vs ROA vs ROIC. ROE = net margin × asset turnover × equity multiplier (DuPont). A high ROE driven by leverage (high multiplier) is weaker than one driven by margin.
3. **DuPont 5-factor.** Tax burden × interest burden × operating margin × turnover × multiplier — tells you WHICH lever moves ROE.
4. **Liquidity.** Current/quick/cash ratios. Quick ratio < 1 with falling cash = short-term stress.
5. **Solvency.** Debt-to-assets, D/E. Cross-check with interest coverage if available.
6. **Efficiency.** Asset/inventory/receivables turnover — declining turnover with rising margin = pricing power vs volume issue.
7. **Cash-flow quality.** OCF/NI < 1 = earnings not converting to cash (red flag). FCF = OCF - capex; persistent negative FCF on a growth story needs explanation.
8. **Valuation cross-check (optional).** PE/PB/PS from the panel + price, versus peers/history.

## Pitfalls
- Ratios come from the LAST REPORTED period — always state the report date; don't present quarterly ratios as annualized without noting it.
- Chinese vendors report line items in CNY and in Chinese; the tool normalizes aliases but currency is per-statement — do not mix currencies.
- One quarter of negative ROE can be seasonality (e.g. Q1 retailers). Compare year-over-year, not just the latest quarter.
- OCF/NI > 1.5 for years can indicate aggressive accrual reversal or one-offs — check the cash-flow statement directly when extreme.
- If the tool returns NO_FUNDAMENTAL_DATA or N/A fields, say so plainly; never fabricate numbers.

## Output
State: (1) profitability level and the DuPont story (which lever drives ROE), (2) liquidity/solvency verdict, (3) efficiency trend, (4) earnings-quality verdict, (5) any red flags, (6) confidence.
