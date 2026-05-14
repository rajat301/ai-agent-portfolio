"""
property_metrics.py
===================
Pure Python property investment calculator.
NO AI. NO API CALLS. NO TOKENS.

Takes enriched property data -> returns 35 real financial metrics.
These metrics are then passed to Claude for interpretation.

Architecture principle:
    Python calculates what Python can calculate.
    Claude interprets what requires intelligence.
    Never pay tokens for arithmetic.

Australian market benchmarks (May 2026):
    RBA cash rate: 4.10%
    Investor loan rate: ~6.50%
    Breakeven gross yield: ~6.0-6.5%
    National vacancy: 1.6% (decade avg 2.5%)
"""

# ─────────────────────────────────────────────────────────────────────────────
# MARKET BENCHMARKS — May 2026
# Source: Cotality HVI, SQM Research, RBA
# ─────────────────────────────────────────────────────────────────────────────

MARKET_BENCHMARKS = {
    "rba_cash_rate_pct": 4.10,               # RBA March 2026
    "typical_investor_loan_rate_pct": 6.50,  # Major bank average May 2026
    "national_gross_yield_pct": 3.59,        # Cotality HVI April 2026
    "breakeven_yield_pct": 6.00,             # Min yield for cash-flow neutral at 80% LVR
    "national_vacancy_rate_pct": 1.60,       # SQM Research May 2026
    "decade_avg_vacancy_pct": 2.50,          # SQM long-run average
    "national_annual_rent_growth_pct": 5.70, # Cotality May 2026
    "typical_mgmt_fee_pct": 8.50,            # % of gross rent — industry standard
    "typical_maintenance_pct": 1.50,         # % of property value annually
    "typical_insurance_annual": 2500,        # AUD — landlord insurance estimate
    "typical_council_rates_annual": 2000,    # AUD — varies by LGA
    "typical_water_rates_annual": 1200,      # AUD — varies by state
    "typical_buying_costs_pct": 2.00,        # Legal, inspection, misc
}

# Capital city gross yield benchmarks — Cotality HVI April 2026
CITY_YIELD_BENCHMARKS = {
    "Sydney": 3.10,
    "Melbourne": 3.30,
    "Brisbane": 3.80,
    "Adelaide": 4.30,
    "Perth": 4.20,
    "Darwin": 6.00,
    "Hobart": 4.30,
    "Canberra": 4.00,
}

# State days-on-market benchmarks — REA Market Insights April 2026
STATE_DOM_BENCHMARKS = {
    "QLD": 22,
    "NSW": 28,
    "VIC": 35,
    "WA": 9,
    "SA": 25,
    "TAS": 38,
    "NT": 45,
    "ACT": 30,
}


def _stamp_duty(price: float, state: str) -> float:
    """
    Estimate investor stamp duty by state.
    Simplified rates — actual duty varies by buyer type and concessions.
    Private function, used only inside calculate_all_metrics.
    """
    rates = {
        "QLD": 0.0450,
        "NSW": 0.0500,
        "VIC": 0.0550,
        "WA": 0.0440,
        "SA": 0.0400,
        "TAS": 0.0400,
        "NT": 0.0490,
        "ACT": 0.0450,
    }
    rate = rates.get(state.upper(), 0.045)  # Default 4.5% if state not found
    return price * rate  # Return dollar amount


