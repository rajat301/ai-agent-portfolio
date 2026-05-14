# abs_client.py — Australian Bureau of Statistics API client.
#
# The ABS publishes free, official government data via a SDMX REST API.
# No API key required. No rate limit documented (be polite: one call at a time).
# Base URL: https://data.api.abs.gov.au/rest/
#
# Data format: SDMX-JSON (application/vnd.sdmx.data+json)
# A specialised time-series format used by statistical agencies worldwide.
# The response nests observations under: dataSets[0].series → each series
# has a key like "0:0:0:0" and observations keyed by time index "0", "1", ...

import sys  # reconfigure stdout encoding before any print — must be first
sys.stdout.reconfigure(encoding="utf-8")  # force UTF-8 so box chars render on Windows

import requests  # third-party HTTP library — sends GET requests to the ABS REST API
from datetime import datetime, timezone  # for ISO timestamps on fetched_at fields
from typing import Optional  # lets us annotate return types as Optional[dict]


# Base URL for all ABS SDMX REST API calls — everything is a sub-path of this.
ABS_BASE = "https://data.api.abs.gov.au/rest"

# SDMX-JSON content type — tells ABS to return the machine-readable JSON format
# rather than their default XML format. Without this header the API returns XML.
SDMX_HEADERS = {"Accept": "application/vnd.sdmx.data+json;version=1.0"}

