# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import logging
import os
import urllib.parse
import urllib.request
import warnings
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence)
from datetime import timedelta
from decimal import Decimal
from typing import Any

from standard_agents._standard_agent_composition import (
    compose_guardian_rubric,
    render_tool_catalog,
    render_tool_catalog_entries)
from standard_agents._standard_agent_configuration import apply_document
from standard_agents.agent import Agent
from standard_agents.brokers.agents.agent_registry_broker import AgentRegistryBroker
from standard_agents.brokers.agents.file_agent_registry_broker import FileAgentRegistryBroker
from standard_agents.brokers.agents.function_agent_registry_broker import (
    FunctionAgentRegistryBroker)
from standard_agents.brokers.approvals.approval_broker import ApprovalBroker, ApprovalDecision
from standard_agents.brokers.approvals.function_approval_broker import FunctionApprovalBroker
from standard_agents.brokers.approvals.not_configured_approval_broker import (
    NotConfiguredApprovalBroker)
from standard_agents.brokers.audits.audit_broker import AuditBroker
from standard_agents.brokers.audits.auditing_logging_broker import AuditingLoggingBroker
from standard_agents.brokers.audits.function_audit_broker import FunctionAuditBroker
from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.classifiers.function_classifier_broker import FunctionClassifierBroker
from standard_agents.brokers.classifiers.not_configured_classifier_broker import (
    NotConfiguredClassifierBroker)
from standard_agents.brokers.classifiers.rule_classifier_broker import RuleClassifierBroker
from standard_agents.brokers.contracts.contract_broker import ContractBroker
from standard_agents.brokers.contracts.function_contract_broker import FunctionContractBroker
from standard_agents.brokers.contracts.rule_contract_broker import RuleContractBroker
from standard_agents.brokers.effects.effect_ledger_broker import EffectLedgerBroker
from standard_agents.brokers.effects.file_effect_ledger_broker import FileEffectLedgerBroker
from standard_agents.brokers.effects.function_effect_ledger_broker import (
    FunctionEffectLedgerBroker)
from standard_agents.brokers.effects.in_memory_effect_ledger_broker import (
    InMemoryEffectLedgerBroker)
from standard_agents.brokers.files.file_broker import FileBroker
from standard_agents.brokers.files.local_file_broker import LocalFileBroker
from standard_agents.brokers.generators.function_generator_broker import FunctionGeneratorBroker
from standard_agents.brokers.generators.function_generator_broker_v1 import (
    FunctionGeneratorBrokerV1)
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.generators.openai_generator_broker import OpenAiGeneratorBroker
from standard_agents.brokers.generators.openai_generator_broker_v1 import OpenAiGeneratorBrokerV1
from standard_agents.brokers.knowledges.function_knowledge_broker import FunctionKnowledgeBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.knowledges.sourced_knowledge_broker import SourcedKnowledgeBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.loggings.stdlib_logging_broker import StdlibLoggingBroker
from standard_agents.brokers.mcps.composite_mcp_broker import CompositeMcpBroker
from standard_agents.brokers.mcps.http_mcp_broker import HttpMcpBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.mcps.not_configured_mcp_broker import NotConfiguredMcpBroker
from standard_agents.brokers.mcps.stdio_mcp_broker import StdioMcpBroker
from standard_agents.brokers.memories.function_memory_broker import FunctionMemoryBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.policies.function_policy_broker import FunctionPolicyBroker
from standard_agents.brokers.policies.not_configured_policy_broker import (
    NotConfiguredPolicyBroker)
from standard_agents.brokers.policies.policy_broker import PolicyBroker
from standard_agents.brokers.redactions.function_redaction_broker import FunctionRedactionBroker
from standard_agents.brokers.redactions.not_configured_redaction_broker import (
    NotConfiguredRedactionBroker)
from standard_agents.brokers.redactions.redaction_broker import RedactionBroker
from standard_agents.brokers.resiliences.fallback_resilience_broker import (
    FallbackResilienceBroker)
