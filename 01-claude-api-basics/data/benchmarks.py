# benchmarks.py — hardcoded city-level property market benchmarks.
#
# These are NOT lazy or placeholder values. They are deliberately hardcoded.
#
# WHY HARDCODE INSTEAD OF SCRAPING?
# Some data simply has no free, stable API. The alternative is scraping HTML from
# SQM Research, Cotality, or Domain — which breaks whenever they redesign their site,
# violates most ToS, and produces fragile code. Hardcoding with clear source labels
# IS the professional pattern when the alternative is brittle scraping or a paid API.
#
# MAINTENANCE CADENCE:
# Update once per month when SQM / Cotality / Domain publish their monthly reports.
# Update the "last_updated" field to today's date and change "source" strings to match.
# This is manual work, but it takes 10 minutes and produces reliable data.
#
# SOURCES (all publicly available, no API key required):
#   SQM Research   — monthly vacancy and rental data (sqmresearch.com.au)
#   Cotality HVI   — formerly CoreLogic; monthly growth and yield data (cotality.com.au)
#   Domain         — quarterly suburb profiles and median prices (domain.com.au)
#   REA / PropTrack — days on market data (realestate.com.au/insights)
#   RBA            — official cash rate (rba.gov.au)
#
# Last updated: 2026-05-14

# ─────────────────────────────────────────────────────────────────────────────
# CITY-LEVEL BENCHMARKS
# ─────────────────────────────────────────────────────────────────────────────

