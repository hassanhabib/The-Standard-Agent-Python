# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from datetime import timedelta

from standard_agents.agent import Agent
from standard_agents.brokers.approvals.not_configured_approval_broker import (
    NotConfiguredApprovalBroker)
from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.classifiers.not_configured_classifier_broker import (
    NotConfiguredClassifierBroker)
from standard_agents.brokers.contracts.rule_contract_broker import RuleContractBroker
from standard_agents.brokers.effects.in_memory_effect_ledger_broker import (
    InMemoryEffectLedgerBroker)
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.generators.openai_generator_broker import OpenAiGeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.loggings.stdlib_logging_broker import StdlibLoggingBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.mcps.not_configured_mcp_broker import NotConfiguredMcpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.policies.not_configured_policy_broker import (
    NotConfiguredPolicyBroker)
from standard_agents.brokers.sessions.not_configured_session_broker import (
    NotConfiguredSessionBroker)
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.brokers.times.system_time_broker import SystemTimeBroker
from standard_agents.brokers.tools.in_memory_tool_broker import InMemoryToolBroker
from standard_agents.brokers.usages.ratio_usage_broker import RatioUsageBroker
from standard_agents.brokers.usages.usage_broker import UsageBroker
from standard_agents.brokers.verifiers.not_configured_verifier_broker import (
    NotConfiguredVerifierBroker)
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.inference_settings import InferenceSettings
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.services.coordinations.data.data_coordination_service import (
    DataCoordinationService)
from standard_agents.services.coordinations.decision.decision_coordination_service import (
    DecisionCoordinationService)
from standard_agents.services.coordinations.direction.direction_coordination_service import (
    DirectionCoordinationService)
from standard_agents.services.foundations.approvals.approval_service import ApprovalService
from standard_agents.services.foundations.brains.brain_service import BrainService
from standard_agents.services.foundations.contracts.contract_service import ContractService
from standard_agents.services.foundations.effect_ledgers.effect_ledger_service import (
    EffectLedgerService)
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
from standard_agents.services.foundations.gates.gate_service import GateService
from standard_agents.services.foundations.internal_tools.internal_tool_service import (
    InternalToolService)
from standard_agents.services.foundations.judges.judge_service import JudgeService
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from standard_agents.services.foundations.memories.memory_service import MemoryService
from standard_agents.services.foundations.policies.policy_service import PolicyService
from standard_agents.services.foundations.returns.return_service import ReturnService
from standard_agents.services.foundations.sessions.session_service import SessionService
from standard_agents.services.foundations.skills.skill_service import SkillService
from standard_agents.services.foundations.usages.usage_service import UsageService
from standard_agents.services.managements.run_management_service import RunManagementService
from standard_agents.services.orchestrations.data.recollections.recollection_orchestration_service \
    import RecollectionOrchestrationService
from standard_agents.services.orchestrations.data.retrievals.retrieval_orchestration_service \
    import RetrievalOrchestrationService
from standard_agents.services.orchestrations.decision.guardians.guardian_orchestration_service \
    import GuardianOrchestrationService
from standard_agents.services.orchestrations.decision.inferences.inference_orchestration_service \
    import InferenceOrchestrationService
from standard_agents.services.orchestrations.direction.executions.execution_orchestration_service \
    import ExecutionOrchestrationService
from standard_agents.services.orchestrations.direction.perimeters.perimeter_orchestration_service \
    import PerimeterOrchestrationService
from standard_agents.tools.remember_tool import RememberTool
from standard_agents.tools.tool import Tool


