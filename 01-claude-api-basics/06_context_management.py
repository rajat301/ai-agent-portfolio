"""
06_context_management.py
========================
Production context management strategies for Claude chat applications.

This script demonstrates two practical ways to keep long conversations cheap:
    1. Sliding window: keep only the newest messages.
    2. Summarisation: compress old messages into a compact memory.

The demo is a property investment assistant so the lesson stays connected to
the broader AI Property Analyser project.
"""

import os  # Read environment variables so API keys stay outside source code.
import time  # Add tiny pauses so the terminal output is easier to follow.
from anthropic import Anthropic  # Use the official Anthropic SDK for Claude calls.
from anthropic import APIError  # Catch Anthropic API failures without crashing.
from anthropic import APIConnectionError  # Catch network failures without crashing.
from dotenv import load_dotenv  # Load ANTHROPIC_API_KEY from the local .env file.

load_dotenv()  # Load .env before creating the client so the key is available.

MODEL_NAME = "claude-haiku-4-5"  # Use Haiku because this teaching demo needs cheap calls.
MAX_MESSAGES = 6  # Keep only the last 6 messages for the sliding-window strategy.
SUMMARISE_THRESHOLD = 8  # Summarise when the managed history reaches 8 messages.
KEEP_RECENT = 3  # Keep the newest 3 messages after summarising older context.

SYSTEM_PROMPT = (  # Store the system prompt separately so it is never trimmed.
    "You are a knowledgeable Australian property investment assistant. "
    "You help investors analyse properties in Australian capital cities. "
    "You remember details about the investor and properties discussed. "
    "Always reference specific numbers when discussing investments. "
    "Current market context: Brisbane vacancy 1.0%, RBA rate 4.10%, "
    "typical investor loan rate 6.50%, breakeven yield ~6%."
)  # End the prompt tuple so every Claude call gets stable business context.

SCRIPTED_MESSAGES = [  # Use fixed messages so the demo is repeatable without user input.
    "Hi, I'm Rajat. I'm a data engineer looking to invest in Brisbane property.",
    "I'm looking at a 3 bedroom house in Kangaroo Point for $950,000. Weekly rent is $750.",
    "What is the gross yield on that property?",
    "The vacancy rate in that suburb is 1.0%. How does that affect my analysis?",
    "I'm also considering 88 Logan Rd in Woolloongabba - $620k, $580/week rent, 2 bedrooms.",
    "Which property has better yield - Kangaroo Point or Woolloongabba?",
    "What are the main risks with Brisbane inner-city investment right now?",
    "Given everything we've discussed, which property would you recommend and why?",
    "What was the gross yield on the first property we discussed?",
    "Summarise the key investment thesis for both properties in 2 sentences each.",
]  # End scripted inputs after the memory-test and final synthesis turns.


def sliding_window(history: list, max_messages: int) -> list:
    """Keep only the newest messages while the system prompt remains separate."""
    if len(history) <= max_messages:  # If history is already small, do nothing.
        return history  # Return the original list because no context needs trimming.
    trimmed = history[-max_messages:]  # Keep the newest messages because they reflect current intent.
    return trimmed  # This is fast, but it loses older facts like names and first properties.


