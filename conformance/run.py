# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""One vector, run through the door it names: batched, streamed, the streamed outcome, a batch
of concurrent requests, concurrent prompts, or prompts in order."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from standard_agents import StandardAgent
from standard_agents.brokers.sessions.file_session_broker import FileSessionBroker
from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.brokers.sessions.agent_session import AgentTurn
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange

from conformance.brokers.scripted_native_generator_broker import ScriptedNativeGeneratorBroker
from conformance.composition import VectorComposition
from conformance.models.request_spec import RequestSpec
from conformance.models.vector import Vector
from conformance.models.vector_run import VectorRun


@dataclass
class _Ending:
    """What the door reported, beyond the text: the batched door and the plain stream say
    nothing more, the others say how the run ended."""

    result: str = ""
    status: AgentStatus | None = None
    pending_effect_tool: str | None = None
    failure_code: str | None = None
    prompt_results: list[str] = field(default_factory=list)


async def run_vector(vector: Vector, base_directory: Path) -> VectorRun:
    composition = VectorComposition(vector, base_directory)
    agent = await composition.build_agent()
    prompts = vector.prompts if vector.prompts else [vector.prompt]

    cancellation = asyncio.Event()

    if vector.cancel_before_start:
        cancellation.set()

    # Every event a streamed run produced, so a vector can certify the Narration channel: what
    # it carried, and what never appeared on any channel at all.
    streamed_events: list[AgentStreamEvent] = []

    if vector.requests:
        ending = await _run_requests(vector, agent, prompts, cancellation)
    elif vector.request is not None:
        ending = await _run_request(vector, agent, streamed_events, cancellation)
    elif vector.concurrent:
        ending = await _run_concurrent_prompts(vector, agent, prompts)
    else:
        ending = await _run_prompts_in_order(vector, composition, agent, prompts, cancellation)

    # The pending effect rides the OUTCOME as well as the session (design 6.2): the outcome is
    # what a stateless exposer reads, the session is what a different process reads. The harness
    # prefers the outcome and falls back to the session, so a vector can certify either seam.
    pending_effect_tool = ending.pending_effect_tool

    if (pending_effect_tool is None
            and vector.session_id is not None
            and vector.expect.pending_effect_tool is not None):
        session = await FileSessionBroker(str(composition.sessions_path)).select_session(
            vector.session_id)

        pending_effect_tool = (
            session.pending_effect.tool_name
            if session is not None and session.pending_effect is not None else None)

    _record_native_model_inputs(
        composition.native_generator, composition.model_inputs, composition.brain_inputs)

    # What the session holds once every prompt has run, read from the store the agent wrote to,
    # so a turn a concurrent save erased is a turn this harness can miss (SPEC.md 4.11).
    session_turn_count = None

    if vector.session_id is not None and vector.expect.session_turn_count is not None:
        recorded_session = await FileSessionBroker(
            str(composition.sessions_path)).select_session(vector.session_id)

        session_turn_count = (
            len(recorded_session.history) if recorded_session is not None else None)

    return VectorRun(
        result=ending.result,
        prompt_results=ending.prompt_results,
        tools=composition.stub_tools,
        gate_rubric=composition.gate_rubric,
        judge_rubric=composition.judge_rubric,
        judge_input=composition.judge_input,
        model_inputs=composition.model_inputs,
        brain_inputs=composition.brain_inputs,
        prompt_screenings=composition.prompt_screenings,
        audit_records=composition.audit_records,
        compensation_order=composition.compensation_order,
        native_generator=composition.native_generator,
        policy_principals=composition.policy_principals,
        mcp_server_calls=[server.call_count for server in composition.scripted_mcp_servers],
        agent_inputs=composition.agent_inputs,
        status=ending.status,
        pending_effect_tool=pending_effect_tool,
        broker_inferences=(
            composition.honoring_generator.inferences
            if composition.honoring_generator is not None else ()),
        streamed_events=streamed_events,
        session_turn_count=session_turn_count,
        failure_code=ending.failure_code)


async def _run_requests(
        vector: Vector,
        agent: StandardAgent,
        prompts: list[str],
        cancellation: asyncio.Event) -> _Ending:
    # One composition, many callers, all at once: the acceptance criterion itself
    # (docs/per-request-inference.md 7).
    outcomes = await asyncio.gather(*(
        agent.run_request(
            _to_request(vector, prompts[min(index, len(prompts) - 1)], spec),
            cancellation=cancellation)
        for index, spec in enumerate(vector.requests)))

    return _ending_of(outcomes[0])


