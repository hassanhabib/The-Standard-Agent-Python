# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses
import uuid
from unittest.mock import call

import pytest

from standard_agents.models.coordinations.directions.perimeter_policy import PerimeterPolicy
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel
from standard_agents.services.coordinations.direction.direction_coordination_service import (
    DirectionCoordinationService)


async def test_should_return_and_terminate_on_act_if_direction_type_is_return_response(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        return_service,
        create_context_with_direction,
        create_random_string):

    # given
    answer = create_random_string()
    input_context = create_context_with_direction("ReturnResponse", answer)
    return_service.return_payload.return_value = answer

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.result == answer
    assert actual_context.status is AgentStatus.RESPONDED
    assert return_service.mock_calls == [call.return_payload(answer)]
    assert internal_tool_service.mock_calls == []
    assert external_tool_service.mock_calls == []


async def test_should_await_input_and_terminate_on_act_if_direction_type_is_await_input(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        return_service,
        create_context_with_direction,
        create_random_string):

    # given
    question = create_random_string()
    input_context = create_context_with_direction("AwaitInput", question)
    return_service.return_payload.return_value = question

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.result == question
    assert actual_context.status is AgentStatus.AWAITING_INPUT
    assert return_service.mock_calls == [call.return_payload(question)]
    assert internal_tool_service.mock_calls == []
    assert external_tool_service.mock_calls == []


async def test_should_refuse_and_terminate_on_act_if_direction_type_is_refuse(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        return_service,
        create_context_with_direction):

    # given
    refusal = "I'm not able to help with that."
    input_context = create_context_with_direction("Refuse", refusal)
    return_service.return_payload.return_value = refusal

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.result == refusal
    assert actual_context.status is AgentStatus.REFUSED
    assert internal_tool_service.mock_calls == []
    assert external_tool_service.mock_calls == []


async def test_should_run_internal_tool_and_append_observation_on_act(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        create_context_with_direction):

    # given
    input_context = create_context_with_direction("calculator", "1+1")
    internal_tool_service.handles.return_value = True
    internal_tool_service.run.return_value = "2"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.status is AgentStatus.WORKING
    assert _count_containing(actual_context.observations, "2") == 1
    assert external_tool_service.call.mock_calls == []


async def test_should_route_to_external_and_recover_on_act_if_tool_is_unknown(
        direction_coordination_service,
        internal_tool_service,
        external_tool_service,
        create_context_with_direction):

    # given
    input_context = create_context_with_direction("weather", "today")
    internal_tool_service.handles.return_value = False
    external_tool_service.call.return_value = "[external 'weather' not configured]"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.status is AgentStatus.WORKING
    assert _count_containing(actual_context.observations, "weather") == 1
    assert external_tool_service.mock_calls == [call.call("weather", "today")]
    assert internal_tool_service.run.mock_calls == []


async def test_should_preserve_existing_observations_on_act(
        direction_coordination_service,
        internal_tool_service,
        create_random_string):

    # given
    prior_observation = create_random_string()

    input_context = AgentContext(
        prompt=create_random_string(),
        direction_type="calculator",
        payload="1+1",
        observations=(prior_observation,))

    internal_tool_service.handles.return_value = True
    internal_tool_service.run.return_value = "2"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert len(actual_context.observations) == 2
    assert prior_observation in actual_context.observations


async def test_should_keep_working_on_act_if_tool_reports_an_error(
        direction_coordination_service,
        internal_tool_service,
        create_context_with_direction):

    # given
    input_context = create_context_with_direction("calculator", "not math")
    internal_tool_service.handles.return_value = True
    internal_tool_service.run.return_value = "error: could not parse expression"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.status is AgentStatus.WORKING

    assert _count_containing(
        actual_context.observations, "could not parse expression") == 1


async def test_should_set_result_to_tool_output_on_act_even_if_non_terminal(
        direction_coordination_service,
        internal_tool_service,
        create_context_with_direction):

    # given
    input_context = create_context_with_direction("loop", "x")
    internal_tool_service.handles.return_value = True
    internal_tool_service.run.return_value = "again"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert actual_context.result == "again"
    assert actual_context.status is AgentStatus.WORKING


async def test_should_name_tool_in_observation_on_act(
        direction_coordination_service,
        internal_tool_service,
        create_context_with_direction):

    # given
    input_context = create_context_with_direction("calculator", "1+1")
    internal_tool_service.handles.return_value = True
    internal_tool_service.run.return_value = "2"

    # when
    actual_context = await direction_coordination_service.act(input_context)

    # then
    assert _count_containing(actual_context.observations, "calculator", "2") == 1


async def test_should_tell_the_brain_a_replay_already_ran_on_act(
        direction_coordination_service,
        internal_tool_service,
        create_context_with_direction):
    """Handed back bare, a replay reads as a fresh answer to a fresh ask.

    A model that asked because it did not have what it wanted asks again (SPEC.md 4.9, v1.14).
    """
    with AgentRun.begin():
        # given
        internal_tool_service.handles.return_value = True
        internal_tool_service.run.return_value = "4"

        first = await direction_coordination_service.act(
            create_context_with_direction("calculator", "2 + 2"))

        # when
        second = await direction_coordination_service.act(
            dataclasses.replace(first, direction_type="calculator", payload="2 + 2"))

        # then
        # The first outcome whole, then the note. The tool ran once.
        assert second.result.startswith("4")
        assert "already ran in this run with the same arguments" in second.result
        assert internal_tool_service.run.mock_calls == [call("calculator", "2 + 2")]


