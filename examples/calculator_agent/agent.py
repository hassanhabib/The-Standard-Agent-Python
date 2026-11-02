# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import re
from pathlib import Path

from standard_agents import StandardAgent
from examples.calculator_agent.calculator_tool import CalculatorTool

SKILLS_PATH = Path(__file__).parent / "skills"
ARITHMETIC = re.compile(r"[-+]?\d[\d\s.+\-*/()^]*[\d)]")
CALCULATOR_RESULT = re.compile(r"- calculator: (.+)")
SECRETS = ("password", "secret", "api key", "token")


# A brain small enough to read: it speaks the same ACTION / FINAL protocol a model does, so the
# agent around it is exactly the agent a real model would drive. Swap it for a local open-weight
# model with use_generator(...) and nothing else changes.
async def local_brain(system_prompt: str, user_prompt: str) -> str:
    calculator_result = CALCULATOR_RESULT.search(user_prompt)
    task = user_prompt.split("\n")[0].removeprefix("Task: ")
    expression = ARITHMETIC.search(task)

    if calculator_result and expression:
        return f"FINAL: {expression.group(0).strip()} = {calculator_result.group(1).strip()}"

    if expression:
        return f"ACTION: calculator: {expression.group(0).strip()}"

    return "FINAL: I can only help with arithmetic."


async def local_gate(rubric: str, text: str) -> str:
    if any(secret in text.lower() for secret in SECRETS):
        return "refuse: asks for credentials"

    return "accept"


def create_agent() -> StandardAgent:
    return (StandardAgent()
        .skills(str(SKILLS_PATH))
        .tool(CalculatorTool())
        .on_gate(local_gate)
        .on_brain(local_brain))