def calculate_all_metrics(property_data: dict) -> dict:
    """
    Master calculation function.
    Input: property dict with raw data.
    Output: dict with 35 financial metrics — all labelled, all calculated.

    Required keys:
        purchase_price, weekly_rent, city, state,
        vacancy_rate_pct, annual_growth_pct, days_on_market,
        loan_lvr_pct, loan_rate_pct, loan_term_years,
        marginal_tax_rate_pct, depreciation_annual
    """
    p = property_data       # shorthand
    b = MARKET_BENCHMARKS   # shorthand

    # ── 1. INCOME ────────────────────────────────────────────────────────────

    # Gross annual rent — full year at asking rate, no vacancy
    gross_annual_rent = p["weekly_rent"] * 52

    # Weeks lost to vacancy per year based on local vacancy rate
    vacancy_weeks = (p["vacancy_rate_pct"] / 100) * 52

    # Effective rent — what you actually collect after vacancy periods
    effective_annual_rent = p["weekly_rent"] * (52 - vacancy_weeks)

    # ── 2. EXPENSES ──────────────────────────────────────────────────────────

    # Property management — percentage of rent collected (8.5% industry avg)
    mgmt_fee = effective_annual_rent * (b["typical_mgmt_fee_pct"] / 100)

    # Maintenance — 1.5% of property value annually (industry rule of thumb)
    maintenance = p["purchase_price"] * (b["typical_maintenance_pct"] / 100)

    # Fixed annual costs (insurance, council, water)
    insurance = b["typical_insurance_annual"]
    council_rates = b["typical_council_rates_annual"]
    water_rates = b["typical_water_rates_annual"]

    # Total operating expenses BEFORE mortgage payments
    total_operating_expenses = (
        mgmt_fee + maintenance + insurance + council_rates + water_rates
    )

    # Operating Expense Ratio — what % of rent goes to expenses
    oer_pct = (
        (total_operating_expenses / effective_annual_rent * 100)
        if effective_annual_rent > 0 else 0
    )

    # ── 3. NET OPERATING INCOME ──────────────────────────────────────────────

    # NOI = effective rent minus operating expenses, before mortgage
    # Foundation metric — used in cap rate, DSCR, debt yield calculations
    noi = effective_annual_rent - total_operating_expenses

    # ── 4. YIELD METRICS ─────────────────────────────────────────────────────

    # Gross yield — simple ratio of annual rent to purchase price
    # Ignores ALL costs — used for quick comparisons only
    gross_yield_pct = (gross_annual_rent / p["purchase_price"]) * 100

    # Net yield — after operating expenses, before mortgage
    # More accurate than gross for understanding true return
    net_yield_pct = (noi / p["purchase_price"]) * 100

    # Cap rate — NOI divided by price — unleveraged return
    # What you earn if you bought with cash, no mortgage
    cap_rate_pct = (noi / p["purchase_price"]) * 100

    # City benchmark for comparison — how does this property compare?
    city_benchmark_yield = CITY_YIELD_BENCHMARKS.get(p["city"], 3.80)

    # Positive = above city average, negative = below
    yield_vs_city_benchmark = gross_yield_pct - city_benchmark_yield

    # Positive = above national average
    yield_vs_national = gross_yield_pct - b["national_gross_yield_pct"]

    # Negative = below breakeven (property costs money to hold)
    # Breakeven ~6% at current 6.5% loan rate and 80% LVR
    yield_vs_breakeven = gross_yield_pct - b["breakeven_yield_pct"]

    # ── 5. DEBT & FINANCING ──────────────────────────────────────────────────

    # Loan amount based on LVR — how much the bank lends
    loan_amount = p["purchase_price"] * (p["loan_lvr_pct"] / 100)

    # Deposit — what comes out of your pocket at purchase
    deposit_required = p["purchase_price"] - loan_amount

    # Monthly interest rate — annual rate divided by 12
    monthly_rate = (p["loan_rate_pct"] / 100) / 12

    # Total number of monthly payments over loan term
    n_payments = p["loan_term_years"] * 12

    # Monthly principal + interest payment — standard amortisation formula
    # P&I formula: M = P × [r(1+r)^n] / [(1+r)^n - 1]
    if monthly_rate > 0:
        monthly_mortgage = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** n_payments
        ) / ((1 + monthly_rate) ** n_payments - 1)
    else:
        # Edge case: zero interest rate
        monthly_mortgage = loan_amount / n_payments

    # Annual mortgage payments — P&I
    annual_mortgage = monthly_mortgage * 12

    # Interest-only annual payment — for comparison
    annual_interest_only = loan_amount * (p["loan_rate_pct"] / 100)

    # DSCR: Debt Service Coverage Ratio
    # NOI divided by annual mortgage payments
    # > 1.0 = rent covers mortgage | < 1.0 = you top it up each month
    dscr = noi / annual_mortgage if annual_mortgage > 0 else 0

    # LTV: Loan-to-Value ratio — same as LVR at purchase
    ltv_pct = (loan_amount / p["purchase_price"]) * 100

    # Debt yield: NOI divided by loan amount
    # Lender's risk metric — higher = safer loan from lender perspective
    debt_yield_pct = (noi / loan_amount) * 100 if loan_amount > 0 else 0

    # ── 6. CASH FLOW ─────────────────────────────────────────────────────────

    # Annual cash flow — what lands in your account after ALL costs including mortgage
    annual_cash_flow = noi - annual_mortgage

    # Monthly cash flow — divide annual by 12
    monthly_cash_flow = annual_cash_flow / 12

    # Weekly cash flow — for comparison with weekly rent figures
    weekly_cash_flow = annual_cash_flow / 52

    # ── 7. ACQUISITION COSTS ─────────────────────────────────────────────────

    # Stamp duty — government tax on property purchase
    stamp_duty = _stamp_duty(p["purchase_price"], p.get("state", "QLD"))

    # Other buying costs — legal, building inspection, conveyancing
    buying_costs = p["purchase_price"] * (b["typical_buying_costs_pct"] / 100)

    # Total acquisition cost — everything needed to take ownership
    total_acquisition_cost = p["purchase_price"] + stamp_duty + buying_costs

    # Total cash required at settlement — deposit + all buying costs
    total_cash_invested = deposit_required + stamp_duty + buying_costs

    # ── 8. TAX METRICS ───────────────────────────────────────────────────────

    # Annual interest expense (for tax calculation)
    annual_interest_expense = loan_amount * (p["loan_rate_pct"] / 100)

    # Taxable rental income — rent minus interest, expenses, depreciation
    # Negative = tax loss (negative gearing) — ATO refunds this × tax rate
    taxable_rental_income = (
        effective_annual_rent
        - annual_interest_expense
        - total_operating_expenses
        - p.get("depreciation_annual", 0)  # Building depreciation deduction
    )

    # Tax impact — positive = extra tax owed | negative = tax refund
    tax_rate = p["marginal_tax_rate_pct"] / 100
    tax_impact = taxable_rental_income * tax_rate

    # After-tax cash flow — real money in/out after ATO is involved
    after_tax_cash_flow = annual_cash_flow - tax_impact

    # Cash-on-cash return — annual cash flow as % of cash invested
    # This is what you actually earn on YOUR money (not the bank's)
    cash_on_cash_return_pct = (
        (annual_cash_flow / total_cash_invested * 100)
        if total_cash_invested > 0 else 0
    )

    # ── 9. MARKET COMPARISON ─────────────────────────────────────────────────

    # Gross Rent Multiplier — price divided by gross annual rent
    # Lower = better value | how many years of rent to pay off the property
    grm = (
        p["purchase_price"] / gross_annual_rent
        if gross_annual_rent > 0 else 0
    )

    # Vacancy rate vs national benchmark — negative = tighter market
    vacancy_vs_national = p["vacancy_rate_pct"] - b["national_vacancy_rate_pct"]

    # Vacancy rate vs decade average — context for how unusual current market is
    vacancy_vs_decade_avg = p["vacancy_rate_pct"] - b["decade_avg_vacancy_pct"]

    # Days on market vs state median — negative = selling faster than average
    state_dom_benchmark = STATE_DOM_BENCHMARKS.get(p.get("state", "QLD"), 25)
    dom_vs_state_median = p["days_on_market"] - state_dom_benchmark

    # ── 10. 5-YEAR PROJECTIONS ───────────────────────────────────────────────

    # Projected property value using compound growth
    growth_rate = p["annual_growth_pct"] / 100
    projected_value_5yr = p["purchase_price"] * (1 + growth_rate) ** 5

    # Capital gain over 5 years
    capital_gain_5yr = projected_value_5yr - p["purchase_price"]

    # Total rent collected over 5 years (simplified, no rent growth)
    total_rent_5yr = effective_annual_rent * 5

    # Total return — capital gain plus rent income
    total_return_5yr = capital_gain_5yr + total_rent_5yr

    # Total return as % of cash invested — the real investor metric
    total_return_5yr_pct = (
        (total_return_5yr / total_cash_invested * 100)
        if total_cash_invested > 0 else 0
    )

    # ── ASSEMBLE AND RETURN ALL 35 METRICS ───────────────────────────────────

    return {
        # Income
        "gross_annual_rent": round(gross_annual_rent, 0),
        "effective_annual_rent": round(effective_annual_rent, 0),
        "vacancy_adjusted_weeks": round(vacancy_weeks, 1),

        # Yield
        "gross_yield_pct": round(gross_yield_pct, 2),
        "net_yield_pct": round(net_yield_pct, 2),
        "cap_rate_pct": round(cap_rate_pct, 2),
        "city_yield_benchmark_pct": city_benchmark_yield,
        "yield_vs_city_benchmark": round(yield_vs_city_benchmark, 2),
        "yield_vs_national_avg": round(yield_vs_national, 2),
        "yield_vs_breakeven": round(yield_vs_breakeven, 2),

        # Expenses & NOI
        "total_operating_expenses": round(total_operating_expenses, 0),
        "noi": round(noi, 0),
        "operating_expense_ratio_pct": round(oer_pct, 1),

        # Debt
        "loan_amount": round(loan_amount, 0),
        "deposit_required": round(deposit_required, 0),
        "monthly_mortgage": round(monthly_mortgage, 0),
        "annual_mortgage": round(annual_mortgage, 0),
        "dscr": round(dscr, 2),
        "ltv_pct": round(ltv_pct, 1),
        "debt_yield_pct": round(debt_yield_pct, 2),

        # Cash flow
        "annual_cash_flow": round(annual_cash_flow, 0),
        "monthly_cash_flow": round(monthly_cash_flow, 0),
        "weekly_cash_flow": round(weekly_cash_flow, 0),
        "after_tax_cash_flow": round(after_tax_cash_flow, 0),
        "cash_on_cash_return_pct": round(cash_on_cash_return_pct, 2),

        # Acquisition
        "stamp_duty": round(stamp_duty, 0),
        "total_acquisition_cost": round(total_acquisition_cost, 0),
        "total_cash_invested": round(total_cash_invested, 0),

        # Market comparison
        "grm": round(grm, 1),
        "vacancy_vs_national": round(vacancy_vs_national, 2),
        "vacancy_vs_decade_avg": round(vacancy_vs_decade_avg, 2),
        "state_dom_benchmark_days": state_dom_benchmark,
        "dom_vs_state_median": round(dom_vs_state_median, 0),

        # 5-year projections
        "projected_value_5yr": round(projected_value_5yr, 0),
        "capital_gain_5yr": round(capital_gain_5yr, 0),
        "total_return_5yr": round(total_return_5yr, 0),
        "total_return_5yr_pct": round(total_return_5yr_pct, 1),

        # Context passed to Claude for reference
        "breakeven_yield_pct": b["breakeven_yield_pct"],
        "rba_cash_rate_pct": b["rba_cash_rate_pct"],
    }


