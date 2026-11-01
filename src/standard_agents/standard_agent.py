# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import logging
import os
import warnings
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import timedelta

from standard_agents._standard_agent_composition import (
    compose_guardian_rubric,
    render_tool_catalog,
    render_tool_catalog_entries)
from standard_agents.agent import Agent
from standard_agents.brokers.approvals.not_configured_approval_broker import (
    NotConfiguredApprovalBroker)
from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.classifiers.function_classifier_broker import FunctionClassifierBroker
from standard_agents.brokers.classifiers.not_configured_classifier_broker import (
    NotConfiguredClassifierBroker)
from standard_agents.brokers.contracts.rule_contract_broker import RuleContractBroker
from standard_agents.brokers.effects.in_memory_effect_ledger_broker import (
    InMemoryEffectLedgerBroker)
from standard_agents.brokers.files.file_broker import FileBroker
from standard_agents.brokers.files.local_file_broker import LocalFileBroker
from standard_agents.brokers.generators.function_generator_broker import FunctionGeneratorBroker
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.generators.openai_generator_broker import OpenAiGeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.loggings.stdlib_logging_broker import StdlibLoggingBroker
from standard_agents.brokers.mcps.http_mcp_broker import HttpMcpBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.mcps.not_configured_mcp_broker import NotConfiguredMcpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.policies.not_configured_policy_broker import (
    NotConfiguredPolicyBroker)
from standard_agents.brokers.sessions.not_configured_session_broker import (
    NotConfiguredSessionBroker)
from standard_agents.brokers.skills.file_skill_broker import FileSkillBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.brokers.times.system_time_broker import SystemTimeBroker
from standard_agents.brokers.tools.in_memory_tool_broker import InMemoryToolBroker
from standard_agents.brokers.usages.ratio_usage_broker import RatioUsageBroker
from standard_agents.brokers.usages.usage_broker import UsageBroker
from standard_agents.brokers.verifiers.not_configured_verifier_broker import (
    NotConfiguredVerifierBroker)
