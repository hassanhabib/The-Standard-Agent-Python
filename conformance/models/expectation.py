# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Expectation:
    """What a vector's run must show. Every assertion is optional; one left unset checks nothing.

    A typo'd field must fail loudly, not silently delete the assertion it carried: a vector that
    asserts less than it appears to reads as coverage (SPEC.md 1.1).
    """

    REJECTS_UNKNOWN_PROPERTIES: ClassVar[bool] = True

    result: str | None
    result_contains: str | None
    tool_input: dict[str, str] | None

    # Guardian-rubric assertions. Each substring must appear in (contains), or be absent from
    # (excludes), BOTH the composed Gate rubric AND the composed Judge rubric, since a
    # constitution binds both guardians and a consumption skill replaces the policy in both.
    guardian_rubric_contains: list[str] | None = None
    guardian_rubric_excludes: list[str] | None = None

    # Decision-log assertions (SPEC.md 4.7, 4.4), observed through the log's custom sink so the
    # certification does not depend on any particular storage.
    #
    #   audit_run_count: how many distinct runs the log must hold: one per prompt, never fewer.
    #       Fewer means runs were merged or discarded.
    #   audit_retains_every_prompt: every prompt's evidence must still be present at the end,
    #       which is what fails when beginning a run truncates the log.
    #   audit_sequences_unique_per_run: within a run the record numbers must not repeat, which
    #       is what fails when run counters are shared between runs.
    audit_run_count: int | None = None
    audit_retains_every_prompt: bool = False
    audit_sequences_unique_per_run: bool = False

    # Guardian-input assertions (SPEC.md 4.2, 7.6).
    #
    #   judge_saw_task: the task must have reached the Judge, not the candidate alone.
    #   guardian_never_answers: a guardian that tries to answer or act must be neutralized, and
    #       its text must never become the agent's result.
    judge_saw_task: bool = False
    guardian_never_answers: bool = False

    # This text must not appear in ANY model call: not the Brain's prompt, not the Gate's
    # input, not the Judge's. Redaction that covers one call and not the others does not
    # satisfy SPEC.md 4.6.
    no_model_sees: str | None = None

    # Perimeter assertions (SPEC.md 4.9, 7.7).
    #
    #   tool_never_ran: these tools must not have executed at all. Held is not performed.
    #   tool_run_count: exactly how many times each tool executed, which is how run-once is
    #       certified: proposing an act three times must still run it once.
    #   brain_never_sees: this text must never reach the Brain, however it entered as Data.
    tool_never_ran: list[str] | None = None
    tool_run_count: dict[str, int] | None = None
    brain_never_sees: str | None = None

    #   brain_sees: this text must have reached the Brain, which is how retrieval is certified:
    #       the passage that answers the question got there.
    #   gate_screened_prompt_times: exactly how many times the Gate was asked about the prompt.
    brain_sees: str | None = None
    gate_screened_prompt_times: int | None = None

    # The exact order the tools were reversed in, which is how the reverse unwind is certified:
    # a later effect may depend on an earlier one, so undoing them in the order they ran would
    # leave state inconsistent.
    compensation_order: list[str] | None = None

    # The tool's result must come back to the model as a tool message naming the call that
    # asked for it, and the assistant's request must be replayed alongside it. This is the one
    # thing the text protocol cannot express, so it is the one thing worth certifying about
    # native tool calling (SPEC.md 6).
    tool_result_answers_call: str | None = None

    # One entry per prompt, in order: what each PROMPT's result must carry. The single
    # result / result_contains sees only the last prompt, so a multi-prompt vector could
    # misbehave on every run but its final one and still print PASS.
    results_contain: list[str] | None = None

    # The identity the policy broker was actually handed when it decided. An audit record naming
    # the caller afterwards is not authorization, so this reads the decision's input rather than
    # the log (SPEC.md 4.9).
    policy_saw_principal: str | None = None

    #   mcp_server_calls: exactly how many calls each scripted server received, in registration
    #       order. Routing across servers is certified by the owner being called and the
    #       bystander not (SPEC.md 4.8 v1.5).
    #   brain_sees_every: every entry must have reached the Brain, which is how accumulation is
    #       certified: a source silently replaced is a source whose text is absent.
    mcp_server_calls: list[int] | None = None
    brain_sees_every: list[str] | None = None

    # The composition refusal must carry this text: a refusal that does not name the offending
    # entry leaves the host searching the document by hand (SPEC.md 4.8 v1.4).
    configuration_refusal_names: str | None = None

    # Each named fleet agent must have RECEIVED a handoff containing this text, which is how
    # grounding is certified (SPEC.md 4.8 v1.6): the specialist saw the user's actual ask (or
    # the transfer's task), not the task alone.
    agent_input: dict[str, str] | None = None

    # Per-request assertions (docs/per-request-inference.md).
    #
    #   status: how the run ended ("Responded", "AwaitingInput", ...), read through run_request
    #       because a held caller call and an answer read alike as text.
    #   pending_effect_tool: the tool name the session's pending effect must carry, which is
    #       how a caller's call is handed to whoever resumes (design 6.2).
    #   broker_temperature / broker_max_tokens: what the scripted Brain was handed, after
    #       precedence resolved at the boundary.
    #   broker_temperatures: every temperature the Brain was handed across concurrent requests,
    #       in any order: one composition, each run keeping its own.
    #   broker_schema_contains: the schema that reached the wire must contain this text, which
    #       is how "one schema survives and seeds both" is certified.
    #   broker_options_include / broker_options_exclude: passthrough keys that must / must not
    #       have survived the core-owned-keys strip (design 4.4).
    status: str | None = None
    pending_effect_tool: str | None = None

    # How many turns the session's history holds once every prompt has run, read from the
    # store afterwards. Under concurrent prompts this is what fails when the last writer erases
    # another's turn (SPEC.md 4.11).
    session_turn_count: int | None = None
    broker_temperature: float | None = None
    broker_max_tokens: int | None = None
    broker_temperatures: list[float] | None = None
    broker_schema_contains: str | None = None
    broker_options_include: list[str] | None = None
    broker_options_exclude: list[str] | None = None

    # Narration assertions (SPEC.md 6.0), observable only on a streamed run: the batched door
    # produces and discards its events, so these require "streamed": true.
    #
    #   narrations_contain: each entry must appear, in order, among the Narration events'
    #       contents.
    #   narrations_exclude: this text must appear in NO stream event of any kind, which is what
    #       proves a withheld narration was withheld and never leaked into Thinking on its way to
    #       the verdict.
    narrations_contain: list[str] | None = None
    narrations_exclude: list[str] | None = None

    # The code the run's outcome reports for a stop without an answer (SPEC.md 3.6, v1.14):
    # cancelled, budget_exhausted, turns_exhausted, going_in_circles.
    failure_code: str | None = None

    # Usage as it is spent (SPEC.md 4.14.1, v1.15), observable only on a streamed run.
    #
    #   usage_events: how many Usage events the run carried: one per model call the loop made
    #       for the Brain. Each must carry its record, a total that grows, and that total as its
    #       text.
    #   usage_estimated: whether the last one says it was counted locally rather than reported.
    #       The scripted Brain reports nothing, so every count here is estimated, and one
    #       presented as a measurement fails.
    usage_events: int | None = None
    usage_estimated: bool | None = None