def format_metrics_summary(property_data: dict, metrics: dict) -> str:
    """
    Format calculated metrics into a readable terminal summary.
    Used for console output and debugging before passing to Claude.
    """
    addr = f"{property_data['address']}, {property_data['suburb']}"
    sep = "=" * 60
    return f"""
{sep}
  PROPERTY: {addr}
  Price: ${property_data['purchase_price']:,.0f}  |  Rent: ${property_data['weekly_rent']:,}/wk
{sep}

  YIELD
  Gross Yield:    {metrics['gross_yield_pct']:.2f}%  (city avg: {metrics['city_yield_benchmark_pct']:.2f}%)
  Net Yield:      {metrics['net_yield_pct']:.2f}%
  vs City:        {metrics['yield_vs_city_benchmark']:+.2f}%
  vs Breakeven:   {metrics['yield_vs_breakeven']:+.2f}%

  CASH FLOW
  Annual:   ${metrics['annual_cash_flow']:+,.0f}
  Monthly:  ${metrics['monthly_cash_flow']:+,.0f}
  After Tax: ${metrics['after_tax_cash_flow']:+,.0f}
  CoC Return: {metrics['cash_on_cash_return_pct']:.2f}%

  DEBT
  Loan: ${metrics['loan_amount']:,.0f}  |  Monthly P&I: ${metrics['monthly_mortgage']:,.0f}
  DSCR: {metrics['dscr']:.2f}  (>1.0 means rent covers mortgage)
  LTV:  {metrics['ltv_pct']:.1f}%

  MARKET
  Vacancy: {property_data['vacancy_rate_pct']:.1f}%  (national: 1.6%)
  DOM: {property_data['days_on_market']} days  (state median: {metrics['state_dom_benchmark_days']})
  GRM: {metrics['grm']:.1f}x

  5-YEAR PROJECTION (@{property_data['annual_growth_pct']}% p.a.)
  Projected Value: ${metrics['projected_value_5yr']:,.0f}
  Capital Gain:    ${metrics['capital_gain_5yr']:,.0f}
  Total Return:    {metrics['total_return_5yr_pct']:.1f}% on cash invested

  ACQUISITION
  Stamp Duty:    ${metrics['stamp_duty']:,.0f}
  Total Cash In: ${metrics['total_cash_invested']:,.0f}
{sep}"""


