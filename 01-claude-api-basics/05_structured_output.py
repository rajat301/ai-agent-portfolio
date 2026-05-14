# 05_structured_output.py — makes Claude return structured JSON instead of free-form prose.
# Structured output is the bridge between Claude and real systems: databases, dashboards, APIs.
# When Claude returns JSON, you can parse it with json.loads() and feed it directly into Databricks,
# a DataFrame, a REST API, or any downstream system without brittle string parsing.

from dotenv import load_dotenv  # reads .env and loads key=value pairs into os.environ
import os  # lets us read environment variables that dotenv loaded

load_dotenv()  # open the .env file in the project root and make all keys available to os.getenv()

import anthropic  # Anthropic SDK — the client that handles API calls to Claude
import json  # standard library module for parsing and writing JSON
import pathlib  # standard library module for creating folders and building file paths safely

api_key = os.getenv("ANTHROPIC_API_KEY")  # fetch the key from the environment; None if the variable is missing

if not api_key:  # stop early with a clear message rather than a cryptic SDK error
    raise ValueError("ANTHROPIC_API_KEY is not set — add it to your .env file")

if api_key == "your_key_here":  # catch the placeholder value before wasting an API round-trip
    raise ValueError("ANTHROPIC_API_KEY is still the placeholder — replace it with your real key")

client = anthropic.Anthropic(api_key=api_key)  # create the client — every API call goes through this object

# ---------------------------------------------------------------------------
# PART 1 — Single property analysis
# ---------------------------------------------------------------------------

def analyse_property(address: str, price: int, bedrooms: int, suburb: str) -> dict:
    """Send one property to Claude and get back a parsed JSON investment analysis."""

    # System prompts set Claude's persona and hard constraints for the whole request.
    # Telling Claude to return ONLY raw JSON (no markdown, no backticks) is critical —
    # if Claude wraps output in ```json ... ``` code fences, json.loads() will fail.
    system_prompt = (
        "You are a property investment analyst. "  # sets the expert persona Claude will adopt
        "Always respond with valid JSON only. "  # the key constraint — JSON or nothing
        "No explanation, no markdown, no backticks. "  # explicitly ban the three common wrappers
        "Just raw JSON."  # reinforce: the entire response body must be parseable by json.loads()
    )

    # Build the user message describing the property.
    # f-string interpolation embeds the function arguments so Claude sees real values, not placeholders.
    user_prompt = f"Analyse this property: {address}, {suburb}, ${price:,}, {bedrooms} bedrooms"

    # Describe the exact JSON schema Claude must return.
    # The more precise the field names and types in the prompt, the more consistent the output.
    schema_description = (
        " Return a JSON object with exactly these fields: "
        "address (string), "                           # the street address passed in
        "suburb (string), "                            # the suburb passed in
        "price (integer), "                            # the purchase price passed in
        "bedrooms (integer), "                         # the bedroom count passed in
        "rental_yield_estimate (float, percentage), "  # estimated gross rental yield e.g. 4.2
        "investment_score (integer 1-10), "            # 1 = terrible, 10 = exceptional
        "recommendation (string: buy or hold or avoid), "  # the analyst's verdict
        "one_line_reason (string)"                     # a single sentence justifying the score
    )

    full_user_prompt = user_prompt + schema_description  # combine property details with schema instructions

    print(f"  Analysing: {address}, {suburb} — ${price:,}, {bedrooms}br...")  # progress indicator before the API call

    response = client.messages.create(  # blocking API call — waits until Claude finishes the full response
        model="claude-haiku-4-5-20251001",  # Haiku is fast and cheap; ideal for batch processing many properties
        max_tokens=512,  # JSON analysis for one property is short — 512 is more than enough
        system=system_prompt,  # system is a separate top-level key, not part of the messages list
        messages=[  # messages list for this single-turn exchange; no history needed here
            {"role": "user", "content": full_user_prompt}  # one user message containing the property + schema
        ],
    )

    raw_text = response.content[0].text  # content is a list of blocks; [0] is the first (and only) text block

    # Even with a strong system prompt, Claude occasionally wraps JSON in ```json ... ``` code fences.
    # strip() removes leading/trailing whitespace first; then we check for a code fence and peel it off.
    # This defensive step keeps the pipeline working even when the model doesn't perfectly follow instructions.
    cleaned = raw_text.strip()  # remove any surrounding whitespace or newlines before inspection

    if cleaned.startswith("```"):  # Claude sometimes wraps JSON in ```json or plain ``` code fences
        lines = cleaned.splitlines()  # split into individual lines so we can drop the fence lines
        cleaned = "\n".join(lines[1:-1])  # drop the first line (```json) and the last line (```) keep the middle

    # json.loads() converts the cleaned JSON string into a Python dict.
    # If parsing still fails, we print the raw response so you can see exactly what Claude returned —
    # that makes debugging fast without needing to add temporary print statements.
    try:
        parsed = json.loads(cleaned)  # parse the cleaned JSON string into a Python dictionary
    except json.JSONDecodeError as e:
        print(f"\n  [ERROR] Could not parse JSON. Claude returned:\n{raw_text}\n")  # show the raw text for debugging
        raise e  # re-raise so the caller knows a property failed; avoids silently corrupt batch results

    return parsed  # return the dict so the caller can collect results, sort them, and save them


