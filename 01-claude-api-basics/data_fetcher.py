# data_fetcher.py — master data orchestrator for the property analyser.
#
# ARCHITECTURE: cache-first, official-sources-preferred, graceful degradation.
#
# Data source hierarchy (highest reliability first):
#   1. USER_PROVIDED     — rent/price the user gives us directly (most accurate)
#   2. ABS RPPI (LIVE)   — official government quarterly price index, cached 90 days
#   3. ABS Census (LIVE) — official 2021 demographics, cached 365 days (5yr cycle)
#   4. BENCHMARK         — hardcoded SQM/Cotality/Domain city-level data (monthly update)
#
# The cache layer (SQLite) ensures we never hit ABS more than once per city per quarter.
# Every field in the returned dict has a corresponding _source field so Claude and
# downstream callers always know the provenance and reliability of each data point.
#
# Run this file directly to see the full pipeline with 2 test properties.

import sys  # must be imported before any print calls
sys.stdout.reconfigure(encoding="utf-8")  # force UTF-8 so box-drawing chars (╔ ║) render on Windows

import os           # read environment variables (DOMAIN_API_APPROVED)
import uuid         # generate unique analysis IDs for audit trail
from datetime import datetime, timezone  # for ISO timestamps

from dotenv import load_dotenv  # reads .env file into os.environ
load_dotenv()  # load .env from the project root before importing anything that needs env vars

# Import our three data modules — each lives in the data/ package
from data.abs_client import fetch_property_price_growth, fetch_suburb_demographics
from data.cache import SuburbCache
from data.benchmarks import get_city_benchmarks, get_national_benchmarks

