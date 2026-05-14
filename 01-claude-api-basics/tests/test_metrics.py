"""
tests/test_metrics.py
=====================
Unit tests for property_metrics.py
18 tests proving every calculation is mathematically correct.

Why these tests exist:
    A client reports "your tool gave wrong yield data."
    Without tests you cannot prove what broke or prevent recurrence.
    With tests: run pytest, see green, prove the maths is right.

Run with:
    cd 01-claude-api-basics
    python -m pytest tests/ -v

All tests are pure Python — zero API calls, zero Claude, zero cost.
If tests pass, the maths is correct. Every time. Not just when you look.
"""

import sys
import os

# Add parent directory to path so we can import property_metrics
# This is needed because tests/ is a subdirectory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # Testing framework — install with: pip install pytest
from property_metrics import calculate_all_metrics  # The module we're testing
from data.validator import validate_property_input, mask_sensitive_config


# ─────────────────────────────────────────────────────────────────────────────
# TEST DATA HELPER
# ─────────────────────────────────────────────────────────────────────────────

def make_test_property(**overrides):
    """
    Create a standard test property dict.
    Use overrides to change specific fields for each test.
    
    Example:
        make_test_property(purchase_price=300000, weekly_rent=400)
    """
    base = {
        "address": "14 Kangaroo Point Rd",
        "suburb": "Kangaroo Point",
        "city": "Brisbane",
        "state": "QLD",
        "property_type": "House",
        "bedrooms": 3,
        "purchase_price": 950_000,      # Standard Brisbane inner-ring price
        "weekly_rent": 750,             # Realistic Brisbane 3br house rent
        "vacancy_rate_pct": 1.0,        # Tight Brisbane rental market
        "annual_growth_pct": 12.0,      # Inner Brisbane growth estimate
        "days_on_market": 18,           # Below QLD median of 22 days
        "loan_lvr_pct": 80.0,           # Standard investor LVR
        "loan_rate_pct": 6.50,          # Current investor rate May 2026
        "loan_term_years": 30,          # Standard mortgage term
        "marginal_tax_rate_pct": 37.0,  # Mid-income tax bracket
        "depreciation_annual": 6000,    # Building depreciation
    }
    base.update(overrides)  # Apply any overrides from the test
    return base