from standard_agents.brokers.resiliences.resilience_broker import ResilienceBroker
from standard_agents.brokers.resiliences.retry_resilience_broker import RetryResilienceBroker
from standard_agents.brokers.sessions.file_session_broker import FileSessionBroker
from standard_agents.brokers.sessions.function_session_broker import FunctionSessionBroker
from standard_agents.brokers.sessions.not_configured_session_broker import (
    NotConfiguredSessionBroker)
from standard_agents.brokers.sessions.session_broker import SessionBroker
from standard_agents.brokers.skills.composite_skill_broker import CompositeSkillBroker
from standard_agents.brokers.skills.file_skill_broker import FileSkillBroker
from standard_agents.brokers.skills.function_skill_broker import FunctionSkillBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.brokers.telemetries.activity_telemetry_broker import ActivityTelemetryBroker
from standard_agents.brokers.telemetries.function_telemetry_broker import FunctionTelemetryBroker
from standard_agents.brokers.telemetries.telemetry_broker import TelemetryBroker
from standard_agents.brokers.times.system_time_broker import SystemTimeBroker
from standard_agents.brokers.tools.in_memory_tool_broker import InMemoryToolBroker
from standard_agents.brokers.usages.function_usage_broker import FunctionUsageBroker
from standard_agents.brokers.usages.ratio_usage_broker import RatioUsageBroker
from standard_agents.brokers.usages.usage_broker import UsageBroker
from standard_agents.brokers.verifiers.function_verifier_broker import FunctionVerifierBroker
from standard_agents.brokers.verifiers.not_configured_verifier_broker import (
    NotConfiguredVerifierBroker)
from standard_agents.brokers.verifiers.rule_verifier_broker import RuleVerifierBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent
from standard_agents.models.brokers.audits.audit_policy import AuditPolicy
from standard_agents.models.brokers.audits.audit_record import AuditRecord
from standard_agents.models.brokers.effects.effect_record import EffectRecord
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    ToolDefinition)
from standard_agents.models.brokers.sessions.agent_session import AgentSession
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.exceptions import (
    InvalidAgentApiUrlException,
    InvalidAgentBudgetException,
    InvalidAgentCompositionException)
