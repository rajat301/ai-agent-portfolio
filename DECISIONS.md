# DECISIONS.md — AI Property Analyser
Architectural decisions made during Week 1 build.
Each decision is grounded in the actual code — see the referenced file for evidence.

---

## 1. SQLite for Caching (not Redis, not in-memory dict)

Date: May 2026
Decision: Use SQLite via Python's built-in `sqlite3` module, stored as `data/suburb_cache.db`.
Alternatives considered: Redis (external service), in-memory dict (lost on restart), Postgres (server required).
Reason: SQLite requires zero infrastructure — no containers, no servers, no pip installs beyond what Python ships with. The ABS API is free but slow (5–30 seconds per call), and RPPI data is quarterly so it never changes between releases. A single file on disk is the right tool for a local tool where data is immutable within a quarter. Evidence: `data/cache.py` lines 1–11: *"Zero infrastructure. No Redis, no Postgres, no docker containers. One file on disk. Python has sqlite3 in the standard library — no pip install. Perfect for a local tool where data doesn't change hourly."*
Revisit when: The tool becomes multi-user, needs concurrent writes, or moves to a hosted service — at that point Redis or Postgres would justify their overhead.

---

## 2. Claude Haiku for Interpretation (not Sonnet or Opus)

Date: May 2026
Decision: Use `claude-haiku-4-5` for all AI interpretation calls in `property_analyst.py` and `06_context_management.py`.
Alternatives considered: `claude-sonnet-4-6` (more capable, ~10× more expensive), `claude-opus-4-7` (most capable, ~30× more expensive).
Reason: The task is structured JSON output from pre-calculated numbers — it does not require reasoning or creativity. Haiku is the cheapest Claude model and is fast enough for interactive use. At Haiku pricing (~$0.80/M input, $4.00/M output), 1,000 analyses cost approximately $1.00. Evidence: `property_analyst.py` lines 14–19: *"Cheapest Claude model. Fast. Sufficient for structured JSON output. Interpretation does not require Sonnet or Opus. Cost at scale: 1000 analyses = ~$1.00"*. Also `06_context_management.py` line 23: *"Use Haiku because this teaching demo needs cheap calls."*
Revisit when: The interpretation task requires multi-step reasoning, comparative analysis across portfolios, or complex free-text synthesis — capabilities that currently require Sonnet or Opus.

---

## 3. 3-Layer Architecture (Data / Metrics / AI)

Date: May 2026
Decision: Enforce a hard three-layer separation: Layer 1 fetches and caches data, Layer 2 calculates all metrics in pure Python, Layer 3 sends pre-calculated results to Claude for interpretation only.
Alternatives considered: Single-layer (Claude does everything), two-layer (data + AI, no separate metrics engine), monolithic script.
Reason: Each layer has a different cost profile, failure mode, and testability requirement. Separating them means: data can be cached independently, metrics can be unit tested without any API calls, and Claude is only invoked when its output is needed. This also makes the token cost predictable — Claude never sees raw data and is never asked to do arithmetic. Evidence: `data_fetcher.py` lines 1–6 (cache-first orchestration); `property_metrics.py` lines 5–8 (*"NO AI. NO API CALLS. NO TOKENS."*); `property_analyst.py` lines 11–15 (*"Claude NEVER calculates anything here. Python already did all the maths."*).
Revisit when: Adding a new capability that does not cleanly fit one layer — e.g., an agentic loop where AI fetches its own data. LangGraph (Week 2) will extend this pattern rather than replace it.

---

## 4. Python Calculates Metrics (not Claude)

Date: May 2026
Decision: All 35 financial metrics (gross yield, DSCR, cash flow, stamp duty, 5-year projection, etc.) are calculated in pure Python in `property_metrics.py` before Claude is called.
Alternatives considered: Pass raw property data to Claude and let it calculate metrics inline, or calculate a subset in Python and let Claude fill in the rest.
Reason: Arithmetic is deterministic and free. Claude output is probabilistic, token-consuming, and costs money. Paying tokens for arithmetic that Python can compute exactly is wasteful engineering. Python is also easier to unit test — the 29 tests in `tests/test_metrics.py` verify every metric independently without API calls. Evidence: `property_metrics.py` architecture principle (lines 14–17): *"Python calculates what Python can calculate. Claude interprets what requires intelligence. Never pay tokens for arithmetic."*
Revisit when: A metric requires genuine reasoning or contextual judgement that arithmetic cannot express — e.g., assessing sovereign risk in a new market with no comparable data.

---

## 5. JSONL for Audit Log (not SQLite, not CSV)

Date: May 2026
Decision: Write one JSON object per line to `logs/analysis_log.jsonl`, opened in append mode (`"a"`).
Alternatives considered: SQLite (requires schema migration for new fields), CSV (cannot represent nested dicts; type coercion problems), plain text (not machine-readable).
Reason: JSONL is append-only by design — adding a record is a single `f.write(json.dumps(record) + "\n")` call. No schema migration is needed when a new field is added; old lines simply won't have it. The file is readable line by line without loading the whole file into memory, and it is directly compatible with pandas, Spark, BigQuery, and Excel. Evidence: `logs/audit.py` lines 9–16: *"Easy to append (just add a line). Easy to query (read line by line). Works with pandas, spark, Excel later. Never need to load entire file to add one record."*
Revisit when: Query patterns become complex (e.g., aggregations by date range, joins across properties) — at that point a proper database would outperform line-by-line parsing.

---

