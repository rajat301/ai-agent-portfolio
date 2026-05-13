# 03_claude_with_tools.py — agent loop that lets Claude call real tools to answer questions

import sys  # sys.path manipulation lets Python find our local tools/ and schemas/ packages
import os  # reads environment variables loaded by dotenv

# Add the directory containing this script to Python's search path.
# Without this, `import tools` would fail because Python wouldn't know where to look.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # insert this script's folder at the front of sys.path

from dotenv import load_dotenv  # reads .env files and loads key=value pairs into os.environ
import anthropic  # Anthropic SDK — the library that communicates with Claude

from tools import get_current_time, calculate  # import our two tool functions from the tools package
from schemas import TOOL_SCHEMAS  # import the list of tool JSON schemas we'll pass to Claude

load_dotenv()  # open the .env file in the project root and load all key=value pairs into the environment

api_key = os.getenv("ANTHROPIC_API_KEY")  # fetch the API key; returns None if it was never set

if not api_key:  # stop immediately if the key is completely absent — avoids a confusing SDK error
    raise ValueError("ANTHROPIC_API_KEY is not set — add it to your .env file")

if api_key == "your_key_here":  # stop if the placeholder was never replaced — catches a common mistake
    raise ValueError("ANTHROPIC_API_KEY is still the placeholder — replace it with your real key")

client = anthropic.Anthropic(api_key=api_key)  # create the Anthropic client — all API calls go through this object


def execute_tool(tool_name: str, tool_input: dict) -> str:  # routes Claude's tool request to the right Python function
    """Look up the requested tool by name, call it with the given inputs, and return the result as a string."""

    if tool_name == "get_current_time":  # Claude is asking for the current Sydney time
        return get_current_time()  # call our time tool and return its string result

    if tool_name == "calculate":  # Claude is asking us to evaluate a maths expression
        expression = tool_input.get("expression", "")  # extract the expression Claude provided
        return calculate(expression)  # call our calculator and return the result string

    return f"Error: unknown tool '{tool_name}'"  # Claude requested a tool we don't have — return an error string


def run_agent(question: str) -> None:  # drives the full tool-use loop for one question; prints the final answer
    """Send a question to Claude, handle all tool calls it makes, and print the final answer."""

    print(f"  Question : {question}")  # echo the question so the output is self-explanatory
    print(f"  {'-' * 56}")  # separator between the question and the agent's working

    messages = [  # start with just the user's question — the list grows with each tool round-trip
        {"role": "user", "content": question}  # "user" role identifies our side of the conversation
    ]

    while True:  # keep looping until Claude finishes using tools and returns a final text answer

        response = client.messages.create(  # call Claude — sends the full message history plus the tool menu
            model="claude-haiku-4-5-20251001",  # Haiku: fast and cheap — good for loops that may call Claude several times
            max_tokens=1024,  # upper bound on response length for each individual API call
            tools=TOOL_SCHEMAS,  # the tool menu — tells Claude what tools exist and how to call them
            messages=messages  # the full conversation so far, including any prior tool results
        )

        if response.stop_reason == "tool_use":  # Claude wants to call one or more tools before giving its final answer

            tool_results = []  # will hold all tool results to send back to Claude in the next turn

            for block in response.content:  # response.content is a list — may contain text blocks AND tool_use blocks
                if block.type == "tool_use":  # this block is Claude asking us to run a specific tool
                    tool_name = block.name  # the tool name Claude chose e.g. "calculate"
                    tool_input = block.input  # the inputs Claude provided e.g. {"expression": "1200000-850000"}
                    tool_use_id = block.id  # unique ID for this tool call — we must echo it back in the result

                    print(f"  [tool call  ] {tool_name}({tool_input})")  # show which tool Claude is invoking

                    result = execute_tool(tool_name, tool_input)  # run the actual Python function and get the result

                    print(f"  [tool result] {result}")  # show what the tool returned

                    tool_results.append({  # build the tool_result object Claude expects to receive
                        "type": "tool_result",  # tells the API this content block is a tool result
                        "tool_use_id": tool_use_id,  # links this result back to the specific tool_use block Claude sent
                        "content": result  # the string our tool function returned
                    })

            messages.append(  # record Claude's tool_use response in the conversation history
                {"role": "assistant", "content": response.content}  # must include the full content list, not just text
            )

            messages.append(  # send tool results back as a new "user" turn — this is how the API expects them
                {"role": "user", "content": tool_results}  # Claude reads these results and continues its reasoning
            )

        elif response.stop_reason == "end_turn":  # Claude is done with tools and has its final text answer

            final_text = ""  # accumulate text across all text blocks in the response
            for block in response.content:  # loop through each block in the final response
                if hasattr(block, "text"):  # only text blocks have a .text attribute
                    final_text += block.text  # append this block's text to the running answer

            print(f"\n  Claude: {final_text}")  # print the complete final answer
            break  # exit the while loop — this question is fully answered

        else:  # unexpected stop_reason — log it and exit to avoid an infinite loop
            print(f"  Unexpected stop_reason: {response.stop_reason}")
            break  # exit the loop


# ── Test questions ─────────────────────────────────────────────────────────────

TEST_QUESTIONS = [  # the three questions that exercise our tools, run in sequence
    "What is the current date and time in Sydney?",  # uses get_current_time only
    "If I buy a property for $850,000 and sell it for $1,200,000 what is my profit and percentage gain?",  # uses calculate (likely twice)
    "What is today's date and if I bought a property 3 years ago today what year was that?",  # uses BOTH tools
]

for i, question in enumerate(TEST_QUESTIONS, 1):  # iterate with a 1-based counter for display
    print()  # blank line before each test block for visual breathing room
    print(f"{'=' * 60}")  # top border
    print(f"  TEST {i} of {len(TEST_QUESTIONS)}")  # progress indicator
    print(f"{'=' * 60}")  # bottom border of the header
    run_agent(question)  # run the full agent loop and print the result
    print()  # blank line after each answer
