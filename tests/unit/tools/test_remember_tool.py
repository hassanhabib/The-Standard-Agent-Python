# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import json
from unittest.mock import create_autospec

import pytest

from standard_agents.services.foundations.memories.memory_service import MemoryService
from standard_agents.tools.remember_tool import RememberTool


async def test_should_write_to_memory_on_execute():
    # given
    fact = "Hassan works on PeerLLM"
    remembered = []

    async def remember(memory):
        remembered.append(memory)

    remember_tool = RememberTool(remember)

    # when
    actual_result = await remember_tool.execute(fact)

    # then
    assert fact in actual_result
    assert remembered == [fact]


async def test_should_extract_fact_from_structured_arguments_on_execute():
    # given
    remembered = []

    async def remember(memory):
        remembered.append(memory)

    remember_tool = RememberTool(remember)

    # when
    await remember_tool.execute('{"fact":"Paris is the capital of France"}')

    # then
    assert remembered == ["Paris is the capital of France"]


# The converting alias keeps working (the same guarantee the local_brain to on_brain aliases
# carry), but nothing of the service survives into the tool: it accepts the service and keeps
# only its routine.
async def test_should_keep_the_obsolete_service_constructor_behaving():
    # given
    memory_service = create_autospec(MemoryService, instance=True)

    with pytest.deprecated_call():
        remember_tool = RememberTool(memory_service)

    # when
    await remember_tool.execute("a fact worth keeping")

    # then
    memory_service.remember.assert_awaited_once_with("a fact worth keeping")


# A tool's parameters is a JSON SCHEMA the wire validates strictly: Azure OpenAI rejects the WHOLE
# request when any advertised tool's parameters is not a schema of type object. This tool shipped
# plain JSON ('{ "fact": "..." }') and production found it: every native run against a strict
# provider 400'd the moment memory was composed in.
def test_should_declare_parameters_as_a_json_schema_object():
    # given
    async def remember(memory):
        pass

    tool = RememberTool(remember)

    # when
    schema = json.loads(tool.parameters)

    # then
    assert schema["type"] == "object"
    assert schema["properties"]["fact"]["type"] == "string"