def count_tokens_estimate(history: list) -> int:
    """Estimate tokens cheaply by assuming one token is about four characters."""
    total_chars = 0  # Start at zero so every message contributes to the estimate.
    for message in history:  # Walk through each message in the managed conversation.
        total_chars += len(message.get("content", ""))  # Count content length because it drives token cost.
    return max(1, total_chars // 4)  # Divide by four so the estimate roughly matches LLM tokenization.


def _fallback_summary(history: list) -> str:
    """Build a local summary when Claude summarisation is unavailable."""
    joined = " ".join(message.get("content", "") for message in history)  # Combine old context for keyword checks.
    rajat = "Rajat" if "Rajat" in joined else "the investor"  # Preserve the investor name if it appears.
    properties = []  # Track properties found so the fallback still preserves useful context.
    if "Kangaroo Point" in joined:  # Detect the first property from the scripted conversation.
        properties.append("Kangaroo Point house at $950,000 renting for $750/week")  # Preserve key numbers.
    if "Woolloongabba" in joined:  # Detect the second property from the scripted conversation.
        properties.append("88 Logan Rd Woolloongabba at $620,000 renting for $580/week")  # Preserve key numbers.
    property_text = "; ".join(properties) if properties else "Brisbane investment properties"  # Avoid empty summaries.
    return (  # Return a compact memory sentence that can stand in for older messages.
        f"{rajat} is a data engineer assessing {property_text}. "
        "Important metrics discussed include gross yield, Brisbane vacancy at 1.0%, "
        "RBA cash rate at 4.10%, investor loan rates near 6.50%, and breakeven yield near 6%. "
        "The conversation is comparing yield, cash-flow risk, and capital-growth thesis."
    )  # End the fallback summary with the key decisions and numbers preserved.


def summarise_history(history: list, client: Anthropic) -> list:
    """Compress older history into one summary message and keep the newest turns."""
    old_history = history[:-KEEP_RECENT]  # Separate older context so only stale messages are summarised.
    recent_history = history[-KEEP_RECENT:]  # Keep recent messages verbatim so the next answer stays precise.
    before_tokens = count_tokens_estimate(history)  # Estimate cost before compression for the savings printout.
    summary_prompt = (  # Ask Claude for a focused production memory, not a generic summary.
        "Summarise this conversation in 3-4 sentences.\n"
        "Keep: investor name, properties discussed, key metrics mentioned, decisions made.\n\n"
        f"Conversation:\n{_history_to_text(old_history)}"
    )  # Include only older history so recent turns remain exact.
    try:  # Use a guarded API call because production assistants must not crash.
        response = client.messages.create(  # Call Claude Haiku because summarisation is a low-cost task.
            model=MODEL_NAME,  # Use the same cheap model for all calls in the demo.
            max_tokens=220,  # Keep the summary compact so future turns save tokens.
            system="You compress chat history into concise memory for a property investment assistant.",
            messages=[{"role": "user", "content": summary_prompt}],  # Send the summary task as one user message.
        )  # End the API call after Claude returns a summary block.
        summary_text = response.content[0].text.strip()  # Extract text so it can become the new memory message.
    except (APIConnectionError, APIError, Exception) as error:  # Catch broad failures to honour never-crash behaviour.
        summary_text = _fallback_summary(old_history)  # Use local fallback so the demo keeps running.
        print(f"WARNING: summarisation fallback used ({error.__class__.__name__})")  # Explain the graceful degradation.
    summary_message = {  # Create a compact user-side memory message for the next Claude call.
        "role": "user",  # Use user role so Anthropic message ordering remains simple and valid.
        "content": f"Conversation summary so far: {summary_text}",  # Label the summary so Claude treats it as memory.
    }  # End summary message construction.
    new_history = [summary_message] + recent_history  # Replace many old messages with one memory plus recent turns.
    after_tokens = count_tokens_estimate(new_history)  # Estimate cost after compression to show token savings.
    saved_pct = _saving_percent(before_tokens, after_tokens)  # Convert token reduction into a readable percentage.
    print(  # Print the trigger line so users can see when the strategy activates.
        f"*** SUMMARISING: {len(history)} messages -> 1 summary + {len(recent_history)} recent "
        f"(saves ~{saved_pct}%) ***"
    )  # End the summarisation status output.
    return new_history  # Return compact history so future requests stay cheap while preserving memory.


def _history_to_text(history: list) -> str:
    """Turn messages into plain text for the summarisation prompt."""
    lines = []  # Build a readable transcript so Claude can summarise accurately.
    for message in history:  # Convert each message into a role-prefixed line.
        role = message.get("role", "unknown").upper()  # Include role so the summary knows who said what.
        content = message.get("content", "")  # Pull content safely to avoid KeyError crashes.
        lines.append(f"{role}: {content}")  # Add one transcript line for this message.
    return "\n".join(lines)  # Join lines into one prompt-ready transcript.


def _saving_percent(before_tokens: int, after_tokens: int) -> int:
    """Calculate percentage saved while avoiding divide-by-zero errors."""
    if before_tokens <= 0:  # Guard against impossible zero-token inputs.
        return 0  # Return zero savings because there was nothing to compress.
    saved = 1 - (after_tokens / before_tokens)  # Compare new estimate against old estimate.
    return max(0, round(saved * 100))  # Clamp at zero so growth never prints negative savings.


def _assistant_fallback(user_message: str, history: list) -> str:
    """Return a deterministic answer when the Claude API is unavailable."""
    text = " ".join(message.get("content", "") for message in history)  # Combine history for simple memory checks.
    if "gross yield" in user_message.lower() and "first property" in user_message.lower():  # Handle memory test turn.
        return "The first property was Kangaroo Point: $750/week x 52 / $950,000 = 4.11% gross yield."  # Preserve key metric.
    if "better yield" in user_message.lower():  # Handle comparison question with exact arithmetic.
        return "Woolloongabba has the better gross yield: $580/week on $620k is 4.86%, versus Kangaroo Point at 4.11%."  # Compare yields.
    if "gross yield" in user_message.lower():  # Handle the first yield question.
        return "Kangaroo Point gross yield is $750 x 52 / $950,000 = 4.11%, below the ~6% breakeven yield."  # Give exact number.
    if "vacancy" in user_message.lower():  # Handle vacancy analysis.
        return "A 1.0% vacancy rate is tight versus the 1.6% national context, improving rent certainty but not fixing low yield."  # Link metric to decision.
    if "recommend" in user_message.lower():  # Handle recommendation question.
        return "I would prefer Woolloongabba for yield efficiency, but both depend on Brisbane growth because both sit below 6% breakeven."  # Provide decision.
    if "summarise" in user_message.lower():  # Handle final thesis request.
        return "Kangaroo Point is the premium growth case with 4.11% yield and tight vacancy. Woolloongabba is the stronger income case at 4.86% yield with lower entry price."  # Summarise both.
    if "Rajat" in text:  # Preserve name awareness when local fallback can see it.
        return "Rajat, I will keep comparing the Brisbane options using yield, vacancy, debt cost, and breakeven risk."  # Show memory.
    return "I can help compare Brisbane properties using rent, price, vacancy, loan rate, and breakeven yield."  # General safe fallback.


class ConversationManager:
    """Manage chat history using either sliding window or summarisation."""

    def __init__(self, strategy: str = "summarise") -> None:
        self.strategy = strategy  # Store the active strategy so chat() can apply the right policy.
        self.history = []  # Store managed conversation history sent to Claude.
        self.unmanaged_history = []  # Store full conversation for estimating what no management would cost.
        self.turn_count = 0  # Count user turns for reporting and demo progress.
        self.total_tokens_used = 0  # Track real API tokens when available and estimates otherwise.
        self.unmanaged_token_estimate = 0  # Track estimated cost if every turn sent full history.
        self.summaries_made = 0  # Count summary events to compare strategy overhead.
        self.client = Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None  # Create client only when a key exists.

    def chat(self, user_message: str) -> str:
        """Add a user message, manage context, call Claude, and return the assistant response."""
        self.turn_count += 1  # Increment first so printed turns match human numbering.
        user_entry = {"role": "user", "content": user_message}  # Wrap raw user text in Anthropic message format.
        self.history.append(user_entry)  # Add the message to managed history before strategy decisions.
        self.unmanaged_history.append(user_entry.copy())  # Add to full history for no-management comparison.
        self._apply_strategy()  # Trim or summarise before the expensive model call.
        response_text, tokens_used = self._call_claude(user_message)  # Ask Claude using the managed context.
        assistant_entry = {"role": "assistant", "content": response_text}  # Store assistant reply for future memory.
        self.history.append(assistant_entry)  # Add assistant reply to managed history.
        self.unmanaged_history.append(assistant_entry.copy())  # Add assistant reply to no-management estimate.
        self.total_tokens_used += tokens_used  # Accumulate real or estimated token cost for comparison.
        self.unmanaged_token_estimate += self._estimate_unmanaged_turn_cost()  # Estimate cost of sending full history.
        self._print_turn_status()  # Show history size and token estimate after each turn.
        return response_text  # Return response so the demo can print it.

    def _apply_strategy(self) -> None:
        """Apply the selected context management policy before each Claude call."""
        if self.strategy == "window":  # Sliding window uses deterministic message trimming.
            self.history = sliding_window(self.history, MAX_MESSAGES)  # Keep only the newest messages.
        elif self.strategy == "summarise":  # Summarisation compresses older context only when needed.
            if len(self.history) >= SUMMARISE_THRESHOLD:  # Trigger only once the history crosses the threshold.
                if self.client is None:  # If there is no API key, fallback summarisation still demonstrates strategy.
                    self.history = self._local_summarise()  # Compress locally so the script never crashes.
                else:  # If Claude is available, use real model summarisation.
                    self.history = summarise_history(self.history, self.client)  # Replace old turns with summary memory.
                self.summaries_made += 1  # Track how often compression occurred.

    def _local_summarise(self) -> list:
        """Compress history locally when no Claude client is available."""
        old_history = self.history[:-KEEP_RECENT]  # Select older messages for compression.
        recent_history = self.history[-KEEP_RECENT:]  # Preserve recent turns exactly.
        before_tokens = count_tokens_estimate(self.history)  # Estimate before compression for status output.
        summary_text = _fallback_summary(old_history)  # Build deterministic compact memory.
        summary_message = {"role": "user", "content": f"Conversation summary so far: {summary_text}"}  # Create memory message.
        new_history = [summary_message] + recent_history  # Replace old context with summary plus recent messages.
        after_tokens = count_tokens_estimate(new_history)  # Estimate after compression.
        saved_pct = _saving_percent(before_tokens, after_tokens)  # Convert saved estimate to percent.
        print(  # Print the same trigger line as the API summariser.
            f"*** SUMMARISING: {len(self.history)} messages -> 1 summary + {len(recent_history)} recent "
            f"(saves ~{saved_pct}%) ***"
        )  # End local summarisation status output.
        return new_history  # Return compacted history.

    def _call_claude(self, user_message: str) -> tuple[str, int]:
        """Call Claude with managed history, falling back gracefully on errors."""
        if self.client is None:  # If no API key exists, keep the demo usable.
            response_text = _assistant_fallback(user_message, self.history)  # Generate deterministic local answer.
            tokens_used = count_tokens_estimate(self.history) + count_tokens_estimate([{"content": response_text}])  # Estimate cost.
            return response_text, tokens_used  # Return fallback response and estimated tokens.
        try:  # Guard the network call so production code does not crash on API issues.
            response = self.client.messages.create(  # Send managed history to Claude.
                model=MODEL_NAME,  # Use cheap Haiku for all assistant responses.
                max_tokens=180,  # Keep the demo concise and cost-controlled.
                system=SYSTEM_PROMPT,  # Send stable instructions outside managed history.
                messages=self.history,  # Send only the managed conversation history.
            )  # End Claude call.
            response_text = response.content[0].text.strip()  # Extract assistant text for printing and memory.
            tokens_used = response.usage.input_tokens + response.usage.output_tokens  # Track actual billed tokens.
            return response_text, tokens_used  # Return successful model output.
        except (APIConnectionError, APIError, Exception) as error:  # Catch network, API, and unexpected failures.
            print(f"WARNING: assistant fallback used ({error.__class__.__name__})")  # Explain graceful fallback.
            response_text = _assistant_fallback(user_message, self.history)  # Keep the demo moving with local logic.
            tokens_used = count_tokens_estimate(self.history) + count_tokens_estimate([{"content": response_text}])  # Estimate cost.
            return response_text, tokens_used  # Return fallback output.

    def _estimate_unmanaged_turn_cost(self) -> int:
        """Estimate tokens if the full conversation had been sent this turn."""
        system_tokens = len(SYSTEM_PROMPT) // 4  # Include system prompt because every call sends it.
        history_tokens = count_tokens_estimate(self.unmanaged_history)  # Count all turns without trimming or summary.
        return system_tokens + history_tokens  # Return approximate no-management prompt cost.

    def _print_turn_status(self) -> None:
        """Print compact status after every turn."""
        est_tokens = count_tokens_estimate(self.history)  # Estimate managed history size after assistant reply.
        print(  # Show the exact progress format requested by the project brief.
            f"Turn {self.turn_count} | History: {len(self.history)} msgs | "
            f"Est. tokens: ~{est_tokens} | Strategy: {self.strategy}"
        )  # End turn status output.

    def results(self) -> dict:
        """Return metrics for the end-of-run comparison table."""
        avg_tokens = self.total_tokens_used // max(1, self.turn_count)  # Avoid divide-by-zero in defensive code.
        saved_pct = _saving_percent(self.unmanaged_token_estimate, self.total_tokens_used)  # Compare managed vs unmanaged.
        return {  # Return a dict so the caller can print consistent tables.
            "strategy": self.strategy,  # Include strategy name for headings.
            "total_turns": self.turn_count,  # Include total turns for sanity checking.
            "total_tokens_used": self.total_tokens_used,  # Include cumulative actual or estimated tokens.
            "avg_tokens_turn": avg_tokens,  # Include average cost per turn.
            "summaries_made": self.summaries_made,  # Include summary count for the summarise strategy.
            "final_history_length": len(self.history),  # Include final managed history size.
            "token_estimate_saved_pct": saved_pct,  # Include estimated savings versus unmanaged history.
        }  # End results dictionary.


def print_results_table(results: dict) -> None:
    """Print the requested per-strategy results table."""
    print("\n================================================")  # Open the results table with ASCII separators.
    print(f"CONTEXT MANAGEMENT RESULTS: {results['strategy']}")  # Name the strategy being reported.
    print("================================================")  # Separate heading from metrics.
    print(f"Total turns:          {results['total_turns']}")  # Show scripted turn count.
    print(f"Total tokens used:    {results['total_tokens_used']:,}")  # Show total token cost with commas.
    print(f"Avg tokens/turn:      {results['avg_tokens_turn']:,}")  # Show average cost per turn.
    print(f"Summaries made:       {results['summaries_made']}")  # Show compression count.
    print(f"Final history length: {results['final_history_length']} messages")  # Show retained memory size.
    print(f"Token estimate saved: ~{results['token_estimate_saved_pct']}% vs no management")  # Show savings.
    print("================================================")  # Close the results table.


def run_demo(strategy: str) -> dict:
    """Run the scripted property-investment conversation for one strategy."""
    manager = ConversationManager(strategy=strategy)  # Create an isolated manager for this strategy.
    print("\n" + "=" * 72)  # Open the strategy run with a clear separator.
    print(f"RUNNING DEMO: {strategy.upper()}")  # Label the current strategy.
    print("=" * 72)  # Close the heading separator.
    for index, message in enumerate(SCRIPTED_MESSAGES, 1):  # Walk through all scripted user turns.
        print(f"\nUSER {index}: {message}")  # Print the user message so the transcript is self-contained.
        reply = manager.chat(message)  # Send the message through the context manager and Claude.
        print(f"ASSISTANT {index}: {reply}")  # Print Claude or fallback response for inspection.
        time.sleep(0.1)  # Pause slightly so live terminal output is readable.
    results = manager.results()  # Collect run metrics after all turns complete.
    print_results_table(results)  # Print the requested per-strategy result table.
    return results  # Return metrics so the final comparison can choose a winner.


def print_final_comparison(window_results: dict, summary_results: dict) -> None:
    """Print the final side-by-side strategy comparison."""
    window_tokens = window_results["total_tokens_used"]  # Pull sliding-window total for readability.
    summary_tokens = summary_results["total_tokens_used"]  # Pull summarisation total for readability.
    winner = "Sliding Window" if window_tokens < summary_tokens else "Summarisation"  # Choose the lower-token strategy.
    print("\n================================================")  # Open final comparison table.
    print("STRATEGY COMPARISON")  # Print table title.
    print("================================================")  # Separate heading from rows.
    print(f"Sliding Window:   {window_tokens:,} total tokens")  # Show window total.
    print(f"Summarisation:    {summary_tokens:,} total tokens")  # Show summary total.
    print(f"Winner:           {winner}")  # Show lower-token winner for this run.
    print("")  # Add spacing before the teaching takeaway.
    print("Key learning:")  # Introduce the lesson.
    print("- Window: simple but loses early context")  # Explain window tradeoff.
    print("  (Claude may forget Rajat's name or the first property by later turns)")  # Connect to the memory test.
    print("- Summarise: more tokens upfront for summarisation")  # Explain summary tradeoff.
    print("  but preserves critical context across full conversation")  # Explain why summaries are valuable.
    print("================================================")  # Close final comparison table.


if __name__ == "__main__":  # Run the demo only when the script is executed directly.
    print("\nSCRIPT 6 - CONTEXT MANAGEMENT DEMO")  # Print the script title.
    print("Property investment chatbot with sliding window vs summarisation.")  # Explain what will run.
    window_results = run_demo("window")  # Run strategy 1 first as requested.
    summary_results = run_demo("summarise")  # Run strategy 2 second as requested.
    print_final_comparison(window_results, summary_results)  # Print final side-by-side comparison.
