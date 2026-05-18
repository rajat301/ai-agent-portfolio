"""
Script 8 — LangGraph Foundations
==================================
The most important script in Week 2.

LangGraph is a stateful graph execution framework.
Every production AI agent in 2026 uses LangGraph because:
  - State flows through every node as a typed dict
  - Checkpoints persist state after every node — survive failures
  - Conditional edges branch based on state values
  - Human-in-the-loop interrupt gates are built in (Script 9)

Parts:
  1. Core concepts — State, Nodes, Edges, Conditional routing (3-node graph)
  2. Checkpointing — survive failures, resume from last good state
  3. Full property analysis agent — wraps Week 1 pipeline in LangGraph
  4. Why this matters — the production difference

LangGraph version: 1.2.0
"""

# ── Stdlib ────────────────────────────────────────────────────────────────────
import os           # read env, change working directory for Week 1 imports
import sys          # path manipulation, stdout encoding
import warnings     # suppress deprecation noise
from pathlib import Path          # resolve sibling-directory paths
from typing import TypedDict, List  # TypedDict = typed state dict, List = type hint

# Force UTF-8 on Windows — prevents encoding errors for box-drawing characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Suppress noisy LangChain/LangGraph deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ── Environment ───────────────────────────────────────────────────────────────
from dotenv import load_dotenv   # read .env into os.environ before anything else

# .env is at project root — two levels above this script
_ROOT = Path(__file__).parent.parent
_ENV_PATH = _ROOT / ".env"
load_dotenv(dotenv_path=_ENV_PATH)   # load first so every subsequent import sees the key

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("ERROR: ANTHROPIC_API_KEY not found. Check .env in project root.")
    sys.exit(1)

# ── Week 1 imports ─────────────────────────────────────────────────────────────
# Script lives in 02-langchain-langgraph/; Week 1 modules live in 01-claude-api-basics/
# sys.path.insert makes those modules importable by name.
# os.chdir fixes SuburbCache — it creates "data/suburb_cache.db" relative to CWD,
# so we must be in 01-claude-api-basics/ when data_fetcher is first imported.

WEEK1_PATH = _ROOT / "01-claude-api-basics"   # absolute path to Week 1 folder

if str(WEEK1_PATH) not in sys.path:
    sys.path.insert(0, str(WEEK1_PATH))   # let Python find data_fetcher, property_metrics, etc.

_original_cwd = os.getcwd()   # remember where we started so we can restore later
os.chdir(WEEK1_PATH)          # SuburbCache("data/suburb_cache.db") now resolves correctly

# Import Week 1 modules — order matters: data_fetcher must come first as it sets up the cache
try:
    from data_fetcher import fetch_all_data          # Layer 1: fetch + cache ABS/benchmark data
    from property_metrics import calculate_all_metrics, SAMPLE_PROPERTIES  # Layer 2: 35 metrics
    from property_analyst import analyse_property    # Layer 3: Claude Haiku interpretation
    from data.validator import validate_property_input  # input security/validation
    WEEK1_AVAILABLE = True  # flag Part 3 can proceed
except Exception as _import_err:
    print(f"Warning: Week 1 import failed ({_import_err}). Part 3 will be skipped.")
    WEEK1_AVAILABLE = False

os.chdir(_original_cwd)   # restore CWD so any file writes from here go to the right place

# ── LangGraph imports ─────────────────────────────────────────────────────────
from langgraph.graph import StateGraph, START, END
# StateGraph: the graph builder — add nodes, edges, compile
# START: virtual source node — first edge always comes FROM START
# END:   virtual sink node — the graph terminates when it reaches END

from langgraph.checkpoint.memory import MemorySaver
# MemorySaver: in-memory checkpoint store — saves state after every node
# In production: use SqliteSaver or RedisSaver for persistence across process restarts

# ── LangChain model (for Part 3 wrapper) ─────────────────────────────────────
from langchain_anthropic import ChatAnthropic   # Anthropic-backed LLM for Part 3 node

