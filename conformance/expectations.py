# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""What a vector's run must show, checked against what the run produced and what its doubles saw.

The first four checks answer yes or no; the report says what they expected. Every other check
returns None when the run conforms, or the sentence that says how it did not.
"""

from __future__ import annotations

import hashlib

from standard_agents.models.brokers.audits.audit_record import AuditRecord
from standard_agents.models.brokers.generators.v1.conversation import MessageRole
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType

from conformance.models.expectation import Expectation
from conformance.models.vector import Vector
from conformance.models.vector_run import VectorRun
from conformance.report import show, enum_name


def result_conformant(vector: Vector, run: VectorRun) -> bool:
    expect = vector.expect

    if expect.result is not None:
        return run.result == expect.result

    return expect.result_contains is not None and expect.result_contains in run.result


def per_prompt_results_conformant(vector: Vector, run: VectorRun) -> bool:
    expected_results = vector.expect.results_contain

    if expected_results is None:
        return True

    return len(run.prompt_results) == len(expected_results) and all(
        expected in actual for expected, actual in zip(expected_results, run.prompt_results))


def tool_input_conformant(vector: Vector, run: VectorRun) -> bool:
    return vector.expect.tool_input is None or all(
        name in run.tools and expected_input in run.tools[name].received_inputs
        for name, expected_input in vector.expect.tool_input.items())


def agent_input_conformant(vector: Vector, run: VectorRun) -> bool:
    # The handoff's content, certified at the specialist: grounding is only real if the text
    # actually arrived (SPEC.md 4.8 v1.6).
    return vector.expect.agent_input is None or all(
        any(expected_text in handed for handed in run.agent_inputs.get(name.lower(), ()))
        for name, expected_text in vector.expect.agent_input.items())


def audit_failure(vector: Vector, records: list[AuditRecord]) -> str | None:
    """The decision log's guarantees, certified from the records themselves.

    One run per prompt, every prompt's evidence still present at the end, and record numbers
    that never repeat within a run (SPEC.md 4.7, 4.4).
    """
    expect = vector.expect

    if (expect.audit_run_count is None
            and not expect.audit_retains_every_prompt
            and not expect.audit_sequences_unique_per_run):
        return None

    prompts = vector.prompts if vector.prompts else [vector.prompt]

    if expect.audit_run_count is not None:
        actual_run_count = len({record.run_id for record in records})

        if actual_run_count != expect.audit_run_count:
            return (
                f"expected {expect.audit_run_count} distinct run(s), "
                + f"found {actual_run_count}")

    if expect.audit_retains_every_prompt:
        for prompt in prompts:
            # Evidence of a prompt is its record: the payload itself when the deployment opted
            # into payload capture, otherwise the payload's hash. The decision log is metadata by
            # default (F-14), and a hash is proof the prompt was received without the prompt
            # travelling to the sink.
            prompt_hash = _sha256_hex(prompt)

            retained = any(
                prompt in record.message
                or (record.payload is not None and prompt in record.payload)
                or record.payload_hash == prompt_hash
                for record in records)

            if not retained:
                return f"no record retained evidence of the prompt {show(prompt)}"

    if expect.audit_sequences_unique_per_run:
        sequences_by_run: dict[str, list[int]] = {}

        for record in records:
            sequences_by_run.setdefault(record.run_id, []).append(record.sequence)

        for run_id, sequences in sequences_by_run.items():
            if len(sequences) != len(set(sequences)):
                return f"run '{run_id}' repeated a record number; runs shared a counter"

    return None


def rubric_failure(
        expect: Expectation,
        gate_rubric: str | None,
        judge_rubric: str | None) -> str | None:
    """A rubric guarantee, certified against BOTH guardians, so both rubrics must exist.

    A vector that asserts a rubric therefore has to drive the agent all the way to a judged final
    answer (gate allows, brain answers); otherwise the judge never runs and there is nothing to
    certify against, which is reported as a failure rather than passing vacuously.
    """
    if expect.guardian_rubric_contains is None and expect.guardian_rubric_excludes is None:
        return None

    if gate_rubric is None or judge_rubric is None:
        return (
            "a guardian rubric was never produced "
            + f"(gate ran: {gate_rubric is not None}, judge ran: {judge_rubric is not None})")

    for needle in expect.guardian_rubric_contains or ():
        if needle not in gate_rubric or needle not in judge_rubric:
            return f"expected in both guardian rubrics: {show(needle)}"

    for needle in expect.guardian_rubric_excludes or ():
        if needle in gate_rubric or needle in judge_rubric:
            return f"expected absent from both guardian rubrics: {show(needle)}"

    return None


def guardian_input_failure(vector: Vector, run: VectorRun) -> str | None:
    """What a guardian was allowed to see, and what it was not allowed to become (SPEC.md 4.2,
    7.6), with the perimeter's and the Brain's observations alongside."""
    expect = vector.expect

    if expect.judge_saw_task:
        if run.judge_input is None:
            return "the judge never ran, so it cannot have seen the task"

        if vector.prompt not in run.judge_input:
            return f"the judge never saw the task {show(vector.prompt)}"

    if (expect.guardian_never_answers
            and vector.gate_verdict is not None
            and vector.gate_verdict in run.result):
        return "the guardian's own text became the agent's answer"

    # Identity must reach the decision, not only the record of it (SPEC.md 4.9). This reads what
    # the policy broker was handed; an implementation that names the caller in the audit log
    # and authorizes without them fails here, which is exactly the defect this check exists for.
    if expect.policy_saw_principal is not None:
        if not run.policy_principals:
            return "policy was never asked, so it cannot have been told who was acting"

        wrong = [
            principal for principal in run.policy_principals
            if principal != expect.policy_saw_principal]

        if wrong:
            named = ", ".join("null" if principal is None else principal for principal in wrong)

            return (
                f"policy decided for principal(s) [{named}], "
                + f"expected '{expect.policy_saw_principal}' every time")

    # A tool result must come back as an answer to the call that asked for it (SPEC.md 6). Both
    # halves are checked: the assistant's request replayed with its id, and the tool's answer
    # naming that id. A framework that narrates the result as prose fails on the second.
    if expect.tool_result_answers_call is not None:
        call_id = expect.tool_result_answers_call

        conversations = (
            run.native_generator.conversations if run.native_generator is not None else ())

        last_conversation = conversations[-1] if conversations else ()

        request_replayed = any(
            message.role is MessageRole.ASSISTANT
            and any(call.id == call_id for call in message.tool_calls)
            for message in last_conversation)

        answer_names_call = any(
            message.role is MessageRole.TOOL and message.tool_call_id == call_id
            for message in last_conversation)

        if not request_replayed or not answer_names_call:
            return (
                f"the model was not handed call '{call_id}' and its answer "
                + f"(request replayed: {request_replayed}, "
                + f"answer names call: {answer_names_call})")

    # The unwind runs in reverse, and only over what the run actually performed (SPEC.md 4.9).
    if (expect.compensation_order is not None
            and run.compensation_order != expect.compensation_order):
        return (
            f"compensation ran [{', '.join(run.compensation_order)}], "
            + f"expected [{', '.join(expect.compensation_order)}]")

    # Held is not performed, and proposing an act many times is still one act (SPEC.md 4.9).
    for tool_name in expect.tool_never_ran or ():
        actual_runs = _runs_of(run, tool_name)

        if actual_runs > 0:
            return f"tool '{tool_name}' ran {actual_runs} time(s); it should never have run"

    for tool_name, expected_runs in (expect.tool_run_count or {}).items():
        actual_runs = _runs_of(run, tool_name)

        if actual_runs != expected_runs:
            return f"tool '{tool_name}' ran {actual_runs} time(s), expected {expected_runs}"

    if expect.brain_never_sees is not None and any(
            expect.brain_never_sees in brain_input for brain_input in run.brain_inputs):
        return (
            "the Brain was shown text that should have been withheld: "
            + show(expect.brain_never_sees))

    # Retrieval is certified by what reached the Brain: the passage that answers the question
    # has to actually get there (SPEC.md 4.2).
    if expect.brain_sees is not None and not any(
            expect.brain_sees in brain_input for brain_input in run.brain_inputs):
        return f"the Brain was never shown the retrieved text: {show(expect.brain_sees)}"

    # Accumulation is certified by every source's text arriving: a source silently replaced is
    # a source whose text is absent (SPEC.md 4.8 v1.5).
    for required in expect.brain_sees_every or ():
        if not any(required in brain_input for brain_input in run.brain_inputs):
            return f"the Brain never saw {show(required)}; a source was lost"

    # Routing is certified by the owner being called and the bystander not (SPEC.md 4.8 v1.5).
    if expect.mcp_server_calls is not None and run.mcp_server_calls != expect.mcp_server_calls:
        return (
            f"server calls were [{', '.join(map(str, run.mcp_server_calls))}], "
            + f"expected [{', '.join(map(str, expect.mcp_server_calls))}]")

    if (expect.gate_screened_prompt_times is not None
            and run.prompt_screenings != expect.gate_screened_prompt_times):
        return (
            f"the Gate screened the prompt {run.prompt_screenings} time(s), "
            + f"expected {expect.gate_screened_prompt_times}")

    # Redaction is only satisfied if EVERY model call is clean. Checking the Brain alone is the
    # exact mistake this check exists to catch (SPEC.md 4.6).
    if expect.no_model_sees is not None:
        if not run.model_inputs:
            return "no model was called, so nothing was certified"

        leaking = sum(
            1 for model_input in run.model_inputs if expect.no_model_sees in model_input)

        if leaking > 0:
            return (
                f"{leaking} of {len(run.model_inputs)} model call(s) saw "
                + f"{show(expect.no_model_sees)} in the clear")

    return None


def request_failure(vector: Vector, run: VectorRun) -> str | None:
    """The request seam's guarantees, certified from what the run reported and what the scripted
    Brain was actually handed (docs/per-request-inference.md 4, 5, 6)."""
    expect = vector.expect

    # The history a session holds once every prompt has run, read from the store afterwards:
    # under concurrent prompts, a save that read, appended and wrote the whole record leaves
    # fewer turns than prompts (SPEC.md 4.11).
    if (expect.session_turn_count is not None
            and run.session_turn_count != expect.session_turn_count):
        held = "no" if run.session_turn_count is None else str(run.session_turn_count)

        return f"the session holds {held} turn(s), expected {expect.session_turn_count}"

    if expect.status is not None:
        actual_status = (
            enum_name(run.status) if run.status is not None else "(not reported)")

        if actual_status.lower() != expect.status.lower():
            return f"the run ended {actual_status}, expected {expect.status}"

    # Why a run stopped without an answer, as the code a caller switches on (SPEC.md 3.6, v1.14).
    if expect.failure_code is not None and run.failure_code != expect.failure_code:
        reported = run.failure_code if run.failure_code is not None else "(none)"

        return f"the run reported failure code '{reported}', expected '{expect.failure_code}'"

    if (expect.pending_effect_tool is not None
            and run.pending_effect_tool != expect.pending_effect_tool):
        carried = run.pending_effect_tool if run.pending_effect_tool is not None else "(none)"

        return (
            f"the pending effect carries '{carried}', "
            + f"expected '{expect.pending_effect_tool}'")

    asks_about_the_wire = (
        expect.broker_temperature is not None
        or expect.broker_max_tokens is not None
        or expect.broker_temperatures is not None
        or expect.broker_schema_contains is not None
        or expect.broker_options_include is not None
        or expect.broker_options_exclude is not None)

    if not asks_about_the_wire:
        return None

    if not run.broker_inferences:
        return "the broker was never handed resolved inference options"

    wire = run.broker_inferences[-1]

    if expect.broker_temperature is not None and wire.temperature != expect.broker_temperature:
        return (
            f"the broker was handed temperature {_number(wire.temperature)}, "
            + f"expected {_number(expect.broker_temperature)}")

    if expect.broker_max_tokens is not None and wire.max_tokens != expect.broker_max_tokens:
        return (
            f"the broker was handed max tokens {wire.max_tokens}, "
            + f"expected {expect.broker_max_tokens}")

    for expected_temperature in expect.broker_temperatures or ():
        if not any(
                inference.temperature == expected_temperature
                for inference in run.broker_inferences):
            return f"no broker call carried temperature {_number(expected_temperature)}"

    schema = wire.response_schema_json if wire.response_schema_json is not None else ""

    if expect.broker_schema_contains is not None and expect.broker_schema_contains not in schema:
        shown_schema = (
            wire.response_schema_json if wire.response_schema_json is not None else "(null)")

        return (
            f"the schema on the wire never contained {show(expect.broker_schema_contains)}; "
            + f"it was {show(shown_schema)}")

    options = wire.provider_options_json if wire.provider_options_json is not None else ""

    shown_options = (
        wire.provider_options_json if wire.provider_options_json is not None else "(null)")

    for needle in expect.broker_options_include or ():
        if needle not in options:
            return (
                f"provider options on the wire lost {show(needle)}; "
                + f"they were {show(shown_options)}")

    for needle in expect.broker_options_exclude or ():
        if needle in options:
            return (
                f"provider options on the wire still carry the core-owned {show(needle)}: "
                + show(options))

    return None


def narration_failure(vector: Vector, run: VectorRun) -> str | None:
    """The Narration channel, certified from the streamed events themselves (SPEC.md 6.0).

    What it carried, in order, and what never appeared on any channel at all, which is what
    proves a withheld narration was withheld rather than rerouted.
    """
    expect = vector.expect

    if expect.narrations_contain is None and expect.narrations_exclude is None:
        return None

    if not vector.streamed and not vector.streamed_outcome:
        return (
            "narration expectations require \"streamed\" or \"streamedOutcome\": true; "
            + "the batched door produces and discards its events")

    narrations = [
        stream_event.content for stream_event in run.streamed_events
        if stream_event.type is AgentStreamEventType.NARRATION]

    cursor = 0

    for expected in expect.narrations_contain or ():
        found = next(
            (index for index in range(cursor, len(narrations)) if expected in narrations[index]),
            -1)

        if found < 0:
            return (
                f"no Narration event carried {show(expected)} in order; "
                + f"narrations were [{' | '.join(map(show, narrations))}]")

        cursor = found + 1

    for excluded in expect.narrations_exclude or ():
        leaked = next(
            (stream_event for stream_event in run.streamed_events
             if excluded in stream_event.content),
            None)

        if leaked is not None:
            return (
                f"{show(excluded)} appeared on the stream as a "
                + f"{enum_name(leaked.type)} event: {show(leaked.content)}")

    return None


def usage_failure(vector: Vector, run: VectorRun) -> str | None:
    """Usage as it is spent, certified from the streamed events themselves (SPEC.md 4.14.1).

    One event per model call, each carrying the run's total so far as a record and as its text,
    a total that grows with every call, and marked estimated when nobody reported it. Not the
    numbers themselves: every implementation counts in its own way where the provider says
    nothing, so a vector that pinned a figure would certify a tokenizer rather than the stream.
    """
    expect = vector.expect

    if expect.usage_events is None and expect.usage_estimated is None:
        return None

    if not vector.streamed and not vector.streamed_outcome:
        return (
            "usage expectations require \"streamed\" or \"streamedOutcome\": true; "
            + "the batched door produces and discards its events")

    usages = [
        stream_event for stream_event in run.streamed_events
        if stream_event.type is AgentStreamEventType.USAGE]

    if expect.usage_events is not None and len(usages) != expect.usage_events:
        return (
            f"the stream carried {len(usages)} Usage event(s), expected {expect.usage_events}, "
            + "one after every model call")

    previous_total = 0

    for usage_event in usages:
        if usage_event.usage is None:
            return f"a Usage event carried no record; its text was {show(usage_event.content)}"

        total_text = str(usage_event.usage.total_tokens)

        if usage_event.content != total_text:
            return (
                f"a Usage event's text was {show(usage_event.content)} while its record "
                + f"totals {total_text}")

        if usage_event.usage.total_tokens <= previous_total:
            return (
                f"the running total went from {previous_total} to "
                + f"{usage_event.usage.total_tokens}; every model call spends something, so "
                + "the total grows")

        previous_total = usage_event.usage.total_tokens

    if expect.usage_estimated is not None and usages:
        last_usage = usages[-1].usage
        last_estimate = last_usage.is_estimated if last_usage is not None else None

        if last_estimate != expect.usage_estimated:
            return (
                f"the last Usage event said estimated={last_estimate}, "
                + f"expected {expect.usage_estimated}")

    return None


def _runs_of(run: VectorRun, tool_name: str) -> int:
    tool = run.tools.get(tool_name)

    return len(tool.received_inputs) if tool is not None else 0


def _number(value: float) -> str:
    # A whole number reads as .NET writes it: 1, not 1.0.
    text = repr(value)

    return text[:-2] if text.endswith(".0") else text


def _sha256_hex(value: str) -> str:
    # The same fingerprint the decision log writes for a payload: SHA-256 of the UTF-8 bytes,
    # lowercase hex.
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