async def test_should_mark_an_exchange_the_ledger_answered_as_replayed_on_act(
        direction_coordination_service,
        internal_tool_service,
        create_context_with_direction):
    """A loop that counts a run's repeated asks has to tell a replay from a call that ran.

    A read after an edit is the same ask and is not a repeat (SPEC.md 3.2, v1.14).
    """
    with AgentRun.begin():
        # given
        internal_tool_service.handles.return_value = True
        internal_tool_service.run.return_value = "4"

        first = await direction_coordination_service.act(
            dataclasses.replace(
                create_context_with_direction("calculator", "2 + 2"),
                tool_call_id="call_1"))

        # when
        second = await direction_coordination_service.act(
            dataclasses.replace(
                first,
                direction_type="calculator",
                payload="2 + 2",
                tool_call_id="call_2"))

        # then
        assert [exchange.replayed for exchange in second.tool_exchanges] == [False, True]


async def test_should_answer_a_third_identical_ask_with_the_note_alone_on_act(
        direction_coordination_service,
        internal_tool_service,
        create_context_with_direction):
    """Watched live: a page of a file asked for fourteen more times.

    Each was answered with the same sixteen kilobytes and the same note. The note was right and
    was not enough, and every copy cost the person a turn's worth of context (SPEC.md 4.9,
    v1.14).
    """
    with AgentRun.begin():
        # given
        internal_tool_service.handles.return_value = True
        internal_tool_service.run.return_value = "the whole page"

        first = await direction_coordination_service.act(
            create_context_with_direction("read_file", "a.txt"))

        second = await direction_coordination_service.act(
            dataclasses.replace(first, direction_type="read_file", payload="a.txt"))

        # when
        third = await direction_coordination_service.act(
            dataclasses.replace(second, direction_type="read_file", payload="a.txt"))

        # then
        # Not a third copy of the bytes: the model has had them twice.
        assert second.result.startswith("the whole page")
        assert "the whole page" not in third.result
        assert "asked for a third time with the same arguments" in third.result


async def test_should_look_again_at_a_scope_the_run_has_since_written_to_on_act(
        scoped_file_service,
        internal_tool_service,
        create_context_with_direction):
    """Watched in both reference implementations.

    A model edited a file and read it back to check its edit, and was handed the file as it was
    before the edit, because the read had the same tool and the same arguments as the read
    before it (SPEC.md 4.9, v1.14).
    """
    # Inside a run, as every act is: what a run has written is the run's to know.
    with AgentRun.begin():
        # given
        internal_tool_service.handles.return_value = True
        internal_tool_service.run.side_effect = _file_tools("version one", "version two")

        first_read = await scoped_file_service.act(
            create_context_with_direction("read_file", "a.txt"))

        written = await scoped_file_service.act(
            dataclasses.replace(first_read, direction_type="write_file", payload="version two"))

        # when
        second_read = await scoped_file_service.act(
            dataclasses.replace(written, direction_type="read_file", payload="a.txt"))

        # then
        # The look after the write is a new question: it runs, and sees what the write left.
        assert second_read.result == "version two"
        assert internal_tool_service.run.mock_calls.count(call("read_file", "a.txt")) == 2


async def test_should_look_again_at_a_scope_written_to_before_the_run_was_resumed_on_act(
        scoped_file_service,
        internal_tool_service,
        create_context_with_direction):
    """A run read a file, wrote to it, and paused.

    Resumed, it keeps its identity, so the ledger still holds the read from before the write,
    and it begins with nothing performed. The writes before the pause are in the conversation it
    was resumed with, and a count read from the run alone handed the resumed read the file as it
    was before the write.
    """
    # given
    run_id = uuid.uuid4().hex
    internal_tool_service.handles.return_value = True
    internal_tool_service.run.side_effect = _file_tools("version one", "version two")

    with AgentRun.begin(run_id):
        first_read = await scoped_file_service.act(
            create_context_with_direction("read_file", "a.txt"))

        written = await scoped_file_service.act(
            dataclasses.replace(first_read, direction_type="write_file", payload="version two"))

    resumed = dataclasses.replace(
        written,
        direction_type="read_file",
        payload="a.txt",
        tool_exchanges=(
            ToolExchange("call-1", "read_file", "a.txt", "version one"),
            ToolExchange("call-2", "write_file", "version two", "written")))

    # when
    with AgentRun.begin(run_id):
        second_read = await scoped_file_service.act(resumed)

    # then
    assert second_read.result == "version two"
    assert internal_tool_service.run.mock_calls.count(call("read_file", "a.txt")) == 2


@pytest.fixture
def scoped_file_service(new_perimeter, new_execution, logging_broker):
    """A file tool pair over one scope: a SAFE read and a SENSITIVE write.

    Both name the same file, the way a coding agent's tools do.
    """
    return DirectionCoordinationService(
        perimeter_service=new_perimeter(),
        execution_service=new_execution(),
        logging_broker=logging_broker,
        policy=PerimeterPolicy(
            tool_risk={"write_file": RiskLevel.SENSITIVE},
            tool_scope={
                "read_file": lambda _: "a.txt",
                "write_file": lambda _: "a.txt"}))


def _file_tools(*read_outcomes: str):
    """The read answers each outcome in turn; the write of "version two" answers "written"."""
    remaining_read_outcomes = iter(read_outcomes)

    def run(name: str, input: str) -> str | None:
        if (name, input) == ("read_file", "a.txt"):
            return next(remaining_read_outcomes)

        if (name, input) == ("write_file", "version two"):
            return "written"

        return None

    return run


def _count_containing(observations: tuple[str, ...], *texts: str) -> int:
    """How many observations contain every text (ContainSingle with a Contains predicate)."""
    return sum(1 for observation in observations if all(text in observation for text in texts))
