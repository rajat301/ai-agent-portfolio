# Data Sources — AI Property Analyser
Last updated: May 2026

---

## LIVE DATA (fetched automatically)

### ABS Residential Property Price Index (RPPI)

Source name: Australian Bureau of Statistics — RPPI
What it provides: Official quarterly residential property price growth by Australian capital city. Returns annual growth %, quarterly growth %, and the raw index value (Laspeyres index, base period 2011–12 = 100). Covers the last 8 quarters (2 years) per request.
How fetched: `01-claude-api-basics/data/abs_client.py`, function `fetch_property_price_growth(city)`. Uses a SDMX REST GET request to `https://data.api.abs.gov.au/rest/data/ABS,RPPI/all` with `lastNObservations=8` and `detail=dataonly`. No API key. Accepts `application/vnd.sdmx.data+json` content type.
Cached by: `data_fetcher.py` via `SuburbCache`, keyed on `(city, state, "growth_data")`, TTL 90 days.
Update frequency: Quarterly (ABS releases RPPI once per quarter).
Cost: Free. No API key required.
Reliability: HIGH — official government statistical release. The same index used by the RBA and Treasury.
Current limitation: Capital city level only — all suburbs within a city share one growth figure. ABS RPPI covers 8 capital cities (Sydney, Melbourne, Brisbane, Adelaide, Perth, Hobart, Darwin, Canberra). Data is typically 6–9 months behind current quarter. ABS servers can be slow (5–30 second response times).

---

### ABS Census 2021 — Demographics (G02)

Source name: Australian Bureau of Statistics — Census 2021, General Community Profile Table G02
What it provides: Suburb-level demographics from the 2021 Census: median household weekly income, median age, and total population. Dataset code: `C21_G02_SAL` (SAL = Suburb and Locality geography).
How fetched: `01-claude-api-basics/data/abs_client.py`, function `fetch_suburb_demographics(state, suburb_name)`. Uses a SDMX REST GET request to `https://data.api.abs.gov.au/rest/data/ABS,C21_G02_SAL/all`. Suburb matching uses case-insensitive substring search against ABS place names (e.g. "Kangaroo Point (Qld)").
Cached by: `data_fetcher.py` via `SuburbCache`, keyed on `(suburb, state, "demographics")`, TTL 365 days.
Update frequency: Every 5 years (next Census due 2026).
Cost: Free. No API key required.
Reliability: MEDIUM — data is from 2021 and may not reflect current demographics in fast-growing suburbs.
Current limitation: Suburb name matching is approximate (substring match); small localities may not appear in SAL geography. Variable classification uses numeric range heuristics (income: $500–$10,000/week; age: 15–90 years; population: >100) because MEASURE dimension codes are not always reliably parsed from the SDMX response.

---

## BENCHMARK DATA (hardcoded, update monthly)

All benchmark data is stored in `01-claude-api-basics/data/benchmarks.py`. To update any benchmark:
1. Open `data/benchmarks.py`.
2. Find the relevant city in `CITY_BENCHMARKS` or the field in `NATIONAL_BENCHMARKS`.
3. Update the numeric value and the corresponding `_source` string (e.g. `"SQM Research June 2026"`).
4. Update `"last_updated"` to today's date in ISO format (e.g. `"2026-06-14"`).
5. Run `pytest tests/ -v` to confirm no metrics tests broke.

---

### SQM Research — Vacancy Rates

Source name: SQM Research Monthly Vacancy Report
What it provides: Monthly percentage of rental properties currently vacant, by capital city. Below 2% = landlord's market; above 3% = tenant's market.
Where stored: `data/benchmarks.py`, `CITY_BENCHMARKS[city]["vacancy_rate_pct"]` and `CITY_BENCHMARKS[city]["vacancy_source"]`. National average in `NATIONAL_BENCHMARKS["national_vacancy_pct"]`.
How to update: Visit sqmresearch.com.au, check the latest monthly vacancy report, update `vacancy_rate_pct` for each city and `vacancy_source` to the new month, update `last_updated`.
Last updated: 2026-05-14 (May 2026 data)
Cities covered: Brisbane (1.0%), Sydney (1.2%), Melbourne (1.4%), Perth (0.8%), Adelaide (0.9%), Darwin (0.4%), Hobart (1.5%), Canberra (1.5%). National average: 1.6%.

---

### Cotality HVI (formerly CoreLogic) — Gross Yield and Rental Growth