CITY_BENCHMARKS: dict = {

    "Brisbane": {
        # Vacancy rate — % of rental properties currently unoccupied
        # Below 2% = landlord's market; Brisbane is extremely tight at 1.0%
        "vacancy_rate_pct":     1.0,
        "vacancy_source":       "SQM Research May 2026",

        # Gross yield — annual rent / purchase price, expressed as %
        # Brisbane's strong price growth has compressed yields vs. Perth / Darwin
        "gross_yield_pct":      3.80,
        "yield_source":         "Cotality HVI April 2026",

        # Rental growth — year-on-year change in asking rents across the city
        # 6.7% reflects continued demand from interstate migration to SEQ
        "rental_growth_pct":    6.7,
        "rental_source":        "Cotality May 2026",

        # Median house price — city-wide median, not suburb-specific
        # Use suburb-level data from abs_client or Claude search when available
        "median_house_price":   850000,
        "price_source":         "Domain suburb profiles Q1 2026",

        # Days on market — average selling time; low DOM = hot market = low vendor bargaining risk
        "days_on_market":       22,
        "dom_source":           "REA Market Insights April 2026",

        "last_updated":         "2026-05-14",
    },

    "Sydney": {
        # Sydney: highest prices, compressed yields, slower growth than Qld/WA markets
        "vacancy_rate_pct":     1.2,
        "vacancy_source":       "SQM Research May 2026",

        "gross_yield_pct":      3.10,
        "yield_source":         "Cotality HVI April 2026",

        "rental_growth_pct":    5.2,
        "rental_source":        "Cotality May 2026",

        "median_house_price":   1550000,
        "price_source":         "Domain suburb profiles Q1 2026",

        "days_on_market":       28,
        "dom_source":           "REA Market Insights April 2026",

        "last_updated":         "2026-05-14",
    },

    "Melbourne": {
        # Melbourne: second-highest prices, highest vacancy (supply > demand), low growth post-COVID
        "vacancy_rate_pct":     1.4,
        "vacancy_source":       "SQM Research May 2026",

        "gross_yield_pct":      3.30,
        "yield_source":         "Cotality HVI April 2026",

        "rental_growth_pct":    4.8,
        "rental_source":        "Cotality May 2026",

        "median_house_price":   960000,
        "price_source":         "Domain suburb profiles Q1 2026",

        "days_on_market":       35,
        "dom_source":           "REA Market Insights April 2026",

        "last_updated":         "2026-05-14",
    },

    "Perth": {
        # Perth: highest growth of any major capital; low vacancy driven by mining/resources boom
        "vacancy_rate_pct":     0.8,
        "vacancy_source":       "SQM Research May 2026",

        "gross_yield_pct":      4.20,
        "yield_source":         "Cotality HVI April 2026",

        "rental_growth_pct":    6.7,
        "rental_source":        "Cotality May 2026",

        "median_house_price":   760000,
        "price_source":         "Domain suburb profiles Q1 2026",

        # Low DOM (9 days!) reflects extremely hot market with limited stock
        "days_on_market":       9,
        "dom_source":           "REA Market Insights April 2026",

        "last_updated":         "2026-05-14",
    },

    "Adelaide": {
        # Adelaide: strong investment fundamentals — high yield, low vacancy, good growth
        "vacancy_rate_pct":     0.9,
        "vacancy_source":       "SQM Research May 2026",

        "gross_yield_pct":      4.30,
        "yield_source":         "Cotality HVI April 2026",

        # Highest rental growth of any mainland capital — severe undersupply
        "rental_growth_pct":    7.1,
        "rental_source":        "Cotality May 2026",

        "median_house_price":   800000,
        "price_source":         "Domain suburb profiles Q1 2026",

        "days_on_market":       25,
        "dom_source":           "REA Market Insights April 2026",

        "last_updated":         "2026-05-14",
    },

    "Darwin": {
        # Darwin: highest yield in Australia; very low vacancy; high DOM due to small market size
        # Risk: small economy, volatile demand, cyclical exposure to resources projects
        "vacancy_rate_pct":     0.4,
        "vacancy_source":       "SQM Research May 2026",

        "gross_yield_pct":      6.00,
        "yield_source":         "Cotality HVI April 2026",

        # Highest rental growth nationally — reflects severe undersupply and transient population
        "rental_growth_pct":    9.2,
        "rental_source":        "Cotality May 2026",

        "median_house_price":   540000,
        "price_source":         "Domain suburb profiles Q1 2026",

        # High DOM reflects the small buyer pool and specialised market
        "days_on_market":       45,
        "dom_source":           "REA Market Insights April 2026",

        "last_updated":         "2026-05-14",
    },

    "Hobart": {
        # Hobart: reversed from the pandemic boom; rising vacancy and softening prices
        "vacancy_rate_pct":     1.5,
        "vacancy_source":       "SQM Research May 2026",

        "gross_yield_pct":      4.30,
        "yield_source":         "Cotality HVI April 2026",

        "rental_growth_pct":    4.5,
        "rental_source":        "Cotality May 2026",

        "median_house_price":   680000,
        "price_source":         "Domain suburb profiles Q1 2026",

        "days_on_market":       38,
        "dom_source":           "REA Market Insights April 2026",

        "last_updated":         "2026-05-14",
    },

    "Canberra": {
        # Canberra: government-employment-driven market; stable but slow growth
        "vacancy_rate_pct":     1.5,
        "vacancy_source":       "SQM Research May 2026",

        "gross_yield_pct":      4.00,
        "yield_source":         "Cotality HVI April 2026",

        "rental_growth_pct":    2.6,
        "rental_source":        "Cotality May 2026",

        "median_house_price":   870000,
        "price_source":         "Domain suburb profiles Q1 2026",

        "days_on_market":       30,
        "dom_source":           "REA Market Insights April 2026",

        "last_updated":         "2026-05-14",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# NATIONAL BENCHMARKS
# ─────────────────────────────────────────────────────────────────────────────

NATIONAL_BENCHMARKS: dict = {
    # RBA official cash rate — set by the Reserve Bank of Australia board
    # This is the overnight interbank rate; retail mortgage rates = cash rate + bank margin (~2.4%)
    "rba_cash_rate_pct":         4.10,
    "rba_source":                "RBA March 2026",

    # Typical investor variable rate from the big 4 banks at 80% LVR
    # = cash rate (4.10%) + average bank margin (~2.40%)
    "investor_loan_rate_pct":    6.50,
    "loan_source":               "Major bank average May 2026",

    # Breakeven yield — the gross yield needed to cover all holding costs at 80% LVR
    # Below this = negatively geared; above = positively geared (rare in major cities)
    # Calculated: interest (6.5% * 80% = 5.2%) + rates/insurance/mgmt (~0.8%) ≈ 6%
    "breakeven_yield_pct":       6.00,
    "breakeven_source":          "Calculated: typical investor at 80% LVR",

    # National averages — weighted average across all 8 capital cities
    "national_vacancy_pct":      1.6,
    "national_yield_pct":        3.59,
    "national_rental_growth_pct": 5.7,
    "national_source":           "Cotality HVI May 2026",

    "last_updated":              "2026-05-14",
}


# ─────────────────────────────────────────────────────────────────────────────
# ACCESSOR FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_city_benchmarks(city: str) -> dict:
    """Return city-level benchmarks merged with national benchmarks.

    City-specific fields override national defaults where they overlap.
    Always includes a reliability note so callers know this is city-level,
    not suburb-level — an important distinction for suburb investment decisions.

    Args:
        city: City name, e.g. "Brisbane". Case-insensitive.
    Returns:
        Merged dict with all city fields plus national fields for the remainder.
    """
    # Normalise input — title-case handles "brisbane", "BRISBANE", "Brisbane"
    city_clean = city.strip().title()

    # Look up city-specific data — fall back to an empty dict if city not found
    city_data = CITY_BENCHMARKS.get(city_clean, {})

    if not city_data:
        # City not in our table — log and use national benchmarks as a proxy
        print(f"[Benchmarks] City '{city}' not found. Using national benchmarks as fallback.")

    # Merge strategy: national benchmarks as base layer, city data on top.
    # City-specific fields (vacancy, yield, etc.) override the national equivalents.
    merged = {
        **NATIONAL_BENCHMARKS,  # base: national data for all fields
        **city_data,            # override: city-specific values where they exist
        # Always append the reliability caveat so Claude (and humans) know the data granularity
        "reliability": "MEDIUM — city level, not suburb",
        "city": city_clean,     # include the normalised city name for reference
    }

    return merged


def get_national_benchmarks() -> dict:
    """Return the national benchmark dict as-is.

    Use this when no city is known or when building a national comparison baseline.
    """
    return {
        **NATIONAL_BENCHMARKS,  # return a copy to prevent accidental mutation of the module-level dict
        "reliability": "MEDIUM — national averages, not city or suburb level",
    }
