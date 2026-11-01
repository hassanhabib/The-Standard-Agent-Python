# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import asyncio
import uuid
from collections.abc import AsyncIterator
from unittest.mock import create_autospec

import pytest

from standard_agents.brokers.contracts.rule_contract_broker import RuleContractBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.models.foundations.usages.agent_usage import AgentUsage
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.coordinations.decision.decision_coordination_service import (
    DecisionCoordinationService)
from standard_agents.services.coordinations.decision.decision_stream import DecisionStream
from standard_agents.services.foundations.brains.brain_service import BrainService
from standard_agents.services.foundations.contracts.contract_service import ContractService
from standard_agents.services.foundations.gates.gate_service import GateService
from standard_agents.services.foundations.judges.judge_service import JudgeService
from standard_agents.services.foundations.usages.usage_service import UsageService
from standard_agents.services.orchestrations.decision.guardians.guardian_orchestration_service \
    import GuardianOrchestrationService
from standard_agents.services.orchestrations.decision.inferences.inference_orchestration_service \
    import InferenceOrchestrationService
from xeptions import Xeption


class SameExceptionAs:
    """Matches, in a recorded call, an exception equivalent to the expected one."""

    def __init__(self, expected_exception: Xeption) -> None:
        self.expected_exception = expected_exception

    def __eq__(self, actual_exception: object) -> bool:
        return self.expected_exception.same_exception_as(actual_exception)

    def __repr__(self) -> str:
        return f"SameExceptionAs({self.expected_exception!r})"


class Containing:
    """Matches, in a recorded call, any text that contains every expected fragment."""

    def __init__(self, *expected_fragments: str) -> None:
        self.expected_fragments = expected_fragments

    def __eq__(self, actual_text: object) -> bool:
        return isinstance(actual_text, str) and all(
            expected_fragment in actual_text for expected_fragment in self.expected_fragments)

    def __repr__(self) -> str:
        return f"Containing{self.expected_fragments!r}"


@pytest.fixture
def gate_service() -> GateService:
    gate_service = create_autospec(GateService, instance=True)

    # A loose Moq mock answers an unarranged string call with null, and most of these tests
    # never arrange the conflict check. The coordination reads that as "no conflict".
    gate_service.detect_conflict.return_value = None

    return gate_service


@pytest.fixture
def brain_service() -> BrainService:
    brain_service = create_autospec(BrainService, instance=True)

    # A loose Moq mock answers an unarranged bool with false: the text protocol.
    brain_service.speaks_natively = False

    return brain_service


@pytest.fixture
def judge_service() -> JudgeService:
    return create_autospec(JudgeService, instance=True)


@pytest.fixture
def usage_service() -> UsageService:
    usage_service = create_autospec(UsageService, instance=True)

    # Measurement is not what these tests are about, so it answers "nothing consumed" and stays
    # out of the way, rather than fault every path through Inference for a reason unrelated to
    # the assertion.
    usage_service.measure.return_value = AgentUsage.EMPTY

    return usage_service


@pytest.fixture
def logging_broker() -> LoggingBroker:
    return create_autospec(LoggingBroker, instance=True)


@pytest.fixture
def decision_coordination_service(
        gate_service,
        brain_service,
        judge_service,
        usage_service,
        logging_broker) -> DecisionCoordinationService:

    # Real regions over mocked foundations: the mocks sit where they sat before
    # regionalization, so every assertion is unchanged.
    return DecisionCoordinationService(
        inference_service=InferenceOrchestrationService(
            brain_service=brain_service,
            usage_service=usage_service,
            logging_broker=logging_broker),
        guardian_service=GuardianOrchestrationService(
            gate_service=gate_service,
            judge_service=judge_service,
            contract_service=ContractService(
                contract_broker=RuleContractBroker(),
                logging_broker=logging_broker),
            logging_broker=logging_broker),
        logging_broker=logging_broker)


@pytest.fixture
def create_random_string():
    return lambda: uuid.uuid4().hex


@pytest.fixture
def create_random_agent_context(create_random_string):
    return lambda: AgentContext(
        prompt=create_random_string(),
        system_prompt=create_random_string())


@pytest.fixture
def setup_gate_allows(gate_service):
    def setup() -> None:
        gate_service.screen.return_value = "allow"

    return setup


@pytest.fixture
def setup_judge_approves(judge_service):
    def setup() -> None:
        judge_service.evaluate.return_value = Judgement(score=1.0)

    return setup


@pytest.fixture
def to_async_stream():
    async def stream(*tokens: str) -> AsyncIterator[str]:
        for token in tokens:
            await asyncio.sleep(0)

            yield token

    return stream


@pytest.fixture
def drain():
    async def drained(decision_stream: DecisionStream) -> list[AgentStreamEvent]:
        return [stream_event async for stream_event in decision_stream]

    return drained


@pytest.fixture
def same_exception_as():
    return SameExceptionAs


@pytest.fixture
def containing():
    return Containing
