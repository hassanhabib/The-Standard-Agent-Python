# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import sys

from examples.calculator_agent.agent import create_agent

# python -m examples.calculator_agent "What is 47 * 89?"


async def main() -> int:
    prompt = " ".join(sys.argv[1:]) or "What is 47 * 89?"
    outcome = await create_agent().run(prompt)

    print(f"Prompt : {prompt}")
    print(f"Status : {outcome.status.name}")
    print(f"Answer : {outcome.result}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