async def _run_request(
        vector: Vector,
        agent: StandardAgent,
        streamed_events: list[AgentStreamEvent],
        cancellation: asyncio.Event) -> _Ending:
    request = _to_request(vector, vector.prompt, vector.request)

    if vector.streamed_outcome:
        # The third door (SPEC.md 4.14): every event live, and the completion carrying the same
        # structured outcome the batched door returns.
        run_stream = agent.run_stream(request, cancellation=cancellation)
        responses = await _read_stream(run_stream, streamed_events)
        ending = _ending_of(run_stream.outcome)
        ending.result = responses

        return ending

    if vector.streamed:
        stream = agent.process_prompt_stream(request, cancellation=cancellation)

        return _Ending(result=await _read_stream(stream, streamed_events))

    return _ending_of(await agent.run_request(request, cancellation=cancellation))


async def _run_concurrent_prompts(
        vector: Vector,
        agent: StandardAgent,
        prompts: list[str]) -> _Ending:
    session_id = vector.session_id if vector.session_id is not None else ""

    results = await asyncio.gather(*(
        agent.process_prompt(prompt, session_id=session_id) for prompt in prompts))

    return _Ending(result=results[0], prompt_results=list(results))


async def _run_prompts_in_order(
        vector: Vector,
        composition: VectorComposition,
        agent: StandardAgent,
        prompts: list[str],
        cancellation: asyncio.Event) -> _Ending:
    session_id = vector.session_id if vector.session_id is not None else ""
    ending = _Ending()

    for prompt in prompts:
        # A new instance per prompt where the vector asks for it: nothing but the files survives
        # between them, which is what makes the next prompt a different process rather than the
        # same one carrying on.
        instance = await composition.build_agent() if vector.new_instance_per_prompt else agent

        ending.result = await instance.process_prompt(
            prompt, session_id=session_id, cancellation=cancellation)

        ending.prompt_results.append(ending.result)

    return ending


async def _read_stream(stream, streamed_events: list[AgentStreamEvent]) -> str:
    responses: list[str] = []

    async for stream_event in stream:
        streamed_events.append(stream_event)

        if stream_event.type is AgentStreamEventType.RESPONSE:
            responses.append(stream_event.content)

    return "".join(responses)


def _ending_of(outcome: AgentOutcome) -> _Ending:
    return _Ending(
        result=outcome.result,
        status=outcome.status,
        pending_effect_tool=(
            outcome.pending_effect.tool_name if outcome.pending_effect is not None else None),
        failure_code=outcome.failure.code if outcome.failure is not None else None)


def _to_request(vector: Vector, prompt: str, spec: RequestSpec) -> PromptRequest:
    return PromptRequest(
        prompt=prompt,
        session_id=vector.session_id if vector.session_id is not None else "",
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
        seed=spec.seed,
        stop=tuple(spec.stop or ()),
        response_schema_json=spec.response_schema_json,
        provider_options_json=spec.provider_options_json,
        history=tuple(
            AgentTurn(
                turn.prompt,
                turn.answer,
                exchanges=tuple(
                    ToolExchange(
                        exchange.call_id,
                        exchange.tool_name,
                        exchange.arguments_json,
                        exchange.result)
                    for exchange in turn.exchanges or ()))
            for turn in spec.history or ()),
        caller_tools=tuple(
            ToolDefinition(tool.name, tool.description, tool.parameters_json)
            for tool in spec.caller_tools or ()),
        cite_knowledge=spec.cite_knowledge)


def _record_native_model_inputs(
        native_generator: ScriptedNativeGeneratorBroker | None,
        model_inputs: list[str],
        brain_inputs: list[str]) -> None:
    """A native conversation is a model call too (SPEC.md 4.6).

    Everything the scripted V1 model was shown joins what the text models saw, message content
    AND the arguments of every tool call replayed to it, so a replayed call carrying a value in
    the clear is a leak this harness can see. Without this, a native vector asserting
    no_model_sees certified nothing at all.
    """
    if native_generator is None:
        return

    for conversation in native_generator.conversations:
        for message in conversation:
            model_inputs.append(message.content)
            brain_inputs.append(message.content)

            for tool_call in message.tool_calls:
                model_inputs.append(tool_call.arguments_json)
                brain_inputs.append(tool_call.arguments_json)
