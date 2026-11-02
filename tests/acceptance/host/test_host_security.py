# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus

# The same host, with the door locked by the one configuration line hosting.md documents.
_LOCKED = {"Host:ApiKey": "psk-test"}


async def test_should_refuse_agent_routes_without_the_api_key_through_http(
        agent,
        serve_host,
        v1_document):

    async with serve_host(_LOCKED) as client:
        # when
        run_response = await client.post_json(
            "api/V1/agents/runs",
            v1_document(prompt="what is owed"))

        heartbeat = await client.get("api/home")

    # then: the agent route is 401 before any run starts; the heartbeat stays open
    assert run_response.status == 401
    assert heartbeat.status == 200
    agent.run.assert_not_called()
