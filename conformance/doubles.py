# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker
from standard_agents.tools.itool import ITool


# Every double here replaces a broker or a tool, never a service: the whole library under test
# is the real one (CONFORMANCE.md, "Every double replaces a broker, never a service").
class ScriptedGeneratorBroker(IGeneratorBroker):
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.calls: list[tuple[str, str]] = []

    # The scripted Brain returns its replies in order, repeating the last when exhausted, so a
    # single non-terminal reply exercises the turn cap.
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        reply = self.replies[min(len(self.calls), len(self.replies) - 1)]
        self.calls.append((system_prompt, user_prompt))

        return reply


class RecordingVerifierBroker(IVerifierBroker):
    def __init__(self, score: str) -> None:
        self.score = score
        self.tasks: list[str] = []

    async def verify(self, task: str, candidate: str) -> str:
        self.tasks.append(task)

        return self.score


class StubTool(ITool):
    def __init__(self, tool_name: str, output: str) -> None:
        self.tool_name = tool_name
        self.output = output
        self.received_inputs: list[str] = []

    @property
    def name(self) -> str:
        return self.tool_name

    async def execute(self, input: str) -> str:
        self.received_inputs.append(input)

        return self.output
