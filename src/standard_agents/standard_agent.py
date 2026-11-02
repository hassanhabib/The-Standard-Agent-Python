# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import logging
import os
import threading
import urllib.parse
import urllib.request
import warnings
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence)
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal
from typing import Any

from standard_agents._standard_agent_composition import (
    advertised,
    compose_guardian_rubric,
    render_tool_catalog,
    render_tool_catalog_entries,
    render_tool_definitions,
    render_tool_narrations)
from standard_agents._standard_agent_configuration import apply_document
from standard_agents._standard_agent_schema import document_schema_json
from standard_agents.agent import Agent
from standard_agents.brokers.agents.agent_registry_broker import AgentRegistryBroker
from standard_agents.brokers.agents.file_agent_registry_broker import FileAgentRegistryBroker
from standard_agents.brokers.agents.function_agent_registry_broker import (
    FunctionAgentRegistryBroker)
from standard_agents.brokers.approvals.approval_broker import ApprovalBroker, ApprovalDecision
from standard_agents.brokers.approvals.function_approval_broker import FunctionApprovalBroker
from standard_agents.brokers.approvals.not_configured_approval_broker import (
    NotConfiguredApprovalBroker)
from standard_agents.brokers.approvals.require_approval_broker import RequireApprovalBroker
from standard_agents.brokers.audits.audit_broker import AuditBroker
from standard_agents.brokers.audits.auditing_logging_broker import AuditingLoggingBroker
from standard_agents.brokers.audits.file_audit_broker import FileAuditBroker
from standard_agents.brokers.audits.function_audit_broker import FunctionAuditBroker
from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.classifiers.function_classifier_broker import FunctionClassifierBroker
from standard_agents.brokers.classifiers.not_configured_classifier_broker import (
    NotConfiguredClassifierBroker)
from standard_agents.brokers.classifiers.openai_classifier_broker import OpenAiClassifierBroker
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
from standard_agents.brokers.generators.anthropic_generator_broker_v1 import (
    AnthropicGeneratorBrokerV1)
from standard_agents.brokers.generators.function_generator_broker import FunctionGeneratorBroker
from standard_agents.brokers.generators.function_generator_broker_v1 import (
    FunctionGeneratorBrokerV1)
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.generators.openai_generator_broker import OpenAiGeneratorBroker
from standard_agents.brokers.generators.openai_generator_broker_v1 import OpenAiGeneratorBrokerV1
from standard_agents.brokers.knowledges.function_knowledge_broker import FunctionKnowledgeBroker
from standard_agents.brokers.knowledges.function_sourced_knowledge_broker import (
    FunctionSourcedKnowledgeBroker)
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
from standard_agents.brokers.memories.not_configured_memory_broker import NotConfiguredMemoryBroker
from standard_agents.brokers.policies.allow_list_policy_broker import AllowListPolicyBroker
from standard_agents.brokers.policies.function_policy_broker import FunctionPolicyBroker
from standard_agents.brokers.policies.not_configured_policy_broker import (
    NotConfiguredPolicyBroker)
from standard_agents.brokers.policies.policy_broker import PolicyBroker
from standard_agents.brokers.redactions.function_redaction_broker import FunctionRedactionBroker
from standard_agents.brokers.redactions.not_configured_redaction_broker import (
    NotConfiguredRedactionBroker)
from standard_agents.brokers.redactions.redacting_classifier_broker import (
    RedactingClassifierBroker)
from standard_agents.brokers.redactions.redacting_generator_broker import RedactingGeneratorBroker
from standard_agents.brokers.redactions.redacting_generator_broker_v1 import (
    RedactingGeneratorBrokerV1)
from standard_agents.brokers.redactions.redacting_verifier_broker import RedactingVerifierBroker
from standard_agents.brokers.redactions.redaction_broker import RedactionBroker
from standard_agents.brokers.redactions.rule_redaction_broker import RuleRedactionBroker
from standard_agents.brokers.resiliences.fallback_resilience_broker import (
    FallbackResilienceBroker)
from standard_agents.brokers.resiliences.not_configured_resilience_broker import (
    NotConfiguredResilienceBroker)
from standard_agents.brokers.resiliences.resilience_broker import ResilienceBroker
from standard_agents.brokers.resiliences.retry_resilience_broker import RetryResilienceBroker
from standard_agents.brokers.resiliences.retrying_generator_broker import RetryingGeneratorBroker
from standard_agents.brokers.resiliences.retrying_generator_broker_v1 import (
    RetryingGeneratorBrokerV1)
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
from standard_agents.brokers.verifiers.openai_verifier_broker import OpenAiVerifierBroker
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
from standard_agents.models.clients.agents.agent_run_stream import AgentRunStream
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.exceptions import (
    InvalidAgentApiUrlException,
    InvalidAgentBudgetException,
    InvalidAgentCompositionException)
from standard_agents.models.clients.agents.inference_settings import InferenceSettings
from standard_agents.models.clients.agents.prompt_request import PromptRequest
from standard_agents.models.coordinations.agents.agent_budget import AgentBudget
from standard_agents.models.coordinations.agents.principal_resolver import PrincipalResolver
from standard_agents.models.coordinations.agents.tool_selector import ToolSelector
from standard_agents.models.coordinations.directions.perimeter_policy import PerimeterPolicy
from standard_agents.models.foundations.brains.redaction_rule import RedactionRule
from standard_agents.models.foundations.brains.redaction_rules import RedactionRules
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.loggings.trace_verbosity import TraceVerbosity
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)
from standard_agents.models.orchestrations.effects.permission_mode import PermissionMode
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel
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
from standard_agents.tools.agent_tool import AgentTool
from standard_agents.tools.remember_tool import RememberTool
from standard_agents.tools.tool import Tool

_ANTHROPIC_API_URL = "https://api.anthropic.com/"