from standard_agents.models.clients.agents.inference_settings import InferenceSettings
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.coordinations.agents.agent_budget import AgentBudget
from standard_agents.models.foundations.brains.redaction_rule import RedactionRule
from standard_agents.models.foundations.brains.redaction_rules import RedactionRules
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)
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
        self._gate_settings: InferenceSettings | None = None
        self._judge_settings: InferenceSettings | None = None
        self._budget: AgentBudget | None = None
        self._audit_broker: AuditBroker | None = None
        self._telemetry_broker: TelemetryBroker | None = None
        self._http_handler_source: Callable[[], urllib.request.BaseHandler] | None = None
        self._identity_resolver: Callable[[], AgentPrincipal | None] | None = None
        self._generator_broker_v1: GeneratorBrokerV1 | None = None
        self._native_brain_source: Callable[[], GeneratorBrokerV1] | None = None
        self._local_gate_screen: Callable[[str, str], Awaitable[str]] | None = None
        self._local_judge_evaluate: Callable[[str, str], Awaitable[str]] | None = None
        self._memory_path = "memory.txt"
        self._knowledge_path = "Knowledge"
        self._log_path = ""
        self._constitution_path = ""
        self._consumption_path = ""
        self._trace_verbosity = TraceVerbosity.FULL
        self._sourced_knowledge_broker: SourcedKnowledgeBroker | None = None
        self._audit_path = ""
        self._allowed_tools: Sequence[str] | None = None
        self._policy_broker: PolicyBroker | None = None
        self._approval_required_tools: Sequence[str] | None = None
        self._approval_broker: ApprovalBroker | None = None
        self._resilience_broker: ResilienceBroker | None = None
        self._session_broker: SessionBroker | None = None
        self._max_history_turns = 20
        self._max_turns = 7
        self._effect_ledger_broker: EffectLedgerBroker | None = None
        self._contract_schema: str | None = None
        self._contract_broker: ContractBroker | None = None
        self._agent_sources: list[AgentRegistryBroker] = []
        self._redaction_rules: Sequence[RedactionRule] | None = None
        self._redaction_broker: RedactionBroker | None = None

        if api_url is not None or api_key is not None or model is not None:
            self.brain(api_url, api_key, model)

    def skills(self, path: str) -> StandardAgent:
        self._skill_sources.append(FileSkillBroker(os.path.join(os.getcwd(), path)))

        return self

    @classmethod
    def from_json(cls, json: str) -> StandardAgent:
        agent = cls()
        apply_document(agent, json)

        return agent

    def max_turns(self, turns: int) -> StandardAgent:
        self._max_turns = 1 if turns < 1 else turns

        return self

    def memory(self, path: str) -> StandardAgent:
        self._memory_path = path

        return self

    def knowledge(self, path: str) -> StandardAgent:
        self._knowledge_path = path

        return self

    def mcp(
            self,
            endpoint_url: str,
            *,
            relative_url: str = "",
            timeout_seconds: int = 30,
            bearer_token: str | None = None,
            api_key: str | None = None,
            api_key_header: str = "X-Api-Key",
            bearer_token_provider: Callable[[], Awaitable[str]] | None = None) -> StandardAgent:

        # A source, not a broker: the HTTP broker is created at composition so the host's handler
        # (http) reaches it whatever the order of the chain (F-23).
        self._mcp_sources.append(lambda: HttpMcpBroker(
            endpoint_url,
            relative_url,
            timeout_seconds,
            bearer_token,
            api_key,
            api_key_header,
            bearer_token_provider,
            handler=self._create_http_opener()))

        return self

    def mcp_process(
            self,
            command: str,
            *,
            arguments: Iterable[str] | None = None,
            environment_variables: Mapping[str, str] | None = None,
            working_directory: str | None = None,
            timeout_seconds: int = 30) -> StandardAgent:

        self._mcp_sources.append(lambda: StdioMcpBroker(
            command=command,
            arguments=arguments if arguments is not None else [],
            environment_variables=environment_variables,
            working_directory=working_directory,
            timeout_seconds=timeout_seconds))

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

        _validate_api_url(api_url)

        self._brain_settings = InferenceSettings(
            api_url, api_key, model, temperature, max_tokens, timeout_seconds)

        return self

    def native_brain(
            self,
            api_url: str,
            api_key: str,
            model: str,
            *,
            temperature: float = 0.7,
            max_tokens: int = 1024) -> StandardAgent:

        _validate_api_url(api_url)

        self._generator_broker_v1 = None

        self._native_brain_source = lambda: OpenAiGeneratorBrokerV1(
            api_url,
            api_key,
            model,
            temperature,
            max_tokens,
            timeout_seconds=120,
            handler=self._create_http_handler())

        return self

    def gate(
            self,
            api_url: str,
            api_key: str,
            model: str,
            *,
            temperature: float = 0.0,
            max_tokens: int = 16,
            timeout_seconds: int = 30) -> StandardAgent:

        _validate_api_url(api_url)

        self._gate_settings = InferenceSettings(
            api_url, api_key, model, temperature, max_tokens, timeout_seconds)

        return self

    def judge(
            self,
            api_url: str,
            api_key: str,
            model: str,
            *,
            temperature: float = 0.0,
            max_tokens: int = 16,
            timeout_seconds: int = 30) -> StandardAgent:

        _validate_api_url(api_url)

        self._judge_settings = InferenceSettings(
            api_url, api_key, model, temperature, max_tokens, timeout_seconds)

        return self

    def budget(
            self,
            *,
            max_tokens: int | None = None,
            max_cost_usd: Decimal | None = None,
            max_wall_clock: timedelta | None = None,
            cost_per_thousand_tokens: Decimal = Decimal(0)) -> StandardAgent:

        _validate_budget(max_cost_usd, cost_per_thousand_tokens)

        self._budget = AgentBudget(
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            max_wall_clock=max_wall_clock,
            cost_per_thousand_tokens=cost_per_thousand_tokens)

        return self

    def use_audit(self, broker: AuditBroker) -> StandardAgent:
        self._audit_broker = broker

        return self

    def on_audit(self, write: Callable[[AuditRecord], Awaitable[None]]) -> StandardAgent:
        self._audit_broker = FunctionAuditBroker(write)

        return self

    def principal(
            self,
            principal: Callable[[], AgentPrincipal | str | None]) -> StandardAgent:

        self._identity_resolver = lambda: _as_principal(principal())

        return self

    def use_telemetry(self, broker: TelemetryBroker) -> StandardAgent:
        self._telemetry_broker = broker

        return self

    def on_telemetry(
            self,
            record: Callable[[str, Mapping[str, Any]], None]) -> StandardAgent:

        self._telemetry_broker = FunctionTelemetryBroker(record)

        return self

    def on_skills(self, select: Callable[[], Awaitable[Sequence[Skill]]]) -> StandardAgent:
        self._skill_sources.append(FunctionSkillBroker(select))

        return self

    def on_memory(
            self,
            recall: Callable[[], Awaitable[Sequence[str]]],
            remember: Callable[[str], Awaitable[None]]) -> StandardAgent:

        self._memory_broker = FunctionMemoryBroker(recall, remember)

        return self

    def on_knowledge(self, retrieve: Callable[[str], Awaitable[Sequence[str]]]) -> StandardAgent:
        self._knowledge_broker = FunctionKnowledgeBroker(retrieve)
        self._sourced_knowledge_broker = None

        return self

    def use_native_brain(self, broker: GeneratorBrokerV1) -> StandardAgent:
        self._native_brain_source = None
        self._generator_broker_v1 = broker

        return self

    def on_native_brain(
            self,
            generate: Callable[
                [Sequence[ConversationMessage], Sequence[ToolDefinition]],
                Awaitable[GenerationResult]]) -> StandardAgent:

        self._native_brain_source = None
        self._generator_broker_v1 = FunctionGeneratorBrokerV1(generate)

        return self

    def rule_gate(self, *refuse_patterns: str) -> StandardAgent:
        self._classifier_broker = RuleClassifierBroker(refuse_patterns)

        return self

    def rule_judge(self, *required_patterns: str) -> StandardAgent:
        self._verifier_broker = RuleVerifierBroker(required_patterns)

        return self

    def audit(self, path: str) -> StandardAgent:
        self._audit_path = path

        return self

    def allow_tools(self, *tool_names: str) -> StandardAgent:
        self._allowed_tools = tool_names

        return self

    def use_policy(self, broker: PolicyBroker) -> StandardAgent:
        self._policy_broker = broker

        return self

    def on_policy(
            self,
            authorize: Callable[[AgentEffect], Awaitable[AuthorizationDecision]]) -> StandardAgent:

        self._policy_broker = FunctionPolicyBroker(authorize)

        return self

    def require_approval(self, *tool_names: str) -> StandardAgent:
        self._approval_required_tools = tool_names

        return self

    def use_approvals(self, broker: ApprovalBroker) -> StandardAgent:
        self._approval_broker = broker

        return self

    def on_approval(
            self,
            request: Callable[[AgentEffect], Awaitable[ApprovalDecision]]) -> StandardAgent:

        self._approval_broker = FunctionApprovalBroker(request)

        return self

    def resilience(self, *, retries: int = 3) -> StandardAgent:
        self._resilience_broker = RetryResilienceBroker(retries)

        return self

    def use_resilience(self, broker: ResilienceBroker) -> StandardAgent:
        self._resilience_broker = broker

        return self

    def fallback(
            self,
            fallback: Callable[[], Awaitable[str]],
            *,
            retries: int = 0,
            failures_before_open: int = 3) -> StandardAgent:

        self._resilience_broker = FallbackResilienceBroker(
            primary=RetryResilienceBroker(retries),
            alternative=fallback,
            failures_before_open=failures_before_open)

        return self

    def sessions(self, path: str, *, max_history_turns: int = 20) -> StandardAgent:
        self._session_broker = FileSessionBroker(path)
        self._max_history_turns = max_history_turns

        return self

    def use_sessions(self, broker: SessionBroker) -> StandardAgent:
        self._session_broker = broker

        return self

    def on_sessions(
            self,
            select: Callable[[str], Awaitable[AgentSession | None]],
            upsert: Callable[[AgentSession], Awaitable[None]]) -> StandardAgent:

        self._session_broker = FunctionSessionBroker(select, upsert)

        return self

    def effect_ledger(self, path: str) -> StandardAgent:
        self._effect_ledger_broker = FileEffectLedgerBroker(path)

        return self

    def use_effect_ledger(self, broker: EffectLedgerBroker) -> StandardAgent:
        self._effect_ledger_broker = broker

        return self

    def on_effect_ledger(
            self,
            insert_claim: Callable[[EffectRecord], Awaitable[bool]],
            select_record: Callable[[str], Awaitable[EffectRecord | None]],
            update_record: Callable[[EffectRecord], Awaitable[None]],
            delete_record: Callable[[str], Awaitable[None]]) -> StandardAgent:

        self._effect_ledger_broker = FunctionEffectLedgerBroker(
            insert_claim,
            select_record,
            update_record,
            delete_record)

        return self

    def usage(self, *, characters_per_token: float = 4.0) -> StandardAgent:
        self._usage_broker = RatioUsageBroker(characters_per_token)

        return self

    def use_usage(self, broker: UsageBroker) -> StandardAgent:
        self._usage_broker = broker

        return self

    def on_usage(self, count: Callable[[str], Awaitable[int]]) -> StandardAgent:
        self._usage_broker = FunctionUsageBroker(count)

        return self

    def telemetry(self, *, agent_name: str = "standard-agent") -> StandardAgent:
        self._telemetry_broker = ActivityTelemetryBroker(agent_name)

        return self

    def contract(self, json_schema: str) -> StandardAgent:
        self._contract_schema = json_schema

        return self

    def use_contract(self, broker: ContractBroker) -> StandardAgent:
        self._contract_broker = broker

        return self

    def on_contract(
            self,
            validate: Callable[[str, str], Awaitable[str | None]]) -> StandardAgent:

        self._contract_broker = FunctionContractBroker(validate)

        return self

    def agents(self, path: str) -> StandardAgent:
        self._agent_sources.append(FileAgentRegistryBroker(os.path.join(os.getcwd(), path)))

        return self

    def use_agents(self, broker: AgentRegistryBroker) -> StandardAgent:
        self._agent_sources.append(broker)

        return self

    def on_agents(
            self,
            select: Callable[[], Awaitable[Sequence[RegisteredAgent]]]) -> StandardAgent:

        self._agent_sources.append(FunctionAgentRegistryBroker(select))

        return self

    def redact(self, *rules: RedactionRule) -> StandardAgent:
        self._redaction_rules = rules if rules else RedactionRules.DEFAULT

        return self

    def use_redaction(self, broker: RedactionBroker) -> StandardAgent:
        self._redaction_broker = broker

        return self

    def on_redaction(
            self,
            redact: Callable[[str, MutableMapping[str, str]], str],
            rehydrate: Callable[[str, Mapping[str, str]], str]) -> StandardAgent:

        self._redaction_broker = FunctionRedactionBroker(redact, rehydrate)

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

    def consumption(self, path: str) -> StandardAgent:
        self._consumption_path = path

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

    def http(self, handlers: Callable[[], urllib.request.BaseHandler]) -> StandardAgent:
        self._http_handler_source = handlers

        return self

    def _create_http_handler(self) -> urllib.request.BaseHandler | None:
        # One handler per HTTP broker: the host's when http(...) was called, otherwise none, and
        # the broker builds its own opener.
        if self._http_handler_source is None:
            return None

        return self._http_handler_source()

    def _create_http_opener(self) -> urllib.request.OpenerDirector | None:
        # The MCP broker takes the composed opener rather than the bare handler; it sends no
        # User-Agent of its own, as its default opener does not.
        handler = self._create_http_handler()

        if handler is None:
            return None

        opener = urllib.request.build_opener(handler)
        opener.addheaders = []

        return opener

    def _current_principal_id(self) -> str | None:
        if self._identity_resolver is None:
            return None

        principal = self._identity_resolver()

        return None if principal is None else principal.id

    def _compose(self) -> RunManagementService:
        _validate_composition(
            has_brain=(
                self._generator_broker is not None
                or self._brain_settings is not None
                or self._generator_broker_v1 is not None
                or self._native_brain_source is not None))

        brain = self._brain_settings
        file = LocalFileBroker()

        # The log is one broker; the decision log is another, applied over it by decoration when
        # an audit sink is configured, over the built-in trace or a host's own logging broker
        # alike, so use_logging and audit compose rather than compete (F-16).
        trace = (
            self._logging_broker if self._logging_broker is not None
            else StdlibLoggingBroker(_null_logger()))

        audit = self._audit_broker

        logging = (
            trace if audit is None
            else AuditingLoggingBroker(
                trace,
                audit,
                SystemTimeBroker(),
                NotConfiguredRedactionBroker(),
                AuditPolicy(payloads=False),
                self._current_principal_id))

        # With only a native brain configured there is no text-protocol generator to build, and
        # none is needed: a native brain routes every call to the V1 seam. The placeholder exists
        # so the Brain foundation keeps one shape rather than growing an optional dependency.
        if self._generator_broker is not None:
            generator: GeneratorBroker = self._generator_broker
        elif brain is None:
            generator = FunctionGeneratorBroker(_native_brain_only)
        else:
            # The legacy-path values, resolved configured to framework default at composition.
            # A per-request value arrives on the request and never through here.
            generator = OpenAiGeneratorBroker(
                brain.api_url,
                brain.api_key,
                brain.model,
                (brain.temperature if brain.temperature is not None
                    else ResolvedInference.DEFAULT_TEMPERATURE),
                (brain.max_tokens if brain.max_tokens is not None
                    else ResolvedInference.DEFAULT_MAX_TOKENS),
                brain.timeout_seconds,
                handler=self._create_http_handler())

        native_brain = (
            self._generator_broker_v1 if self._generator_broker_v1 is not None
            else self._native_brain_source() if self._native_brain_source is not None
            else None)

        if self._memory_broker is not None:
            memory_service = MemoryService(
                memory_broker=self._memory_broker,
                logging_broker=logging)
        else:
            memory_service = MemoryService(
                file_broker=file,
                memory_path=os.path.abspath(self._memory_path),
                logging_broker=logging)
        all_tools = [*self._tools, RememberTool(memory_service.remember)]

        constitution = _read_optional_file(file, self._constitution_path)
        consumption = _read_optional_file(file, self._consumption_path)
        is_consumption_blank = not consumption or consumption.isspace()
        policy_of_gate = gate_policy() if is_consumption_blank else consumption
        policy_of_judge = judge_policy() if is_consumption_blank else consumption
        gate_rubric = compose_guardian_rubric(constitution, policy_of_gate, gate_contract())

        if self._classifier_broker is not None:
            classifier = self._classifier_broker
        elif self._local_gate_screen is not None:
            classifier = FunctionClassifierBroker(self._local_gate_screen, gate_rubric)
        else:
            classifier = NotConfiguredClassifierBroker()

        judge_rubric = compose_guardian_rubric(constitution, policy_of_judge, judge_contract())

        if self._verifier_broker is not None:
            verifier = self._verifier_broker
        elif self._local_judge_evaluate is not None:
            verifier = FunctionVerifierBroker(self._local_judge_evaluate, judge_rubric)
        else:
            verifier = NotConfiguredVerifierBroker()

        tool_broker = InMemoryToolBroker(all_tools)

        # One source composes as itself; several compose behind the same seam the service already
        # speaks, so the tier above never learns how many integrations answered.
        mcp_brokers = [source() for source in self._mcp_sources]

        if not mcp_brokers:
            mcp: McpBroker = NotConfiguredMcpBroker()
        elif len(mcp_brokers) == 1:
            mcp = mcp_brokers[0]
        else:
            mcp = CompositeMcpBroker(mcp_brokers)

        if not self._skill_sources:
            skills: SkillBroker = FileSkillBroker(os.path.join(os.getcwd(), "Skills"))
        elif len(self._skill_sources) == 1:
            skills = self._skill_sources[0]
        else:
            skills = CompositeSkillBroker(self._skill_sources)

        skill_service = SkillService(skill_broker=skills, logging_broker=logging)

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
                    logging_broker=logging,
                    generator_broker_v1=native_brain),
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
            logging_broker=logging,
            telemetry_broker=self._telemetry_broker)


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


