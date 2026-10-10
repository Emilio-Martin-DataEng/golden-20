# Golden 20: Claude Opus 5.5 on wwi_raw, 2026-10-09

Claude.ai chat (Opus 5.5, Pro plan) with the Google Cloud BigQuery connector, dataset `wwi_raw` only. The questions were asked verbatim, with no definitions. About 9 minutes, about 30 read-only queries.

## What Claude found in our demo data

- 2025 starts on 11 May 2025, so every "2025" answer covers a partial year.
- Every customer is a "Novelty Shop", so Q10 is trivial.
- The bill-to on invoices disagrees with the bill-to in the customer master for many invoices. This is probably from the customer seeding in `prep_wwi_bq.py`, which sets bill-to = customer on the invoices it assigns.
- All 84 unpaid invoices are dated 9 Oct 2026, which is a side effect of re-anchoring the dates.
- 200,959 of payments on 11 May 2025 are for invoices dated before the data starts.

## Scorecard

**Score: 20 / 20**

| # | Question | Answer | Golden | Match |
|---|---|---|---|---|
| Q01 | What was revenue in September 2026? | 4,745,125.35 | 4745125.35 | yes |
| Q02 | What was revenue in 2025? | 35,140,904.05 | 35140904.05 | yes |
| Q03 | What was gross profit in September 2026? | 2,315,663.90 | 2315663.9 | yes |
| Q04 | What was our gross margin in 2025? | 49.91% | 49.91 | yes |
| Q05 | How many invoices did we issue in September 2026? | 1,842 | 1842 | yes |
| Q06 | What was the average invoice value in September 2026? | 2,576.07 | 2576.07 | yes |
| Q07 | How many units did we sell in September 2026? | 258,716 | 258716 | yes |
| Q08 | Which product earned the most revenue in 2025? | Air cushion machine (Blue) \| 2,210,436.00 | Air cushion machine (Blue) \| 2210436 | yes |
| Q09 | Which buying group brought in the most revenue in 2025? | Tailspin Toys \| 17,422,095.90 | Tailspin Toys \| 17422095.9 | yes |
| Q10 | Which customer category brought in the most revenue in 2025? | Novelty Shop \| 34,570,905.85 | Novelty Shop \| 34570905.85 | yes |
| Q11 | How many customers bought from us in September 2026? | 397 | 397 | yes |
| Q12 | What was the value of orders placed in September 2026? | 4,903,377.15 | 4903377.15 | yes |
| Q13 | How many orders were placed in September 2026? | 1,935 | 1935 | yes |
| Q14 | How many orders placed in September 2026 had to be backordered? | 193 | 193 | yes |
| Q15 | How much did customers pay us in September 2026? | 5,682,587.67 | 5682587.67 | yes |
| Q16 | How much do customers owe us right now? | 267,011.44 | 267011.44 | yes |
| Q17 | Which customer owes us the most right now? | Wingtip Toys (Birds, IL) \| 28,280.80 | Wingtip Toys (Birds, IL) \| 28280.8 | yes |
| Q18 | Who was our top salesperson by revenue in 2025? | Lily Code \| 3,781,278.35 | Lily Code \| 3781278.35 | yes |
| Q19 | How much did revenue grow in September 2026 compared with September 2025? | +5.79% | 5.79 | yes |
| Q20 | Which month of 2025 had the highest revenue? | August 2025 \| 5,223,973.95 | 2025-08 \| 5223973.95 | yes |
