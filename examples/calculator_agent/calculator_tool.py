# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import ast
import operator

from standard_agents import ITool

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg
}


# Arithmetic only: the expression is parsed and walked, never handed to eval, so a brain that
# writes something other than arithmetic gets an error back instead of running code.
class CalculatorTool(ITool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "evaluates an arithmetic expression, for example 2*(3+4)"

    async def execute(self, input: str) -> str:
        result = evaluate(ast.parse(input, mode="eval").body)

        return format(result, "g")


def evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))

    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](evaluate(node.operand))

    raise ValueError(f"not arithmetic: {ast.dump(node)}")
