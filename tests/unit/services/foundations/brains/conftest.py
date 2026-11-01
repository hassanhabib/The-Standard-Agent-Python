# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import uuid
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.services.foundations.brains.brain_service import BrainService
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
def generator_broker() -> GeneratorBroker:
    return create_autospec(GeneratorBroker, instance=True)


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def brain_service(generator_broker, logging_broker) -> BrainService:
    return BrainService(generator_broker=generator_broker, logging_broker=logging_broker)


@pytest.fixture
def same_exception_as():
    return SameExceptionAs


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def to_async_stream():
    async def stream(*tokens: str):
        for token in tokens:
            await asyncio.sleep(0)

            yield token

    return stream


@pytest.fixture
def throwing_stream():
    async def stream(exception: Exception):
        await asyncio.sleep(0)

        raise exception

        yield

    return stream


@pytest.fixture
def drain():
    async def drain_stream(stream) -> list[str]:
        return [token async for token in stream]

    return drain_stream
