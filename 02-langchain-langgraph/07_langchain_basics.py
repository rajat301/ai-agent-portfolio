"""
Script 7 — LangChain Basics
============================
Demonstrates what LangChain does and WHY it exists by reproducing
Week 1 patterns (Scripts 2, 3, 5, 6) in significantly fewer lines.

Parts:
  1. LCEL (LangChain Expression Language) — chain components with |
  2. LangChain Memory — automatic conversation history
  3. LangChain Tools — @tool decorator + bind_tools()
  4. Bridge to LangGraph — why LCEL alone is not enough for production

Versions:
  langchain:           1.3.0
  langchain-anthropic: 1.4.3
"""

# ── Stdlib ────────────────────────────────────────────────────────────────────
import os          # read env vars
import sys         # exit on fatal errors
import warnings    # suppress expected deprecation warnings from intentionally old patterns
from pathlib import Path  # resolve .env path relative to this file

# Force UTF-8 output on Windows — prevents UnicodeEncodeError for em-dashes, arrows, etc.
# Windows terminals default to CP1252 which cannot encode most Unicode characters.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Suppress LangChain deprecation warning for RunnableWithMessageHistory.
# We use it intentionally to demonstrate the pre-LangGraph pattern (Part 2),
# then explain in Part 4 why LangGraph persistence replaces it.
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")

# ── Third-party: env ──────────────────────────────────────────────────────────
from dotenv import load_dotenv  # load ANTHROPIC_API_KEY from .env

# ── LangChain core ────────────────────────────────────────────────────────────
from langchain_anthropic import ChatAnthropic           # Anthropic-backed LLM
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# ChatPromptTemplate: reusable prompt with named variables
# MessagesPlaceholder: slot where conversation history is injected
from langchain_core.output_parsers import StrOutputParser  # parse LLM output → plain string
from langchain_core.runnables import RunnableLambda         # wrap a lambda as an LCEL step
from langchain_core.tools import tool                       # @tool decorator
from langchain_core.messages import HumanMessage, ToolMessage  # message types for tool loop
from langchain_core.chat_history import InMemoryChatMessageHistory
# InMemoryChatMessageHistory: stores conversation turns in RAM (no DB needed)
from langchain_core.runnables.history import RunnableWithMessageHistory
# RunnableWithMessageHistory: wraps any chain to auto-inject + save history

# ── Pydantic — for structured output typing ───────────────────────────────────
from pydantic import BaseModel, Field  # pydantic v2 — defines type-safe output schemas

# ── Load environment ──────────────────────────────────────────────────────────
# .env lives at the project root (one level above this script's folder)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)  # silently no-ops if file missing

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    # Fatal: every LangChain call below needs this key
    print("ERROR: ANTHROPIC_API_KEY not found. Check .env in project root.")
    sys.exit(1)

# ── Shared LLM instance ───────────────────────────────────────────────────────
# claude-haiku-4-5: cheapest Claude model, fast, sufficient for all demos here
# temperature=0: deterministic output — same input always produces same output
llm = ChatAnthropic(
    model="claude-haiku-4-5",
    temperature=0,
    anthropic_api_key=ANTHROPIC_API_KEY,  # explicit; also picked up from env
)

print("=" * 60)
print("Script 7 — LangChain Basics")
print("Model: claude-haiku-4-5 | langchain 1.3.0 | langchain-anthropic 1.4.3")
print("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — LCEL: LangChain Expression Language
# ══════════════════════════════════════════════════════════════════════════════
# LCEL uses the | (pipe) operator to chain prompt → llm → parser.
# Internally: each component implements __or__ to pass output to the next.
# This is the same as Unix pipes: each stage reads stdin, writes stdout.

print("\n" + "=" * 60)
print("PART 1 — LCEL (LangChain Expression Language)")
print("=" * 60 + "\n")

# ── Chain 1: Simple Q&A ───────────────────────────────────────────────────────
print("--- Chain 1: Simple Q&A ---\n")

# Define a reusable prompt template with a named variable {question}
qa_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an Australian property investment expert. Be concise."),
    ("human", "{question}"),  # {question} filled at invoke() time
])

# LCEL chain: prompt formats the dict → llm calls Anthropic API → parser strips metadata
chain_1 = qa_prompt | llm | StrOutputParser()
# | is __or__: prompt.__or__(llm).__or__(parser) → a Runnable sequence
# invoke() runs the entire chain end-to-end in one call

