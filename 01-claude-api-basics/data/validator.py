"""
data/validator.py
=================
Input validation and security layer.
Runs BEFORE any API call, cache access, or calculation.

Why this exists:
    - Bad input data produces wrong financial metrics
    - Wrong metrics lead to wrong investment decisions
    - SQL injection could corrupt the SQLite cache
    - API keys must never appear in logs

Elite engineering principle:
    Validate at the boundary. Once data is inside the system,
    every other layer can trust it is clean and correct.
"""

from dataclasses import dataclass, field  # dataclass = clean way to define data structures
from typing import List                   # for type hints on lists

# Valid Australian states and territories
VALID_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT"}

# Valid Australian capital cities our system supports
VALID_CITIES = {
    "Sydney", "Melbourne", "Brisbane",
    "Perth", "Adelaide", "Darwin", "Hobart", "Canberra"
}

# Characters that could enable SQL injection attacks
# These are stripped from all string inputs before touching the database
SQL_INJECTION_CHARS = ["'", '"', ";", "--", "\\", "/", "\x00"]


@dataclass
class ValidationResult:
    """
    Result of validating a property input.
    Dataclass gives us clean attribute access and automatic __repr__.
    
    is_valid:       True if safe to proceed, False if must reject
    errors:         List of blocking problems — input rejected if any exist
    warnings:       List of unusual values — input accepted but flagged
    sanitised_data: Cleaned version of input — use this, not original
    """
    is_valid: bool = True                        # Assume valid until proven otherwise
    errors: List[str] = field(default_factory=list)    # Blocking issues
    warnings: List[str] = field(default_factory=list)  # Non-blocking concerns
    sanitised_data: dict = field(default_factory=dict) # Cleaned input


def validate_property_input(data: dict) -> ValidationResult:
    """
    Validate and sanitise a property input dict.
    
    Call this FIRST before any API call or calculation.
    Use result.sanitised_data instead of original data.
    
    Args:
        data: Raw property input dict from user
        
    Returns:
        ValidationResult with is_valid, errors, warnings, sanitised_data
    """
    result = ValidationResult()   # Start with clean result
    clean = {}                    # Will hold sanitised values

    # ── PURCHASE PRICE ────────────────────────────────────────────────────────

    if "purchase_price" in data:
        price = data["purchase_price"]
        # Must be a number — reject strings like "nine hundred thousand"
        if not isinstance(price, (int, float)):
            result.errors.append(
                f"purchase_price must be a number, got: {type(price).__name__}"
            )
        # Must be in realistic range for Australian property
        elif price < 50_000:
            result.errors.append(
                "purchase_price must be at least $50,000"
            )
        elif price > 50_000_000:
            result.errors.append(
                "purchase_price must be less than $50,000,000"
            )
        else:
            clean["purchase_price"] = round(float(price))  # Normalise to float, round to dollar

    # ── WEEKLY RENT ───────────────────────────────────────────────────────────

    if "weekly_rent" in data:
        rent = data["weekly_rent"]
        if not isinstance(rent, (int, float)):
            result.errors.append("weekly_rent must be a number")
        elif rent < 50:
            result.errors.append("weekly_rent must be at least $50/week")
        elif rent > 10_000:
            result.errors.append("weekly_rent must be less than $10,000/week")
        else:
            clean["weekly_rent"] = round(float(rent))  # Normalise to float
            # Warnings for unusual but not impossible values
            if rent < 200:
                result.warnings.append(
                    f"Weekly rent ${rent} is very low — please verify"
                )
            if rent > 3_000:
                result.warnings.append(
                    f"Weekly rent ${rent} is very high — please verify"
                )

    # ── BEDROOMS ──────────────────────────────────────────────────────────────

    if "bedrooms" in data:
        beds = data["bedrooms"]
        if not isinstance(beds, int):
            result.errors.append("bedrooms must be an integer")
        elif beds < 1 or beds > 20:
            result.errors.append("bedrooms must be between 1 and 20")
        else:
            clean["bedrooms"] = beds

    # ── SUBURB ────────────────────────────────────────────────────────────────

    if "suburb" in data:
        suburb = str(data["suburb"])               # Convert to string
        suburb = suburb.strip()                    # Remove leading/trailing whitespace
        suburb = _remove_sql_injection(suburb)     # Remove dangerous characters
        suburb = suburb.title()                    # Title case: "kangaroo point" -> "Kangaroo Point"
        # Check length after cleaning
        if len(suburb) < 2:
            result.errors.append("suburb must be at least 2 characters")
        elif len(suburb) > 50:
            result.errors.append("suburb must be less than 50 characters")
        else:
            clean["suburb"] = suburb

    # ── CITY ──────────────────────────────────────────────────────────────────

    if "city" in data:
        city = str(data["city"]).strip().title()   # Normalise to title case
        if city not in VALID_CITIES:
            result.errors.append(
                f"city '{city}' not recognised. "
                f"Must be one of: {', '.join(sorted(VALID_CITIES))}"
            )
        else:
            clean["city"] = city

    # ── STATE ─────────────────────────────────────────────────────────────────

    if "state" in data:
        state = str(data["state"]).strip().upper()  # Normalise to uppercase
        if state not in VALID_STATES:
            result.errors.append(
                f"state '{state}' not recognised. "
                f"Must be one of: {', '.join(sorted(VALID_STATES))}"
            )
        else:
            clean["state"] = state

    # ── LOAN LVR ──────────────────────────────────────────────────────────────

    if "loan_lvr_pct" in data:
        lvr = data["loan_lvr_pct"]
        if not isinstance(lvr, (int, float)):
            result.errors.append("loan_lvr_pct must be a number")
        elif lvr < 1 or lvr > 99:
            result.errors.append("loan_lvr_pct must be between 1 and 99")
        else:
            clean["loan_lvr_pct"] = float(lvr)

    # ── LOAN RATE ─────────────────────────────────────────────────────────────

    if "loan_rate_pct" in data:
        rate = data["loan_rate_pct"]
        if not isinstance(rate, (int, float)):
            result.errors.append("loan_rate_pct must be a number")
        elif rate < 1 or rate > 25:
            result.errors.append("loan_rate_pct must be between 1% and 25%")
        else:
            clean["loan_rate_pct"] = float(rate)

    # ── ANNUAL GROWTH ─────────────────────────────────────────────────────────

    if "annual_growth_pct" in data:
        growth = data["annual_growth_pct"]
        if not isinstance(growth, (int, float)):
            result.errors.append("annual_growth_pct must be a number")
        elif growth < -50 or growth > 100:
            result.errors.append("annual_growth_pct must be between -50% and 100%")
        else:
            clean["annual_growth_pct"] = float(growth)
            if growth > 30:
                result.warnings.append(
                    f"annual_growth_pct {growth}% is very high — verify data source"
                )

    # ── PASS THROUGH OTHER VALID FIELDS ──────────────────────────────────────

    # These fields are passed through without specific validation
    # They're either internal flags or have safe default handling
    passthrough_fields = [
        "address", "property_type", "loan_term_years",
        "marginal_tax_rate_pct", "depreciation_annual",
        "vacancy_rate_pct", "days_on_market"
    ]
    for field_name in passthrough_fields:
        if field_name in data:
            clean[field_name] = data[field_name]  # Pass through as-is

    # ── FINAL RESULT ──────────────────────────────────────────────────────────

    # If any errors were found, mark as invalid
    if result.errors:
        result.is_valid = False

    # Store the cleaned data in the result
    result.sanitised_data = clean

    return result


