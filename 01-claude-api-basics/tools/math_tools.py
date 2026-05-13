# math_tools.py — functions that safely evaluate mathematical expressions

import ast  # ast parses a string into a syntax tree so we can inspect it before running anything
import operator  # operator module provides named functions for +, -, *, / etc. that we can call safely


# Whitelist of allowed AST node types mapped to their safe operator functions.
# Using a whitelist means anything NOT in this dict is automatically blocked —
# no function calls, no imports, no attribute access, nothing dangerous can sneak through.
_ALLOWED_OPERATORS = {
    ast.Add:  operator.add,       # handles the "+" binary operator
    ast.Sub:  operator.sub,       # handles the "-" binary operator
    ast.Mult: operator.mul,       # handles the "*" binary operator
    ast.Div:  operator.truediv,   # handles the "/" binary operator; returns a float, not an int
    ast.Pow:  operator.pow,       # handles the "**" exponentiation operator
    ast.USub: operator.neg,       # handles unary minus e.g. -5
    ast.UAdd: operator.pos,       # handles unary plus e.g. +5
}


def _eval_node(node) -> float:  # private helper — walks one node of the AST and returns its numeric value
    """Recursively evaluate a single AST node. Raises ValueError for anything unsafe."""

    if isinstance(node, ast.Constant):  # base case — a literal number like 850000 or 3.14
        if not isinstance(node.value, (int, float)):  # reject non-numeric constants like strings or booleans
            raise ValueError(f"Non-numeric constant: {node.value!r}")
        return node.value  # return the raw number

    if isinstance(node, ast.BinOp):  # binary operation — two operands with one operator e.g. a + b
        left = _eval_node(node.left)  # recursively evaluate the left side
        right = _eval_node(node.right)  # recursively evaluate the right side
        op_func = _ALLOWED_OPERATORS.get(type(node.op))  # look up the operator in the whitelist
        if op_func is None:  # operator not in whitelist — block it
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_func(left, right)  # apply the operator and return the numeric result

    if isinstance(node, ast.UnaryOp):  # unary operation — one operand e.g. -850000
        operand = _eval_node(node.operand)  # recursively evaluate the operand
        op_func = _ALLOWED_OPERATORS.get(type(node.op))  # look up the unary operator in the whitelist
        if op_func is None:  # unary operator not in whitelist — block it
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op_func(operand)  # apply the unary operator and return the result

    # anything else — function calls, names, attribute access — is not a number, reject it
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def calculate(expression: str) -> str:  # public function — takes expression string, returns result string
    """Safely evaluate a mathematical expression string and return the result as a string.

    Only supports +, -, *, /, ** and numeric literals. No function calls or variable names.
    Returns an error message string if the expression is invalid, so callers never receive an exception.
    """

    if not expression or not expression.strip():  # reject empty or whitespace-only input
        return "Error: empty expression"

    try:
        tree = ast.parse(expression.strip(), mode="eval")  # parse the string into an AST; mode="eval" means single expression
        result = _eval_node(tree.body)  # walk the AST starting from the root expression node
        # Round to 6 decimal places to avoid floating-point noise like 41.17647058823529411...
        rounded = round(result, 6)  # round to 6 decimal places for clean display
        # If the result is a whole number, show it without a decimal point
        if rounded == int(rounded):  # e.g. 350000.0 → display as 350000, not 350000.0
            return str(int(rounded))
        return str(rounded)  # otherwise return the float string e.g. "41.176471"
    except ZeroDivisionError:  # catch division by zero separately for a clearer message
        return "Error: division by zero"
    except Exception as e:  # catch syntax errors, unsupported nodes, or any other evaluation failure
        return f"Error: {e}"  # return the error as a string so the agent can relay it to Claude
