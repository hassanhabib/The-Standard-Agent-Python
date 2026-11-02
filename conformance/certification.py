# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Every vector run and checked, then, when a profile is named, the profile certified.

Certifying a profile is a separate question from running the vectors: not "did everything we
happen to have pass" but "is every requirement of this level actually evidenced". A requirement
whose vector does not exist fails; otherwise a profile could be claimed by never writing its
evidence, which is the failure mode profiles exist to prevent.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from standard_agents import StandardAgent

from conformance import expectations, report
from conformance.models.document_binding import bind
from conformance.models.vector import Vector
from conformance.models.vector_verdict import VectorVerdict
from conformance.profiles import profile_requirements
from conformance.run import run_vector


async def certify(
        vectors_path: Path,
        profiles_path: Path,
        profile_name: str | None,
        base_directory: Path) -> int:
    """Runs every vector in name order and returns the process exit code.

    Zero only when every vector passed and, for a named profile, every requirement was met.
    base_directory is where the vectors' files are written; the caller makes it the working
    directory, where the agent resolves relative names.
    """
    passed = 0
    failed = 0
    passed_vectors: set[str] = set()

    for vector_file in sorted(vectors_path.glob("*.json"), key=lambda path: str(path)):
        vector = bind(
            Vector,
            json.loads(vector_file.read_text(encoding="utf-8-sig"), parse_float=Decimal))

        if await _certify_vector(vector, base_directory):
            passed += 1
            passed_vectors.add(vector.name.lower())
        else:
            failed += 1

    report.print_totals(passed, failed)

    if profile_name is None:
        return 0 if failed == 0 else 1

    missing = [
        requirement for requirement in profile_requirements(profile_name, profiles_path)
        if requirement.lower() not in passed_vectors]

    report.print_certification(profile_name, missing)

    if missing:
        return 1

    return 0 if failed == 0 else 1


async def _certify_vector(vector: Vector, base_directory: Path) -> bool:
    # Composition-from-data vectors certify the refusal itself: the document must not compose,
    # and the refusal must name the offending entry (SPEC.md 4.8 v1.4). No run happens.
    if vector.configuration_json is not None:
        return _certify_refusal(vector)

    run = await run_vector(vector, base_directory)

    verdict = VectorVerdict(
        result_conformant=expectations.result_conformant(vector, run),
        per_prompt_results_conformant=expectations.per_prompt_results_conformant(vector, run),
        tool_input_conformant=expectations.tool_input_conformant(vector, run),
        agent_input_conformant=expectations.agent_input_conformant(vector, run),
        rubric_failure=expectations.rubric_failure(
            vector.expect, run.gate_rubric, run.judge_rubric),
        audit_failure=expectations.audit_failure(vector, run.audit_records),
        guardian_input_failure=expectations.guardian_input_failure(vector, run),
        request_failure=expectations.request_failure(vector, run),
        narration_failure=expectations.narration_failure(vector, run),
        usage_failure=expectations.usage_failure(vector, run))

    if verdict.conformant:
        report.print_passed(vector)
    else:
        report.print_failed(vector, run, verdict)

    return verdict.conformant


def _certify_refusal(vector: Vector) -> bool:
    refusal: str | None = None

    try:
        StandardAgent.from_json(vector.configuration_json)
    except Exception as exception:
        refusal = str(exception)

    required_naming = (
        vector.expect.configuration_refusal_names
        if vector.expect.configuration_refusal_names is not None else "")

    if refusal is not None and required_naming in refusal:
        report.print_passed(vector)

        return True

    report.print_refusal_failure(vector, refusal, required_naming)

    return False
