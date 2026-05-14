"""
property_analyst.py
===================
Layer 3 — AI Interpretation.

Takes 35 pre-calculated financial metrics and asks Claude Haiku
to interpret what they mean for an Australian property investor.

Architecture principle:
    Claude NEVER calculates anything here.
    Python already did all the maths in property_metrics.py.
    Claude ONLY interprets pre-calculated numbers.
    This keeps token usage minimal (~$0.001 per analysis).

Why Claude Haiku:
    Cheapest Claude model. Fast. Sufficient for structured JSON output.
    Interpretation does not require Sonnet or Opus.
    Cost at scale: 1000 analyses = ~$1.00
"""

import json                          # for parsing Claude's JSON response
import time                          # for measuring duration
from anthropic import Anthropic      # Anthropic Python SDK
from dotenv import load_dotenv       # for loading API key from .env
import os                            # for accessing environment variables

# Load API key from .env file
load_dotenv()


def analyse_property(
    property_input: dict,
    metrics: dict,
    data_sources: dict,
) -> dict:
    """
    Send pre-calculated metrics to Claude for investment interpretation.

    Args:
        property_input: Raw property data (address, price, etc.)
        metrics:        35 calculated metrics from property_metrics.py
        data_sources:   Source labels for each data point

    Returns:
        dict with recommendation, thesis, risks, confidence, and metadata
    """
    # Record start time so we can track how long analysis takes
    start_time = time.time()

    # Initialise Anthropic client — reads ANTHROPIC_API_KEY from environment
    client = Anthropic()

    # -- SYSTEM PROMPT --------------------------------------------------------
    # This defines Claude's role and response format.
    # Strict JSON-only instruction prevents Claude from adding prose.
    system_prompt = """You are a senior Australian property investment analyst.

You will receive pre-calculated financial metrics for a property.
DO NOT recalculate anything — every number has already been computed.
Your job is to interpret what the numbers mean for an investor.

Australian market context (May 2026):
- RBA cash rate: 4.10% (two hikes in 2026)
- Typical investor loan rate: 6.50%
- Breakeven gross yield: ~6.0% at 80% LVR
- National vacancy rate: 1.6% (decade avg 2.5%)
- Negative gearing: losses offset taxable income at marginal rate
- Brisbane Olympics 2032 infrastructure tailwind for inner suburbs

Respond ONLY with valid JSON. No preamble, no explanation, no markdown.
Just the raw JSON object. It must parse with json.loads() with no errors.

Required format:
{
  "recommendation": "buy" or "hold" or "avoid",
  "confidence": "high" or "medium" or "low",
  "one_line_summary": "max 15 words — the verdict a busy investor needs",
  "investment_thesis": "2 sentences max — the core argument for or against",
  "cash_flow_verdict": "1 sentence — is the negative carry acceptable given growth?",
  "top_3_positives": ["specific positive 1", "specific positive 2", "specific positive 3"],
  "top_3_risks": ["specific risk 1", "specific risk 2", "specific risk 3"],
  "key_metric_flags": {
    "yield_assessment": "1 line on yield vs benchmarks",
    "dscr_assessment": "1 line on what DSCR means for this investor",
    "growth_assessment": "1 line on whether 5yr gain justifies carry cost"
  }
}"""

    # -- USER PROMPT ----------------------------------------------------------
    # Pass ALL 35 metrics as context.
    # Structured clearly so Claude can reference exact numbers.
    # Data sources included so Claude can note confidence level.
    user_prompt = f"""Analyse this Australian investment property.

PROPERTY: {property_input.get('address')}, {property_input.get('suburb')}
PURCHASE PRICE: ${property_input.get('purchase_price', 0):,}
TYPE: {property_input.get('bedrooms')} bedroom {property_input.get('property_type', 'property')}

PRE-CALCULATED METRICS:

YIELD:
  Gross yield:          {metrics.get('gross_yield_pct')}%
  Net yield:            {metrics.get('net_yield_pct')}%
  Cap rate:             {metrics.get('cap_rate_pct')}%
  City benchmark:       {metrics.get('city_yield_benchmark_pct')}%
  vs city benchmark:    {metrics.get('yield_vs_city_benchmark'):+}%
  vs breakeven (6%):    {metrics.get('yield_vs_breakeven'):+}%

CASH FLOW:
  Annual:               ${metrics.get('annual_cash_flow'):,}
  Monthly:              ${metrics.get('monthly_cash_flow'):,}
  Weekly:               ${metrics.get('weekly_cash_flow'):,}
  After-tax annual:     ${metrics.get('after_tax_cash_flow'):,}
  Cash-on-cash return:  {metrics.get('cash_on_cash_return_pct')}%

DEBT:
  Loan amount:          ${metrics.get('loan_amount'):,}
  Monthly P&I:          ${metrics.get('monthly_mortgage'):,}
  DSCR:                 {metrics.get('dscr')} (>1.0 = rent covers mortgage)
  LTV:                  {metrics.get('ltv_pct')}%
  Debt yield:           {metrics.get('debt_yield_pct')}%

MARKET CONTEXT:
  Vacancy rate:         {property_input.get('vacancy_rate_pct')}%
  vs national (1.6%):   {metrics.get('vacancy_vs_national'):+}%
  Days on market:       {property_input.get('days_on_market')} days
  vs state median:      {metrics.get('dom_vs_state_median'):+} days
  GRM:                  {metrics.get('grm')}x

5-YEAR PROJECTION (@{property_input.get('annual_growth_pct')}% p.a.):
  Projected value:      ${metrics.get('projected_value_5yr'):,}
  Capital gain:         ${metrics.get('capital_gain_5yr'):,}
  Total return:         {metrics.get('total_return_5yr_pct')}% on cash invested

ACQUISITION:
  Total cash required:  ${metrics.get('total_cash_invested'):,}
  Stamp duty:           ${metrics.get('stamp_duty'):,}

DATA QUALITY: {metrics.get('data_quality_score', 'unknown')}
DATA SOURCES: {json.dumps(data_sources, indent=2)}"""

    # -- CLAUDE API CALL ------------------------------------------------------
    # Use Haiku — cheapest model, sufficient for structured interpretation
    # max_tokens=1000 is enough for the JSON response format
    response = client.messages.create(
        model="claude-haiku-4-5",        # Cheapest Claude model — ~$0.001 per call
        max_tokens=1000,                 # JSON response fits comfortably in 1000 tokens
        system=system_prompt,            # Defines Claude's role and output format
        messages=[
            {"role": "user", "content": user_prompt}  # The 35 metrics as context
        ]
    )

    # -- PARSE RESPONSE -------------------------------------------------------

    # Extract the text from Claude's response
    raw_response = response.content[0].text

    # Parse the JSON object even if Claude wraps it in extra text
    try:
        start = raw_response.find("{")            # Find the first JSON object boundary
        end = raw_response.rfind("}") + 1         # Find the last JSON object boundary
        json_str = raw_response[start:end]        # Extract only the JSON payload
        recommendation = json.loads(json_str)     # Parse JSON string to dict
    except json.JSONDecodeError as e:
        # If Claude returned invalid JSON (rare but possible), return a safe fallback
        recommendation = {
            "recommendation": "hold",
            "confidence": "low",
            "one_line_summary": "Analysis failed — JSON parse error",
            "investment_thesis": f"Could not parse Claude response: {e}",
            "cash_flow_verdict": "Unable to assess",
            "top_3_positives": ["Analysis unavailable"],
            "top_3_risks": ["JSON parse error — rerun analysis"],
            "key_metric_flags": {
                "yield_assessment": "unavailable",
                "dscr_assessment": "unavailable",
                "growth_assessment": "unavailable",
            }
        }

    # -- CALCULATE COST -------------------------------------------------------

    # Track token usage for cost reporting
    input_tokens = response.usage.input_tokens    # Tokens in the prompt
    output_tokens = response.usage.output_tokens  # Tokens in the response
    total_tokens = input_tokens + output_tokens

    # Haiku pricing May 2026: $0.80/M input, $4.00/M output (approximate)
    cost_usd = (input_tokens * 0.00000080) + (output_tokens * 0.00000400)

    # Calculate how long the analysis took
    duration_seconds = round(time.time() - start_time, 2)

    # -- RETURN COMPLETE RESULT ----------------------------------------------

    return {
        # The actual recommendation from Claude
        **recommendation,                          # Unpack all Claude's fields

        # Technical metadata for audit logging and cost tracking
        "model_used": "claude-haiku-4-5",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
        "duration_seconds": duration_seconds,
    }