Source name: Cotality Home Value Index (HVI) — monthly report
What it provides: City-level gross rental yield (%) and year-on-year rental growth (%). Gross yield = annual rent / purchase price.
Where stored: `data/benchmarks.py`, `CITY_BENCHMARKS[city]["gross_yield_pct"]` and `CITY_BENCHMARKS[city]["rental_growth_pct"]` (plus matching `_source` fields). National averages in `NATIONAL_BENCHMARKS["national_yield_pct"]` and `NATIONAL_BENCHMARKS["national_rental_growth_pct"]`. Also mirrored in `property_metrics.py` `CITY_YIELD_BENCHMARKS` dict for metrics calculations.
How to update: Visit cotality.com.au, check the latest HVI monthly report, update yield and rental growth per city, update `yield_source` and `rental_source` strings, update `last_updated`.
Last updated: 2026-05-14 (Cotality HVI April–May 2026 data)
Cities covered: Brisbane (3.80% yield, 6.7% rental growth), Sydney (3.10%, 5.2%), Melbourne (3.30%, 4.8%), Perth (4.20%, 6.7%), Adelaide (4.30%, 7.1%), Darwin (6.00%, 9.2%), Hobart (4.30%, 4.5%), Canberra (4.00%, 2.6%). National: 3.59% yield, 5.7% rental growth.

---

### Domain Suburb Profiles — Median House Price

Source name: Domain quarterly suburb profiles
What it provides: Median house price per capital city (city-wide median, not suburb-specific).
Where stored: `data/benchmarks.py`, `CITY_BENCHMARKS[city]["median_house_price"]` and `CITY_BENCHMARKS[city]["price_source"]`.
How to update: Visit domain.com.au/research, check the latest quarterly suburb profiles, update `median_house_price` per city and `price_source` to reflect the new quarter, update `last_updated`.
Last updated: 2026-05-14 (Q1 2026 Domain data)
Cities covered: Brisbane ($850,000), Sydney ($1,550,000), Melbourne ($960,000), Perth ($760,000), Adelaide ($800,000), Darwin ($540,000), Hobart ($680,000), Canberra ($870,000).

---

### REA / PropTrack — Days on Market

Source name: REA Market Insights / PropTrack
What it provides: Average number of days a property sits on market before selling. Low DOM = hot market = lower vendor negotiation risk.
Where stored: `data/benchmarks.py`, `CITY_BENCHMARKS[city]["days_on_market"]` and `CITY_BENCHMARKS[city]["dom_source"]`. Also mirrored in `property_metrics.py` `STATE_DOM_BENCHMARKS` for per-state variance calculations.
How to update: Visit realestate.com.au/insights, check PropTrack monthly market report, update `days_on_market` per city and `dom_source`, update `last_updated`.
Last updated: April 2026 (REA Market Insights data)
Cities covered: Brisbane (22 days), Sydney (28 days), Melbourne (35 days), Perth (9 days), Adelaide (25 days), Darwin (45 days), Hobart (38 days), Canberra (30 days).

---

### RBA — Cash Rate and Derived Loan Rate

Source name: Reserve Bank of Australia — official cash rate target
What it provides: Official overnight interbank rate (the RBA cash rate) and a derived typical investor variable mortgage rate (cash rate + ~2.40% bank margin). Also a calculated breakeven gross yield (the minimum yield needed to cover all holding costs at 80% LVR).
Where stored: `data/benchmarks.py`, `NATIONAL_BENCHMARKS["rba_cash_rate_pct"]`, `NATIONAL_BENCHMARKS["investor_loan_rate_pct"]`, `NATIONAL_BENCHMARKS["breakeven_yield_pct"]`. Mirrored in `property_metrics.py` `MARKET_BENCHMARKS` dict.
How to update: After each RBA board meeting (held 8 times per year), update `rba_cash_rate_pct` and `rba_source`. Recalculate `investor_loan_rate_pct` as cash rate + 2.40%. The `breakeven_yield_pct` (currently 6.00%) may also need adjustment if the loan rate changes significantly.
Last updated: March 2026 (RBA held at 4.10%)
Cities covered: National (applies to all cities).

---

## UNAVAILABLE FREE DATA (honest list)

The following data types were investigated and found to have no free, stable, programmatic source as of May 2026.