result_1 = chain_1.invoke({"question": "What is gross rental yield and why does it matter?"})
print(f"Answer: {result_1}\n")
print("Week 1 equivalent: ~25 lines (build messages list, call client.messages.create,")
print("extract content[0].text manually).")
print("LangChain: 4 lines. LCEL handles message formatting, API call, and parsing.\n")

# ── Chain 2: Structured output (reproduces Script 5 / 05_structured_output.py) ──
print("--- Chain 2: Structured Output (Pydantic) ---\n")


# Define the expected output shape as a Pydantic model
class PropertyAnalysis(BaseModel):
    """Type-safe schema Claude must return — validated automatically."""
    address: str = Field(description="Full property address")
    gross_yield_pct: float = Field(description="Gross rental yield as a percentage")
    recommendation: str = Field(description="One of: buy / hold / avoid")
    one_line_reason: str = Field(description="Single sentence explaining the recommendation")


# with_structured_output tells the LLM to return JSON matching PropertyAnalysis
# Internally, LangChain-Anthropic uses tool_use mode — Claude is given the schema
# as a tool definition and forced to return a valid argument payload.
structured_llm = llm.with_structured_output(PropertyAnalysis)

struct_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an Australian property investment analyst. "
               "Analyse the property and return a structured assessment."),
    ("human", "Property: {property_details}"),
])

# chain: format prompt → call structured LLM → returns validated PropertyAnalysis object
chain_2 = struct_prompt | structured_llm

try:
    analysis = chain_2.invoke({
        "property_details": "14 Kangaroo Point Rd, Brisbane. "
                            "Purchase $950k. Weekly rent $750. "
                            "Vacancy rate 1.0%. City yield benchmark 3.80%."
    })
    # analysis is a real Python object — fields accessible via dot notation
    print(f"Address:         {analysis.address}")
    print(f"Gross yield:     {analysis.gross_yield_pct:.2f}%")
    print(f"Recommendation:  {analysis.recommendation}")
    print(f"Reason:          {analysis.one_line_reason}")
    print(f"\nType check: {type(analysis).__name__} — not a string, not a dict.")
except Exception as e:
    print(f"Chain 2 error: {e}")

print("\nWeek 1 equivalent: json.loads() + manual key extraction + KeyError handling.")
print("LangChain: with_structured_output() returns a validated Pydantic object.")
print("If Claude returns invalid JSON, LangChain raises ValidationError — not silent garbage.\n")

# ── Chain 3: Sequential chain (two steps in one pipeline) ────────────────────
print("--- Chain 3: Sequential Chain (extract → summarise) ---\n")

# Step 1 prompt: extract structured details from natural language
extract_prompt = ChatPromptTemplate.from_messages([
    ("system", "Extract property details from the user's natural language input. "
               "Output ONLY: suburb, bedrooms, price, weekly rent, and calculated "
               "gross yield. Be concise — 4–5 bullet points."),
    ("human", "Input: {property_input}"),
])

# Step 1 chain: natural language → extracted bullet points (plain string)
extract_chain = extract_prompt | llm | StrOutputParser()

# Step 2 prompt: generate investment summary from the extracted details
summarise_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an Australian property investment expert. "
               "Given extracted property details, provide a 2-sentence investment summary."),
    ("human", "Extracted details:\n{extracted_details}"),
])

# Step 2 chain: extracted details → investment summary (plain string)
summarise_chain = summarise_prompt | llm | StrOutputParser()

# Bridge between steps: Step 1 outputs a string; Step 2 expects a dict.
# RunnableLambda wraps the dict conversion so LCEL can pipe it.
# This is the "chain of thought" pattern — each step builds on the previous.
bridge = RunnableLambda(lambda text: {"extracted_details": text})

# Full sequential chain: input dict → extract → bridge → summarise → output string
full_chain = extract_chain | bridge | summarise_chain

property_input = (
    "I'm looking at a unit in Woolloongabba, 2 bedrooms, "
    "asking $620k, comparable rents around $580/week."
)

try:
    summary = full_chain.invoke({"property_input": property_input})
    print(f"Input:   {property_input}\n")
    print(f"Summary: {summary}")
except Exception as e:
    print(f"Chain 3 error: {e}")

print("\nComment: 'chain of thought' — Step 1 extracts facts, Step 2 interprets them.")
print("LCEL | operator wires them together; output of Step 1 is input of Step 2.\n")