# Map from plain English city name to ABS Greater Capital City Statistical Area code.
# These GCCSA codes are official ABS geography identifiers used across all their datasets.
# Source: ABS Australian Statistical Geography Standard (ASGS) Edition 3, 2021.
CITY_TO_ABS_CODE = {
    "Sydney":    "1GSYD",  # Greater Sydney
    "Melbourne": "2GMEL",  # Greater Melbourne
    "Brisbane":  "3GBRI",  # Greater Brisbane
    "Adelaide":  "4GADE",  # Greater Adelaide
    "Perth":     "5GPER",  # Greater Perth
    "Hobart":    "6GHOB",  # Greater Hobart
    "Darwin":    "7GDAR",  # Greater Darwin
    "Canberra":  "8ACTE",  # Australian Capital Territory — ABS uses 8ACTE, not 8GCAN
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 1 — fetch_property_price_growth
# ─────────────────────────────────────────────────────────────────────────────

def fetch_property_price_growth(city: str) -> Optional[dict]:
    """Fetch the Residential Property Price Index (RPPI) for the given Australian capital city.

    The RPPI is the ABS's official measure of residential property price changes.
    It is a Laspeyres price index (base quarter = 100) published quarterly.
    We request the last 8 observations (2 years) to calculate annual and quarterly growth.

    ABS dataset code: RPPI
    Full dataset key: ABS,RPPI (agency=ABS, dataset=RPPI)
    Endpoint: /data/ABS,RPPI/all
    Returns None and prints an error if the API call fails or data is missing.
    """

    # Normalise the city name: strip whitespace, title-case so "brisbane" → "Brisbane"
    city_clean = city.strip().title()

    # Look up the ABS region code for this city — None if city is not in our map
    region_code = CITY_TO_ABS_CODE.get(city_clean)

    if not region_code:
        # We can't call the API without a valid region code — fail fast with a clear message
        print(f"[ABS] Unknown city '{city}'. Supported cities: {list(CITY_TO_ABS_CODE.keys())}")
        return None

    # Build the full endpoint URL for this dataset
    # "all" is the SDMX key — means: return all series in the dataset (we filter by region below)
    url = f"{ABS_BASE}/data/ABS,RPPI/all"

    # Query params:
    #   lastNObservations=8 — only the last 8 time periods (8 quarters = 2 years)
    #   detail=dataonly     — omit metadata and annotations to reduce response size
    params = {
        "lastNObservations": 8,   # 8 quarters gives us 1 year of data for annual growth calc
        "detail": "dataonly",     # strip metadata; we only need the raw index values
    }

    print(f"[ABS] Fetching RPPI for {city_clean} (region: {region_code})...")

    try:
        # Make the GET request — timeout=30s to avoid hanging indefinitely on slow ABS servers
        response = requests.get(url, headers=SDMX_HEADERS, params=params, timeout=30)

        # Raise an HTTPError for 4xx / 5xx status codes so we catch it below
        response.raise_for_status()

        # Parse the SDMX-JSON response into a Python dict
        data = response.json()

    except requests.exceptions.Timeout:
        # ABS API can be slow — a timeout isn't unusual; log clearly and return None
        print(f"[ABS] Timeout fetching RPPI for {city_clean} — ABS API took > 30s")
        return None

    except requests.exceptions.HTTPError as e:
        # 404 = dataset not found; 503 = ABS servers down; either way we can't proceed
        print(f"[ABS] HTTP error fetching RPPI for {city_clean}: {e}")
        return None

    except requests.exceptions.RequestException as e:
        # Catches DNS failures, connection refused, SSL errors, etc.
        print(f"[ABS] Network error fetching RPPI for {city_clean}: {e}")
        return None

    except Exception as e:
        # Unexpected error (e.g., malformed JSON from ABS) — log and bail
        print(f"[ABS] Unexpected error fetching RPPI for {city_clean}: {e}")
        return None

    # ── Navigate the SDMX-JSON structure ────────────────────────────────────
    # SDMX-JSON structure (simplified):
    # {
    #   "data": {
    #     "dataSets": [{
    #       "series": {
    #         "KEY": {                      ← series key like "0:1:2:3"
    #           "observations": {
    #             "0": [value, ...],        ← time index "0" = oldest, "7" = newest
    #             "1": [value, ...],
    #             ...
    #           }
    #         }
    #       }
    #     }],
    #     "structure": {
    #       "dimensions": {
    #         "series": [...],              ← ordered list of dimension metadata
    #         "observation": [...]
    #       }
    #     }
    #   }
    # }

    try:
        # Navigate to the dataSets array — index 0 is always the primary dataset
        datasets = data["data"]["dataSets"]

        if not datasets:
            # ABS returned a valid response but with no data (can happen for small regions)
            print(f"[ABS] No datasets in RPPI response for {city_clean}")
            return None

        # The series dict maps composite keys ("0:1:2:3") to their observations
        series_dict = datasets[0]["series"]

        if not series_dict:
            print(f"[ABS] Empty series in RPPI response for {city_clean}")
            return None

        # ── Find the series that corresponds to our target region ────────────
        # The structure.dimensions.series list tells us what each component of
        # the composite key means and the order of values within each dimension.
        # We need to find which position in the key represents the region dimension
        # and which value index maps to our region_code.

        # Get the ordered list of series dimensions (e.g., ["MEASURE", "REGION", "FREQ"])
        dims = data["data"]["structure"]["dimensions"]["series"]

        # Build a lookup: dimension name → its position in the composite key
        # e.g., if REGION is the 2nd dimension, position=1 (0-indexed)
        dim_positions = {d["id"]: i for i, d in enumerate(dims)}

        # Find the position of the REGION dimension in the composite key
        # ABS RPPI uses "REGION" as the dimension id for geographic breakdowns
        region_pos = dim_positions.get("REGION")  # None if dimension name differs

        if region_pos is None:
            # Fallback: some ABS datasets use different dimension names
            # Try "REF_AREA" which is the standard SDMX geographic dimension name
            region_pos = dim_positions.get("REF_AREA")

        if region_pos is None:
            # Can't identify the region dimension — take the first series as a rough fallback
            print(f"[ABS] Cannot identify REGION dimension; using first series as fallback")
            target_series = next(iter(series_dict.values()))
        else:
            # Find which index value within the REGION dimension maps to our region_code
            region_dim = dims[region_pos]  # the full dimension metadata dict

            # region_dim["values"] is a list like [{"id": "1GSYD", ...}, {"id": "2GMEL", ...}]
            region_value_index = None
            for idx, val in enumerate(region_dim.get("values", [])):
                if val.get("id") == region_code:  # match by ABS region code (e.g., "3GBRI")
                    region_value_index = idx  # remember the integer index for key matching
                    break

            if region_value_index is None:
                # Our city's code is not in this dataset response — API may have filtered it
                print(f"[ABS] Region code {region_code} not found in RPPI response dimensions")
                return None

            # Now scan all series keys to find the one where position region_pos == region_value_index
            # Series keys look like "0:1:2:3" — split on ":" to get each dimension's value index
            target_series = None
            for key, series in series_dict.items():
                key_parts = key.split(":")  # split "0:1:2:3" into ["0", "1", "2", "3"]
                if len(key_parts) > region_pos:  # ensure key has enough parts
                    if int(key_parts[region_pos]) == region_value_index:  # this key is for our region
                        target_series = series  # found our series
                        break

            if target_series is None:
                print(f"[ABS] No RPPI series found for region code {region_code} ({city_clean})")
                return None

        # ── Extract observation values ───────────────────────────────────────
        # observations is a dict: {"0": [value, status], "1": [value, status], ...}
        # Keys are string integers ("0", "1", ...) representing time period indices.
        # The value at each key is a list where index 0 is the numeric observation value.
        observations = target_series.get("observations", {})

        if not observations:
            print(f"[ABS] No observations in RPPI series for {city_clean}")
            return None

        # Sort by integer key so "0" < "1" < ... < "7" (oldest to newest)
        sorted_obs = sorted(observations.items(), key=lambda x: int(x[0]))

        # Extract just the numeric values (index 0 of each observation list)
        # ABS encodes missing values as None — filter those out
        values = []
        for _, obs_list in sorted_obs:
            if obs_list and obs_list[0] is not None:  # obs_list[0] is the index value
                values.append(float(obs_list[0]))  # convert to float for arithmetic

        if len(values) < 2:
            # Need at least 2 data points to calculate any growth rate
            print(f"[ABS] Insufficient RPPI observations for {city_clean}: found {len(values)}")
            return None

        # ── Calculate growth rates ───────────────────────────────────────────
        # IMPORTANT: ABS SDMX-JSON returns observations newest-first when using
        # lastNObservations. After sorting by integer key ascending, key "0" = most recent.
        # So values[0] = latest quarter, values[1] = previous quarter, values[4] = year ago.
        latest = values[0]       # most recent index value (e.g., 142.7)
        prev_quarter = values[1] # one quarter earlier (e.g., 140.1)

        # Annual: compare latest to the observation 4 quarters (1 year) ago
        # If we don't have 5 observations, use the oldest available as the year-ago proxy
        year_ago = values[4] if len(values) >= 5 else values[-1]

        # Growth = (new - old) / old * 100, expressed as a percentage
        quarterly_growth = ((latest - prev_quarter) / prev_quarter) * 100
        annual_growth = ((latest - year_ago) / year_ago) * 100

        # ── Build reference period string ────────────────────────────────────
        # Get the observation dimension (time periods) to find the period label
        obs_dims = data["data"]["structure"]["dimensions"].get("observation", [])

        reference_period = "Unknown"  # default if we can't parse the time dimension
        if obs_dims:
            # The first observation dimension is typically the time period
            time_dim = obs_dims[0]
            time_values = time_dim.get("values", [])  # list of {"id": "2023-Q3", "name": "..."}

            if time_values:
                # The FIRST time value (index 0) is the most recent period.
                # ABS returns time periods newest-first when lastNObservations is used.
                # ABS uses period IDs like "2025-Q3", "2025-Q4", etc.
                last_period = time_values[0]
                period_id = last_period.get("id", "")  # e.g., "2025-Q3"

                if period_id:
                    reference_period = period_id  # use the ABS period ID directly

        # ── Return structured result ─────────────────────────────────────────
        return {
            "annual_growth_pct":    round(annual_growth, 2),     # e.g., 17.3
            "quarterly_growth_pct": round(quarterly_growth, 2),  # e.g., 4.1
            "index_value":          round(latest, 1),            # e.g., 142.7 (base 100 = 2011-12)
            "reference_period":     reference_period,            # e.g., "2025-Q3"
            "city":                 city_clean,                  # normalised city name
            "source":               "OFFICIAL: ABS Residential Property Price Index",
            "source_url":           "https://data.api.abs.gov.au",
            "reliability":          "HIGH",                      # official government statistical release
            "fetched_at":           datetime.now(timezone.utc).isoformat(),  # ISO 8601 UTC timestamp
        }

    except KeyError as e:
        # SDMX-JSON structure wasn't what we expected — ABS may have changed the schema
        print(f"[ABS] Unexpected SDMX-JSON structure for {city_clean}: missing key {e}")
        return None

    except Exception as e:
        # Any other parsing error — log and return None gracefully
        print(f"[ABS] Error parsing RPPI response for {city_clean}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 2 — fetch_suburb_demographics
# ─────────────────────────────────────────────────────────────────────────────

def fetch_suburb_demographics(state: str, suburb_name: str) -> dict:
    """Fetch ABS Census 2021 demographics for a suburb: population, income, age.

    Dataset: C21_G02_SAL — Census 2021 General Community Profile, Table G02
    G02 = Selected Medians and Averages (income, age, mortgage, rent)
    SAL = Suburb and Locality geographic level

    This function is best-effort: Census 2021 data doesn't always have SAL-level
    records for every suburb, and suburb name matching is approximate.
    Returns graceful None values on any failure rather than raising exceptions.
    """

    # Endpoint: /data/{agency},{dataset}/{key}
    # Using "all" as the key to get all geographic areas, then we filter locally
    url = f"{ABS_BASE}/data/ABS,C21_G02_SAL/all"

    # Limit to a small number of observations — G02 is a cross-sectional Census
    # (not time series), so 1 observation per area is the maximum anyway
    params = {
        "lastNObservations": 1,  # only the 2021 Census data point per area
        "detail": "dataonly",    # strip metadata to reduce response size
    }

    # Default return structure — all None means "data unavailable" rather than "zero"
    empty_result = {
        "median_household_income_weekly": None,
        "median_age":                     None,
        "population":                     None,
        "source":                         "OFFICIAL: ABS Census 2021",
        "reliability":                    "MEDIUM",  # 2021 data, 5-year cycle
        "note":                           "2021 Census — updated every 5 years",
    }

    print(f"[ABS] Fetching Census demographics for {suburb_name}, {state}...")

    try:
        # Request Census G02 data — this call may return a large payload for all SALs
        response = requests.get(url, headers=SDMX_HEADERS, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        print(f"[ABS] Timeout fetching Census data for {suburb_name} — ABS API took > 30s")
        return empty_result  # return Nones gracefully rather than crashing

    except requests.exceptions.HTTPError as e:
        print(f"[ABS] HTTP error fetching Census data for {suburb_name}: {e}")
        return empty_result

    except requests.exceptions.RequestException as e:
        print(f"[ABS] Network error fetching Census data for {suburb_name}: {e}")
        return empty_result

    except Exception as e:
        print(f"[ABS] Unexpected error fetching Census data for {suburb_name}: {e}")
        return empty_result

    try:
        # ── Find the series corresponding to our suburb ──────────────────────
        datasets = data["data"]["dataSets"]
        if not datasets:
            print(f"[ABS] No Census datasets returned for {suburb_name}")
            return empty_result

        series_dict = datasets[0]["series"]

        # Get dimension metadata to find the geography dimension and its values
        dims = data["data"]["structure"]["dimensions"]["series"]

        # Find the SAL (Suburb and Locality) dimension — it contains suburb names
        # ABS typically uses "REGION" or "SAL_CODE_2021" as the dimension ID
        geo_dim = None
        geo_pos = None
        for i, d in enumerate(dims):
            # The geographic dimension for SAL data usually has "SAL" or "REGION" in its ID
            if "SAL" in d.get("id", "").upper() or "REGION" in d.get("id", "").upper():
                geo_dim = d    # save the full dimension metadata
                geo_pos = i    # save its position in the composite key
                break

        if geo_dim is None or geo_pos is None:
            # Can't identify the suburb dimension — cannot match to the right series
            print(f"[ABS] Cannot identify geography dimension in Census G02 data")
            return empty_result

        # Search the suburb dimension values for a case-insensitive name match
        # ABS suburb names in the Census include the state suffix, e.g. "Kangaroo Point (Qld)"
        target_value_index = None
        suburb_lower = suburb_name.lower().strip()  # normalise for comparison

        for idx, val in enumerate(geo_dim.get("values", [])):
            # val["name"] typically looks like "Kangaroo Point (Qld)" or "Woolloongabba (Qld)"
            val_name = val.get("name", "").lower()
            if suburb_lower in val_name:  # substring match to handle state suffix variations
                target_value_index = idx  # found a matching suburb
                break

        if target_value_index is None:
            # Suburb not found in Census data — this is common for small localities
            print(f"[ABS] Suburb '{suburb_name}' not found in Census G02 SAL data")
            return {
                **empty_result,
                "note": f"2021 Census — '{suburb_name}' not found in ABS SAL geography",
            }

        # Find the series key that matches our suburb's value index at the geo dimension position
        target_series = None
        measure_dim = None  # we'll also need the MEASURE dimension to find the right variables

        for key, series in series_dict.items():
            key_parts = key.split(":")
            if len(key_parts) > geo_pos and int(key_parts[geo_pos]) == target_value_index:
                target_series = series
                break  # take the first matching series (they share geography, differ by measure)

        if target_series is None:
            print(f"[ABS] No Census series found for suburb index {target_value_index}")
            return empty_result

        # ── Extract key demographic variables ────────────────────────────────
        # Census G02 contains multiple measures per series key; the MEASURE dimension
        # tells us which variable each series represents. We look for:
        #   Median_Tot_Fam_Inc_Weekly   — median total family income per week
        #   Median_age_persons          — median age of persons
        #   Tot_P_P                     — total persons (population)
        # These variable names are approximate; ABS uses specific codes.

        # For this implementation: collect all observations from all series for this suburb
        # and return the first non-None values found for each target field.
        income  = None  # median household weekly income in dollars
        age     = None  # median age in years
        pop     = None  # total population count

        # Iterate all series to find those matching our suburb index
        for key, series in series_dict.items():
            key_parts = key.split(":")
            if len(key_parts) <= geo_pos:
                continue  # skip malformed keys

            if int(key_parts[geo_pos]) != target_value_index:
                continue  # not our suburb

            # Each matching series has one observation (Census point in time)
            obs = series.get("observations", {})
            if not obs:
                continue  # empty — skip

            # Get the first (and likely only) observation value
            first_obs = next(iter(obs.values()), None)
            if not first_obs or first_obs[0] is None:
                continue  # no data — skip

            val = float(first_obs[0])  # convert to float for all comparisons

            # Heuristics to classify the variable based on its numeric range:
            # - Weekly household income: typically $500–$5000/week
            # - Median age: typically 20–80 years
            # - Population: typically 1000–100000 persons
            # This is a rough classification since we can't always read the MEASURE dimension
            if income is None and 500 <= val <= 10000:
                income = int(val)  # plausible weekly household income
            elif age is None and 15 <= val <= 90:
                age = int(val)     # plausible median age
            elif pop is None and val > 100:
                pop = int(val)     # plausible population count (will be overwritten by larger values)

        return {
            "median_household_income_weekly": income,   # None if not found or ABS didn't report it
            "median_age":                     age,      # None if not found
            "population":                     pop,      # None if not found
            "source":                         "OFFICIAL: ABS Census 2021",
            "reliability":                    "MEDIUM",
            "note":                           "2021 Census — updated every 5 years",
        }

    except KeyError as e:
        print(f"[ABS] Unexpected Census data structure for {suburb_name}: missing key {e}")
        return empty_result

    except Exception as e:
        print(f"[ABS] Error parsing Census data for {suburb_name}: {e}")
        return empty_result
