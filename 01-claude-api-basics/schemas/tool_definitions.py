# tool_definitions.py — Anthropic-format JSON schemas that describe our tools to Claude
#
# WHY this file exists separately from the tool functions:
# The schema is Claude's "menu" — it tells Claude what tools exist, what they do, and
# what inputs to provide. The actual Python functions are separate because Claude never
# calls them directly; WE call them after Claude asks us to. Keeping schemas separate
# makes it easy to add, edit, or version them without touching business logic.

TOOL_SCHEMAS = [  # list passed directly to the `tools` parameter of client.messages.create()

    {  # ── Tool 1: get_current_time ──────────────────────────────────────────
        "name": "get_current_time",  # exact identifier Claude uses when requesting this tool — must match execute_tool()
        "description": (  # plain English explanation Claude reads to decide WHEN to call this tool
            "Returns the current date and time in Sydney, Australia. "
            "Use this whenever the user asks about the current time, today's date, or the current year."
        ),
        "input_schema": {  # JSON Schema object that defines what inputs Claude must provide
            "type": "object",  # the input is always a JSON object, even when there are no properties
            "properties": {},  # empty dict — this tool needs no inputs; it figures out the time itself
            "required": []  # nothing is required because properties is empty
        }
    },

    {  # ── Tool 2: calculate ────────────────────────────────────────────────
        "name": "calculate",  # exact identifier Claude uses when requesting this tool — must match execute_tool()
        "description": (  # plain English explanation Claude reads to decide WHEN to call this tool
            "Performs a mathematical calculation and returns the numeric result. "
            "Use this for arithmetic: addition, subtraction, multiplication, division, and exponentiation. "
            "Provide the expression as a standard maths string, e.g. '(1200000 - 850000) / 850000 * 100'."
        ),
        "input_schema": {  # JSON Schema object describing what Claude must send when calling this tool
            "type": "object",  # the input is a JSON object containing the fields below
            "properties": {  # dict of named input fields this tool accepts
                "expression": {  # the single input this tool requires
                    "type": "string",  # Claude must provide the expression as a string, not a number
                    "description": (  # Claude reads this to know how to format the expression correctly
                        "A mathematical expression to evaluate using standard operators: "
                        "+, -, *, /, ** (power). "
                        "Example: '(1200000 - 850000) / 850000 * 100'"
                    )
                }
            },
            "required": ["expression"]  # Claude MUST include "expression" — the SDK will error if it's missing
        }
    },

]  # end of TOOL_SCHEMAS
