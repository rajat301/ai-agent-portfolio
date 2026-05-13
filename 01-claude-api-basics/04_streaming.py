# 04_streaming.py — streams Claude responses token by token instead of waiting for the full reply.
# Streaming matters in production: users see output immediately rather than staring at a blank screen.

from dotenv import load_dotenv  # reads .env and loads key=value pairs into os.environ
import os  # lets us read environment variables that dotenv loaded

load_dotenv()  # open the .env file in the project root and make all keys available to os.getenv()

import anthropic  # Anthropic SDK — provides both .create() (blocking) and .stream() (streaming)

api_key = os.getenv("ANTHROPIC_API_KEY")  # fetch the key from the environment; None if missing

if not api_key:  # stop early with a clear message rather than a cryptic SDK error
    raise ValueError("ANTHROPIC_API_KEY is not set — add it to your .env file")

if api_key == "your_key_here":  # catch the placeholder before wasting an API round-trip
    raise ValueError("ANTHROPIC_API_KEY is still the placeholder — replace it with your real key")

client = anthropic.Anthropic(api_key=api_key)  # create the client — all API calls go through this object

total_session_tokens = {"input": 0, "output": 0}  # mutable dict to track cumulative token usage across the whole session


def stream_response(messages: list, system_prompt: str = None) -> str:
    """Stream Claude's reply to the terminal chunk by chunk and return the full text when done."""

    print("\nClaude is thinking...\n")  # visual indicator so the user knows the request is in flight

    full_response = ""  # accumulate every chunk here so we can return the complete text at the end

    # client.messages.stream() opens a streaming connection and yields text chunks as they arrive.
    # Using `with` ensures the HTTP connection is cleanly closed when we exit the block.
    stream_kwargs = {  # build keyword arguments as a dict so we can conditionally add system_prompt
        "model": "claude-haiku-4-5-20251001",  # Haiku streams fast — good for showing real-time output
        "max_tokens": 2048,  # higher cap than earlier scripts because property answers can be detailed
        "messages": messages,  # the full conversation history so Claude has context
    }

    if system_prompt:  # only include the system key if a system prompt was actually provided
        stream_kwargs["system"] = system_prompt  # system sets Claude's persona and behaviour for the session

    with client.messages.stream(**stream_kwargs) as stream:  # open the streaming connection using our kwargs

        for chunk in stream.text_stream:  # text_stream is a generator that yields one text chunk per iteration
            print(chunk, end="", flush=True)  # end="" prevents newlines between chunks; flush=True forces immediate display
            full_response += chunk  # append this chunk to the running full text

    # After the `with` block closes the stream, get_final_message() returns the completed Message object.
    # It contains usage stats (token counts) that are only available once streaming is fully done.
    final_message = stream.get_final_message()  # retrieve the finished message with token usage data

    input_tokens = final_message.usage.input_tokens  # tokens consumed by our messages sent TO Claude
    output_tokens = final_message.usage.output_tokens  # tokens in Claude's response

    total_session_tokens["input"] += input_tokens  # add this call's input tokens to the running session total
    total_session_tokens["output"] += output_tokens  # add this call's output tokens to the running session total

    print("\n")  # newline after streaming ends so the next print starts on a fresh line
    print(f"  [tokens this message — input: {input_tokens:,}  output: {output_tokens:,}]")  # show per-message cost
    print(f"  [session total      — input: {total_session_tokens['input']:,}  output: {total_session_tokens['output']:,}]")  # show running total
    print()  # blank line before the next user prompt for visual breathing room

    return full_response  # return the complete text so the caller can store it in conversation history


def chat_with_streaming() -> None:
    """Run an interactive streaming chat loop with a property advisor persona."""

    # System prompts set Claude's role and behaviour for the entire conversation.
    # They are sent separately from the messages list and cannot be overridden by user messages.
    system_prompt = (  # multi-line string for readability
        "You are an expert Australian property investment advisor with 20 years of experience. "
        "You have deep knowledge of all Australian capital city and regional markets. "
        "Be detailed, specific, and thorough in your responses. "
        "Always include real suburb names, realistic figures, and practical next steps."
    )

    conversation_history = []  # grows with each turn; sending the full history gives Claude memory of prior messages

    print("=" * 60)  # top border of the welcome block
    print("  Claude Streaming Chat — Australian Property Advisor")  # title
    print("  Responses stream word by word in real time.")  # explain the feature to the user
    print("  Type 'quit' to exit.")  # tell the user how to stop
    print("=" * 60)  # bottom border of the welcome block
    print()  # blank line before the first prompt

    while True:  # keep looping until the user types 'quit'

        user_input = input("> ")  # display ">" prompt and wait for the user to type a message and press Enter

        if user_input.strip().lower() == "quit":  # strip() removes accidental leading/trailing spaces before checking
            break  # exit the while loop cleanly

        if not user_input.strip():  # ignore completely empty input — just re-show the prompt
            continue  # skip the rest of this iteration and go back to the top of the loop

        conversation_history.append(  # add the user's message to history BEFORE calling the API
            {"role": "user", "content": user_input}  # "user" role identifies our side of the conversation
        )

        # Call stream_response with the full history and the system prompt.
        # The function prints the response live as it streams, then returns the complete text.
        assistant_reply = stream_response(conversation_history, system_prompt=system_prompt)

        conversation_history.append(  # add Claude's reply to history so future turns have full context
            {"role": "assistant", "content": assistant_reply}  # "assistant" role identifies Claude's side
        )

    print()  # blank line before the exit summary
    print("─" * 60)  # separator above the session summary
    print(f"  Session ended.")  # confirm the chat is over
    print(f"  Total messages exchanged : {len(conversation_history)}")  # each turn adds 2 entries (user + assistant)
    print(f"  Total input tokens used  : {total_session_tokens['input']:,}")  # cumulative input cost
    print(f"  Total output tokens used : {total_session_tokens['output']:,}")  # cumulative output cost
    print("─" * 60)  # closing separator


chat_with_streaming()  # entry point — start the interactive chat when the script is run directly
