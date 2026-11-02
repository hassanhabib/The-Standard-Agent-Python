# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import pytest

from standard_agents.host.models.v1.agent_run_request_v1 import AgentRunRequestV1
from standard_agents.host.models.v1.agent_turn_v1 import AgentTurnV1
from standard_agents.host.models.v1.caller_tool_v1 import CallerToolV1
from standard_agents.host.models.v1.tool_exchange_v1 import ToolExchangeV1
from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.brokers.sessions.agent_session import AgentTurn
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange


@pytest.fixture
def full_request() -> AgentRunRequestV1:
    return AgentRunRequestV1(
        prompt="what is owed",
        session_id="trip-3",
        history=(AgentTurnV1(prompt="hello", answer="hi"),),

        tool_exchanges=(
            ToolExchangeV1(
                call_id="call-1",
                tool_name="lookup",
                arguments_json='{"account":"42"}',
                result="owed: 12"),),

        caller_tools=(
            CallerToolV1(
                name="lookup",
                description="looks up an account",
                parameters_json='{"type":"object"}'),),

        response_schema_json='{"type":"object"}',
        temperature=0.2,
        max_tokens=256,
        seed=7,
        stop=("END",),
        provider_options_json='{"thinking":true}')


@pytest.fixture
def expected_prompt_request() -> PromptRequest:
    return PromptRequest(
        prompt="what is owed",
        session_id="trip-3",
        history=(AgentTurn(prompt="hello", answer="hi"),),

        tool_exchanges=(
            ToolExchange(
                call_id="call-1",
                tool_name="lookup",
                arguments_json='{"account":"42"}',
                result="owed: 12"),),

        response_schema_json='{"type":"object"}',
        temperature=0.2,
        max_tokens=256,
        seed=7,
        stop=("END",),

        caller_tools=(
            ToolDefinition(
                name="lookup",
                description="looks up an account",
                parameters_json='{"type":"object"}'),),

        provider_options_json='{"thinking":true}')