class StandardAgent(Agent):
    def __init__(
            self,
            api_url: str | None = None,
            api_key: str | None = None,
            model: str | None = None) -> None:

        self._tools: list[Tool] = []
        self._skill_sources: list[SkillBroker] = []
        self._mcp_sources: list[Callable[[], McpBroker]] = []
        self._generator_broker: GeneratorBroker | None = None
        self._memory_broker: MemoryBroker | None = None
        self._knowledge_broker: KnowledgeBroker | None = None
        self._classifier_broker: ClassifierBroker | None = None
        self._verifier_broker: VerifierBroker | None = None
        self._logging_broker: LoggingBroker | None = None
        self._usage_broker: UsageBroker = RatioUsageBroker()
        self._brain_settings: InferenceSettings | None = None

        if api_url is not None or api_key is not None or model is not None:
            self.brain(api_url, api_key, model)

    def brain(
            self,
            api_url: str,
            api_key: str,
            model: str,
            *,
            temperature: float | None = None,
            max_tokens: int | None = None,
            timeout_seconds: int = 120) -> StandardAgent:

        self._brain_settings = InferenceSettings(
            api_url, api_key, model, temperature, max_tokens, timeout_seconds)

        return self

    def use_skills(self, broker: SkillBroker) -> StandardAgent:
        self._skill_sources.append(broker)

        return self

    def use_generator(self, broker: GeneratorBroker) -> StandardAgent:
        self._generator_broker = broker

        return self

    def use_memory(self, broker: MemoryBroker) -> StandardAgent:
        self._memory_broker = broker

        return self

    def use_knowledge(self, broker: KnowledgeBroker) -> StandardAgent:
        self._knowledge_broker = broker

        return self

    def use_gate(self, broker: ClassifierBroker) -> StandardAgent:
        self._classifier_broker = broker

        return self

    def use_judge(self, broker: VerifierBroker) -> StandardAgent:
        self._verifier_broker = broker

        return self

    def use_mcp(self, broker: McpBroker) -> StandardAgent:
        self._mcp_sources.append(lambda: broker)

        return self

    def use_logging(self, broker: LoggingBroker) -> StandardAgent:
        self._logging_broker = broker

        return self

    async def process_prompt(
            self,
            prompt: PromptRequest | str,
            *,
            session_id: str = "",
            cancellation: asyncio.Event | None = None) -> str:
        return await self._compose().process_prompt(prompt)

    async def run_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        raise NotImplementedError

    def stream_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        raise NotImplementedError

    def _compose(self) -> RunManagementService:
        brain = self._brain_settings

        logging = (
            self._logging_broker if self._logging_broker is not None
            else StdlibLoggingBroker(_null_logger()))

        generator = (
            self._generator_broker if self._generator_broker is not None
            else OpenAiGeneratorBroker(
                brain.api_url,
                brain.api_key,
                brain.model,
                (brain.temperature if brain.temperature is not None
                    else ResolvedInference.DEFAULT_TEMPERATURE),
                (brain.max_tokens if brain.max_tokens is not None
                    else ResolvedInference.DEFAULT_MAX_TOKENS),
                brain.timeout_seconds))

        memory_service = MemoryService(memory_broker=self._memory_broker, logging_broker=logging)
        all_tools = [*self._tools, RememberTool(memory_service.remember)]

        classifier = (
            self._classifier_broker if self._classifier_broker is not None
            else NotConfiguredClassifierBroker())

        verifier = (
            self._verifier_broker if self._verifier_broker is not None
            else NotConfiguredVerifierBroker())

        tool_broker = InMemoryToolBroker(all_tools)

        mcp = (
            self._mcp_sources[0]() if self._mcp_sources
            else NotConfiguredMcpBroker())
        skill_service = SkillService(skill_broker=self._skill_sources[0], logging_broker=logging)

        knowledge_service = KnowledgeService(
            knowledge_broker=self._knowledge_broker,
            logging_broker=logging)

        external_tool_service = ExternalToolService(mcp_broker=mcp, logging_broker=logging)

        data = DataCoordinationService(
            retrieval_service=RetrievalOrchestrationService(
                skill_service=skill_service,
                knowledge_service=knowledge_service,
                tool_catalog="",
                logging_broker=logging,
                external_tool_service=external_tool_service),
            recollection_service=RecollectionOrchestrationService(
                memory_service=memory_service,
                session_service=SessionService(
                    session_broker=NotConfiguredSessionBroker(),
                    logging_broker=logging),
                logging_broker=logging),
            logging_broker=logging)

        decision = DecisionCoordinationService(
            inference_service=InferenceOrchestrationService(
                brain_service=BrainService(
                    generator_broker=generator,
                    logging_broker=logging),
                usage_service=UsageService(usage_broker=self._usage_broker, logging_broker=logging),
                logging_broker=logging),
            guardian_service=GuardianOrchestrationService(
                gate_service=GateService(
                    classifier_broker=classifier,
                    logging_broker=logging),
                judge_service=JudgeService(
                    verifier_broker=verifier,
                    logging_broker=logging),
                contract_service=ContractService(
                    contract_broker=RuleContractBroker(),
                    logging_broker=logging),
                logging_broker=logging),
            logging_broker=logging)

        direction = DirectionCoordinationService(
            perimeter_service=PerimeterOrchestrationService(
                policy_service=PolicyService(
                    policy_broker=NotConfiguredPolicyBroker(),
                    logging_broker=logging),
                approval_service=ApprovalService(
                    approval_broker=NotConfiguredApprovalBroker(),
                    logging_broker=logging),
                effect_ledger_service=EffectLedgerService(
                    effect_ledger_broker=InMemoryEffectLedgerBroker(),
                    time_broker=SystemTimeBroker(),
                    logging_broker=logging,
                    lease=timedelta(minutes=5)),
                time_broker=SystemTimeBroker(),
                logging_broker=logging),
            execution_service=ExecutionOrchestrationService(
                internal_tool_service=InternalToolService(
                    tool_broker=tool_broker,
                    logging_broker=logging),
                external_tool_service=external_tool_service,
                return_service=ReturnService(logging_broker=logging),
                logging_broker=logging),
            logging_broker=logging)

        return RunManagementService(
            data_coordination_service=data,
            decision_coordination_service=decision,
            direction_coordination_service=direction,
            logging_broker=logging)


def _null_logger() -> logging.Logger:
    """A logger that writes nothing, as .NET's NullLogger: the trace file is the record."""
    logger = logging.Logger("standard_agents")
    logger.disabled = True

    return logger