def format_recommendation(property_input: dict, metrics: dict, rec: dict) -> str:
    """
    Format the Claude recommendation into a readable terminal report.
    Called after analyse_property() to display results.

    Args:
        property_input: Raw property data
        metrics:        Calculated metrics
        rec:            Claude's recommendation dict

    Returns:
        Formatted string ready to print
    """
    addr = f"{property_input.get('address')}, {property_input.get('suburb')}"
    verdict = rec.get('recommendation', '?').upper()
    confidence = rec.get('confidence', '?').upper()
    sep = "=" * 64

    # Build the positives list
    positives = rec.get('top_3_positives', [])
    positive_lines = "\n".join(f"    + {p}" for p in positives)

    # Build the risks list
    risks = rec.get('top_3_risks', [])
    risk_lines = "\n".join(f"    - {r}" for r in risks)

    # Build key metric flags
    flags = rec.get('key_metric_flags', {})

    return f"""
+{sep}+
|  INVESTMENT ANALYSIS: {addr[:42]:<42} |
+{sep}+
|  VERDICT: {verdict} ({confidence} confidence)
|  {rec.get('one_line_summary', '')[:60]}
+{sep}+
|  THESIS:
|  {rec.get('investment_thesis', '')[:120]}
+{sep}+
|  POSITIVES:
{positive_lines}
+{sep}+
|  RISKS:
{risk_lines}
+{sep}+
|  KEY METRICS:
|    Yield:  {flags.get('yield_assessment', '')[:55]}
|    DSCR:   {flags.get('dscr_assessment', '')[:55]}
|    Growth: {flags.get('growth_assessment', '')[:55]}
+{sep}+
|  CASH FLOW: {rec.get('cash_flow_verdict', '')[:52]}
+{sep}+
|  Cost: ${rec.get('cost_usd', 0):.4f}  |  Tokens: {rec.get('total_tokens', 0)}  |  Time: {rec.get('duration_seconds', 0)}s
+{sep}+
WARNING: Not financial advice. Educational purposes only.
    Always consult a licensed financial adviser."""


# ----------------------------------------------------------------------------
# STANDALONE TEST — tests Layer 3 in isolation
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    # Import metrics calculator for the test
    from property_metrics import calculate_all_metrics, SAMPLE_PROPERTIES

    print("\n PROPERTY ANALYST - Layer 3 Test")
    print("Sending pre-calculated metrics to Claude Haiku...\n")

    # Use first sample property
    test_prop = SAMPLE_PROPERTIES[0]

    # Calculate metrics (Layer 2)
    metrics = calculate_all_metrics(test_prop)
    metrics["data_quality_score"] = 0.75  # Simulate data quality score

    # Fake data sources for standalone test
    test_sources = {
        "rent_source": "USER_PROVIDED",
        "growth_source": "OFFICIAL: ABS RPPI 2021",
        "vacancy_source": "BENCHMARK: SQM May 2026",
    }

    # Get Claude's recommendation (Layer 3)
    print(f"Analysing: {test_prop['address']}...")
    rec = analyse_property(test_prop, metrics, test_sources)

    # Print formatted report
    print(format_recommendation(test_prop, metrics, rec))