# ─────────────────────────────────────────────────────────────────────────────
# TEST DATA — Run standalone to verify calculations
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_PROPERTIES = [
    {
        "address": "14 Kangaroo Point Rd",
        "suburb": "Kangaroo Point",
        "city": "Brisbane",
        "state": "QLD",
        "property_type": "house",
        "bedrooms": 3,
        "purchase_price": 950_000,
        "weekly_rent": 750,
        "vacancy_rate_pct": 1.2,
        "annual_growth_pct": 12.0,
        "days_on_market": 18,
        "loan_lvr_pct": 80.0,
        "loan_rate_pct": 6.50,
        "loan_term_years": 30,
        "marginal_tax_rate_pct": 37.0,
        "depreciation_annual": 6000,
    },
    {
        "address": "88 Logan Rd",
        "suburb": "Woolloongabba",
        "city": "Brisbane",
        "state": "QLD",
        "property_type": "unit",
        "bedrooms": 2,
        "purchase_price": 620_000,
        "weekly_rent": 580,
        "vacancy_rate_pct": 1.0,
        "annual_growth_pct": 14.0,
        "days_on_market": 12,
        "loan_lvr_pct": 80.0,
        "loan_rate_pct": 6.50,
        "loan_term_years": 30,
        "marginal_tax_rate_pct": 37.0,
        "depreciation_annual": 9000,
    },
    {
        "address": "5 Newstead Ave",
        "suburb": "Newstead",
        "city": "Brisbane",
        "state": "QLD",
        "property_type": "house",
        "bedrooms": 4,
        "purchase_price": 1_100_000,
        "weekly_rent": 900,
        "vacancy_rate_pct": 1.5,
        "annual_growth_pct": 10.0,
        "days_on_market": 24,
        "loan_lvr_pct": 80.0,
        "loan_rate_pct": 6.50,
        "loan_term_years": 30,
        "marginal_tax_rate_pct": 45.0,
        "depreciation_annual": 7000,
    },
]

if __name__ == "__main__":
    print("\n PROPERTY METRICS CALCULATOR — Standalone Test")
    print("Pure Python. Zero AI. Zero tokens.\n")
    for prop in SAMPLE_PROPERTIES:
        metrics = calculate_all_metrics(prop)
        print(format_metrics_summary(prop, metrics))
        print(f"  {len(metrics)} metrics calculated. Ready for Claude.\n")
