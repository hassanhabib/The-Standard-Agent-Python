# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.agent import Agent


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def nested_agent() -> Agent:
    return create_autospec(Agent, instance=True)
