# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""What the runner prints: a line per vector, and under a failure, what was expected and seen."""

from __future__ import annotations

from enum import Enum

from conformance.models.vector import Vector
from conformance.models.vector_run import VectorRun
from conformance.models.vector_verdict import VectorVerdict


def show(value: str) -> str:
    """Text on one line: a newline reads as the two characters that write it."""
    return value.replace("\n", "\\n").replace("\r", "\\r")


def enum_name(member: Enum) -> str:
    """A member's name as the reference runner prints it: AWAITING_INPUT is AwaitingInput."""
    return "".join(word.capitalize() for word in member.name.split("_"))


def print_header(vectors_path: str, profile_name: str | None) -> None:
    print(f"Conformance vectors: {vectors_path}")

    if profile_name is not None:
        print(f"Certifying profile: {profile_name}")

    print()


def print_passed(vector: Vector) -> None:
    print(f"PASS  {vector.name}")


def print_refusal_failure(vector: Vector, refusal: str | None, required_naming: str) -> None:
    print(f"FAIL  {vector.name}")

    if refusal is None:
        print("        the document composed; it should have refused")
    else:
        print(f"        the refusal does not name {show(required_naming)}: {show(refusal)}")


def print_failed(vector: Vector, run: VectorRun, verdict: VectorVerdict) -> None:
    expect = vector.expect
    print(f"FAIL  {vector.name}")

    if not verdict.result_conformant:
        expectation = (
            expect.result if expect.result is not None
            else f"contains: {expect.result_contains}")

        print(f"        expected result: {show(expectation)}")
        print(f"        actual result:   {show(run.result)}")

    if not verdict.per_prompt_results_conformant:
        print(
            "        expected per-prompt results containing: "
            + " | ".join(expect.results_contain))

        print(
            "        actual per-prompt results: "
            + " | ".join(map(show, run.prompt_results)))

    if not verdict.tool_input_conformant:
        for name, expected_input in expect.tool_input.items():
            tool = run.tools.get(name)

            actual_inputs = (
                " | ".join(map(show, tool.received_inputs)) if tool is not None
                else "(tool never called)")

            print(f"        tool '{name}' expected input: {show(expected_input)}")
            print(f"        tool '{name}' actual inputs:  {actual_inputs}")

    if not verdict.agent_input_conformant:
        for name, expected_text in expect.agent_input.items():
            handed = run.agent_inputs.get(name.lower())

            actual_handoffs = (
                " | ".join(map(show, handed)) if handed else "(agent never ran)")

            print(
                f"        agent '{name}' expected handoff containing: {show(expected_text)}")

            print(f"        agent '{name}' actually received: {actual_handoffs}")

    if verdict.rubric_failure is not None:
        gate_rubric = run.gate_rubric if run.gate_rubric is not None else "(gate never ran)"

        judge_rubric = (
            run.judge_rubric if run.judge_rubric is not None else "(judge never ran)")

        print(f"        guardian rubric: {verdict.rubric_failure}")
        print(f"        gate rubric:  {show(gate_rubric)}")
        print(f"        judge rubric: {show(judge_rubric)}")

    if verdict.guardian_input_failure is not None:
        judge_input = run.judge_input if run.judge_input is not None else "(judge never ran)"

        print(f"        guardian input: {verdict.guardian_input_failure}")
        print(f"        judge input: {show(judge_input)}")

    if verdict.audit_failure is not None:
        runs = len({record.run_id for record in run.audit_records})

        print(f"        decision log: {verdict.audit_failure}")
        print(f"        records: {len(run.audit_records)} across {runs} run(s)")

    if verdict.request_failure is not None:
        print(f"        request: {verdict.request_failure}")

    if verdict.narration_failure is not None:
        print(f"        narration: {verdict.narration_failure}")

    if verdict.usage_failure is not None:
        print(f"        usage: {verdict.usage_failure}")


def print_totals(passed: int, failed: int) -> None:
    print()
    print(f"{passed} passed, {failed} failed")


def print_certification(profile_name: str, missing: list[str]) -> None:
    print()

    if not missing:
        print(f"CERTIFIED  {profile_name}")

        return

    print(f"NOT CERTIFIED  {profile_name}: {len(missing)} requirement(s) unmet:")

    for requirement in missing:
        print(f"  - {requirement}")
