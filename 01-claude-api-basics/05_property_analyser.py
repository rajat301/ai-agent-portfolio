"""
05_property_analyser.py
=======================
Master script — wires all 3 layers together.

This is the full end-to-end property analysis pipeline:

    Layer 1: data_fetcher.py      → collect data (ABS API + benchmarks)
    Layer 2: property_metrics.py  → calculate 35 metrics (pure Python)
    Layer 3: property_analyst.py  → Claude interprets numbers (AI)

    Governance: logs/audit.py     → log every analysis permanently

Total cost per property: ~$0.001
Total time per property: ~4-6 seconds
"""

import time                              # for measuring total pipeline duration
import json                              # for saving results to file
import os                                # for file path handling
from dotenv import load_dotenv           # for loading API key

# Import all three layers
from data_fetcher import fetch_all_data           # Layer 1: data collection
from property_metrics import (                    # Layer 2: financial calculations
    calculate_all_metrics,
    format_metrics_summary,
    SAMPLE_PROPERTIES,
)
from property_analyst import (                    # Layer 3: AI interpretation
    analyse_property,
    format_recommendation,
)
from logs.audit import AuditLogger               # Governance: audit trail
from data.validator import validate_property_input  # Security: input validation

# Load environment variables (ANTHROPIC_API_KEY etc.)
load_dotenv()

# Initialise audit logger — creates logs/ directory if needed
audit = AuditLogger()


def run_full_analysis(property_input: dict) -> dict:
    """
    Run the complete 3-layer analysis pipeline for one property.

    Args:
        property_input: Dict with property details. Required:
            address, suburb, city, state, bedrooms, property_type,
            purchase_price, weekly_rent, loan_lvr_pct, loan_rate_pct,
            loan_term_years, marginal_tax_rate_pct, annual_growth_pct,
            vacancy_rate_pct, days_on_market, depreciation_annual

    Returns:
        Complete analysis dict with metrics + recommendation + metadata
    """
    pipeline_start = time.time()  # Track total pipeline duration

    print("\n" + "-" * 60)
    print(f"  ANALYSING: {property_input.get('address')}")
    print(f"  {property_input.get('suburb')}, {property_input.get('city')}")
    print(f"  Price: ${property_input.get('purchase_price', 0):,}")
    print("-" * 60)

    # -- STEP 1: VALIDATE INPUT ------------------------------------------------
    # Run validation BEFORE any API calls or calculations
    # Prevents bad data from corrupting results

    print("\n  Step 1/4: Validating input...")
    validation = validate_property_input(property_input)

    # Hard stop if input is invalid — never analyse bad data
    if not validation.is_valid:
        error_msg = f"Invalid input: {validation.errors}"
        print(f"  ✗ REJECTED: {error_msg}")
        audit.log_error("VALIDATION_ERROR", error_msg, property_input)
        raise ValueError(error_msg)

    # Print warnings but continue — unusual but not invalid
    for warning in validation.warnings:
        print(f"  ⚠️  WARNING: {warning}")

    # Use sanitised data from here on (cleaned + validated)
    property_input = validation.sanitised_data
    print("  ✓ Input validated")

    # -- STEP 2: COLLECT DATA --------------------------------------------------
    # Layer 1: fetch ABS growth data, benchmarks, cache results

    print("\n  Step 2/4: Collecting market data...")
    enriched_data = fetch_all_data(property_input)

    # Check if benchmarks need updating
    freshness = audit.check_benchmarks_freshness()
    if freshness.get("is_stale"):
        print(f"\n  ⚠️  {freshness['warning']}")

    print(f"  ✓ Data collected (quality: {enriched_data.get('data_quality_score', 0):.0%})")

    # -- STEP 3: CALCULATE METRICS --------------------------------------------
    # Layer 2: pure Python maths — 35 metrics, zero API cost

    print("\n  Step 3/4: Calculating 35 financial metrics...")

    merged_data = {**property_input, **enriched_data}
    metrics = calculate_all_metrics(merged_data)

    # Add data quality score to metrics dict so it's available everywhere
    metrics["data_quality_score"] = enriched_data.get("data_quality_score", 0.5)

    # Print the full metrics summary to terminal
    print(format_metrics_summary(enriched_data, metrics))
    print("  ✓ Metrics calculated (zero API cost)")


    # -- STEP 4: AI INTERPRETATION --------------------------------------------
    # Layer 3: Claude Haiku interprets the pre-calculated numbers

    print("\n  Step 4/4: Requesting Claude investment analysis...")

    # Build data sources summary for Claude's context
    data_sources = {
        "rent_source": enriched_data.get("weekly_rent_source", "unknown"),
        "growth_source": enriched_data.get("annual_growth_source", "unknown"),
        "vacancy_source": enriched_data.get("vacancy_source", "unknown"),
        "data_quality": enriched_data.get("data_quality_score", 0),
    }

    # Call Claude — passes 35 numbers, gets back structured recommendation
    recommendation = analyse_property(enriched_data, metrics, data_sources)

    print(f"  ✓ Analysis complete (${recommendation.get('cost_usd', 0):.4f})")

    # -- PRINT FINAL REPORT ----------------------------------------------------

    print(format_recommendation(enriched_data, metrics, recommendation))

    # -- LOG TO AUDIT TRAIL ----------------------------------------------------
    # Record everything permanently — never lose an analysis

    analysis_id = audit.log_analysis(
        property_input=enriched_data,
        metrics=metrics,
        recommendation=recommendation.get("recommendation", "unknown"),
        data_sources=data_sources,
        model_used=recommendation.get("model_used", "claude-haiku-4-5"),
        tokens_used=recommendation.get("total_tokens", 0),
        cost_usd=recommendation.get("cost_usd", 0),
        duration_seconds=round(time.time() - pipeline_start, 2),
    )

    print(f"\n  📋 Logged: analysis_id={analysis_id}")

    # -- BUILD AND RETURN COMPLETE RESULT --------------------------------------

    result = {
        # Property details
        "analysis_id": analysis_id,
        "address": enriched_data.get("address"),
        "suburb": enriched_data.get("suburb"),
        "purchase_price": enriched_data.get("purchase_price"),

        # Key metrics (subset of all 35)
        "gross_yield_pct": metrics["gross_yield_pct"],
        "monthly_cash_flow": metrics["monthly_cash_flow"],
        "dscr": metrics["dscr"],
        "projected_value_5yr": metrics["projected_value_5yr"],
        "capital_gain_5yr": metrics["capital_gain_5yr"],
        "total_return_5yr_pct": metrics["total_return_5yr_pct"],

        # All metrics (for saving to file)
        "all_metrics": metrics,

        # AI recommendation
        "recommendation": recommendation.get("recommendation"),
        "confidence": recommendation.get("confidence"),
        "one_line_summary": recommendation.get("one_line_summary"),
        "investment_thesis": recommendation.get("investment_thesis"),
        "top_3_positives": recommendation.get("top_3_positives"),
        "top_3_risks": recommendation.get("top_3_risks"),
        "cash_flow_verdict": recommendation.get("cash_flow_verdict"),

        # Metadata
        "data_quality_score": metrics["data_quality_score"],
        "data_sources": data_sources,
        "cost_usd": recommendation.get("cost_usd"),
        "total_duration_seconds": round(time.time() - pipeline_start, 2),

        # Legal
        "disclaimer": "Not financial advice. Educational purposes only.",
    }

    return result