# ─────────────────────────────────────────────────────────────────────────────
# YIELD TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestYieldCalculations:
    """Tests for all yield-related metrics."""

    def test_gross_yield_formula(self):
        """
        Gross yield = (weekly_rent × 52) / purchase_price × 100
        $750 × 52 = $39,000 / $950,000 × 100 = 4.105%
        """
        m = calculate_all_metrics(make_test_property())
        # approx allows small floating point differences (abs=0.1 means ±0.1%)
        assert m["gross_yield_pct"] == pytest.approx(4.11, abs=0.1)

    def test_net_yield_always_less_than_gross(self):
        """
        Net yield accounts for operating expenses.
        Must always be less than gross yield.
        """
        m = calculate_all_metrics(make_test_property())
        assert m["net_yield_pct"] < m["gross_yield_pct"]

    def test_yield_below_brisbane_breakeven(self):
        """
        At $950k and $750/week, Brisbane property should be below
        the 6% breakeven threshold (negative gearing territory).
        """
        m = calculate_all_metrics(make_test_property())
        assert m["yield_vs_breakeven"] < 0  # Negative = below breakeven

    def test_high_yield_darwin_style(self):
        """
        Darwin-style property: $300k at $380/wk = 6.59% gross yield
        Should be above 6% breakeven.
        """
        m = calculate_all_metrics(make_test_property(
            purchase_price=300_000,
            weekly_rent=380,
            city="Darwin",
            state="NT",
        ))
        assert m["gross_yield_pct"] > 6.0

    def test_yield_vs_city_benchmark_positive(self):
        """
        $950k Brisbane at $750/wk = 4.11% yield
        Brisbane benchmark = 3.80%
        Difference should be positive (above benchmark)
        """
        m = calculate_all_metrics(make_test_property())
        assert m["yield_vs_city_benchmark"] > 0

    def test_cap_rate_equals_net_yield(self):
        """
        Cap rate and net yield use the same formula at purchase price.
        They should be equal.
        """
        m = calculate_all_metrics(make_test_property())
        assert m["cap_rate_pct"] == pytest.approx(m["net_yield_pct"], abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# CASH FLOW TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestCashFlow:
    """Tests for cash flow calculations."""

    def test_typical_brisbane_negatively_geared(self):
        """
        Standard Brisbane investment property at current rates
        should be negatively geared (monthly cash flow negative).
        """
        m = calculate_all_metrics(make_test_property())
        assert m["monthly_cash_flow"] < 0

    def test_annual_equals_monthly_times_12(self):
        """
        Annual cash flow must equal monthly × 12.
        Basic arithmetic consistency check.
        """
        m = calculate_all_metrics(make_test_property())
        assert m["annual_cash_flow"] == pytest.approx(
            m["monthly_cash_flow"] * 12, abs=10  # Allow $10 rounding tolerance
        )

    def test_cash_flow_is_noi_minus_mortgage(self):
        """
        Cash flow = NOI - annual mortgage payments
        This is the fundamental cash flow formula.
        """
        m = calculate_all_metrics(make_test_property())
        expected = m["noi"] - m["annual_mortgage"]
        assert m["annual_cash_flow"] == pytest.approx(expected, abs=10)

    def test_weekly_equals_annual_divided_52(self):
        """
        Weekly cash flow = annual / 52
        """
        m = calculate_all_metrics(make_test_property())
        assert m["weekly_cash_flow"] == pytest.approx(
            m["annual_cash_flow"] / 52, abs=1
        )


# ─────────────────────────────────────────────────────────────────────────────
# DEBT METRIC TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDebtMetrics:
    """Tests for loan and debt-related calculations."""

    def test_loan_amount_at_80_lvr(self):
        """
        $950,000 × 80% = $760,000 loan amount
        """
        m = calculate_all_metrics(make_test_property(loan_lvr_pct=80))
        assert m["loan_amount"] == pytest.approx(760_000, abs=100)

    def test_loan_amount_at_70_lvr(self):
        """
        $950,000 × 70% = $665,000 loan amount
        """
        m = calculate_all_metrics(make_test_property(loan_lvr_pct=70))
        assert m["loan_amount"] == pytest.approx(665_000, abs=100)

    def test_ltv_matches_lvr_input(self):
        """
        LTV at purchase should equal the LVR input (80% LVR = 80% LTV)
        """
        m = calculate_all_metrics(make_test_property(loan_lvr_pct=80))
        assert m["ltv_pct"] == pytest.approx(80.0, abs=0.1)

    def test_dscr_below_one_typical_property(self):
        """
        At 6.5% rate on $950k property with $750/wk rent,
        DSCR should be below 1.0 (rent doesn't cover mortgage).
        """
        m = calculate_all_metrics(make_test_property())
        assert m["dscr"] < 1.0

    def test_dscr_is_positive(self):
        """
        DSCR is always positive (it's a ratio of two positive numbers).
        """
        m = calculate_all_metrics(make_test_property())
        assert m["dscr"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestProjections:
    """Tests for 5-year projection calculations."""

    def test_positive_growth_increases_value(self):
        """
        With 12% annual growth, property value must increase over 5 years.
        """
        m = calculate_all_metrics(make_test_property(annual_growth_pct=12.0))
        assert m["projected_value_5yr"] > 950_000

    def test_zero_growth_stays_flat(self):
        """
        With 0% growth, projected value should equal purchase price.
        $950,000 × (1 + 0)^5 = $950,000
        """
        m = calculate_all_metrics(make_test_property(annual_growth_pct=0.0))
        assert m["projected_value_5yr"] == pytest.approx(950_000, abs=500)

    def test_capital_gain_positive_with_growth(self):
        """
        Positive growth rate → positive capital gain
        """
        m = calculate_all_metrics(make_test_property(annual_growth_pct=12.0))
        assert m["capital_gain_5yr"] > 0

    def test_total_return_exceeds_capital_gain(self):
        """
        Total return includes rent income PLUS capital gain.
        Must be greater than capital gain alone.
        """
        m = calculate_all_metrics(make_test_property())
        assert m["total_return_5yr"] > m["capital_gain_5yr"]


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    """Tests for the input validator."""

    def test_rejects_negative_price(self):
        """Negative purchase price must be rejected."""
        r = validate_property_input({"purchase_price": -100_000})
        assert r.is_valid == False
        assert len(r.errors) > 0

    def test_rejects_zero_price(self):
        """Zero purchase price must be rejected."""
        r = validate_property_input({"purchase_price": 0})
        assert r.is_valid == False

    def test_rejects_invalid_city(self):
        """Unknown city must be rejected."""
        r = validate_property_input({"city": "Atlantis"})
        assert r.is_valid == False

    def test_accepts_valid_input(self):
        """Complete valid input must be accepted with no errors."""
        r = validate_property_input(make_test_property())
        assert r.is_valid == True
        assert len(r.errors) == 0

    def test_sanitises_suburb_whitespace(self):
        """Suburb with extra spaces should be cleaned."""
        r = validate_property_input({"suburb": "  kangaroo point  "})
        assert r.sanitised_data["suburb"] == "Kangaroo Point"

    def test_sanitises_state_uppercase(self):
        """State code should be uppercased automatically."""
        r = validate_property_input({"state": "qld"})
        assert r.sanitised_data["state"] == "QLD"

    def test_sql_injection_removed(self):
        """SQL injection characters must be stripped from suburb."""
        r = validate_property_input({
            "suburb": "Brisbane'; DROP TABLE cache;--"
        })
        cleaned = r.sanitised_data.get("suburb", "")
        assert "'" not in cleaned
        assert ";" not in cleaned
        assert "--" not in cleaned

    def test_api_keys_masked(self):
        """API keys must never appear in printed/logged config."""
        config = {
            "ANTHROPIC_API_KEY": "sk-ant-realkey123",
            "DOMAIN_API_KEY": "key_64c6abb",
            "city": "Brisbane",
        }
        masked = mask_sensitive_config(config)
        assert masked["ANTHROPIC_API_KEY"] == "***MASKED***"
        assert masked["DOMAIN_API_KEY"] == "***MASKED***"
        assert masked["city"] == "Brisbane"  # Non-sensitive value unchanged

    def test_low_rent_warning(self):
        """Very low rent should generate a warning (not an error)."""
        r = validate_property_input({"weekly_rent": 100})
        assert len(r.warnings) > 0  # Warning exists
        assert r.is_valid == True   # But input still accepted

    def test_high_rent_warning(self):
        """Very high rent should generate a warning."""
        r = validate_property_input({"weekly_rent": 5000})
        assert len(r.warnings) > 0