class StandardAgent(Agent):
    """The door: one class that composes an agent and runs it.

    StandardAgent(api_url, api_key, model) is a working agent. Every other capability is a verb
    that configures it and returns the same agent, so calls chain; the first run composes the
    configured pieces (brain, skills, tools, guardians, memory, knowledge) and later runs reuse
    that composition until a verb changes the configuration. There is no build step: the verbs
    are the configuration, and the runs compose it (principal review 2026-09-04, F-31).
    """

    def __init__(
            self,
            api_url: str | None = None,
            api_key: str | None = None,
            model: str | None = None) -> None:
        """An agent with nothing configured, or a ready one against an OpenAI-compatible endpoint.

        StandardAgent(api_url, api_key, model) is the same as StandardAgent().brain(api_url,
        api_key, model): the simplest start. api_url is the endpoint's base, ending with '/'; the
        chat/completions route is appended.
        """
        # Composes once and reuses. Guarded because one agent serves prompts concurrently
        # (SPEC.md 4.4), and every verb drops the cached composition so configuration set after
        # a prompt still takes effect.
        self._composition_lock = threading.Lock()
        self._agent: RunManagementService | None = None

        self._tools: list[Tool] = []

        # Integrations accumulate, never replace: a second skill source, MCP server or registry
        # adds to the agent the way a second .tool() always has. MCP sources are sources, not
        # brokers: an HTTP broker is created at composition so the host's handler (http)
        # reaches it whatever the order of the chain (F-23).
        self._skill_sources: list[SkillBroker] = []
        self._mcp_sources: list[Callable[[], McpBroker]] = []
        self._agent_sources: list[AgentRegistryBroker] = []
        self._owned_mcp_brokers: list[StdioMcpBroker] = []

        self._name = ""
        self._description = ""
        self._constitution_path = ""
        self._consumption_path = ""
        self._log_path = ""
        self._trace_verbosity = TraceVerbosity.FULL
        self._audit_path = ""
        self._audit_payloads = False
        self._memory_path = "memory.txt"
        self._memory_disabled = False
        self._knowledge_path = "Knowledge"
        self._knowledge_pattern = "*.md"
        self._knowledge_max_results = 3
        self._knowledge_min_score = 0.0
        self._max_turns = 7
        self._identical_call_limit = 8
        self._max_history_turns = 20

        self._brain_settings: InferenceSettings | None = None
        self._gate_settings: InferenceSettings | None = None
        self._judge_settings: InferenceSettings | None = None

        self._generator_broker: GeneratorBroker | None = None
        self._generator_broker_v1: GeneratorBrokerV1 | None = None
        self._native_brain_source: Callable[[], GeneratorBrokerV1] | None = None
        self._memory_broker: MemoryBroker | None = None
        self._knowledge_broker: KnowledgeBroker | None = None
        self._sourced_knowledge_broker: SourcedKnowledgeBroker | None = None

        # Citation (SPEC.md 4.2): None means the deployment expressed no opinion, which is what
        # lets a request's choice take effect, the same precedence every request field obeys.
        self._cite_knowledge: bool | None = None
        self._knowledge_citation_prefix = "Source: "

        self._classifier_broker: ClassifierBroker | None = None
        self._verifier_broker: VerifierBroker | None = None
        self._local_gate_screen: Callable[[str, str], Awaitable[str]] | None = None
        self._local_judge_evaluate: Callable[[str, str], Awaitable[str]] | None = None
        self._local_tool_selector: (
            Callable[[str, Sequence[str]], Awaitable[Sequence[str]]] | None) = None
        self._enforce_selection = False
        self._logging_broker: LoggingBroker | None = None
        self._audit_broker: AuditBroker | None = None
        self._telemetry_broker: TelemetryBroker | None = None
        self._redaction_rules: Sequence[RedactionRule] | None = None
        self._redaction_broker: RedactionBroker | None = None
        self._allowed_tools: Sequence[str] | None = None
        self._policy_broker: PolicyBroker | None = None
        self._approval_required_tools: Sequence[str] | None = None
        self._approval_broker: ApprovalBroker | None = None
        self._effect_ledger_broker: EffectLedgerBroker | None = None
        self._effect_lease = timedelta(minutes=5)
        self._screen_tool_output = False
        self._compensate_on_failure = False
        self._budget: AgentBudget | None = None
        self._resilience_broker: ResilienceBroker | None = None
        self._session_broker: SessionBroker | None = None

        # Counting is always on and costs nothing to leave on; BLOCKING is what has to be asked
        # for. So the default is a counter rather than a no-op: an agent with no budget is wide
        # open and still measurable, and budget() alone makes a bound real on any endpoint.
        self._usage_broker: UsageBroker = RatioUsageBroker()

        # Wide open by default: an agent given no contract is not constrained by having become
        # checkable, the same way counting is always on and blocking is not.
        self._contract_schema: str | None = None
        self._contract_broker: ContractBroker | None = None
        self._permission_mode = PermissionMode.OPEN
        self._declared_risk: dict[str, RiskLevel] = {}
        self._identity_resolver: Callable[[], AgentPrincipal | None] | None = None
        self._http_handler_source: Callable[[], urllib.request.BaseHandler] | None = None

        if api_url is not None or api_key is not None or model is not None:
            self.brain(api_url, api_key, model)

    @property
    def name(self) -> str:
        """The agent's name: what a registry lists and a handoff calls."""
        return self._name

    @property
    def description(self) -> str:
        """What the agent does, as a registry advertises it."""
        return self._description

    def skills(self, path: str) -> StandardAgent:
        """Points the agent at a folder of .md skill files, the prompts-as-Data that shape how it
        thinks (SPEC.md 7.2). A skill containing the {{tools}} marker is where advertised tools
        are listed. Sources accumulate: a second call adds another folder."""
        with self._configuring():
            self._skill_sources.append(FileSkillBroker(_beside_the_process(path)))

        return self

    def constitution(self, path: str) -> StandardAgent:
        """The ethical constitution: a Markdown file prepended to every guardian rubric (Gate and
        Judge), above the built-in policy. It takes effect only when a guardian is configured and
        never replaces the built-in output contract."""
        with self._configuring():
            self._constitution_path = path

        return self

    def consumption(self, path: str) -> StandardAgent:
        """The consumption skill: a Markdown file that replaces the built-in guardian policy
        (what the Gate screens for and what the Judge scores). The output contract is always
        kept, so a replacement policy cannot break the guardian's wiring."""
        with self._configuring():
            self._consumption_path = path

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
        """The brain: an OpenAI-compatible chat-completions endpoint that does the reasoning.

        Omitted, temperature and max_tokens are the framework's 0.7 and 1024, and a request may
        speak, because the deployment said nothing. Set, they are hard configuration that no
        request can move (docs/per-request-inference.md 4.2).
        """
        _validate_api_url(api_url)

        with self._configuring():
            self._brain_settings = InferenceSettings(
                api_url, api_key, model, temperature, max_tokens, timeout_seconds)

        return self

    def local_brain(self, generate: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """Renamed to on_brain: a delegate is the Custom mode, not the Local one."""
        _warn_renamed("on_brain")

        return self.on_brain(generate)

    def on_brain(self, generate: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """Your own brain as a (system_prompt, user_prompt) -> answer coroutine: the Custom
        mode. The agent makes no API calls; you supply the inference."""
        with self._configuring():
            self._generator_broker = FunctionGeneratorBroker(generate)

        return self

    def local_gate(self, screen: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """Renamed to on_gate: a delegate is the Custom mode, not the Local one."""
        _warn_renamed("on_gate")

        return self.on_gate(screen)

    def on_gate(self, screen: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """The Gate as your own (gate_rubric, prompt) -> verdict coroutine: the Custom mode. It
        receives the composed gate rubric as the system prompt."""
        with self._configuring():
            self._local_gate_screen = screen

        return self

    def on_select_tools(
            self,
            selector: Callable[[str, Sequence[str]], Awaitable[Sequence[str]]]) -> StandardAgent:
        """Per-run tool selection (SPEC.md 4.15): (task, described_tool_names) -> offered names.

        Selection narrows what a run is OFFERED, never what the agent carries: an unselected tool
        behaves exactly like an undescribed one. Caller-declared tools are never selected away.
        """
        with self._configuring():
            self._local_tool_selector = selector

        return self

    def enforce_selection(self) -> StandardAgent:
        """Makes the run's offering binding at the Direction perimeter (SPEC.md 4.15): an act
        naming an advertised tool the run was not offered is denied, told and recoverable. It
        takes effect only when a selector is configured."""
        with self._configuring():
            self._enforce_selection = True

        return self

    def local_judge(self, evaluate: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """Renamed to on_judge: a delegate is the Custom mode, not the Local one."""
        _warn_renamed("on_judge")

        return self.on_judge(evaluate)

    def on_judge(self, evaluate: Callable[[str, str], Awaitable[str]]) -> StandardAgent:
        """The Judge as your own (judge_rubric, draft_answer) -> score coroutine: the Custom
        mode. It receives the composed judge rubric as the system prompt."""
        with self._configuring():
            self._local_judge_evaluate = evaluate

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
        """The Gate on an endpoint: an opt-in guardian that screens each prompt before the brain
        sees it and can refuse. It runs its own screening rubric and is never the brain."""
        _validate_api_url(api_url)

        with self._configuring():
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
        """The Judge on an endpoint: an opt-in guardian that scores the brain's draft answer and
        sends it back for revision when the score is too low."""
        _validate_api_url(api_url)

        with self._configuring():
            self._judge_settings = InferenceSettings(
                api_url, api_key, model, temperature, max_tokens, timeout_seconds)

        return self

    def rule_gate(self, *refuse_patterns: str) -> StandardAgent:
        """A deterministic Gate: it refuses any prompt containing one of the patterns
        (case-insensitive) and accepts everything else."""
        with self._configuring():
            self._classifier_broker = RuleClassifierBroker(refuse_patterns)

        return self

    def rule_judge(self, *required_patterns: str) -> StandardAgent:
        """A deterministic Judge: it passes a draft only when it contains every pattern
        (case-insensitive), naming the first missing one as the revise-out reason."""
        with self._configuring():
            self._verifier_broker = RuleVerifierBroker(required_patterns)

        return self

    def memory(self, path: str) -> StandardAgent:
        """A memory file the agent reads on recall and writes through the built-in remember
        tool, so facts survive across turns and runs."""
        with self._configuring():
            self._memory_path = path

        return self

    def without_memory(self) -> StandardAgent:
        """No memory at all: nothing is recalled and the remember tool is never offered.

        A flag rather than a broker swap, so the opt-out wins whatever order the memory verbs
        were called in (principal review 2026-09-04, F-05).
        """
        with self._configuring():
            self._memory_disabled = True

        return self

    def knowledge(
            self,
            path: str,
            *,
            pattern: str = "*.md",
            max_results: int = 3,
            min_score: float = 0.0) -> StandardAgent:
        """A folder of knowledge files, retrieved by relevance to the prompt."""
        with self._configuring():
            self._knowledge_path = path
            self._knowledge_pattern = pattern
            self._knowledge_max_results = max_results
            self._knowledge_min_score = min_score

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
        """An MCP server over HTTP whose tools the agent discovers and calls. Servers accumulate;
        a refresh-flow token is bearer_token_provider, asked for on every request."""
        with self._configuring():
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
        """An MCP server the agent starts itself and speaks to over standard input and output."""
        with self._configuring():
            self._mcp_sources.append(lambda: self._own(StdioMcpBroker(
                command=command,
                arguments=arguments if arguments is not None else [],
                environment_variables=environment_variables,
                working_directory=working_directory,
                timeout_seconds=timeout_seconds)))

        return self

    def tool(self, tool: Tool) -> StandardAgent:
        """A tool the agent may call. A tool with a description is advertised to the model."""
        with self._configuring():
            self._tools.append(tool)

        return self

    def tools(self, tools: Iterable[Tool]) -> StandardAgent:
        """Several tools at once, as tool() each."""
        with self._configuring():
            self._tools.extend(tools)

        return self

    def log_to(
            self,
            path: str,
            *,
            verbosity: TraceVerbosity = TraceVerbosity.FULL) -> StandardAgent:
        """The human-readable trace, written to a file at the given verbosity."""
        with self._configuring():
            self._log_path = path
            self._trace_verbosity = verbosity

        return self

    def audit(self, path: str) -> StandardAgent:
        """The decision log (SPEC.md 4.8), written as JSON lines to a file."""
        with self._configuring():
            self._audit_path = path

        return self

    def audit_payloads(self) -> StandardAgent:
        """Records payloads in the decision log, as the configured redaction leaves them. Off,
        the default, the log records each payload's length and hash, never the payload."""
        with self._configuring():
            self._audit_payloads = True

        return self

    def use_audit(self, broker: AuditBroker) -> StandardAgent:
        """The decision log through your own audit broker."""
        with self._configuring():
            self._audit_broker = broker

        return self

    def on_audit(self, write: Callable[[AuditRecord], Awaitable[None]]) -> StandardAgent:
        """The decision log through your own write coroutine, one record at a time."""
        with self._configuring():
            self._audit_broker = FunctionAuditBroker(write)

        return self

    def telemetry(self, *, agent_name: str = "standard-agent") -> StandardAgent:
        """OpenTelemetry-shaped spans and metrics under this service name."""
        with self._configuring():
            self._telemetry_broker = ActivityTelemetryBroker(agent_name)

        return self

    def use_telemetry(self, broker: TelemetryBroker) -> StandardAgent:
        """Telemetry through your own telemetry broker."""
        with self._configuring():
            self._telemetry_broker = broker

        return self

    def on_telemetry(
            self,
            record: Callable[[str, Mapping[str, Any]], None]) -> StandardAgent:
        """Telemetry through your own (event_name, attributes) callable, for pipelines no
        listener reaches."""
        with self._configuring():
            self._telemetry_broker = FunctionTelemetryBroker(record)

        return self

    def principal(
            self,
            principal: Callable[[], AgentPrincipal | str | None]) -> StandardAgent:
        """Who is acting (SPEC.md 4.9), asked per act: a callable returning the principal, or
        just its id. It stamps the audit, owns sessions and is consulted by the perimeter."""
        with self._configuring():
            self._identity_resolver = lambda: _as_principal(principal())

        return self

    def redact(self, *rules: RedactionRule) -> StandardAgent:
        """PII redaction at every model boundary, with these rules, or the default ones."""
        with self._configuring():
            self._redaction_rules = rules if rules else RedactionRules.DEFAULT

        return self

    def use_redaction(self, broker: RedactionBroker) -> StandardAgent:
        """Redaction through your own redaction broker."""
        with self._configuring():
            self._redaction_broker = broker

        return self

    def on_redaction(
            self,
            redact: Callable[[str, MutableMapping[str, str]], str],
            rehydrate: Callable[[str, Mapping[str, str]], str]) -> StandardAgent:
        """Redaction through your own redact and rehydrate callables."""
        with self._configuring():
            self._redaction_broker = FunctionRedactionBroker(redact, rehydrate)

        return self

    def allow_tools(self, *tool_names: str) -> StandardAgent:
        """The only tools the agent may call, expressed as a policy; none closes the
        perimeter. An entry may name a scope: write_file:/project/."""
        with self._configuring():
            self._allowed_tools = tool_names

        return self

    def use_policy(self, broker: PolicyBroker) -> StandardAgent:
        """The perimeter's policy through your own policy broker."""
        with self._configuring():
            self._policy_broker = broker

        return self

    def on_policy(
            self,
            authorize: Callable[[AgentEffect], Awaitable[AuthorizationDecision]]) -> StandardAgent:
        """The perimeter's policy through your own authorize coroutine."""
        with self._configuring():
            self._policy_broker = FunctionPolicyBroker(authorize)

        return self

    def require_approval(self, *tool_names: str) -> StandardAgent:
        """Tools a person must approve before they run; their acts are irreversible."""
        with self._configuring():
            self._approval_required_tools = tool_names

        return self

    def use_approvals(self, broker: ApprovalBroker) -> StandardAgent:
        """Approvals through your own approval broker."""
        with self._configuring():
            self._approval_broker = broker

        return self

    def on_approval(
            self,
            request: Callable[[AgentEffect], Awaitable[ApprovalDecision]]) -> StandardAgent:
        """Approvals through your own request coroutine."""
        with self._configuring():
            self._approval_broker = FunctionApprovalBroker(request)

        return self

    def use_effect_ledger(self, broker: EffectLedgerBroker) -> StandardAgent:
        """The run-once ledger (SPEC.md 4.9) through your own broker."""
        with self._configuring():
            self._effect_ledger_broker = broker

        return self

    def effect_ledger(self, path: str) -> StandardAgent:
        """The run-once ledger in a folder, durable across processes, so a resumed session
        recognises an act it already performed."""
        with self._configuring():
            self._effect_ledger_broker = FileEffectLedgerBroker(path)

        return self

    def effect_lease(self, lease: timedelta) -> StandardAgent:
        """How long an in-flight claim on the ledger is presumed live. Defaults to five
        minutes."""
        with self._configuring():
            self._effect_lease = lease

        return self

    def on_effect_ledger(
            self,
            insert_claim: Callable[[EffectRecord], Awaitable[bool]],
            select_record: Callable[[str], Awaitable[EffectRecord | None]],
            update_record: Callable[[EffectRecord], Awaitable[None]],
            delete_record: Callable[[str], Awaitable[None]]) -> StandardAgent:
        """The run-once ledger through your own four coroutines."""
        with self._configuring():
            self._effect_ledger_broker = FunctionEffectLedgerBroker(
                insert_claim,
                select_record,
                update_record,
                delete_record)

        return self

    def screen_tool_output(self) -> StandardAgent:
        """Screens tool results with the Gate before the brain sees them."""
        with self._configuring():
            self._screen_tool_output = True

        return self

    def compensate_on_failure(self) -> StandardAgent:
        """Unwinds performed effects, through each tool's compensate, when a run fails."""
        with self._configuring():
            self._compensate_on_failure = True

        return self

    def max_turns(self, turns: int) -> StandardAgent:
        """How many turns a run may take. Fewer than one is one."""
        with self._configuring():
            self._max_turns = 1 if turns < 1 else turns

        return self

    def identical_call_limit(self, times: int) -> StandardAgent:
        """How many times a run may ask for an act the ledger already answered before it stops
        as going in circles. Fewer than two is two."""
        with self._configuring():
            self._identical_call_limit = 2 if times < 2 else times

        return self

    def use_skills(self, broker: SkillBroker) -> StandardAgent:
        """A skill source through your own skill broker. Sources accumulate."""
        with self._configuring():
            self._skill_sources.append(broker)

        return self

    def on_skills(self, select: Callable[[], Awaitable[Sequence[Skill]]]) -> StandardAgent:
        """A skill source through your own select coroutine. Sources accumulate."""
        with self._configuring():
            self._skill_sources.append(FunctionSkillBroker(select))

        return self

    def agents(self, path: str) -> StandardAgent:
        """A folder of agent documents, each registered as an agent the brain may hand off to.
        Registries accumulate."""
        with self._configuring():
            self._agent_sources.append(FileAgentRegistryBroker(_beside_the_process(path)))

        return self

    def use_agents(self, broker: AgentRegistryBroker) -> StandardAgent:
        """A registry of agents through your own registry broker."""
        with self._configuring():
            self._agent_sources.append(broker)

        return self

    def on_agents(
            self,
            select: Callable[[], Awaitable[Sequence[RegisteredAgent]]]) -> StandardAgent:
        """A registry of agents through your own select coroutine."""
        with self._configuring():
            self._agent_sources.append(FunctionAgentRegistryBroker(select))

        return self

    def identity(self, name: str, *, description: str = "") -> StandardAgent:
        """The agent's name and description: what a registry lists and a handoff calls."""
        with self._configuring():
            self._name = name
            self._description = description

        return self

    def use_generator(self, broker: GeneratorBroker) -> StandardAgent:
        """The brain through your own text-protocol generator broker."""
        with self._configuring():
            self._generator_broker = broker

        return self

    def native_brain(
            self,
            api_url: str,
            api_key: str,
            model: str,
            *,
            temperature: float = 0.7,
            max_tokens: int = 1024) -> StandardAgent:
        """A native tool-calling brain on an OpenAI-compatible endpoint."""
        _validate_api_url(api_url)

        with self._configuring():
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

    def native_brain_anthropic(
            self,
            api_key: str,
            model: str,
            *,
            temperature: float = 0.7,
            max_tokens: int = 1024) -> StandardAgent:
        """A native tool-calling brain on the Anthropic Messages API."""
        with self._configuring():
            self._generator_broker_v1 = None

            self._native_brain_source = lambda: AnthropicGeneratorBrokerV1(
                api_key,
                model,
                temperature,
                max_tokens,
                timeout_seconds=120,
                api_url=_ANTHROPIC_API_URL,
                handler=self._create_http_handler())

        return self

    def use_native_brain(self, broker: GeneratorBrokerV1) -> StandardAgent:
        """The native brain through your own native generator broker."""
        with self._configuring():
            self._native_brain_source = None
            self._generator_broker_v1 = broker

        return self

    def on_native_brain(
            self,
            generate: Callable[
                [Sequence[ConversationMessage], Sequence[ToolDefinition]],
                Awaitable[GenerationResult]]) -> StandardAgent:
        """The native brain through your own (conversation, tools) -> result coroutine."""
        with self._configuring():
            self._native_brain_source = None
            self._generator_broker_v1 = FunctionGeneratorBrokerV1(generate)

        return self

    def use_memory(self, broker: MemoryBroker) -> StandardAgent:
        """Memory through your own memory broker."""
        with self._configuring():
            self._memory_broker = broker

        return self

    def on_memory(
            self,
            recall: Callable[[], Awaitable[Sequence[str]]],
            remember: Callable[[str], Awaitable[None]]) -> StandardAgent:
        """Memory through your own recall and remember coroutines."""
        with self._configuring():
            self._memory_broker = FunctionMemoryBroker(recall, remember)

        return self

    def use_knowledge(self, broker: KnowledgeBroker | SourcedKnowledgeBroker) -> StandardAgent:
        """Knowledge through your own broker, plain or sourced (one that says where each passage
        came from, so an answer can cite it)."""
        with self._configuring():
            if isinstance(broker, SourcedKnowledgeBroker):
                self._sourced_knowledge_broker = broker
                self._knowledge_broker = None
            else:
                self._knowledge_broker = broker
                self._sourced_knowledge_broker = None

        return self

    def on_knowledge(self, retrieve: Callable[[str], Awaitable[Sequence[str]]]) -> StandardAgent:
        """Knowledge through your own retrieve coroutine."""
        with self._configuring():
            self._knowledge_broker = FunctionKnowledgeBroker(retrieve)
            self._sourced_knowledge_broker = None

        return self

    def on_sourced_knowledge(
            self,
            retrieve: Callable[[str], Awaitable[Sequence[KnowledgeResult]]]) -> StandardAgent:
        """Sourced knowledge through your own retrieve coroutine."""
        with self._configuring():
            self._sourced_knowledge_broker = FunctionSourcedKnowledgeBroker(retrieve)
            self._knowledge_broker = None

        return self

    def cite_knowledge(self, *, cite: bool = True, prefix: str = "Source: ") -> StandardAgent:
        """Whether answers end with the sources of the knowledge their run recalled (SPEC.md
        4.2), and the words each citation line starts with."""
        with self._configuring():
            self._cite_knowledge = cite
            self._knowledge_citation_prefix = prefix

        return self

    def use_gate(self, broker: ClassifierBroker) -> StandardAgent:
        """The Gate through your own classifier broker."""
        with self._configuring():
            self._classifier_broker = broker

        return self

    def use_judge(self, broker: VerifierBroker) -> StandardAgent:
        """The Judge through your own verifier broker."""
        with self._configuring():
            self._verifier_broker = broker

        return self

    def use_mcp(self, broker: McpBroker) -> StandardAgent:
        """An MCP server through your own MCP broker. Servers accumulate."""
        with self._configuring():
            self._mcp_sources.append(lambda: broker)

        return self

    def use_logging(self, broker: LoggingBroker) -> StandardAgent:
        """The trace through your own logging broker. An audit sink still decorates it."""
        with self._configuring():
            self._logging_broker = broker

        return self

    def sessions(self, path: str, *, max_history_turns: int = 20) -> StandardAgent:
        """Conversations kept in a folder (SPEC.md 4.11), each bounded to its recent turns."""
        with self._configuring():
            self._session_broker = FileSessionBroker(path)
            self._max_history_turns = max_history_turns

        return self

    def use_sessions(self, broker: SessionBroker) -> StandardAgent:
        """Conversations through your own session broker."""
        with self._configuring():
            self._session_broker = broker

        return self

    def on_sessions(
            self,
            select: Callable[[str], Awaitable[AgentSession | None]],
            upsert: Callable[[AgentSession], Awaitable[None]]) -> StandardAgent:
        """Conversations through your own select and upsert coroutines."""
        with self._configuring():
            self._session_broker = FunctionSessionBroker(select, upsert)

        return self

    def budget(
            self,
            *,
            max_tokens: int | None = None,
            max_cost_usd: Decimal | None = None,
            max_wall_clock: timedelta | None = None,
            cost_per_thousand_tokens: Decimal = Decimal(0)) -> StandardAgent:
        """What one prompt may consume (SPEC.md 4.10). A cost bound needs a positive rate,
        because cost is the token count times the rate."""
        _validate_budget(max_cost_usd, cost_per_thousand_tokens)

        with self._configuring():
            self._budget = AgentBudget(
                max_tokens=max_tokens,
                max_cost_usd=max_cost_usd,
                max_wall_clock=max_wall_clock,
                cost_per_thousand_tokens=cost_per_thousand_tokens)

        return self

    def usage(self, *, characters_per_token: float = 4.0) -> StandardAgent:
        """How tokens are counted when the provider does not say."""
        with self._configuring():
            self._usage_broker = RatioUsageBroker(characters_per_token)

        return self

    def permissions(self, mode: PermissionMode) -> StandardAgent:
        """The disposition toward acts that nothing explicitly permitted (SPEC.md 4.9)."""
        with self._configuring():
            self._permission_mode = mode

        return self

    def risk(self, level: RiskLevel, *tool_names: str) -> StandardAgent:
        """Declares the risk of tools the host did not write; the host's word wins over what a
        tool says of itself."""
        with self._configuring():
            for tool_name in tool_names:
                self._declared_risk[tool_name] = level

        return self

    def contract(self, json_schema: str) -> StandardAgent:
        """The JSON Schema every answer must satisfy; an answer that does not is revised."""
        with self._configuring():
            self._contract_schema = json_schema

        return self

    def use_contract(self, broker: ContractBroker) -> StandardAgent:
        """The contract's validation through your own contract broker."""
        with self._configuring():
            self._contract_broker = broker

        return self

    def on_contract(
            self,
            validate: Callable[[str, str], Awaitable[str | None]]) -> StandardAgent:
        """The contract's validation through your own (schema, answer) -> error coroutine."""
        with self._configuring():
            self._contract_broker = FunctionContractBroker(validate)

        return self

    def use_usage(self, broker: UsageBroker) -> StandardAgent:
        """Token counting through your own usage broker."""
        with self._configuring():
            self._usage_broker = broker

        return self

    def on_usage(self, count: Callable[[str], Awaitable[int]]) -> StandardAgent:
        """Token counting through your own count coroutine."""
        with self._configuring():
            self._usage_broker = FunctionUsageBroker(count)

        return self

    def resilience(self, *, retries: int = 3) -> StandardAgent:
        """Retries on the brain, with backoff."""
        with self._configuring():
            self._resilience_broker = RetryResilienceBroker(retries)

        return self

    def fallback(
            self,
            fallback: Callable[[], Awaitable[str]],
            *,
            retries: int = 0,
            failures_before_open: int = 3) -> StandardAgent:
        """A fallback answer when the brain keeps failing: retried, then a circuit that opens
        after failures_before_open failures and answers with the fallback."""
        with self._configuring():
            self._resilience_broker = FallbackResilienceBroker(
                primary=RetryResilienceBroker(retries),
                alternative=fallback,
                failures_before_open=failures_before_open)

        return self

    def use_resilience(self, broker: ResilienceBroker) -> StandardAgent:
        """Resilience through your own resilience broker."""
        with self._configuring():
            self._resilience_broker = broker

        return self

    def http(self, handlers: Callable[[], urllib.request.BaseHandler]) -> StandardAgent:
        """The host's HTTP handler under every HTTP broker the agent composes (F-23).

        Called once per broker. The handler is the host's: a proxy, a certificate, an observer.
        Without it, each broker builds its own.
        """
        with self._configuring():
            self._http_handler_source = handlers

        return self

    @classmethod
    def from_json(cls, json: str) -> StandardAgent:
        """An agent composed from a document: one key per verb, camelCased (docs/how-to.md).

        Tools and callables stay code; the document reaches everything that is data, and a key
        or value the agent does not know is refused by name with an
        InvalidAgentConfigurationException.
        """
        agent = cls()
        apply_document(agent, json)

        return agent

    @classmethod
    def from_json_file(cls, path: str) -> StandardAgent:
        """An agent composed from a document file."""
        with open(path, encoding="utf-8-sig") as file:
            return cls.from_json(file.read())

    @staticmethod
    def document_schema_json() -> str:
        """The JSON Schema of the document from_json reads, for an editor."""
        return document_schema_json()

    async def process_prompt(
            self,
            prompt: PromptRequest | str,
            *,
            session_id: str = "",
            cancellation: asyncio.Event | None = None) -> str:
        """Runs the agent to completion and returns the final answer.

        A session_id makes the prompt part of a conversation (SPEC.md 4.11): what was said
        before is loaded, and this exchange is recorded when it answers. A request carries its
        own session and inference options. Setting cancellation stops the run at its next turn
        boundary (SPEC.md 4.10). A composition failure surfaces on await.
        """
        agent = await self._resolve_agent()

        if isinstance(prompt, PromptRequest):
            return (await agent.run(prompt, cancellation=cancellation)).result

        return await agent.process_prompt(
            prompt,
            session_id=session_id,
            cancellation=cancellation)

    async def run_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        """The run asked for by a request, reported with how it ended."""
        return await (await self._resolve_agent()).run(request, cancellation=cancellation)

    async def resume(
            self,
            session_id: str,
            answer: str,
            *,
            cancellation: asyncio.Event | None = None) -> str:
        """Continues a session that stopped in the middle of something: waiting on a person,
        waiting on an authority, or killed outright (SPEC.md 4.9, 4.11).

        The same run as process_prompt in that session; it exists because resuming is what the
        caller is doing. A session that never delivered keeps the interrupted run's identity, so
        an act it already performed is replayed rather than performed twice.
        """
        return await (await self._resolve_agent()).process_prompt(
            answer,
            session_id=session_id,
            cancellation=cancellation)

    def process_prompt_stream(
            self,
            prompt: PromptRequest | str,
            *,
            session_id: str = "",
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        """The run's progress as it happens: status, thinking and response text as events.

        Every control the batched door enforces holds here too: budgets, cancellation and
        sessions (SPEC.md 7.6). A composition failure surfaces when iteration starts.
        """
        return self.stream_request(_as_request(prompt, session_id), cancellation=cancellation)

    async def stream_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        """The streamed run asked for by a request."""
        agent = await self._resolve_agent()

        async for stream_event in agent.run_stream(request, cancellation=cancellation):
            yield stream_event

    def run_stream(
            self,
            prompt: PromptRequest | str,
            *,
            session_id: str = "",
            cancellation: asyncio.Event | None = None) -> AgentRunStream:
        """The streamed outcome (SPEC.md 4.14): the run's events, carrying, once they are read,
        the same structured outcome run returns, pending effect and call id included."""
        request = _as_request(prompt, session_id)

        return AgentRunStream(
            lambda set_outcome: self._resolved_run_stream(request, set_outcome, cancellation))

    async def _resolved_run_stream(
            self,
            request: PromptRequest,
            set_outcome: Callable[[AgentOutcome], None],
            cancellation: asyncio.Event | None) -> AsyncIterator[AgentStreamEvent]:

        # The inner stream's outcome is handed outward when the enumeration ends, so the wrapper
        # the caller holds carries what the composed agent's run concluded.
        events = (await self._resolve_agent()).run_stream(request, cancellation=cancellation)

        async for stream_event in events:
            yield stream_event

        set_outcome(events.outcome)

    async def __aenter__(self) -> StandardAgent:
        return self

    async def __aexit__(self, *exception_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        with self._composition_lock:
            owned_mcp_brokers = list(self._owned_mcp_brokers)

        for owned_mcp_broker in owned_mcp_brokers:
            await owned_mcp_broker.aclose()

    @contextmanager
    def _configuring(self) -> Iterator[None]:
        # Every verb drops the cached composition, so configuration set after a prompt still
        # takes effect; returning self without doing so would silently ignore the change.
        with self._composition_lock:
            yield
            self._agent = None

    async def _resolve_agent(self) -> RunManagementService:
        # Registry selection is async (a registry can be a service call away) and a lock cannot
        # be held across an await, so resolution is three steps: reuse under the lock, select
        # outside it, compose under it again. A verb landing between the steps drops the cache,
        # so the next resolution selects and composes afresh: nothing configured is lost.
        with self._composition_lock:
            if self._agent is not None:
                return self._agent

            registries = list(self._agent_sources)

        registered_agents: list[RegisteredAgent] = []

        for registry in registries:
            registered_agents.extend(await registry.select_agents())

        with self._composition_lock:
            if self._agent is None:
                self._agent = self._compose(registered_agents)

            return self._agent

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

    def _own(self, mcp_broker: StdioMcpBroker) -> StdioMcpBroker:
        # Called by composition, under the composition lock: a broker the agent created is the
        # agent's to close, while one the host handed to use_mcp stays the host's.
        self._owned_mcp_brokers.append(mcp_broker)

        return mcp_broker

    def _current_principal_id(self) -> str | None:
        if self._identity_resolver is None:
            return None

        principal = self._identity_resolver()

        return None if principal is None else principal.id

    def _compose(self, registered_agents: Sequence[RegisteredAgent]) -> RunManagementService:
        """The one place the configured verbs become a graph of brokers and services."""
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
            else StdlibLoggingBroker(
                _null_logger(),
                self._trace_verbosity,
                self._log_path if self._log_path else None))

        audit = (
            self._audit_broker if self._audit_broker is not None
            else FileAuditBroker(self._audit_path) if self._audit_path
            else None)

        # Composed above the log, because the same redaction that guards the model boundary
        # guards the audit boundary (F-14); the generators and guardians take it by decoration.
        if self._redaction_broker is not None:
            redaction = self._redaction_broker
        elif self._redaction_rules is None:
            redaction = NotConfiguredRedactionBroker()
        else:
            redaction = RuleRedactionBroker(self._redaction_rules)

        logging = (
            trace if audit is None
            else AuditingLoggingBroker(
                trace,
                audit,
                SystemTimeBroker(),
                redaction,
                AuditPolicy(payloads=self._audit_payloads),
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

        # Without memory there is nothing to recall and no way to store: the foundation reads a
        # not-configured broker, and the remember tool is never registered, so the model is not
        # offered it (principal review 2026-09-04, F-05).
        if self._memory_disabled:
            memory_service = MemoryService(
                memory_broker=NotConfiguredMemoryBroker(),
                logging_broker=logging)
        elif self._memory_broker is not None:
            memory_service = MemoryService(
                memory_broker=self._memory_broker,
                logging_broker=logging)
        else:
            memory_service = MemoryService(
                file_broker=file,
                memory_path=os.path.abspath(self._memory_path),
                logging_broker=logging)

        all_tools = (
            list(self._tools) if self._memory_disabled
            else [*self._tools, RememberTool(memory_service.remember)])

        # The fleet materializes as tools, which is the whole design: a handoff is an act, so the
        # advertisement opt-in, the perimeter, the audit and cancellation across the seam all
        # apply because they already applied to tools. First to claim a name keeps it, the rule
        # MCP servers live by, so a registry cannot shadow a tool the host wired in code.
        claimed_names = {tool.name.lower() for tool in all_tools}

        for registered in registered_agents:
            if registered.name.lower() in claimed_names:
                continue

            claimed_names.add(registered.name.lower())

            all_tools.append(AgentTool(
                registered.name,
                registered.agent,
                AgentTool.GROUNDED_HANDOFF,
                registered.description))

        constitution = _read_optional_file(file, self._constitution_path)
        consumption = _read_optional_file(file, self._consumption_path)
        is_consumption_blank = not consumption or consumption.isspace()
        policy_of_gate = gate_policy() if is_consumption_blank else consumption
        policy_of_judge = judge_policy() if is_consumption_blank else consumption
        gate_rubric = compose_guardian_rubric(constitution, policy_of_gate, gate_contract())
        judge_rubric = compose_guardian_rubric(constitution, policy_of_judge, judge_contract())

        if self._classifier_broker is not None:
            classifier = self._classifier_broker
        elif self._local_gate_screen is not None:
            classifier = FunctionClassifierBroker(self._local_gate_screen, gate_rubric)
        elif self._gate_settings is None:
            classifier = NotConfiguredClassifierBroker()
        else:
            gate = self._gate_settings

            classifier = OpenAiClassifierBroker(
                gate.api_url,
                gate.api_key,
                gate.model,
                gate.temperature if gate.temperature is not None else 0.0,
                gate.max_tokens if gate.max_tokens is not None else 16,
                gate.timeout_seconds,
                gate_rubric)

        if self._verifier_broker is not None:
            verifier = self._verifier_broker
        elif self._local_judge_evaluate is not None:
            verifier = FunctionVerifierBroker(self._local_judge_evaluate, judge_rubric)
        elif self._judge_settings is None:
            verifier = NotConfiguredVerifierBroker()
        else:
            judge = self._judge_settings

            verifier = OpenAiVerifierBroker(
                judge.api_url,
                judge.api_key,
                judge.model,
                judge.temperature if judge.temperature is not None else 0.0,
                judge.max_tokens if judge.max_tokens is not None else 16,
                judge.timeout_seconds,
                judge_rubric)

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
            skills: SkillBroker = FileSkillBroker(_beside_the_process("Skills"))
        elif len(self._skill_sources) == 1:
            skills = self._skill_sources[0]
        else:
            skills = CompositeSkillBroker(self._skill_sources)

        skill_service = SkillService(skill_broker=skills, logging_broker=logging)

        if self._sourced_knowledge_broker is not None:
            knowledge_service = KnowledgeService(
                sourced_knowledge_broker=self._sourced_knowledge_broker,
                logging_broker=logging)
        elif self._knowledge_broker is not None:
            knowledge_service = KnowledgeService(
                knowledge_broker=self._knowledge_broker,
                logging_broker=logging)
        else:
            knowledge_service = KnowledgeService(
                file_broker=file,
                knowledge_path=os.path.abspath(self._knowledge_path),
                search_pattern=self._knowledge_pattern,
                max_results=self._knowledge_max_results,
                logging_broker=logging,
                minimum_score=self._knowledge_min_score)

        # One foundation over the remote tools, shared by the two natures that need it: Data
        # advertises what the servers offer, Direction performs what the Brain chose.
        external_tool_service = ExternalToolService(mcp_broker=mcp, logging_broker=logging)

        # The Data nature, as two regions and the coordination that composes them. Retrieval is
        # authored material selected by relevance; Recollection is what the agent accumulated.
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
                    session_broker=(
                        self._session_broker if self._session_broker is not None
                        else NotConfiguredSessionBroker()),
                    logging_broker=logging),
                logging_broker=logging),
            logging_broker=logging)

        # One redaction broker across every model the agent drives (SPEC.md 4.6), applied by
        # DECORATING each model broker: a foundation holds one broker and knows nothing of
        # redaction, so a model call added tomorrow cannot forget. Retry inside, redaction
        # outside: the redacted prompt is what gets retried, and rehydration happens once.
        resilience = (
            self._resilience_broker if self._resilience_broker is not None
            else NotConfiguredResilienceBroker())

        generator_at_the_wire = RedactingGeneratorBroker(
            RetryingGeneratorBroker(generator, resilience),
            redaction)

        native_brain = (
            self._generator_broker_v1 if self._generator_broker_v1 is not None
            else self._native_brain_source() if self._native_brain_source is not None
            else None)

        native_at_the_wire = (
            None if native_brain is None
            else RedactingGeneratorBrokerV1(
                RetryingGeneratorBrokerV1(native_brain, resilience),
                redaction))

        # The Decision nature, as two regions and the judgment between them. Inference asks the
        # model and reads its answer; Guardian screens what goes in and scores what comes out.
        decision = DecisionCoordinationService(
            inference_service=InferenceOrchestrationService(
                brain_service=BrainService(
                    generator_broker=generator_at_the_wire,
                    logging_broker=logging,
                    generator_broker_v1=native_at_the_wire),
                usage_service=UsageService(usage_broker=self._usage_broker, logging_broker=logging),
                logging_broker=logging,
                tool_definitions=render_tool_definitions(all_tools)),
            guardian_service=GuardianOrchestrationService(
                gate_service=GateService(
                    classifier_broker=RedactingClassifierBroker(classifier, redaction),
                    logging_broker=logging),
                judge_service=JudgeService(
                    verifier_broker=RedactingVerifierBroker(verifier, redaction),
                    logging_broker=logging),
                contract_service=ContractService(
                    contract_broker=(
                        self._contract_broker if self._contract_broker is not None
                        else RuleContractBroker()),
                    logging_broker=logging),
                logging_broker=logging),
            logging_broker=logging,
            contract_schema=self._contract_schema)

        # The allow-list is expressed as a policy, so the simple answer and an external policy
        # engine travel one seam and a denial carries a reason either way (SPEC.md 4.9).
        if self._policy_broker is not None:
            policy = self._policy_broker
        elif self._allowed_tools is None:
            policy = NotConfiguredPolicyBroker()
        else:
            policy = AllowListPolicyBroker(self._allowed_tools)

        if self._approval_broker is not None:
            approvals = self._approval_broker
        elif self._approval_required_tools is None:
            approvals = NotConfiguredApprovalBroker()
        else:
            approvals = RequireApprovalBroker(self._approval_required_tools)

        # The Direction nature, as two regions and the order between them. Perimeter answers
        # whether an act may happen; Execution performs it; the sequence belongs to neither.
        direction = DirectionCoordinationService(
            perimeter_service=PerimeterOrchestrationService(
                policy_service=PolicyService(policy_broker=policy, logging_broker=logging),
                approval_service=ApprovalService(
                    approval_broker=approvals,
                    logging_broker=logging),
                effect_ledger_service=EffectLedgerService(
                    effect_ledger_broker=(
                        self._effect_ledger_broker if self._effect_ledger_broker is not None
                        else InMemoryEffectLedgerBroker()),
                    time_broker=SystemTimeBroker(),
                    logging_broker=logging,
                    lease=self._effect_lease),
                time_broker=SystemTimeBroker(),
                logging_broker=logging),
            execution_service=ExecutionOrchestrationService(
                internal_tool_service=InternalToolService(
                    tool_broker=tool_broker,
                    logging_broker=logging),
                external_tool_service=external_tool_service,
                return_service=ReturnService(logging_broker=logging),
                logging_broker=logging),
            logging_broker=logging,
            policy=PerimeterPolicy(
                mode=self._permission_mode,
                irreversible_tools=tuple(self._approval_required_tools or ()),
                declared_risk=dict(self._declared_risk),

                # What each tool says about itself, read once at composition. The tool is the
                # only thing that knows what its arguments mean; the framework never parses them.
                tool_risk={tool.name: tool.risk for tool in all_tools},
                tool_scope={tool.name: tool.scope_of for tool in all_tools},

                # Whether the allow-list speaks to an act at all, which the mode needs and a
                # yes/no decision cannot carry. None without an allow-list, so ASK asks about
                # everything.
                explicitly_permits=(
                    policy.mentions if isinstance(policy, AllowListPolicyBroker) else None),
                identity_resolver=self._identity_resolver,
                enforce_selection=self._enforce_selection,

                # What selection could have offered, from the same rendering the catalogs use, so
                # the perimeter can tell a withheld tool from an undescribed one.
                advertised_tools=tuple(tool.name for tool in advertised(all_tools))))

        return RunManagementService(
            data_coordination_service=data,
            decision_coordination_service=decision,
            direction_coordination_service=direction,
            logging_broker=logging,
            max_turns=self._max_turns,
            time_broker=SystemTimeBroker(),
            budget=self._budget,
            max_history_turns=self._max_history_turns,
            compensate_on_failure=self._compensate_on_failure,
            screen_tool_output=self._screen_tool_output,
            telemetry_broker=self._telemetry_broker,
            contract_schema=self._contract_schema,
            configured_temperature=brain.temperature if brain is not None else None,
            configured_max_tokens=brain.max_tokens if brain is not None else None,
            configured_tool_names=[tool.name for tool in all_tools],
            tool_narrations=render_tool_narrations(all_tools),
            tool_selector=(
                ToolSelector(self._local_tool_selector)
                if self._local_tool_selector is not None else None),
            described_tool_names=[tool.name for tool in advertised(all_tools)],
            principal_resolver=(
                PrincipalResolver(self._identity_resolver)
                if self._identity_resolver is not None else None),
            identical_call_limit=self._identical_call_limit,
            configured_cite_knowledge=self._cite_knowledge,
            knowledge_citation_prefix=self._knowledge_citation_prefix)


def _as_request(prompt: PromptRequest | str, session_id: str) -> PromptRequest:
    # A plain prompt is a request that expressed no opinions; a request carries its own session.
    if isinstance(prompt, PromptRequest):
        return prompt

    return PromptRequest(prompt=prompt, session_id=session_id)


def _as_principal(principal: AgentPrincipal | str | None) -> AgentPrincipal | None:
    # A host that has only a user id passes the id; the agent wraps it, as the C# string form of
    # Principal does.
    return AgentPrincipal(id=principal) if isinstance(principal, str) else principal


def _beside_the_process(path: str) -> str:
    # .NET resolves these against the application's base directory; a Python process's is its
    # working directory. An absolute path stays as it is.
    return os.path.join(os.getcwd(), path)


def _null_logger() -> logging.Logger:
    """A logger that writes nothing, as .NET's NullLogger: the trace file is the record."""
    logger = logging.Logger("standard_agents")
    logger.disabled = True

    return logger


def _read_optional_file(file: FileBroker, path: str) -> str:
    """An optional prompt file (constitution, consumption), or empty when there is none.

    A missing file yields empty rather than an error, so a stale path degrades to the built-in
    guardian policy instead of bricking composition.
    """
    if not path or path.isspace():
        return ""

    full_path = _beside_the_process(path)

    return file.read_file_sync(full_path) if file.file_exists(full_path) else ""


async def _native_brain_only(system_prompt: str, user_prompt: str) -> str:
    raise RuntimeError("This agent has a native brain; the text protocol is not in use.")


def _warn_renamed(new_name: str) -> None:
    warnings.warn(
        f"Renamed to {new_name}: a delegate is the Custom mode, not the Local one. "
        + "Local means a provider that runs on your own machine. This alias keeps working.",
        DeprecationWarning,
        stacklevel=3)


def _validate_composition(has_brain: bool) -> None:
    # A native brain is a brain. Either seam satisfies this: the check exists to catch an agent
    # with no way to think at all, not to prefer one contract over the other.
    if not has_brain:
        raise InvalidAgentCompositionException(
            message=(
                "Agent has no brain. Call Brain(apiUrl, apiKey, model), "
                + "UseGenerator(broker) or NativeBrain(apiUrl, apiKey, model) "
                + "before processing a prompt."))


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