from standard_agents.brokers.verifiers.function_verifier_broker import FunctionVerifierBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.exceptions import InvalidAgentCompositionException
from standard_agents.models.clients.agents.inference_settings import InferenceSettings
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity
from standard_agents.prompts.guardian_prompts import (
    gate_contract,
    gate_policy,
    judge_contract,
    judge_policy)
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
        self._local_gate_screen: Callable[[str, str], Awaitable[str]] | None = None
        self._local_judge_evaluate: Callable[[str, str], Awaitable[str]] | None = None
        self._memory_path = "memory.txt"
        self._knowledge_path = "Knowledge"
        self._log_path = ""
        self._constitution_path = ""
        self._trace_verbosity = TraceVerbosity.FULL

        if api_url is not None or api_key is not None or model is not None:
            self.brain(api_url, api_key, model)

    def skills(self, path: str) -> StandardAgent:
        self._skill_sources.append(FileSkillBroker(os.path.join(os.getcwd(), path)))

        return self

    def memory(self, path: str) -> StandardAgent:
        self._memory_path = path

        return self

    def knowledge(self, path: str) -> StandardAgent:
        self._knowledge_path = path

        return self

    def mcp(self, endpoint_url: str) -> StandardAgent:
        self._mcp_sources.append(lambda: HttpMcpBroker(endpoint_url, "", 30))

        return self

    def log_to(
            self,
            path: str,
            *,
            verbosity: TraceVerbosity = TraceVerbosity.FULL) -> StandardAgent:

        self._log_path = path
        self._trace_verbosity = verbosity

        return self

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

    def local_brain(self, generate: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """Renamed to on_brain: a delegate is the Custom mode, not the Local one."""
        _warn_renamed("local_brain", "on_brain")

        return self.on_brain(generate)

    def local_gate(self, screen: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """Renamed to on_gate: a delegate is the Custom mode, not the Local one."""
        _warn_renamed("local_gate", "on_gate")

        return self.on_gate(screen)

    def local_judge(self, evaluate: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """Renamed to on_judge: a delegate is the Custom mode, not the Local one."""
        _warn_renamed("local_judge", "on_judge")

        return self.on_judge(evaluate)

    def constitution(self, path: str) -> StandardAgent:
        self._constitution_path = path

        return self

    def on_gate(self, screen: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        self._local_gate_screen = screen

        return self

    def on_judge(self, evaluate: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        self._local_judge_evaluate = evaluate

        return self

    def tool(self, tool: Tool) -> StandardAgent:
        self._tools.append(tool)

        return self

    def on_brain(self, generate: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        self._generator_broker = FunctionGeneratorBroker(generate)

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

    async def stream_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        async for stream_event in self._compose().run_stream(request, cancellation=cancellation):
            yield stream_event

    def _compose(self) -> RunManagementService:
        _validate_composition(
            has_brain=self._generator_broker is not None or self._brain_settings is not None)

        brain = self._brain_settings
        file = LocalFileBroker()

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

        constitution = _read_optional_file(file, self._constitution_path)
        gate_rubric = compose_guardian_rubric(constitution, gate_policy(), gate_contract())

        if self._classifier_broker is not None:
            classifier = self._classifier_broker
        elif self._local_gate_screen is not None:
            classifier = FunctionClassifierBroker(self._local_gate_screen, gate_rubric)
        else:
            classifier = NotConfiguredClassifierBroker()

        judge_rubric = compose_guardian_rubric(constitution, judge_policy(), judge_contract())

        if self._verifier_broker is not None:
            verifier = self._verifier_broker
        elif self._local_judge_evaluate is not None:
            verifier = FunctionVerifierBroker(self._local_judge_evaluate, judge_rubric)
        else:
            verifier = NotConfiguredVerifierBroker()

        tool_broker = InMemoryToolBroker(all_tools)

        mcp = (
            self._mcp_sources[0]() if self._mcp_sources
            else NotConfiguredMcpBroker())
        skill_service = SkillService(skill_broker=self._skill_sources[0], logging_broker=logging)

        if self._knowledge_broker is not None:
            knowledge_service = KnowledgeService(
                knowledge_broker=self._knowledge_broker,
                logging_broker=logging)
        else:
            knowledge_service = KnowledgeService(
                file_broker=file,
                knowledge_path=os.path.abspath(self._knowledge_path),
                search_pattern="*.md",
                max_results=3,
                logging_broker=logging,
                minimum_score=0.0)

        external_tool_service = ExternalToolService(mcp_broker=mcp, logging_broker=logging)

        data = DataCoordinationService(
            retrieval_service=RetrievalOrchestrationService(
                skill_service=skill_service,
                knowledge_service=knowledge_service,
                tool_catalog=render_tool_catalog(all_tools),
                logging_broker=logging,
                external_tool_service=external_tool_service,
                tool_catalog_entries=render_tool_catalog_entries(all_tools)),
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


def _validate_composition(has_brain: bool) -> None:
    # A native brain is a brain. Either seam satisfies this: the check exists to catch an agent
    # with no way to think at all, not to prefer one contract over the other.
    if not has_brain:
        raise InvalidAgentCompositionException(
            message=(
                "Agent has no brain. Call Brain(apiUrl, apiKey, model), "
                + "UseGenerator(broker) or NativeBrain(apiUrl, apiKey, model) "
                + "before processing a prompt."))


def _warn_renamed(obsolete_name: str, new_name: str) -> None:
    warnings.warn(
        f"Renamed to {new_name}: a delegate is the Custom mode, not the Local one. "
        + "Local means a provider that runs on your own machine. This alias keeps working.",
        DeprecationWarning,
        stacklevel=3)


def _read_optional_file(file: FileBroker, path: str) -> str:
    """An optional prompt file (constitution, consumption), or empty when there is none.

    A missing file yields empty rather than an error, so a stale path degrades to the built-in
    guardian policy instead of bricking composition.
    """
    if not path or path.isspace():
        return ""

    full_path = os.path.join(os.getcwd(), path)

    return file.read_file_sync(full_path) if file.file_exists(full_path) else ""
