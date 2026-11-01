# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.mcps import mcp_json
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from xeptions import Xeption


class SameExceptionAs:
    """Matches, in a recorded call, an exception equivalent to the expected one."""

    def __init__(self, expected_exception: Xeption) -> None:
        self.expected_exception = expected_exception

    def __eq__(self, actual_exception: object) -> bool:
        return self.expected_exception.same_exception_as(actual_exception)

    def __repr__(self) -> str:
        return f"SameExceptionAs({self.expected_exception!r})"


@pytest.fixture
def mcp_broker() -> McpBroker:
    return create_autospec(McpBroker, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def external_tool_service(mcp_broker, logging_broker) -> ExternalToolService:
    return ExternalToolService(mcp_broker=mcp_broker, logging_broker=logging_broker)


@pytest.fixture
def same_exception_as():
    return SameExceptionAs


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def expected_arguments_json():
    """What the foundation hands the broker for plain text.

    The text as the one argument a schema-less tool understands. A JSON object is handed over
    as given.
    """
    return lambda input: mcp_json.to_json_string({"input": input})