def _validate_api_url(api_url: str) -> None:
    # An endpoint is the base the route is appended to, so its shape is load-bearing. Without the
    # trailing '/' the route resolves against the parent ('https://host/v1' reaches
    # 'https://host/chat/completions'), and a base that already names chat/completions reaches
    # 'v1/chat/chat/completions' (principal review 2026-09-04, F-12). Both fail at the first
    # prompt with a 404 that blames the provider.
    endpoint = urllib.parse.urlsplit(api_url)
    is_absolute_http = endpoint.scheme in ("http", "https") and bool(endpoint.netloc)
    names_the_route = api_url.rstrip("/").lower().endswith("/chat/completions")

    if not is_absolute_http or not api_url.endswith("/") or names_the_route:
        raise InvalidAgentApiUrlException(
            message=(
                "Invalid agent API URL. An endpoint is the base the route is appended to: an "
                + "absolute http(s) URL ending with '/', such as "
                + "https://api.peerllm.com/v1/, that does not name chat/completions "
                + "itself."))


def _validate_budget(max_cost_usd: Decimal | None, cost_per_thousand_tokens: Decimal) -> None:
    # Spend is the token count times the rate, so a cost bound with no positive rate computes
    # zero forever and never trips. The framework cannot know what a model costs and so cannot
    # fill the rate in; it can refuse the contradiction of a dollar bound on a model declared
    # free. Token and wall-clock bounds need no price and are not checked here.
    if max_cost_usd is not None and cost_per_thousand_tokens <= 0:
        raise InvalidAgentBudgetException(
            message=(
                "Invalid agent budget: a cost bound (maxCostUsd) needs a positive "
                + "costPerThousandTokens. Cost is the token count times that rate, so at "
                + "zero the bound can never trip. Pass your model's rate, or bound by "
                + "maxTokens instead."))


def _as_principal(principal: AgentPrincipal | str | None) -> AgentPrincipal | None:
    # A host that has only a user id passes the id; the agent wraps it, as the C# string form of
    # Principal does.
    return AgentPrincipal(id=principal) if isinstance(principal, str) else principal


async def _native_brain_only(system_prompt: str, user_prompt: str) -> str:
    raise RuntimeError("This agent has a native brain; the text protocol is not in use.")