# ---------------------------------------------------------------------------
# PART 2 — Batch analysis
# ---------------------------------------------------------------------------

def analyse_batch(properties: list) -> list:
    """Analyse every property in the list and return results sorted by investment_score descending."""

    results = []  # accumulate each parsed dict here as we process properties one by one

    for prop in properties:  # iterate over the list; each element is a dict with address/price/bedrooms/suburb keys
        result = analyse_property(  # call the single-property function for each item
            address=prop["address"],      # unpack the address from the dict
            price=prop["price"],          # unpack the price from the dict
            bedrooms=prop["bedrooms"],    # unpack the bedroom count from the dict
            suburb=prop["suburb"],        # unpack the suburb from the dict
        )
        results.append(result)  # add this property's parsed analysis dict to the running list
        print(f"  Done. Score: {result.get('investment_score', '?')}/10 — {result.get('recommendation', '?')}")  # immediate feedback after each call
        print()  # blank line between properties for visual breathing room

    # Sort the collected results so the best investment opportunities appear at the top.
    # key=lambda r: r.get("investment_score", 0) extracts the score from each dict for comparison.
    # reverse=True makes it descending (highest score first).
    sorted_results = sorted(results, key=lambda r: r.get("investment_score", 0), reverse=True)

    return sorted_results  # return the ranked list so the caller can display and save it


# ---------------------------------------------------------------------------
# PART 3 — Save to file
# ---------------------------------------------------------------------------

def save_results(results: list, filepath: str) -> None:
    """Write the results list to a JSON file, creating the output folder if needed."""

    output_path = pathlib.Path(filepath)  # wrap the string in a Path object for safe cross-platform handling

    output_path.parent.mkdir(parents=True, exist_ok=True)  # create the output/ folder if it doesn't exist yet;
    # parents=True creates any missing intermediate directories; exist_ok=True suppresses the error if it already exists

    with open(output_path, "w", encoding="utf-8") as f:  # open the file for writing; encoding ensures safe Unicode handling
        json.dump(results, f, indent=2)  # write the list as pretty-printed JSON; indent=2 makes it human-readable

    print(f"  Results saved to: {output_path.resolve()}")  # resolve() converts the relative path to an absolute one for clarity


# ---------------------------------------------------------------------------
# MAIN BLOCK
# ---------------------------------------------------------------------------

properties_to_analyse = [  # define the three test properties as a list of dicts
    {"address": "14 Kangaroo Point Rd", "suburb": "Kangaroo Point", "price": 950000,  "bedrooms": 3},  # property 1
    {"address": "88 Logan Rd",          "suburb": "Woolloongabba",  "price": 620000,  "bedrooms": 2},  # property 2
    {"address": "5 Newstead Ave",       "suburb": "Newstead",       "price": 1100000, "bedrooms": 4},  # property 3
]

print("=" * 60)  # top border of the run header
print("  Claude Structured Output — Property Batch Analyser")  # script title
print("  Each property is analysed and returned as parsed JSON.")  # one-line description
print("=" * 60)  # bottom border of the run header
print()  # blank line before processing begins

ranked = analyse_batch(properties_to_analyse)  # run all three properties through Claude and get back sorted results

# Print a summary table so the user can immediately see rankings at a glance.
# Using plain "-" instead of the Unicode box-drawing character (U+2500) because
# Windows terminals default to cp1252 encoding which cannot render U+2500.
print("-" * 60)  # top border of the summary table
print(f"  {'Rank':<5} {'Address':<30} {'Score':>5} {'Rec':<8}")  # header row with fixed-width columns
print("-" * 60)  # separator below the header

for i, prop in enumerate(ranked, start=1):  # enumerate with start=1 gives human-readable rank numbers (1, 2, 3)
    address   = prop.get("address", "unknown")[:28]          # truncate long addresses to keep columns aligned
    score     = prop.get("investment_score", "?")             # pull the score; "?" guards against a missing key
    rec       = prop.get("recommendation", "?")               # pull the recommendation verdict
    print(f"  {i:<5} {address:<30} {score:>5} {rec:<8}")      # print one row with aligned columns

print("-" * 60)  # bottom border of the summary table
print()  # blank line before the save message

save_results(ranked, "output/property_analysis.json")  # write the ranked results to disk in the output/ folder

print()  # blank line after the save confirmation
print("  Done. Open output/property_analysis.json to see the full analysis.")  # final instruction for the user