def mask_sensitive_config(config_dict: dict) -> dict:
    """
    Return a safe-to-print version of a config dict.
    Replaces values of sensitive keys with ***MASKED***.
    
    Use this whenever printing or logging config/environment data.
    API keys must NEVER appear in logs, terminal output, or error messages.
    
    Args:
        config_dict: Dict that may contain sensitive values
        
    Returns:
        New dict with sensitive values replaced by ***MASKED***
    """
    # Keywords that indicate a sensitive field
    sensitive_keywords = ["key", "secret", "password", "token", "api", "auth"]

    masked = {}  # Build new dict — never modify original
    for k, v in config_dict.items():
        # Check if this key name contains any sensitive keyword
        key_lower = k.lower()
        is_sensitive = any(kw in key_lower for kw in sensitive_keywords)

        if is_sensitive:
            masked[k] = "***MASKED***"  # Replace value, keep key name
        else:
            masked[k] = v  # Pass through non-sensitive values unchanged

    return masked


def _remove_sql_injection(text: str) -> str:
    """
    Remove characters commonly used in SQL injection attacks.
    Private function — only used internally within this module.
    
    Why: Our SQLite cache uses string values in queries.
    An attacker could pass suburb="Brisbane'; DROP TABLE cache;--"
    to corrupt or destroy the cache database.
    """
    clean = text  # Start with original text
    for char in SQL_INJECTION_CHARS:
        clean = clean.replace(char, "")  # Remove each dangerous character
    return clean


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE TEST — Run to verify validator works
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n VALIDATOR — Standalone Test\n")

    # Test 1: Valid input
    valid = validate_property_input({
        "purchase_price": 950000,
        "weekly_rent": 750,
        "bedrooms": 3,
        "suburb": "kangaroo point",   # lowercase — will be fixed
        "city": "Brisbane",
        "state": "qld",               # lowercase — will be fixed
        "loan_lvr_pct": 80,
        "loan_rate_pct": 6.5,
        "annual_growth_pct": 12.0,
    })
    print(f"Test 1 (valid input): is_valid={valid.is_valid}")
    print(f"  suburb cleaned: '{valid.sanitised_data.get('suburb')}'")
    print(f"  state cleaned:  '{valid.sanitised_data.get('state')}'")

    # Test 2: Invalid city
    invalid_city = validate_property_input({"city": "Atlantis"})
    print(f"\nTest 2 (invalid city): is_valid={invalid_city.is_valid}")
    print(f"  errors: {invalid_city.errors}")

    # Test 3: SQL injection attempt
    sql_attempt = validate_property_input({
        "suburb": "Brisbane'; DROP TABLE cache;--"
    })
    print(f"\nTest 3 (SQL injection): cleaned='{sql_attempt.sanitised_data.get('suburb')}'")

    # Test 4: Key masking
    config = {
        "ANTHROPIC_API_KEY": "sk-ant-realkey123",
        "DOMAIN_API_KEY": "key_64c6abb",
        "city": "Brisbane"
    }
    masked = mask_sensitive_config(config)
    print(f"\nTest 4 (key masking):")
    print(f"  ANTHROPIC_API_KEY: {masked['ANTHROPIC_API_KEY']}")
    print(f"  DOMAIN_API_KEY:    {masked['DOMAIN_API_KEY']}")
    print(f"  city:              {masked['city']}")