| Data type | Why unavailable | Paid alternative | Approx. cost |
|-----------|-----------------|-----------------|--------------|
| Suburb-level rent estimates | Domain API pending approval (`DOMAIN_API_APPROVED=false` in `.env`). No free API exists for current asking rents at suburb level. | Domain API (paid tier) | ~$299/month |
| Suburb-level capital growth | CoreLogic/Cotality provides suburb-level HVI but only via paid API. ABS RPPI is city-level only. | Cotality API | ~$500/month |
| Real-time vacancy rates by suburb | SQM publishes suburb-level vacancy data but behind a paywall. No free API exists. | SQM Research API | ~$199/month |
| Current median rent by bedroom count | REA/Domain publish this in their UI but no free structured API is available. | PropTrack API | ~$300/month |
| Suburb demographic updates (post-2021) | ABS Census runs every 5 years; next full dataset due 2027. No interim free source. | ABS TableBuilder (free but manual) | Free but no API |

---

## DATA QUALITY SCORING

The `data_quality_score` (0.000–1.000) is calculated in `data_fetcher.py`, `fetch_all_data()`, lines 167–198. It accumulates points as each data source is confirmed available. Claude's interpretation prompt receives this score so it can calibrate its confidence accordingly.

### Scoring table

| Source | Points | Condition |
|--------|--------|-----------|
| ABS RPPI (live or cached) | +0.25 | `abs_growth` is not None AND `abs_growth["reliability"] == "HIGH"` |
| Rent — user-provided | +0.35 | `rent_source == "USER_PROVIDED"` |
| Rent — benchmark estimate | +0.10 | `"BENCHMARK" in rent_source` (city yield × median price ÷ 52) |
| ABS Census demographics | +0.15 | `demographics` is not None AND `demographics["population"]` is not None |
| City benchmarks | +0.25 | Always added — hardcoded data is always available |

**Maximum possible score:** 1.00
Achieved when: user provides actual rent (`+0.35`) + ABS RPPI succeeds (`+0.25`) + Census demographics found (`+0.15`) + benchmarks (`+0.25`).

**Minimum possible score:** 0.35
Achieved when: rent is estimated from benchmarks (`+0.10`) + ABS RPPI fails (`+0.00`) + no Census data (`+0.00`) + benchmarks (`+0.25`).

### Confidence thresholds

| Score range | Confidence label | Meaning |
|-------------|-----------------|---------|
| > 0.70 | HIGH | At least 3 of 4 sources available; analysis is reliable |
| > 0.40 | MEDIUM | 2 sources available; treat projections as indicative |
| ≤ 0.40 | LOW | Only benchmark data; do not make investment decisions on this alone |

The rent data point carries the most weight (`+0.35`) because it is the single biggest source of estimation error. A city-level yield estimate for rent can be off by 20–30% for a specific suburb. User-provided actual rent dramatically improves cash-flow and yield accuracy.

---

## WEEK 2 DATA NEEDS

The following data sources will be required for Week 2 scripts. None have been implemented yet.

### LangGraph Agents

What data: LangGraph agents in Week 2 will need the same property data as Week 1 (ABS RPPI, benchmarks, metrics) plus tool state that persists across graph nodes (e.g., which properties have been analysed, which are awaiting human approval). The human-in-the-loop script will need a mechanism to pass structured approval/rejection decisions between nodes.
Storage approach: LangGraph manages state as a typed dict passed through graph edges. No new external data sources required — the existing `data_fetcher.py` pipeline can be wrapped as a LangGraph tool node.

### RAG Part 1–3 (Chunking, Embeddings, Full Pipeline)

What data: A corpus of Australian property investment documents for retrieval. Candidates include:
- RBA Statement on Monetary Policy (public PDF, quarterly)
- NHFIC State of the Nation's Housing reports (public PDF, annual)
- ABS housing market publications (public PDF)
- Property council reports and suburb investment guides
- Any plain-text briefing documents about Australian markets

Storage approach: Documents chunked and stored in a local vector store (ChromaDB or FAISS) during Week 2. Embeddings generated via the Anthropic embeddings API or an open-source alternative (sentence-transformers).

### RAG Evaluation (RAGAS)

What data: A ground-truth question–answer dataset built manually from the document corpus above. Typically 20–50 question/answer/context triplets used to evaluate retrieval precision, answer faithfulness, and context relevance.

### RAG on Databricks

What data: Delta tables on a Databricks workspace containing structured property data (suburb medians, historical growth, demographic profiles). Exact table schema to be determined when Databricks environment is confirmed.
Likely sources: ABS data loaded into Delta Lake, possibly supplemented with Domain or CoreLogic data if a licence is available in the Databricks environment.

### Snowflake Cortex

What data: Snowflake tables containing property or financial data to be queried via Cortex (Snowflake's managed LLM service). Exact tables to be confirmed when Snowflake environment details are available.
Note: Snowflake Cortex integration was listed in Week 2 scope in early planning but does not appear in the current AGENTS.md NEXT list — confirm whether this is still in scope before building.