# Module-level cache instance — shared across all calls in this process.
# One SQLite file, one cache object, zero duplication.
cache = SuburbCache()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def fetch_all_data(property_input: dict) -> dict:
    """Orchestrate all data sources into a single enriched property dict.

    Implements cache-first pattern: checks SQLite cache before hitting any API.
    Falls back gracefully at every step — missing data never crashes the pipeline.

    Args:
        property_input: dict with keys:
            address       (str)  — street address for display only
            suburb        (str)  — suburb name for cache key and ABS lookup
            city          (str)  — capital city for benchmarks and ABS RPPI region
            state         (str)  — state code e.g. "QLD", "NSW"
            bedrooms      (int)  — number of bedrooms (used for rent estimates)
            property_type (str)  — "House", "Unit", "Apartment", etc.
            purchase_price (int) — property purchase price in dollars
            weekly_rent   (int, optional) — user-provided rent; skips benchmark if present

    Returns:
        Enriched dict with all data fields plus corresponding _source fields,
        a data_quality_score float, confidence string, and analysis_id UUID.
    """

    # ── Unpack property input ────────────────────────────────────────────────
    address        = property_input.get("address", "")
    suburb         = property_input.get("suburb", "")
    # Fall back to suburb if city not provided (works for single-suburb searches)
    city           = property_input.get("city", suburb)
    state          = property_input.get("state", "")
    bedrooms       = property_input.get("bedrooms", 3)
    property_type  = property_input.get("property_type", "House")
    purchase_price = property_input.get("purchase_price", 0)
    weekly_rent_input = property_input.get("weekly_rent")  # None if not provided

    print(f"\n{'─' * 66}")
    print(f"  PROPERTY: {address}, {suburb} {state}")
    print(f"{'─' * 66}")

    # ── STEP 1: Cache check ──────────────────────────────────────────────────
    # Print what we're looking for before making any decisions
    print(f"  Checking cache for {suburb}...")

    # RPPI is a capital city index — all suburbs in the same city share the same growth figure.
    # Cache under city name (not suburb) so Kangaroo Point and Woolloongabba both hit the same entry.
    cached_growth  = cache.get(city, state, "growth_data", max_age_days=90)

    # Census demographics are suburb-level — cache under suburb name with a long TTL
    # (Census runs every 5 years; 365 days is conservative and safe)
    cached_demo    = cache.get(suburb, state, "demographics", max_age_days=365)

    # ── STEP 2: ABS RPPI growth data (cache-first) ───────────────────────────
    abs_growth = None  # will hold the ABS RPPI result dict or None
    growth_from_cache = False  # track whether we used cache or hit the API

    if cached_growth is not None:
        # Cache hit — use stored data; no API call needed
        fetched_date = cached_growth.get("fetched_at", "unknown date")[:10]  # show YYYY-MM-DD only
        print(f"  Using cached growth data for {city} (fetched {fetched_date})")
        abs_growth = cached_growth        # use the cached dict directly
        growth_from_cache = True          # flag so data quality scoring knows this is fresh

    else:
        # Cache miss — call the ABS API for the city-level RPPI
        print(f"  Fetching ABS property price growth for {city}...")
        abs_growth = fetch_property_price_growth(city)  # returns dict or None on failure

        if abs_growth is not None:
            # Cache under city name — all suburbs in the city share this entry.
            # 90-day TTL matches the quarterly RPPI release cycle.
            cache.set(city, state, "growth_data", abs_growth, ttl_days=90)
            print(f"  [ABS] Cached RPPI for {city} for 90 days")
        else:
            # ABS call failed — we'll fall back to benchmark data in Step 3
            print(f"  [ABS] RPPI fetch failed for {city} — will use benchmark data")

    # ── STEP 3: ABS Census demographics (cache-first) ───────────────────────
    demographics = None  # will hold demographic dict or None

    if cached_demo is not None:
        # Census data is from 2021 — it changes every 5 years, so 365-day TTL is appropriate
        fetched_date = cached_demo.get("fetched_at", "unknown date")[:10] if isinstance(cached_demo, dict) else "cached"
        print(f"  Using cached demographics for {suburb}")
        demographics = cached_demo
    else:
        # Don't block the pipeline on Census data — call it but accept None gracefully
        print(f"  Fetching ABS Census demographics for {suburb}...")
        demographics = fetch_suburb_demographics(state, suburb)  # returns dict (never None — uses empty_result)

        if demographics and demographics.get("population") is not None:
            # Only cache if we actually got useful data — no point caching all-None results
            cache.set(suburb, state, "demographics", demographics, ttl_days=365)
            print(f"  [ABS] Cached Census demographics for {suburb} for 365 days")

    # ── STEP 4: City benchmarks (always from benchmarks.py, no API) ─────────
    print(f"  Loading {city} market benchmarks...")
    benchmarks = get_city_benchmarks(city)  # instant — no API call; reads from hardcoded dict

    # ── STEP 5: Determine rent data ──────────────────────────────────────────
    # Priority: user-provided > Domain API (future) > city benchmark

    if weekly_rent_input is not None:
        # User told us the actual rent — this is the most accurate possible figure
        weekly_rent       = int(weekly_rent_input)
        rent_source       = "USER_PROVIDED"
        rent_reliability  = "HIGH"  # actual rent, not an estimate

    elif os.getenv("DOMAIN_API_APPROVED", "").lower() == "true":
        # Domain API integration point — gated behind env var until officially implemented.
        # Set DOMAIN_API_APPROVED=true in .env when Domain API access is configured.
        # For now: this branch never executes; it's a documented hook for future work.
        weekly_rent       = None  # placeholder — replace with Domain API call
        rent_source       = "FUTURE: Domain API — not yet implemented"
        rent_reliability  = "MEDIUM"

    else:
        # Fall back to city benchmark median rent, derived from gross yield × median price.
        # gross_yield = annual_rent / price → annual_rent = yield × price
        # weekly_rent = annual_rent / 52
        # This is a rough estimate — always flag it so the user knows to provide actual rent.
        city_yield        = benchmarks.get("gross_yield_pct", 3.5) / 100  # convert % to decimal
        city_price        = benchmarks.get("median_house_price", 800000)
        weekly_rent       = int((city_yield * city_price) / 52)           # estimated weekly rent
        rent_source       = f"BENCHMARK: city median gross yield {benchmarks.get('gross_yield_pct')}% — provide actual rent for better accuracy"
        rent_reliability  = "LOW"  # city-level estimate; user must verify before relying on this

    # ── STEP 5: Calculate data quality score ────────────────────────────────
    # Each data source contributes a portion of the overall quality score (0.0–1.0).
    # Weighting reflects how much each source improves analysis accuracy:
    #   - ABS RPPI (25%): official price growth from the government
    #   - Rent (35%):     the biggest unknown — user-provided is far more accurate
    #   - Demographics (15%): helpful context but not decision-critical
    #   - Benchmarks (25%): always available; forms the baseline floor

    score = 0.0  # start at 0, accumulate as we confirm each data source

    # ABS RPPI contribution: +0.25 if we got real ABS data (cached or live)
    if abs_growth is not None and abs_growth.get("reliability") == "HIGH":
        score += 0.25  # official government data — highest quality growth figure

    # Rent contribution: varies by source quality
    if rent_source == "USER_PROVIDED":
        score += 0.35  # actual rent — no estimation error
    elif "BENCHMARK" in rent_source:
        score += 0.10  # estimated from city yield — less accurate

    # Demographics contribution: +0.15 if we have Census population data
    if demographics and demographics.get("population") is not None:
        score += 0.15  # real population data from 2021 Census

    # Benchmarks always available — hardcoded baseline always contributes 0.25
    score += 0.25

    # Classify confidence based on total score
    if score > 0.70:
        confidence = "HIGH"
    elif score > 0.40:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # ── STEP 6: Build enriched result dict ───────────────────────────────────
    # Every data field has a corresponding _source field so Claude knows provenance.
    # Merge order: benchmarks (base) → ABS growth → demographics → calculated fields

    # Determine which growth figure to use — prefer ABS RPPI over benchmark
    if abs_growth and abs_growth.get("annual_growth_pct") is not None:
        annual_growth_pct    = abs_growth["annual_growth_pct"]
        quarterly_growth_pct = abs_growth.get("quarterly_growth_pct")
        growth_source        = abs_growth["source"]
        reference_period     = abs_growth.get("reference_period", "Unknown")
    else:
        # ABS not available — fall back to city benchmark growth (less precise)
        annual_growth_pct    = None  # benchmark doesn't include a clean annual growth pct
        quarterly_growth_pct = None
        growth_source        = "BENCHMARK: Cotality HVI — city level (ABS RPPI unavailable)"
        reference_period     = "N/A"

    # Unique ID for every analysis run — useful for debugging, logging, and audit trails
    analysis_id = str(uuid.uuid4())

    enriched = {
        # ── Property identification ──────────────────────────────────────────
        "analysis_id":            analysis_id,                  # UUID for audit trail
        "address":                address,
        "suburb":                 suburb,
        "city":                   city,
        "state":                  state,
        "bedrooms":               bedrooms,
        "property_type":          property_type,
        "purchase_price":         purchase_price,
        "purchase_price_source":  "USER_PROVIDED",

        # ── Rent data ────────────────────────────────────────────────────────
        "weekly_rent":            weekly_rent,
        "weekly_rent_source":     rent_source,
        "weekly_rent_reliability": rent_reliability,

        # ── Price growth (ABS RPPI preferred, benchmark fallback) ────────────
        "annual_growth_pct":      annual_growth_pct,
        "annual_growth_source":   growth_source,
        "quarterly_growth_pct":   quarterly_growth_pct,
        "reference_period":       reference_period,

        # ── Market benchmarks (city-level) ───────────────────────────────────
        "vacancy_rate_pct":       benchmarks.get("vacancy_rate_pct"),
        "vacancy_source":         benchmarks.get("vacancy_source"),
        "gross_yield_pct":        benchmarks.get("gross_yield_pct"),
        "yield_source":           benchmarks.get("yield_source"),
        "rental_growth_pct":      benchmarks.get("rental_growth_pct"),
        "rental_growth_source":   benchmarks.get("rental_source"),
        "median_house_price":     benchmarks.get("median_house_price"),
        "median_house_source":    benchmarks.get("price_source"),
        "days_on_market":         benchmarks.get("days_on_market"),
        "dom_source":             benchmarks.get("dom_source"),

        # ── National financial benchmarks ────────────────────────────────────
        "rba_cash_rate_pct":      benchmarks.get("rba_cash_rate_pct"),
        "rba_source":             benchmarks.get("rba_source"),
        "investor_loan_rate_pct": benchmarks.get("investor_loan_rate_pct"),
        "loan_source":            benchmarks.get("loan_source"),
        "breakeven_yield_pct":    benchmarks.get("breakeven_yield_pct"),
        "breakeven_source":       benchmarks.get("breakeven_source"),

        # ── Demographics (ABS Census 2021) ───────────────────────────────────
        "median_household_income_weekly": demographics.get("median_household_income_weekly") if demographics else None,
        "median_age":                     demographics.get("median_age") if demographics else None,
        "population":                     demographics.get("population") if demographics else None,
        "demographics_source":            demographics.get("source", "ABS Census 2021 — not fetched") if demographics else "NOT_FETCHED",
        "demographics_note":              demographics.get("note") if demographics else None,

        # ── Data quality ─────────────────────────────────────────────────────
        "data_quality_score":     round(score, 3),  # 0.000–1.000
        "confidence":             confidence,        # "HIGH", "MEDIUM", or "LOW"
        "analysed_at":            datetime.now(timezone.utc).isoformat(),
    }

    # ── STEP 7: Print source transparency table ───────────────────────────────
    # This table shows exactly where every key figure came from.
    # OFFICIAL = government API,  BENCHMARK = hardcoded public report,
    # USER_PROVIDED = user input,  N/A = not available
    _print_source_table(enriched, score, confidence)

    return enriched  # full enriched dict ready for Claude analysis