# Shared LLM instance — claude-haiku-4-5, cheapest model (same as Week 1 DECISIONS.md §2)
llm = ChatAnthropic(
    model="claude-haiku-4-5",
    temperature=0,
    anthropic_api_key=ANTHROPIC_API_KEY,
)

print("=" * 60)
print("Script 8 — LangGraph Foundations")
print("LangGraph 1.2.0 | Model: claude-haiku-4-5")
print("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — Core Concepts: State, Nodes, Edges, Conditional Routing
# ══════════════════════════════════════════════════════════════════════════════
# Build the simplest possible LangGraph to understand all 5 core concepts.
# This graph does one job: validate a property input, calculate yield, recommend.

print("\n" + "=" * 60)
print("PART 1 — Core Concepts (Hello LangGraph)")
print("=" * 60 + "\n")

# ── State definition ──────────────────────────────────────────────────────────
# State = a TypedDict that flows through every node.
# Every node reads from state and returns a dict of keys to update.
# Think of it as a shared whiteboard all nodes can read and write.

class PropertyState(TypedDict):
    """State shared across all nodes in the simple demo graph."""
    address: str           # property street address — display only
    purchase_price: float  # purchase price in AUD
    weekly_rent: float     # weekly rent in AUD
    gross_yield: float     # calculated gross yield as a percentage
    recommendation: str    # BUY / HOLD / AVOID — set by the final node
    messages: list         # conversation messages — for AI integration later
    error: str             # any error message — non-empty = validation failed


# ── Node 1: validate_input ────────────────────────────────────────────────────
# Nodes are plain Python functions: (state: TypedDict) -> dict
# The returned dict contains ONLY the keys that changed.
# LangGraph merges the returned dict into the current state.

def validate_input(state: PropertyState) -> dict:
    """Check that price and rent are positive before touching any API."""
    # Guard: reject zero or negative price — would produce a division-by-zero in yield calc
    if state["purchase_price"] <= 0:
        print(f"  >> validate_input: REJECTED — price must be > 0")
        return {"error": f"purchase_price must be > 0, got {state['purchase_price']}"}

    # Guard: reject zero or negative rent — meaningless yield result
    if state["weekly_rent"] <= 0:
        print(f"  >> validate_input: REJECTED — rent must be > 0")
        return {"error": f"weekly_rent must be > 0, got {state['weekly_rent']}"}

    # Both values are valid — print confirmation and return no changes (empty dict)
    print(f"  >> validate_input: OK — {state['address']} | "
          f"${state['purchase_price']:,.0f} | ${state['weekly_rent']}/wk")
    return {}   # empty dict = no state change needed


# ── Node 2: calculate_yield ───────────────────────────────────────────────────

def calculate_yield(state: PropertyState) -> dict:
    """Calculate gross rental yield from price and weekly rent."""
    # Gross yield = (annual rent / price) × 100
    # Annual rent = weekly × 52 weeks
    annual_rent = state["weekly_rent"] * 52
    gross_yield = (annual_rent / state["purchase_price"]) * 100
    print(f"  >> calculate_yield: {gross_yield:.2f}%  "
          f"(${annual_rent:,.0f} annual rent / ${state['purchase_price']:,.0f})")
    return {"gross_yield": round(gross_yield, 2)}   # update only gross_yield


# ── Node 3: make_recommendation ──────────────────────────────────────────────

def make_recommendation(state: PropertyState) -> dict:
    """Apply Brisbane benchmark thresholds to produce a buy/hold/avoid signal."""
    # Brisbane benchmarks from DECISIONS.md §7 and data/benchmarks.py
    # > 5.0%: above breakeven yield — positive cash flow possible
    # > 3.5%: above city gross yield benchmark (3.80%) — acceptable
    # <= 3.5%: below city benchmark — likely negative carry, avoid
    yield_pct = state["gross_yield"]
    if yield_pct > 5.0:
        rec = "BUY"     # above breakeven — positive carry potential
    elif yield_pct > 3.5:
        rec = "HOLD"    # above city benchmark — acceptable but watch cash flow
    else:
        rec = "AVOID"   # below city benchmark — poor yield relative to Brisbane
    print(f"  >> make_recommendation: {rec}  (yield {yield_pct:.2f}%)")
    return {"recommendation": rec}


# ── Build the graph ───────────────────────────────────────────────────────────
# StateGraph(State) creates a blank graph that passes PropertyState between nodes.

graph_1 = StateGraph(PropertyState)

# add_node(name, function) registers a node — name is used in edges and debug output
graph_1.add_node("validate", validate_input)
graph_1.add_node("calculate", calculate_yield)
graph_1.add_node("recommend", make_recommendation)

# add_edge(from, to) — unconditional: always go this way
graph_1.add_edge(START, "validate")    # graph always starts at validate
graph_1.add_edge("calculate", "recommend")  # if calculate completes, always go to recommend
graph_1.add_edge("recommend", END)     # after recommend, graph terminates

# add_conditional_edges(from, router_fn, route_map)
# router_fn receives current state and returns a key for route_map
# route_map maps that key to the next node name
graph_1.add_conditional_edges(
    "validate",
    # Router: if state["error"] is non-empty, stop — otherwise calculate yield
    lambda state: "stop" if state.get("error") else "continue",
    {"stop": END, "continue": "calculate"},  # "stop" → END kills the graph cleanly
)

# compile(checkpointer=...) locks the graph and prepares it for execution
# MemorySaver checkpoints state in RAM after every node — allows get_state() later
checkpointer_1 = MemorySaver()
app_1 = graph_1.compile(checkpointer=checkpointer_1)

# ── Run 1: Valid input ────────────────────────────────────────────────────────
print("--- Run 1: Valid input (14 Kangaroo Point Rd) ---\n")

valid_input: PropertyState = {
    "address": "14 Kangaroo Point Rd",
    "purchase_price": 950_000,
    "weekly_rent": 750,
    "gross_yield": 0.0,     # will be calculated by node 2
    "recommendation": "",   # will be set by node 3
    "messages": [],
    "error": "",
}

# config identifies this run — thread_id lets us retrieve the checkpoint later
cfg_valid = {"configurable": {"thread_id": "part1-valid-run"}}

result_1 = app_1.invoke(valid_input, config=cfg_valid)
print(f"\nFinal state:")
print(f"  Gross yield:     {result_1['gross_yield']:.2f}%")
print(f"  Recommendation:  {result_1['recommendation']}")
print(f"  Error:           '{result_1['error']}' (empty = no error)")

# ── Run 2: Invalid input (price = 0) ─────────────────────────────────────────
print("\n--- Run 2: Invalid input (price = 0) ---\n")

invalid_input: PropertyState = {
    "address": "Invalid Property",
    "purchase_price": 0,       # invalid — should trigger conditional edge to END
    "weekly_rent": 750,
    "gross_yield": 0.0,
    "recommendation": "",
    "messages": [],
    "error": "",
}

cfg_invalid = {"configurable": {"thread_id": "part1-invalid-run"}}
result_2 = app_1.invoke(invalid_input, config=cfg_invalid)

print(f"\nFinal state:")
print(f"  Recommendation:  '{result_2['recommendation']}' (empty = graph stopped early)")
print(f"  Error:           '{result_2['error']}'")
print(f"  Gross yield:     {result_2['gross_yield']} (never calculated — node never ran)")

print("\nPART 1 KEY LEARNING:")
print("  - State flows through every node as a shared typed dict")
print("  - Conditional edges branch based on any state value")
print("  - Invalid input stops the graph cleanly — no crash, no exception")
print("  - Every node does ONE thing: validate, calculate, OR recommend")

print("\n" + "=" * 60)
print("PART 1 COMPLETE")
print("=" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — Checkpointing: Survive Failures, Resume From Last Good State
# ══════════════════════════════════════════════════════════════════════════════
# This is the most important LangGraph feature.
# Production example from Script 7 Part 4:
#   Analyse 50 properties → fail at #23 → LangGraph: resume from #23
#   Without LangGraph: restart from #1, losing all prior work.

print("\n" + "=" * 60)
print("PART 2 — Checkpointing (Resume On Failure)")
print("=" * 60 + "\n")

# ── Add a failing node to the same graph ─────────────────────────────────────

def failing_node(state: PropertyState) -> dict:
    """Simulates a transient failure — network timeout, API rate limit, etc."""
    print("  >> failing_node: running... simulating network timeout")
    # Raise a realistic production error (API timeout, rate limit, DB unavailable)
    raise Exception("Network timeout — ABS API call failed after 30 seconds")

# Build graph 2: validate → calculate → FAIL → recommend
# The failing_node sits between calculate and recommend
graph_2 = StateGraph(PropertyState)
graph_2.add_node("validate", validate_input)
graph_2.add_node("calculate", calculate_yield)
graph_2.add_node("fail_node", failing_node)   # the node that will throw
graph_2.add_node("recommend", make_recommendation)

graph_2.add_edge(START, "validate")
graph_2.add_edge("calculate", "fail_node")    # calculate → fail_node (before recommend)
graph_2.add_edge("fail_node", "recommend")    # fail_node → recommend (never reached)
graph_2.add_edge("recommend", END)
graph_2.add_conditional_edges(
    "validate",
    lambda state: "stop" if state.get("error") else "continue",
    {"stop": END, "continue": "calculate"},
)

# SHARED checkpointer — both graph_2 and the recovery graph use the same memory store
# This is what allows the recovery run to access the failed run's checkpoint
shared_memory = MemorySaver()
app_2 = graph_2.compile(checkpointer=shared_memory)

# ── Step 1 + 2: Run until failure ─────────────────────────────────────────────
print("--- Step 1+2: Running graph with a failing node ---\n")

checkpoint_input: PropertyState = {
    "address": "14 Kangaroo Point Rd",
    "purchase_price": 950_000,
    "weekly_rent": 750,
    "gross_yield": 0.0,
    "recommendation": "",
    "messages": [],
    "error": "",
}
cfg_fail = {"configurable": {"thread_id": "checkpoint-demo-1"}}

try:
    # This will raise inside failing_node — we catch it here to continue the demo
    app_2.invoke(checkpoint_input, config=cfg_fail)
except Exception as exc:
    # Graph failed — but checkpoints for validate and calculate were already saved
    print(f"\n  GRAPH FAILED: {exc}")
    print("  (validate and calculate nodes completed and were checkpointed before the error)")

# ── Step 3: Inspect the saved checkpoint ──────────────────────────────────────
print("\n--- Step 3: Inspect checkpoint saved before the failure ---\n")

# get_state() retrieves the most recent checkpoint for this thread_id
# Even though the graph crashed, validate and calculate results were saved
saved = app_2.get_state(cfg_fail)

# saved.values is the state dict at the last successful checkpoint
gross_yield_saved = saved.values.get("gross_yield", "NOT FOUND")
next_nodes = saved.next   # which nodes LangGraph would run next

print(f"  Saved gross_yield:     {gross_yield_saved}%")
print(f"  Saved address:         {saved.values.get('address')}")
print(f"  Saved purchase_price:  ${saved.values.get('purchase_price'):,.0f}")
print(f"  Next node (pending):   {next_nodes}")
print()
print("  The graph failed but the yield calculation (4.11%) was saved.")
print("  In production: fix the error, resume from this point.")
print("  Without LangGraph: restart entire analysis from the beginning.")

# ── Step 4: Resume from checkpoint ───────────────────────────────────────────
print("\n--- Step 4: Resume from checkpoint (skip failing node) ---\n")

# update_state() lets us inject new state as if a node ran.
# as_node="fail_node" tells LangGraph: "fail_node completed with these values."
# After this call, the graph's 'next' pointer advances to "recommend".
# We pass the existing state values (fail_node made no changes — it's a no-op to fix).
app_2.update_state(
    cfg_fail,
    saved.values,           # same state values — fail_node was a no-op
    as_node="fail_node",    # pretend fail_node ran successfully
)

# Confirm the graph is now pointing at recommend
state_after_update = app_2.get_state(cfg_fail)
print(f"  Next node after update: {state_after_update.next}")
print("  (graph now pointing at 'recommend' — ready to resume)")

# invoke(None) means "resume from the current checkpoint, no new input"
# LangGraph uses the thread_id to find the checkpoint and continue execution
result_resumed = app_2.invoke(None, config=cfg_fail)

print(f"\n  RESUMED — Recommendation: {result_resumed['recommendation']}")
print(f"  Gross yield reused:       {result_resumed['gross_yield']}% (NOT recalculated)")
print()
print("PART 2 KEY LEARNING:")
print("  - MemorySaver checkpoints state after every successful node")
print("  - thread_id identifies a specific run — used to retrieve its checkpoint")
print("  - Failed runs save their progress up to the failure point")
print("  - update_state() + invoke(None) = resume from last good state")
print("  - Production impact: analyse 50 properties, fail at #23,")
print("    resume from #23 — not #1")

print("\n" + "=" * 60)
print("PART 2 COMPLETE")
print("=" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — Full Property Analysis Agent
# ══════════════════════════════════════════════════════════════════════════════
# Wraps the entire Week 1 3-layer pipeline (data → metrics → AI) as a
# LangGraph agent. Each layer becomes one node. Routing handles data quality.

print("\n" + "=" * 60)
print("PART 3 — Full Property Analysis Agent (Week 1 pipeline as LangGraph)")
print("=" * 60 + "\n")

if not WEEK1_AVAILABLE:
    print("Skipping Part 3 — Week 1 modules could not be imported.")
    print("Check that 01-claude-api-basics/ exists and packages are installed.\n")
else:
    # ── State definition ──────────────────────────────────────────────────────
    # State carries everything the pipeline needs across all 5 nodes.
    # Each node reads what it needs and writes back its results.

    class FullPropertyState(TypedDict):
        """State for the full 5-node property analysis agent."""
        property_input: dict    # raw property dict — from SAMPLE_PROPERTIES
        enriched_data: dict     # Layer 1 output from fetch_all_data()
        metrics: dict           # Layer 2 output from calculate_all_metrics()
        recommendation: dict    # Layer 3 output from analyse_property()
        data_quality: float     # 0.000–1.000 score from data_fetcher
        current_step: str       # label for the node that just ran (for logging)
        errors: list            # non-fatal errors accumulated during the run
        retry_count: int        # how many fetch retries have been attempted

    # ── Node 1: validate_node ─────────────────────────────────────────────────
    # Uses the Week 1 validator (data/validator.py) — same security layer as Script 5

    def validate_node(state: FullPropertyState) -> dict:
        """Validate property input using Week 1 validator before touching any API."""
        prop = state["property_input"]
        print(f"  >> [validate_node]  {prop.get('address')}, {prop.get('suburb')}")

        # Call the Week 1 validator — checks price, rent, city, state, LVR, etc.
        validation = validate_property_input(prop)

        if not validation.is_valid:
            # Validation failed — record errors but do NOT crash the graph
            new_errors = state.get("errors", []) + validation.errors
            print(f"     INVALID: {validation.errors}")
            return {"errors": new_errors, "current_step": "validate_FAILED"}

        # Validation passed — carry any warnings but proceed
        if validation.warnings:
            print(f"     warnings: {validation.warnings}")
        return {"current_step": "validate_OK"}

    # ── Node 2: fetch_data_node ───────────────────────────────────────────────
    # Calls Week 1 data_fetcher.fetch_all_data() — ABS RPPI + census + benchmarks

    def fetch_data_node(state: FullPropertyState) -> dict:
        """Fetch enriched property data — ABS RPPI, census demographics, benchmarks."""
        prop = state["property_input"]
        print(f"  >> [fetch_data_node]  fetching data for {prop.get('suburb')}...")

        try:
            # fetch_all_data implements cache-first — checks SQLite before hitting ABS
            # Data quality score: 0.35 (benchmark only) to 1.00 (all sources)
            enriched = fetch_all_data(prop)
            quality = enriched.get("data_quality_score", 0.35)
            print(f"     quality score: {quality:.2f} ({enriched.get('confidence')})")
            return {
                "enriched_data": enriched,
                "data_quality": quality,
                "current_step": "fetch_OK",
            }
        except Exception as err:
            # Fetch failed — record error but don't crash; quality_check will route around it
            new_errors = state.get("errors", []) + [f"fetch_data_node error: {err}"]
            print(f"     ERROR: {err}")
            return {
                "errors": new_errors,
                "data_quality": 0.0,
                "current_step": "fetch_FAILED",
            }

    # ── Node 3: quality_check_node ────────────────────────────────────────────
    # Conditional routing logic: retry low-quality fetches up to 2 times

    def quality_check_node(state: FullPropertyState) -> dict:
        """Decide whether data quality is good enough to proceed, or retry the fetch."""
        quality = state.get("data_quality", 0.0)
        retries = state.get("retry_count", 0)
        print(f"  >> [quality_check_node]  quality={quality:.2f}  retries={retries}")

        if quality < 0.5 and retries < 2:
            # Quality too low AND we haven't exhausted retries — try fetching again
            print(f"     quality below 0.5 — scheduling retry #{retries + 1}")
            return {"retry_count": retries + 1, "current_step": "quality_RETRY"}

        # Quality is acceptable, OR we've already retried twice — proceed to calculate
        print(f"     quality acceptable (or retries exhausted) — proceeding to calculate")
        return {"current_step": "quality_OK"}

    # ── Node 4: calculate_node ────────────────────────────────────────────────
    # Calls Week 1 calculate_all_metrics() — 35 pure Python metrics, zero API calls

    def calculate_node(state: FullPropertyState) -> dict:
        """Calculate all 35 financial metrics from enriched data — pure Python, no AI."""
        prop_input = state["property_input"]
        enriched = state.get("enriched_data", {})
        print(f"  >> [calculate_node]  calculating 35 metrics...")

        # Merge: enriched_data fields override property_input fields (better data wins)
        # Then overlay original property_input fields for any that enriched_data lacks
        merged = {**prop_input}   # start with original input

        # Overlay enriched fields — prefer live data where available
        for key in [
            "vacancy_rate_pct", "days_on_market", "annual_growth_pct",
            "investor_loan_rate_pct",
        ]:
            if enriched.get(key) is not None:
                merged[key] = enriched[key]

        # annual_growth_pct may be None if ABS RPPI failed — use input fallback
        if merged.get("annual_growth_pct") is None:
            merged["annual_growth_pct"] = prop_input.get("annual_growth_pct", 8.0)

        # investor_loan_rate maps to loan_rate_pct field name in calculate_all_metrics
        if "investor_loan_rate_pct" in merged and "loan_rate_pct" not in merged:
            merged["loan_rate_pct"] = merged["investor_loan_rate_pct"]

        try:
            # Layer 2: 35 deterministic financial metrics — NO AI, NO tokens
            # (see DECISIONS.md §4: "Python calculates what Python can calculate")
            metrics = calculate_all_metrics(merged)
            # Inject data quality score so Claude can calibrate confidence
            metrics["data_quality_score"] = state.get("data_quality", 0.35)
            print(f"     {len(metrics)} metrics calculated  "
                  f"(gross yield: {metrics.get('gross_yield_pct')}%)")
            return {"metrics": metrics, "current_step": "calculate_OK"}
        except Exception as err:
            new_errors = state.get("errors", []) + [f"calculate_node error: {err}"]
            print(f"     ERROR: {err}")
            return {"errors": new_errors, "current_step": "calculate_FAILED"}

    # ── Node 5: analyse_node ──────────────────────────────────────────────────
    # Calls Week 1 analyse_property() — Claude Haiku interprets pre-calculated metrics

    def analyse_node(state: FullPropertyState) -> dict:
        """Send 35 pre-calculated metrics to Claude Haiku for investment interpretation."""
        prop_input = state["property_input"]
        metrics = state.get("metrics", {})
        enriched = state.get("enriched_data", {})
        print(f"  >> [analyse_node]  sending metrics to Claude Haiku...")

        # Build data_sources dict — provenance labels for each key figure
        data_sources = {
            "rent_source":     enriched.get("weekly_rent_source", "USER_PROVIDED"),
            "growth_source":   enriched.get("annual_growth_source", "BENCHMARK"),
            "vacancy_source":  enriched.get("vacancy_source", "BENCHMARK"),
            "demo_source":     enriched.get("demographics_source", "NOT_FETCHED"),
        }

        try:
            # Layer 3: Claude interprets pre-calculated numbers — never calculates
            # (see DECISIONS.md §3: 3-layer architecture — Claude only in Layer 3)
            rec = analyse_property(prop_input, metrics, data_sources)
            verdict = rec.get("recommendation", "?").upper()
            confidence = rec.get("confidence", "?").upper()
            cost_usd = rec.get("cost_usd", 0)
            print(f"     verdict: {verdict} ({confidence} confidence)  "
                  f"cost: ${cost_usd:.4f}")
            return {"recommendation": rec, "current_step": "analyse_OK"}
        except Exception as err:
            new_errors = state.get("errors", []) + [f"analyse_node error: {err}"]
            print(f"     ERROR: {err}")
            # Return a safe fallback recommendation so the graph completes
            return {
                "recommendation": {
                    "recommendation": "hold",
                    "confidence": "low",
                    "one_line_summary": f"Analysis error: {err}",
                },
                "errors": new_errors,
                "current_step": "analyse_FAILED",
            }

    # ── Routing functions ─────────────────────────────────────────────────────

    def route_after_validate(state: FullPropertyState) -> str:
        """Stop graph if validation failed; proceed to fetch if valid."""
        if state.get("current_step") == "validate_FAILED":
            return "stop"    # → END
        return "fetch"       # → fetch_data_node

    def route_after_quality(state: FullPropertyState) -> str:
        """Retry fetch if quality low and retries available; otherwise calculate."""
        if state.get("current_step") == "quality_RETRY":
            return "retry"   # → fetch_data_node (loop back)
        return "calculate"   # → calculate_node

    def route_after_calculate(state: FullPropertyState) -> str:
        """Stop if calculate failed (bad data); otherwise analyse."""
        if state.get("current_step") == "calculate_FAILED":
            return "stop"    # → END (nothing useful to send Claude)
        return "analyse"     # → analyse_node

    # ── Build the full agent graph ────────────────────────────────────────────

    agent_graph = StateGraph(FullPropertyState)

    # Register all 5 nodes
    agent_graph.add_node("validate",      validate_node)
    agent_graph.add_node("fetch_data",    fetch_data_node)
    agent_graph.add_node("quality_check", quality_check_node)
    agent_graph.add_node("calculate",     calculate_node)
    agent_graph.add_node("analyse",       analyse_node)

    # Unconditional edges
    agent_graph.add_edge(START, "validate")           # always start with validation
    agent_graph.add_edge("fetch_data", "quality_check")  # fetch → always check quality
    agent_graph.add_edge("analyse", END)              # analyse is always the last node

    # Conditional edges — routing based on state values
    agent_graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"stop": END, "fetch": "fetch_data"},
    )
    agent_graph.add_conditional_edges(
        "quality_check",
        route_after_quality,
        {"retry": "fetch_data", "calculate": "calculate"},  # loop or advance
    )
    agent_graph.add_conditional_edges(
        "calculate",
        route_after_calculate,
        {"stop": END, "analyse": "analyse"},
    )

    # Compile with MemorySaver — checkpoints state after every node
    agent_checkpointer = MemorySaver()
    agent_app = agent_graph.compile(checkpointer=agent_checkpointer)

    # ── Run on all 3 SAMPLE_PROPERTIES ────────────────────────────────────────
    print("Running full pipeline on all 3 SAMPLE_PROPERTIES from Week 1...\n")

    for idx, prop in enumerate(SAMPLE_PROPERTIES, start=1):
        print(f"\n{'─' * 60}")
        print(f"  Property {idx}/3: {prop['address']}, {prop['suburb']}")
        print(f"{'─' * 60}")

        # Each property gets its own thread_id — separate checkpoints, no state bleed
        prop_config = {"configurable": {"thread_id": f"property-{idx}"}}

        # Build initial state — only property_input is populated; all other fields empty
        initial_state: FullPropertyState = {
            "property_input": prop,
            "enriched_data": {},
            "metrics": {},
            "recommendation": {},
            "data_quality": 0.0,
            "current_step": "init",
            "errors": [],
            "retry_count": 0,
        }

        try:
            final_state = agent_app.invoke(initial_state, config=prop_config)

            # Print the result summary
            rec = final_state.get("recommendation", {})
            metrics = final_state.get("metrics", {})
            errs = final_state.get("errors", [])

            print(f"\n  >> Node execution order: {final_state.get('current_step')}")
            print(f"  >> Data quality:  {final_state.get('data_quality', 0):.0%}")
            print(f"  >> Gross yield:   {metrics.get('gross_yield_pct', 'n/a')}%")
            print(f"  >> Cash flow/mo:  ${metrics.get('monthly_cash_flow', 0):,.0f}")
            print(f"  >> Verdict:       {rec.get('recommendation', '?').upper()} "
                  f"({rec.get('confidence', '?').upper()} confidence)")
            print(f"  >> Summary:       {rec.get('one_line_summary', '')}")
            if errs:
                print(f"  >> Errors:        {errs}")

        except Exception as exc:
            print(f"  Pipeline failed for property {idx}: {exc}")

    print()

print("\n" + "=" * 60)
print("PART 3 COMPLETE")
print("=" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# PART 4 — Why This Matters
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("PART 4 — Why This Matters (The Production Difference)")
print("=" * 60 + "\n")

print("""
LANGGRAPH vs LANGCHAIN — THE PRODUCTION DIFFERENCE
===================================================

What we built in Part 3:
  - State flows through every node as a typed dict
  - Each node does ONE thing (single responsibility principle)
  - quality_check_node routes to fetch_data_node on low quality — automatic retry
  - Errors accumulate in state["errors"] — graph never crashes
  - Every node logs current_step — full visibility into execution
  - Checkpointed: fails safely at any node, resumes from last good state

What a LangChain LCEL chain would do instead:
  - Run linearly — no branching, no quality-based retry
  - Failure = restart the entire chain from the beginning
  - No intermediate state — you see the final output or an exception
  - No retry logic without writing complex custom code around the chain

What clients pay $120-150/hr for:
  "Can it retry if the ABS API times out?"           YES — quality_check retries
  "Can we see what it did at each step?"             YES — current_step + errors
  "Can a human approve before the email goes out?"   YES — Script 9 (next)
  "Can it resume overnight if it crashes at 2am?"    YES — MemorySaver/SqliteSaver

─────────────────────────────────────────────────────────
The Week 2 stack:
─────────────────────────────────────────────────────────

  LangChain (Script 7)  →  components: prompts, parsers, tools, memory
  LangGraph (Script 8)  →  graph that orchestrates those components
                           with state, branching, retry, checkpointing
  Human-in-the-loop     →  Script 9: interrupt gate before sending outputs

─────────────────────────────────────────────────────────
LangGraph core concepts demonstrated this script:
─────────────────────────────────────────────────────────

  State      →  TypedDict shared across all nodes (single source of truth)
  Nodes      →  Plain Python functions: (state) -> partial_update_dict
  Edges      →  Wires node A output to node B input
  Conditional →  Branching: route based on any field in state
  Checkpoint  →  MemorySaver saves state after every node — resume on failure
  Compiled   →  app = graph.compile(checkpointer=...) produces the runnable

Next: Script 9 adds interrupt_before — human approval gates.
""")

print("=" * 60)
print("PART 4 COMPLETE")
print("=" * 60)

print("\n" + "=" * 60)
print("SCRIPT 8 COMPLETE — LangGraph Foundations")
print("  Part 1: 3-node graph — State, Nodes, Conditional edges")
print("  Part 2: MemorySaver checkpointing — survive failures, resume")
print("  Part 3: Full 5-node property agent — wraps Week 1 pipeline")
print("  Part 4: Production difference — LangGraph vs LangChain")
print("Next: Script 9 — LangGraph human-in-the-loop")
print("=" * 60 + "\n")