print("\n" + "=" * 60)
print("PART 1 COMPLETE")
print("=" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — LangChain Memory (reproduces Script 2: 02_chat_with_memory.py)
# ══════════════════════════════════════════════════════════════════════════════
# Week 1 Script 2 built memory manually: appended dicts to a list, sliced for
# sliding window, counted tokens by hand.
# LangChain provides RunnableWithMessageHistory — it handles all of that.

print("\n" + "=" * 60)
print("PART 2 — LangChain Memory (reproduces Script 2)")
print("=" * 60 + "\n")

# Session store: maps session_id → InMemoryChatMessageHistory
# In production this would be a Redis or database-backed store
_session_store: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Return (or create) the message history for a given session."""
    if session_id not in _session_store:
        # First call for this session — start with an empty history
        _session_store[session_id] = InMemoryChatMessageHistory()
    return _session_store[session_id]


# Prompt includes a MessagesPlaceholder — this is where prior turns are injected
memory_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an Australian property investment expert helping an investor "
               "evaluate properties. Remember all details the investor shares."),
    MessagesPlaceholder(variable_name="history"),  # prior turns injected here automatically
    ("human", "{input}"),                          # current user message
])

# Base chain: prompt → llm → string parser
memory_chain = memory_prompt | llm | StrOutputParser()

# Wrap the chain with automatic history management:
# - Before invoke: fetches history from store and injects into {history}
# - After invoke: appends human message + AI response back to store
chain_with_history = RunnableWithMessageHistory(
    memory_chain,
    get_session_history,          # called with the session_id from config
    input_messages_key="input",   # which key in the invoke dict is the new human message
    history_messages_key="history",  # which placeholder in the prompt to fill
)

# Scripted conversation — no user input needed, same 4 turns as Script 2 demo
conversation_turns = [
    "Hi, I'm Rajat. I'm looking at Brisbane property.",
    "I'm considering Kangaroo Point — $950k purchase price, 3-bedroom house.",
    "What's the gross yield if rent is $750 per week?",
    "What's my name and what property are we discussing?",  # memory test turn
]

SESSION_ID = "rajat_brisbane_session"  # unique ID ties all turns to one history

print("Running scripted 4-turn conversation...\n")
final_response = ""

for turn_num, user_message in enumerate(conversation_turns, start=1):
    print(f"Turn {turn_num} — User: {user_message}")
    try:
        response = chain_with_history.invoke(
            {"input": user_message},
            # configurable dict tells RunnableWithMessageHistory which session to use
            config={"configurable": {"session_id": SESSION_ID}},
        )
        print(f"Turn {turn_num} — Claude: {response}\n")
        if turn_num == 4:
            final_response = response  # save Turn 4 response for memory test below
    except Exception as e:
        print(f"Turn {turn_num} error: {e}\n")

# Memory test: did Claude retain facts from Turns 1 and 2 when answering Turn 4?
remembered_name = "rajat" in final_response.lower()
remembered_property = "kangaroo point" in final_response.lower()

print("MEMORY TEST:")
print(f"  Did Claude remember Rajat's name?          {'YES' if remembered_name else 'NO'}")
print(f"  Did Claude remember Kangaroo Point?        {'YES' if remembered_property else 'NO'}")
print()
print("Week 1 equivalent: manual history list, slice for window, pass to API — ~40 lines.")
print("LangChain: RunnableWithMessageHistory handles fetch, inject, save automatically.")

print("\n" + "=" * 60)
print("PART 2 COMPLETE")
print("=" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — LangChain Tools (reproduces Script 3: 03_claude_with_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
# Week 1 Script 3 built tool schemas manually (JSON dicts), wrote an
# execute_tool() dispatcher, and ran the agentic loop by hand (~80 lines).
# LangChain @tool + bind_tools() reduces this to ~20 lines.

print("\n" + "=" * 60)
print("PART 3 — LangChain Tools (reproduces Script 3)")
print("=" * 60 + "\n")


@tool
def calculate_gross_yield(purchase_price: float, weekly_rent: float) -> str:
    """Calculate gross rental yield for an Australian investment property.

    Args:
        purchase_price: Full purchase price in AUD.
        weekly_rent: Weekly rental income in AUD.
    """
    # Annual rent = weekly × 52 weeks
    annual_rent = weekly_rent * 52
    # Gross yield = annual rent divided by purchase price, expressed as percentage
    # This is the standard formula used by all Australian property analysts
    yield_pct = (annual_rent / purchase_price) * 100
    return (
        f"Gross yield: {yield_pct:.2f}% "
        f"(annual rent ${annual_rent:,.0f} / purchase ${purchase_price:,.0f})"
    )


@tool
def calculate_monthly_cashflow(
    purchase_price: float,
    weekly_rent: float,
    loan_lvr_pct: float,
    loan_rate_pct: float,
) -> str:
    """Calculate monthly cash flow for an Australian investment property.

    Args:
        purchase_price: Full purchase price in AUD.
        weekly_rent: Weekly rental income in AUD.
        loan_lvr_pct: Loan-to-value ratio as a percentage (e.g. 80 for 80% LVR).
        loan_rate_pct: Annual interest rate as a percentage (e.g. 6.5 for 6.5%).
    """
    # Loan amount = purchase price × LVR fraction
    loan_amount = purchase_price * (loan_lvr_pct / 100)
    # Monthly interest-only repayment (standard for investment properties in Australia)
    monthly_interest = loan_amount * (loan_rate_pct / 100) / 12
    # Monthly rental income: weekly rent × 52 weeks ÷ 12 months
    monthly_rent = weekly_rent * 52 / 12
    # Property management fee: 8% of gross rent (typical Brisbane rate)
    management_fee = monthly_rent * 0.08
    # Body corporate / rates estimate: $300/month for a house (rough benchmark)
    holding_costs = 300
    # Net monthly cash flow = income minus all outgoings
    monthly_cashflow = monthly_rent - monthly_interest - management_fee - holding_costs
    return (
        f"Monthly cash flow: ${monthly_cashflow:,.0f}/month\n"
        f"  Gross rent:       ${monthly_rent:,.0f}/month\n"
        f"  Mortgage (I/O):  -${monthly_interest:,.0f}/month\n"
        f"  Mgmt fee (8%):   -${management_fee:,.0f}/month\n"
        f"  Holding costs:   -${holding_costs:,.0f}/month\n"
        f"  Loan amount:      ${loan_amount:,.0f} at {loan_rate_pct}% p.a."
    )


@tool
def get_brisbane_benchmark() -> str:
    """Get current Brisbane property market benchmarks (May 2026).

    Returns hardcoded SQM/Cotality/RBA benchmark figures for Brisbane.
    Source: data/benchmarks.py CITY_BENCHMARKS['brisbane'] — May 2026.
    """
    # Hardcoded benchmarks — same values as 01-claude-api-basics/data/benchmarks.py
    # Source: SQM Research May 2026, Cotality HVI May 2026, RBA March 2026
    return (
        "Brisbane May 2026 Benchmarks:\n"
        "  Vacancy rate:         1.0%  (national avg 1.6%) — landlord's market\n"
        "  City gross yield:     3.80% (Cotality HVI)\n"
        "  Breakeven yield:      6.00% (RBA cash rate 4.10% + bank margin)\n"
        "  RBA cash rate:        4.10% (held March 2026)\n"
        "  Investor loan rate:   6.50% (cash rate + 2.40% typical bank margin)\n"
        "  Median house price:   $850,000 (Domain Q1 2026)\n"
        "  Days on market:       22 days (REA April 2026) — fast-moving market"
    )


# Define the full list of tools — LangChain will generate JSON schemas automatically
# from the docstrings and type annotations above.
tools = [calculate_gross_yield, calculate_monthly_cashflow, get_brisbane_benchmark]

# Map tool name → tool object — used to dispatch tool calls in the loop below
tool_map = {t.name: t for t in tools}

# bind_tools: attaches the tool schemas to the LLM config.
# When invoked, Claude can now return tool_calls in its response.
# LangChain reads type hints + docstrings to build Anthropic-format tool schemas.
llm_with_tools = llm.bind_tools(tools)

question = (
    "I'm looking at 14 Kangaroo Point Rd, Brisbane. "
    "Purchase price $950,000, weekly rent $750, 80% LVR at 6.5% interest rate. "
    "Can you calculate the gross yield, monthly cash flow, and compare to Brisbane benchmarks?"
)

print(f"Question: {question}\n")
print("Running agentic tool loop...\n")

# ── Manual agentic loop ───────────────────────────────────────────────────────
# LangChain does NOT auto-execute tools — it surfaces tool_calls in the response.
# This loop: call LLM → execute any tools → feed results back → repeat until done.
# In LangGraph (Script 8) this loop is replaced by a graph with ToolNode.

messages = [HumanMessage(content=question)]  # start with just the user's question

max_iterations = 5   # safety cap — prevent infinite loops if Claude misbehaves
iteration = 0

try:
    while iteration < max_iterations:
        iteration += 1
        # Call the LLM (may return tool_calls, final text, or both)
        response = llm_with_tools.invoke(messages)
        messages.append(response)  # always add assistant response to history

        if not response.tool_calls:
            # No more tool calls — Claude is done, print the final answer
            print(f"Final answer:\n{response.content}\n")
            break

        # Execute each tool call Claude requested
        for tc in response.tool_calls:
            tool_name = tc["name"]    # e.g. "calculate_gross_yield"
            tool_args = tc["args"]    # e.g. {"purchase_price": 950000, "weekly_rent": 750}
            print(f"  [Tool called] {tool_name}({tool_args})")

            try:
                # tool_map lookup + .invoke() runs the Python function above
                tool_result = tool_map[tool_name].invoke(tool_args)
            except Exception as tool_err:
                tool_result = f"Tool error: {tool_err}"

            print(f"  [Tool result] {tool_result}\n")

            # ToolMessage wraps the result and links it back to the tool_call_id
            # Claude needs this linkage to know which tool_call each result answers
            messages.append(ToolMessage(
                content=str(tool_result),
                tool_call_id=tc["id"],  # must match the id Claude sent
            ))

except Exception as e:
    print(f"Tool loop error: {e}")

print("Week 1 equivalent: manual JSON tool schemas, execute_tool() dispatcher,")
print("agentic while-loop — ~80 lines.")
print("LangChain: @tool decorator + bind_tools() generates schemas automatically.")
print("Same result. ~20 lines. LangChain handles schema generation + dispatch.")

print("\n" + "=" * 60)
print("PART 3 COMPLETE")
print("=" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# PART 4 — The Bridge to LangGraph
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("PART 4 — Why LangGraph Exists (Bridge to Script 8)")
print("=" * 60 + "\n")

print("""
WHY LANGCHAIN IS NOT ENOUGH FOR PRODUCTION
==========================================

LangChain LCEL + manual tool loop (what we just used):
  - Linear execution only — runs top to bottom, no branching
  - No state persistence between runs — restart = lose everything
  - If it fails halfway, restart from step 1
  - No conditional logic — can't branch based on tool results
  - No human approval gates — Claude emails before you approve
  - Hard to debug — entire chain is one opaque call stack

LangGraph (Script 8):
  - Stateful graph execution — state is a typed dict passed between nodes
  - State persists across runs via checkpointing (SQLite, Redis, Postgres)
  - Resume from exact failure point — no data lost
  - Conditional edges — branch on any field in state (e.g. "is yield > 5%?")
  - Human-in-the-loop interrupt gates built in — pause graph, wait for approval
  - Full observability — every node, every state transition is inspectable

─────────────────────────────────────────────────────────
Real example: Analyse 50 properties → flag top 10 →
              email summary to investment committee
─────────────────────────────────────────────────────────

  LangChain LCEL:
    Runs linearly. Fails at property 23 (API timeout).
    Restart from property 1. All prior results lost.
    No approval gate — email fires automatically.
    No way to pause and say "wait for human sign-off."

  LangGraph:
    Fails at property 23. State checkpointed after property 22.
    Resume from property 23. Properties 1–22 preserved in state.
    Before email node: graph hits an interrupt gate.
    Human reviews the top-10 list and approves or edits.
    Email node only executes after explicit human approval.
    Full audit trail of every node execution in the checkpoint store.

─────────────────────────────────────────────────────────
The pattern every enterprise AI team uses in 2026:
─────────────────────────────────────────────────────────

  LangChain  →  components (prompts, parsers, tools, memory)
  LangGraph  →  the graph that orchestrates those components
               with state, branching, and human-in-the-loop

Script 7 (this script): LangChain components — DONE.
Script 8 (next session): LangGraph — build the graph.
""")

print("=" * 60)
print("PART 4 COMPLETE")
print("=" * 60)

print("\n" + "=" * 60)
print("SCRIPT 7 COMPLETE — LangChain Basics")
print("  Part 1: LCEL chains (Q&A, structured output, sequential)")
print("  Part 2: Automatic memory with RunnableWithMessageHistory")
print("  Part 3: @tool decorator + bind_tools() + manual agentic loop")
print("  Part 4: Why LangGraph replaces the manual loop for production")
print("Next: Script 8 — LangGraph foundations")
print("=" * 60 + "\n")