# ─────────────────────────────────────────────────────────────────────────────
# TABLE PRINTER
# ─────────────────────────────────────────────────────────────────────────────

def _print_source_table(enriched: dict, score: float, confidence: str) -> None:
    """Print a formatted table showing every key data field and its source."""

    # Helper to format a value for display in a fixed-width column
    def fmt_val(v, fmt=None) -> str:
        if v is None:
            return "N/A"
        if fmt:
            return fmt.format(v)
        return str(v)

    # Truncate a string to max_len characters to keep columns aligned
    def trunc(s: str, max_len: int) -> str:
        s = str(s) if s else "N/A"
        return s[:max_len] if len(s) > max_len else s

    # Column widths: Field=22, Value=20, Source=25
    W_FIELD  = 22
    W_VALUE  = 20
    W_SOURCE = 25

    # Build the header line
    suburb = enriched.get("suburb", "")
    city   = enriched.get("city", "")
    header = f"DATA QUALITY: {score:.0%} confidence ({confidence})"

    total_width = W_FIELD + W_VALUE + W_SOURCE + 9  # 9 = borders and padding

    print()
    print(f"  ╔{'═' * total_width}╗")
    print(f"  ║  {header:<{total_width - 2}}║")
    print(f"  ╠{'═' * (W_FIELD + 2)}╦{'═' * (W_VALUE + 2)}╦{'═' * (W_SOURCE + 2)}╣")
    print(f"  ║  {'Field':<{W_FIELD}}║  {'Value':<{W_VALUE}}║  {'Source':<{W_SOURCE}}║")
    print(f"  ╠{'═' * (W_FIELD + 2)}╬{'═' * (W_VALUE + 2)}╬{'═' * (W_SOURCE + 2)}╣")

    def row(field: str, value: str, source: str) -> None:
        # Print one data row, truncating each column to its max width
        f = trunc(field,  W_FIELD)
        v = trunc(value,  W_VALUE)
        s = trunc(source, W_SOURCE)
        print(f"  ║  {f:<{W_FIELD}}║  {v:<{W_VALUE}}║  {s:<{W_SOURCE}}║")

    # Weekly rent — most important single figure for yield and cash-flow analysis
    rent_val = f"${enriched['weekly_rent']}/week" if enriched.get("weekly_rent") else "N/A"
    row("Weekly Rent", rent_val, enriched.get("weekly_rent_source", "N/A"))

    # Annual growth — official ABS figure (quarterly index) or benchmark fallback
    growth_val = f"{enriched['annual_growth_pct']}%" if enriched.get("annual_growth_pct") else "N/A (benchmark)"
    row("Annual Growth", growth_val, enriched.get("annual_growth_source", "N/A"))

    # Vacancy rate — how tight the rental market is (< 2% = landlord's market)
    vacancy_val = f"{enriched['vacancy_rate_pct']}%" if enriched.get("vacancy_rate_pct") else "N/A"
    row("Vacancy Rate", vacancy_val, enriched.get("vacancy_source", "N/A"))

    # Gross yield benchmark — city-level figure for context
    yield_val = f"{enriched['gross_yield_pct']}%" if enriched.get("gross_yield_pct") else "N/A"
    row("Gross Yield (city)", yield_val, enriched.get("yield_source", "N/A"))

    # Days on market — proxy for market liquidity and how quickly a vendor can exit
    dom_val = f"{enriched['days_on_market']} days" if enriched.get("days_on_market") else "N/A"
    row("Days on Market", dom_val, enriched.get("dom_source", "N/A"))

    # RBA cash rate — underpins the investor loan rate calculation
    rba_val = f"{enriched['rba_cash_rate_pct']}%" if enriched.get("rba_cash_rate_pct") else "N/A"
    row("RBA Cash Rate", rba_val, enriched.get("rba_source", "N/A"))

    # Census demographics — population and income context
    income_val = f"${enriched['median_household_income_weekly']}/wk" if enriched.get("median_household_income_weekly") else "N/A"
    row("Household Income", income_val, enriched.get("demographics_source", "N/A"))

    # Data quality summary row
    row("Data Quality", f"{score:.0%}", confidence)

    print(f"  ╚{'═' * (W_FIELD + 2)}╩{'═' * (W_VALUE + 2)}╩{'═' * (W_SOURCE + 2)}╝")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# TEST — run twice to prove caching works
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 66)
    print("  RUN 1 — Kangaroo Point (hits ABS API if not cached)")
    print("=" * 66)

    result1 = fetch_all_data({
        "address":        "14 Kangaroo Point Rd",
        "suburb":         "Kangaroo Point",
        "city":           "Brisbane",
        "state":          "QLD",
        "bedrooms":       3,
        "property_type":  "House",
        "purchase_price": 950000,
        "weekly_rent":    750,  # user-provided: contributes 0.35 to quality score
    })

    print("\n" + "=" * 66)
    print("  RUN 2 — Woolloongabba (same city; growth data served from cache)")
    print("=" * 66)

    result2 = fetch_all_data({
        "address":        "88 Logan Rd",
        "suburb":         "Woolloongabba",
        "city":           "Brisbane",
        "state":          "QLD",
        "bedrooms":       2,
        "property_type":  "Unit",
        "purchase_price": 620000,
        "weekly_rent":    580,
    })

    # Show cache performance after both runs
    print("\nCache stats:", cache.stats())

    # Show a sample of what the enriched dict contains
    print("\nSample keys from result1:")
    important_keys = [
        "annual_growth_pct", "annual_growth_source",
        "vacancy_rate_pct", "gross_yield_pct",
        "weekly_rent", "weekly_rent_source",
        "rba_cash_rate_pct", "data_quality_score", "confidence",
        "analysis_id",
    ]
    for k in important_keys:
        print(f"  {k}: {result1.get(k)}")
