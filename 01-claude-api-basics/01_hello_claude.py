# 01_hello_claude.py — sends a single prompt to Claude and prints the response

from dotenv import load_dotenv  # dotenv reads key=value pairs from a .env file into os.environ
import os  # os.getenv lets us read environment variables that dotenv just loaded
import anthropic  # the official Anthropic Python SDK for calling the Claude API

load_dotenv()  # reads the .env file in the current (or parent) directory and loads it into the environment

api_key = os.getenv("ANTHROPIC_API_KEY")  # fetch the API key from the environment; returns None if missing

if not api_key:  # guard: if the variable is missing entirely, stop early with a clear message
    raise ValueError("ANTHROPIC_API_KEY is not set — add it to your .env file")

if api_key == "your_key_here":  # guard: if the placeholder value was never replaced, stop early
    raise ValueError("ANTHROPIC_API_KEY is still the placeholder — replace it with your real key in .env")

client = anthropic.Anthropic(api_key=api_key)  # create the Anthropic client; all API calls go through this object

prompt = (  # the exact question we want Claude to answer
    "What is today's date and what are the top 3 things "
    "a property investor in Australia should know about AI agents?"
)

print("Sending prompt to Claude...\n")  # let the user know the script is running
print(f"Prompt: {prompt}\n")  # echo the prompt so the output is self-explanatory
print("-" * 60)  # visual separator between the prompt and the response

response = client.messages.create(  # call the Claude Messages API — this is what sends the request
    model="claude-haiku-4-5-20251001",  # use Claude Haiku 4.5, the fast and cost-efficient model
    max_tokens=1024,  # cap the response at 1024 tokens; Claude may use fewer
    messages=[  # the conversation history; a single user turn here
        {"role": "user", "content": prompt}  # role="user" means this is our side of the conversation
    ],
)

answer = response.content[0].text  # extract the text from the first content block in the response

print("Claude's response:\n")  # header before printing Claude's answer
print(answer)  # print the actual response text to the terminal
print("\n" + "-" * 60)  # closing visual separator

print(  # report token counts so we can track API usage and cost
    f"\nTokens used — input: {response.usage.input_tokens}, "
    f"output: {response.usage.output_tokens}"
)
