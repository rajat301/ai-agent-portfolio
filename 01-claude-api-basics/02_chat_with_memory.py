# 02_chat_with_memory.py — multi-turn chat that keeps full conversation history so Claude remembers earlier messages

from dotenv import load_dotenv  # dotenv reads .env files and loads them into os.environ
import os  # lets us read environment variables after dotenv has loaded them
import anthropic  # the official Anthropic SDK for calling the Claude API

load_dotenv()  # opens the .env file in the current directory and loads all key=value pairs into the environment

api_key = os.getenv("ANTHROPIC_API_KEY")  # read the API key from the environment; returns None if it wasn't found

if not api_key:  # stop immediately if the key is missing entirely — better to fail fast with a clear message
    raise ValueError("ANTHROPIC_API_KEY is not set — add it to your .env file")

if api_key == "your_key_here":  # stop if the placeholder was never replaced — catches a common setup mistake
    raise ValueError("ANTHROPIC_API_KEY is still the placeholder — replace it with your real key in .env")

client = anthropic.Anthropic(api_key=api_key)  # create the Anthropic client — all API calls go through this object

conversation_history = []  # empty list that will grow with each turn; this IS the memory — Claude sees all of it every call

print("=" * 60)  # top border to make the welcome block stand out visually
print("Claude Chat with Memory")  # title so the user knows what script they are running
print("Each message you send includes the full conversation")  # explain WHY memory works: the whole history is sent each time
print("so Claude remembers everything said earlier in the chat.")  # continuation of the explanation
print("Type 'quit' to exit.")  # tell the user how to stop the loop cleanly
print("=" * 60)  # bottom border closing the welcome block
print()  # blank line for visual breathing room before the first prompt

while True:  # loop forever — we will break out manually when the user types 'quit'

    user_message = input("You: ")  # pause and wait for the user to type something and press Enter

    if user_message.lower() == "quit":  # check if the user wants to exit; .lower() makes it case-insensitive
        break  # exit the while loop immediately and jump to the code after it

    conversation_history.append(  # add the user's message to the history list before sending to Claude
        {"role": "user", "content": user_message}  # "role": "user" tells Claude this was said by the human
    )

    response = client.messages.create(  # send the entire conversation history to Claude — this is what gives it memory
        model="claude-haiku-4-5-20251001",  # Haiku is fast and cheap — good for interactive chat loops
        max_tokens=1024,  # cap the reply length; Claude may use fewer but never more than this
        messages=conversation_history  # pass the FULL list — Claude sees every prior turn, not just the latest message
    )

    response_text = response.content[0].text  # extract the plain text from the first content block in the response object

    conversation_history.append(  # add Claude's reply to history so future turns know what Claude already said
        {"role": "assistant", "content": response_text}  # "role": "assistant" marks this as Claude's side of the conversation
    )

    print()  # blank line before Claude's response for readability
    print(f"Claude: {response_text}")  # print Claude's reply to the terminal
    print()  # blank line after the response
    print("-" * 60)  # separator line between turns so each exchange is visually distinct
    print()  # blank line after the separator before the next input prompt

print()  # blank line before the summary for clean spacing
print(f"Conversation ended. Total messages in history: {len(conversation_history)}")  # show how many turns were stored; each turn = 2 entries (user + assistant)
