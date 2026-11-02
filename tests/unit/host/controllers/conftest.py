# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from unittest.mock import create_autospec

import pytest

from standard_agents.agent import Agent
from standard_agents.host.controllers.agents_controller import AgentsController
from standard_agents.host.controllers.v1.agents_v1_controller import AgentsV1Controller


@pytest.fixture
def agent():
    return create_autospec(Agent, instance=True)


@pytest.fixture
def agents_controller(agent):
    return AgentsController(agent)


@pytest.fixture
def agents_v1_controller(agent):
    return AgentsV1Controller(agent)
