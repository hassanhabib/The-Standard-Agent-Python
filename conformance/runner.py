# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from conformance.doubles import RecordingVerifierBroker, ScriptedGeneratorBroker, StubTool
from standard_agents import AgentOutcome, StandardAgent

# What this runner can drive. A vector that asks for anything else is reported UNSUPPORTED rather
# than run half-configured: a vector run without the capability it configures would pass or fail
# for the wrong reason, and either answer would be a claim about the harness.
SUPPORTED_SETUP = {
    "name", "description", "generatorReplies", "tools", "prompt", "prompts", "concurrent",
    "expect", "maxTurns", "judgeScore"
}

SUPPORTED_EXPECTATIONS = {
    "result", "resultContains", "resultsContain", "toolInput", "toolRunCount", "toolNeverRan",
    "brainSees", "brainNeverSees", "judgeSawTask", "status"
}


@dataclass
class VectorRun:
    outcomes: list[AgentOutcome]
    generator: ScriptedGeneratorBroker
    verifier: RecordingVerifierBroker
    tools: dict[str, StubTool] = field(default_factory=dict)


async def certify(vectors_path: Path, profile_name: str | None, profiles_path: Path) -> int:
    print(f"Conformance vectors: {vectors_path}")
    passed, failed, unsupported = set(), set(), {}

    for vector_file in sorted(vectors_path.glob("*.json")):
        vector = json.loads(vector_file.read_text(encoding="utf-8"))
        name = vector["name"]
        missing = unsupported_fields(vector)

        if missing:
            unsupported[name] = missing
            print(f"SKIP  {name}  (unsupported: {', '.join(sorted(missing))})")

            continue

        run = await run_vector(vector)
        failures = check(vector, run)

        if failures:
            failed.add(name)
            print(f"FAIL  {name}")

            for failure in failures:
                print(f"        {failure}")
        else:
            passed.add(name)
            print(f"PASS  {name}")

    print(f"\n{len(passed)} passed, {len(failed)} failed, {len(unsupported)} unsupported")

    if profile_name is None:
        return 1 if failed else 0

    required = required_vectors(profiles_path, profile_name)
    missing_vectors = sorted(required - passed)

    if missing_vectors:
        print(f"\nNOT CERTIFIED: {profile_name}; missing {', '.join(missing_vectors)}")

        return 1

    print(f"\nCERTIFIED: {profile_name} ({len(required)} vectors)")

    return 0


def unsupported_fields(vector: dict) -> set[str]:
    return (set(vector) - SUPPORTED_SETUP) | (set(vector["expect"]) - SUPPORTED_EXPECTATIONS)


# A profile lists the vectors it requires and may inherit another's (conformance/profiles).
def required_vectors(profiles_path: Path, profile_name: str) -> set[str]:
    profile = json.loads(
        (profiles_path / f"{profile_name.lower()}.json").read_text(encoding="utf-8"))

    inherited = set()

    if "inherits" in profile:
        inherited = required_vectors(profiles_path, profile["inherits"])

    return inherited | set(profile["requires"])


async def run_vector(vector: dict) -> VectorRun:
    generator = ScriptedGeneratorBroker(vector["generatorReplies"])
    verifier = RecordingVerifierBroker(vector.get("judgeScore", "1.0"))

    tools = {
        tool_name: StubTool(tool_name, output)
        for tool_name, output in vector.get("tools", {}).items()
    }

    agent = (StandardAgent()
        .use_generator(generator)
        .use_judge(verifier)
        .tools(tools.values()))

    if "maxTurns" in vector:
        agent.max_turns(vector["maxTurns"])

    prompts = vector.get("prompts", [vector["prompt"]])

    if vector.get("concurrent", False):
        outcomes = list(await asyncio.gather(*(agent.run(prompt) for prompt in prompts)))
    else:
        outcomes = [await agent.run(prompt) for prompt in prompts]

    return VectorRun(outcomes=outcomes, generator=generator, verifier=verifier, tools=tools)


def check(vector: dict, run: VectorRun) -> list[str]:
    expect = vector["expect"]
    result = run.outcomes[-1].result
    seen_by_brain = [system + "\n" + user for system, user in run.generator.calls]
    failures = []

    if "result" in expect and result != expect["result"]:
        failures.append(f"result {result!r}, expected {expect['result']!r}")

    if "resultContains" in expect and expect["resultContains"] not in result:
        failures.append(f"result {result!r} does not contain {expect['resultContains']!r}")

    for index, expected in enumerate(expect.get("resultsContain", [])):
        if expected not in run.outcomes[index].result:
            failures.append(f"prompt {index} result does not contain {expected!r}")

    for tool_name, expected_input in expect.get("toolInput", {}).items():
        if expected_input not in run.tools[tool_name].received_inputs:
            failures.append(
                f"{tool_name} received {run.tools[tool_name].received_inputs}, "
                + f"expected {expected_input!r}")

    for tool_name, expected_count in expect.get("toolRunCount", {}).items():
        actual_count = len(run.tools[tool_name].received_inputs)

        if actual_count != expected_count:
            failures.append(f"{tool_name} ran {actual_count} times, expected {expected_count}")

    for tool_name in expect.get("toolNeverRan", []):
        if run.tools[tool_name].received_inputs:
            failures.append(f"{tool_name} ran, and must never have")

    for expected in as_list(expect.get("brainSees")):
        if not any(expected in seen for seen in seen_by_brain):
            failures.append(f"the Brain never saw {expected!r}")

    for unexpected in as_list(expect.get("brainNeverSees")):
        if any(unexpected in seen for seen in seen_by_brain):
            failures.append(f"the Brain saw {unexpected!r}")

    if expect.get("judgeSawTask") and vector["prompt"] not in run.verifier.tasks:
        failures.append("the Judge was never handed the task")

    if "status" in expect and run.outcomes[-1].status.name != status_name(expect["status"]):
        failures.append(f"status {run.outcomes[-1].status.name}, expected {expect['status']}")

    return failures


def as_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []

    return [value] if isinstance(value, str) else value


# The vectors name statuses as the specification does (AwaitingInput); Python spells them as
# constants (AWAITING_INPUT).
def status_name(spec_status: str) -> str:
    return "".join(
        "_" + character if character.isupper() and index > 0 else character
        for index, character in enumerate(spec_status)).upper()