## 6. ABS API for Growth Data (not CoreLogic, not scraping)

Date: May 2026
Decision: Fetch residential property price growth from the ABS SDMX REST API (`data.api.abs.gov.au`), which publishes the official Residential Property Price Index (RPPI) quarterly.
Alternatives considered: CoreLogic/Cotality API (paid, ~$500/month), Domain API (pending approval, paid tier), scraping real estate websites (fragile, violates ToS).
Reason: The ABS API is free, requires no API key, and publishes official government data with HIGH reliability. The RPPI is an authoritative Laspeyres price index — the same index the RBA and Treasury use. No paid alternative provides higher quality growth data. Evidence: `abs_client.py` lines 1–5: *"The ABS publishes free, official government data via a SDMX REST API. No API key required."* The returned dict includes `"reliability": "HIGH"` and `"source": "OFFICIAL: ABS Residential Property Price Index"`.
Revisit when: The ABS changes their SDMX schema (it has been stable since 2021), or a free alternative with suburb-level granularity becomes available.

---

## 7. Hardcoded Benchmarks for Vacancy (not SQM API)

Date: May 2026
Decision: Hardcode monthly SQM Research, Cotality, Domain, and REA figures directly in `data/benchmarks.py` and update them manually each month.
Alternatives considered: SQM Research API (paid, ~$199/month), scraping SQM HTML, scraping Domain suburb profiles.
Reason: There is no free, stable API for vacancy rates, gross yields, or days-on-market. Scraping breaks whenever providers redesign their sites, violates most Terms of Service, and produces fragile code. Hardcoding with clear source labels is the professional pattern when the only alternatives are brittle scraping or a paid API. The update cadence (monthly, 10 minutes of work) is acceptable for a portfolio tool. Evidence: `data/benchmarks.py` lines 1–18: *"These are NOT lazy or placeholder values. They are deliberately hardcoded... Hardcoding with clear source labels IS the professional pattern when the alternative is brittle scraping or a paid API."*
Revisit when: The tool scales to production use where stale benchmarks create liability, or a free structured data source for vacancy rates becomes available.

---

## 8. Both Sliding Window and Summarisation Demonstrated in Script 6

Date: May 2026
Decision: Script 6 runs both the sliding window strategy and the summarisation strategy sequentially using the same 10-turn scripted conversation, then prints a side-by-side comparison.
Alternatives considered: Demonstrate only one strategy (simpler but less educational), let the user choose interactively (harder to reproduce), use only production code without comparison.
Reason: The two strategies have fundamentally different trade-offs that are only visible when compared directly. Sliding window is deterministic and cheap but loses early context; summarisation costs more tokens upfront but preserves investor name, property details, and key metrics across the full conversation. Demonstrating both with the same scripted input (same 10 turns, same properties, same user "Rajat") makes the trade-off concrete and measurable. Evidence: `06_context_management.py` lines 3–10 (docstring) and `run_demo()` / `print_final_comparison()` functions; `__main__` block: `run_demo("window")` followed by `run_demo("summarise")` followed by `print_final_comparison()`.
Revisit when: A third strategy (e.g., token-budget-aware dynamic compression) is worth adding to the comparison.

---

## 9. Summarisation Wins Over Sliding Window

Date: May 2026
Decision: The final `print_final_comparison()` function designates summarisation as the recommended strategy for production property investment assistants.
Alternatives considered: Sliding window as default (simpler, lower per-turn cost when context is short).
Reason: The memory-test turn (Turn 9: *"What was the gross yield on the first property we discussed?"*) is where sliding window fails. After 6+ turns, the sliding window has discarded Turn 1 (Kangaroo Point, $950k, $750/week) and cannot answer accurately. Summarisation compresses this into a single memory message that retains investor name, both properties, and all key metrics. For a property investment use case, forgetting earlier properties would produce wrong advice. Evidence: `06_context_management.py` `print_final_comparison()` (lines 296–313): *"Window: simple but loses early context (Claude may forget Rajat's name or the first property by later turns). Summarise: more tokens upfront for summarisation but preserves critical context across full conversation."* The winner is determined by lower total tokens — but the key learning notes that the window strategy's token savings come at the cost of lost facts.
Revisit when: Conversations are reliably short (under 6 turns) and memory of early context is not required — sliding window is the better choice in that regime.

---

## 10. Cache TTL Is 90 Days for ABS Data (not 30 days)

Date: May 2026
Decision: ABS RPPI growth data is cached with `ttl_days=90`. ABS Census demographics are cached with `ttl_days=365`.
Alternatives considered: 30-day TTL (matches the benchmark update cadence but over-fetches for quarterly data), 7-day TTL (appropriate for weekly data, wasteful here), no TTL (would re-fetch every run).
Reason: The ABS RPPI is a quarterly publication — it is released once every three months and the values do not change between releases. A 90-day TTL ensures exactly one API fetch per city per quarter regardless of how many properties in that city are analysed. Fetching more often would hit the same data while adding latency (5–30 seconds per call) and unnecessary load on the ABS servers. Evidence: `data/cache.py` lines 8–9: *"ABS RPPI is quarterly data — it never changes between releases. Caching with a 90-day TTL means we call the API once per city per quarter."* Also `cache.py` `set()` docstring: *"Use 90 for quarterly ABS data, 30 for monthly benchmarks, 7 for anything that changes more frequently."*
Revisit when: ABS changes the RPPI publication cadence (currently quarterly since 1986), or a more frequently updated government data source replaces RPPI.
