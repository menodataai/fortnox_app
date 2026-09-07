"""Exact arithmetic for the assistant: a safe expression evaluator on
`decimal.Decimal`. Verdicts must never rest on LLM mental arithmetic."""

import ast
from decimal import Decimal, DivisionByZero, InvalidOperation, localcontext

_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}


def _eval(node: ast.AST) -> Decimal:
    match node:
        case ast.Constant(value=v) if isinstance(v, (int, float)) and not isinstance(v, bool):
            return Decimal(str(v))
        case ast.UnaryOp(op=ast.USub(), operand=operand):
            return -_eval(operand)
        case ast.UnaryOp(op=ast.UAdd(), operand=operand):
            return _eval(operand)
        case ast.BinOp(op=op, left=left, right=right) if type(op) in _BINOPS:
            return _BINOPS[type(op)](_eval(left), _eval(right))
        case ast.Call(func=ast.Name(id="round"), args=args, keywords=[]) if 1 <= len(args) <= 2:
            value = _eval(args[0])
            digits = int(_eval(args[1])) if len(args) == 2 else 0
            exp = Decimal(1).scaleb(-digits)
            return value.quantize(exp)
        case ast.Call(func=ast.Name(id="abs"), args=[arg], keywords=[]):
            return abs(_eval(arg))
    raise ValueError(
        f"Unsupported syntax: {ast.dump(node) if not isinstance(node, ast.expr) else type(node).__name__}. "
        "Allowed: numbers, + - * /, parentheses, round(x, n), abs(x)."
    )


def calculate(expression: str) -> str:
    """Evaluate an arithmetic expression exactly; returns the decimal result
    as a string (no float rounding errors)."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Not a valid expression: {e.msg}") from e
    try:
        with localcontext() as ctx:
            ctx.prec = 28
            result = _eval(tree.body)
    except DivisionByZero:
        raise ValueError("Division by zero.") from None
    except InvalidOperation as e:
        raise ValueError(f"Invalid operation: {e}") from None
    text = format(result, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