def run_batch_analysis(properties: list) -> list:
    """
    Analyse multiple properties and print a comparison table.

    Args:
        properties: List of property input dicts

    Returns:
        List of complete analysis results
    """
    results = []       # Will hold all analysis results
    total_cost = 0.0   # Track total API cost for the batch

    print(f"\n{'='*60}")
    print(f"  BATCH ANALYSIS - {len(properties)} properties")
    print(f"{'='*60}")

    # Analyse each property in sequence
    for i, prop in enumerate(properties, 1):
        print(f"\n  Property {i} of {len(properties)}")
        try:
            result = run_full_analysis(prop)
            results.append(result)
            total_cost += result.get("cost_usd", 0)
        except ValueError as e:
            # Validation failed — log and skip this property
            print(f"  ✗ SKIPPED: {e}")
            results.append({
                "address": prop.get("address"),
                "recommendation": "ERROR",
                "error": str(e)
            })

    # -- COMPARISON TABLE ------------------------------------------------------

    print(f"\n{'='*60}")
    print("  BATCH COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"  {'#':<3} {'Property':<25} {'Rec':<7} {'Conf':<7} {'Monthly CF':<12} {'5yr Gain'}")
    print(f"  {'-'*3} {'-'*25} {'-'*7} {'-'*7} {'-'*12} {'-'*10}")

    # Print one row per property
    for i, r in enumerate(results, 1):
        if r.get("recommendation") == "ERROR":
            print(f"  {i:<3} {r.get('address', 'unknown')[:25]:<25} ERROR")
            continue

        # Format each field — handle missing data gracefully
        addr = (r.get("address") or "")[:25]
        rec = (r.get("recommendation") or "?").upper()[:6]
        conf = (r.get("confidence") or "?").upper()[:6]
        cf = f"${r.get('monthly_cash_flow', 0):+,.0f}"
        gain = f"${r.get('capital_gain_5yr', 0):,.0f}"

        print(f"  {i:<3} {addr:<25} {rec:<7} {conf:<7} {cf:<12} {gain}")

    print(f"\n  Total API cost: ${total_cost:.4f}")
    print(f"  Avg cost/property: ${total_cost/len(results):.4f}")

    # -- SAVE RESULTS TO FILE --------------------------------------------------

    output_file = "output/property_analysis.json"
    os.makedirs("output", exist_ok=True)  # Create output folder if needed

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)  # default=str handles non-serialisable types

    print(f"\n  Results saved: {output_file}")

    return results


# ----------------------------------------------------------------------------
# MAIN - Run analysis on all 3 sample properties
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  PROPERTY ANALYSER - Full 3-Layer Pipeline")
    print("  Layer 1: Data -> Layer 2: Metrics -> Layer 3: Claude AI")
    print("=" * 60)

    # Run batch analysis on all 3 sample properties
    results = run_batch_analysis(SAMPLE_PROPERTIES)

    # Print audit summary
    print("\n" + "-" * 60)
    summary = audit.get_summary(last_n_days=1)  # Today's analyses
    print(f"  SESSION SUMMARY")
    print(f"  Analyses run:    {summary['total_analyses']}")
    print(f"  Recommendations: {summary['recommendations']}")
    print(f"  Total cost:      ${summary['total_cost_usd']:.4f}")
    print("-" * 60)
