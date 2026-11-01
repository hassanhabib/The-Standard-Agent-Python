# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The agent a vector describes, composed through the same verbs a host would call.

Every double here replaces a broker or a tool, never a service: the whole library under test is
the real one. The doubles are created once per vector, so call counts, scripts and recorded
inputs survive the instance rebuilds a cross-process vector asks for, the way a real server's
would.
"""

from __future__ import annotations

import shutil
from collections import deque
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

from standard_agents import StandardAgent
from standard_agents.brokers.approvals.approval_broker import ApprovalDecision
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.models.brokers.agents.registered_agent import RegisteredAgent
from standard_agents.models.brokers.audits.audit_record import AuditRecord
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)
from standard_agents.models.orchestrations.effects.permission_mode import PermissionMode
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel

from conformance.brokers.not_configured_mcp_broker import NotConfiguredMcpBroker
from conformance.brokers.recording_generator_broker import RecordingGeneratorBroker
from conformance.brokers.scripted_generator_broker import ScriptedGeneratorBroker
from conformance.brokers.scripted_honoring_generator_broker import (
    ScriptedHonoringGeneratorBroker)
from conformance.brokers.scripted_mcp_server import ScriptedMcpServer
from conformance.brokers.scripted_native_generator_broker import ScriptedNativeGeneratorBroker
from conformance.brokers.stub_knowledge_broker import StubKnowledgeBroker
from conformance.brokers.stub_memory_broker import StubMemoryBroker
from conformance.brokers.stub_skill_broker import StubSkillBroker
from conformance.models.fleet_agent import FleetAgent
from conformance.models.vector import Vector
from conformance.tools.stub_tool import StubTool


class VectorComposition:
    """One vector's doubles, what they observe, and the agent built on them.

    base_directory stands where .NET's application base directory stands: files a vector writes
    (sessions, ledger, knowledge, constitution, consumption) live there, and the agent resolves
    the relative constitution and consumption names against it as the process's working
    directory.
    """

    def __init__(self, vector: Vector, base_directory: Path) -> None:
        self.vector = vector
        self._base_directory = base_directory

        # The order the run was unwound in, written by the stubs as they reverse themselves.
        self.compensation_order: list[str] = []

        # Every identity the policy broker was handed, in order.
        self.policy_principals: list[str | None] = []

        # One scripted native model for the whole vector, so its recorded conversations survive
        # across instances exactly as a real endpoint's would.
        self.native_generator = (
            ScriptedNativeGeneratorBroker(vector.native_replies, vector.transient_failures)
            if vector.native_replies else None)

        self._approval_decisions = deque(
            ApprovalDecision[decision.upper()] for decision in vector.approval_decisions or ())

        self.scripted_mcp_servers = [
            ScriptedMcpServer(catalog, vector.mcp_tool_schemas)
            for catalog in vector.mcp_servers or ()]

        # The fleet (SPEC.md 4.8 v1.6): scripted specialists whose scripted brains keep their
        # place across instance rebuilds. What each was HANDED is recorded, because the grounded
        # handoff, the user's actual ask crossing the seam, is the thing worth certifying.
        self.agent_inputs: dict[str, list[str]] = {}
        self._fleet = [self._create_specialist(member) for member in vector.agents or ()]

        self.stub_tools = {
            name: self._create_stub_tool(name, output)
            for name, output in (vector.tools or {}).items()}

        # The guardians run through the real composition (on_gate / on_judge), so each is handed
        # the rubric the framework composed: constitution, then policy (or the consumption
        # skill), then the framework-owned contract. The defaults ("allow" / "1.0") are inert, so
        # a vector that sets no guardian fields behaves exactly as an always-allowing gate and an
        # always-approving judge.
        self.gate_rubric: str | None = None
        self.judge_rubric: str | None = None
        self.judge_input: str | None = None

        # The decision log, observed through its own custom sink (SPEC.md 4.8), so the
        # certification watches the records the framework produces rather than any storage.
        self.audit_records: list[AuditRecord] = []

        # Everything any model was shown, so a vector can certify that a sensitive value reached
        # none of them (SPEC.md 4.6).
        self.model_inputs: list[str] = []
        self.brain_inputs: list[str] = []
        self.prompt_screenings = 0

        # The honoring Brain by default; the one that never opted in when the vector certifies
        # degradation, so the interface's real default is what degrades, not a simulation.
        self.honoring_generator = (
            ScriptedHonoringGeneratorBroker(vector.generator_replies, vector.transient_failures)
            if vector.broker_honors_request else None)

        scripted_generator: GeneratorBroker = (
            self.honoring_generator
            if self.honoring_generator is not None
            else ScriptedGeneratorBroker(vector.generator_replies, vector.transient_failures))

        # Wrapped rather than replaced, so the real Brain path (redaction, rehydration,
        # streaming buffers) is what gets certified.
        self._recording_generator = RecordingGeneratorBroker(
            scripted_generator, self._record_brain_input)

        # Anything on disk from a previous run is cleared once, here, not inside build_agent,
        # which may be called again for the next prompt and would then erase the very session
        # and ledger that prompt is meant to resume from.
        for folder in (self.sessions_path, self._ledger_path):
            shutil.rmtree(folder, ignore_errors=True)

    @property
    def sessions_path(self) -> Path:
        # A real session store, in a folder unique to this vector, so conversation is certified
        # against something that actually persists.
        return self._base_directory / f"sessions-{self.vector.name}"

    @property
    def _ledger_path(self) -> Path:
        return self._base_directory / f"ledger-{self.vector.name}"

    async def build_agent(self) -> StandardAgent:
        """A fresh agent over the vector's doubles.

        Each prompt may run through a brand-new instance, which is the closest this harness
        comes to a different process: nothing but the files on disk survives between them. It
        is the only way to certify that a session and an effect ledger outlive the agent that
        wrote them.
        """
        vector = self.vector

        agent = (StandardAgent()
            .use_skills(StubSkillBroker())
            .use_generator(self._recording_generator)
            .use_memory(StubMemoryBroker(vector.memories))
            .use_mcp(NotConfiguredMcpBroker())
            .tools(self.stub_tools.values()))

        self._configure_integrations(agent)
        self._configure_guardians(agent)
        self._configure_perimeter(agent)
        self._configure_inference(agent)
        self._configure_resilience(agent)
        self._configure_data(agent)
        self._write_guardian_documents(agent)

        # A folder-backed ledger, so run-once is certified against a claim that outlives the
        # instance that made it rather than one held in the instance's own memory.
        if vector.durable_effect_ledger:
            agent.effect_ledger(str(self._ledger_path))

        return agent

    def _configure_integrations(self, agent: StandardAgent) -> None:
        vector = self.vector

        # Selection (SPEC.md 4.15): a scripted selector returning the vector's fixed set,
        # whatever the task, with an empty list as the valid offered-nothing case.
        if vector.enforce_selection:
            agent.enforce_selection()

        if vector.select_tools is not None:
            selected_tools = vector.select_tools

            async def select_tools(task: str, described: Sequence[str]) -> Sequence[str]:
                return selected_tools

            agent.on_select_tools(select_tools)

        # Plural integrations (SPEC.md 4.8 v1.5): scripted servers join in registration order,
        # the order IS the contract under contention, and each extra skill source accumulates
        # after the harness's stub through the same verb a host would use.
        for scripted_server in self.scripted_mcp_servers:
            agent.use_mcp(scripted_server)

        for extra_skill in vector.extra_skills or ():
            agent.on_skills(_select_extra_skill(extra_skill))

        # The fleet registers through the same verb a host would use, so what is certified is
        # the registry path itself: materialization as tools, the grounded default handoff, and
        # transfer semantics included.
        if self._fleet:
            fleet = self._fleet

            async def select_agents() -> Sequence[RegisteredAgent]:
                return fleet

            agent.on_agents(select_agents)

    def _configure_guardians(self, agent: StandardAgent) -> None:
        agent.on_gate(self._screen)
        agent.on_judge(self._evaluate)
        agent.on_audit(self._write_audit_record)

        if self.vector.redact:
            agent.redact()

        if self.vector.screen_tool_output:
            agent.screen_tool_output()

    def _configure_perimeter(self, agent: StandardAgent) -> None:
        vector = self.vector

        if vector.require_approval:
            agent.require_approval(*vector.require_approval)

        # The allow-list, which can say WHERE as well as WHAT: an entry is "tool" or
        # "tool:scopePrefix".
        if vector.allow_tools:
            agent.allow_tools(*vector.allow_tools)

        # The disposition toward an act nothing explicitly permitted.
        if vector.permission_mode and not vector.permission_mode.isspace():
            agent.permissions(PermissionMode[vector.permission_mode.upper()])

        # A scripted authority, so a vector can hold an act on one run and permit it on the next:
        # the shape of every real approval, where the answer arrives after the agent stopped. The
        # queue is shared across instances, so the second process sees the second decision.
        if vector.approval_decisions:
            agent.on_approval(self._request_approval)

        if vector.compensate_on_failure:
            agent.compensate_on_failure()

        if vector.principal is not None:
            principal = vector.principal
            agent.principal(lambda: principal)

        # A scripted policy engine that decides on the identity, which the allow-list cannot do:
        # it can say "not this tool", never "not for them". The principal it was handed is
        # recorded, because the decision's input is the thing worth certifying.
        if vector.principal is not None or vector.denied_for_principal:
            agent.on_policy(self._authorize)

    def _configure_inference(self, agent: StandardAgent) -> None:
        vector = self.vector

        if self.native_generator is not None:
            agent.use_native_brain(self.native_generator)

        # The deployment's side of precedence (docs/per-request-inference.md 4): a configured
        # contract, and hard-configured inference knobs. The URL is never dialed, the scripted
        # generator replaces the broker; only the configured VALUES matter here.
        if vector.contract_schema is not None:
            agent.contract(vector.contract_schema)

        if vector.configured_temperature is not None or vector.configured_max_tokens is not None:
            agent.brain(
                "http://scripted.invalid/",
                "",
                "scripted",
                temperature=vector.configured_temperature,
                max_tokens=vector.configured_max_tokens)

    def _configure_resilience(self, agent: StandardAgent) -> None:
        vector = self.vector

        if vector.retries > 0:
            agent.resilience(retries=vector.retries)

        if vector.max_turns is not None:
            agent.max_turns(vector.max_turns)

        if vector.identical_call_limit is not None:
            agent.identical_call_limit(vector.identical_call_limit)

        if vector.budget_max_wall_clock_seconds is not None:
            agent.budget(max_wall_clock=timedelta(seconds=vector.budget_max_wall_clock_seconds))

        # Set together rather than in separate calls: budget() replaces the whole bound, so
        # calling it twice would silently drop whichever was configured first.
        if vector.budget_max_tokens is not None or vector.budget_max_cost_usd is not None:
            agent.budget(
                max_tokens=vector.budget_max_tokens,
                max_cost_usd=vector.budget_max_cost_usd,
                cost_per_thousand_tokens=vector.budget_cost_per_thousand_tokens)

        if vector.session_id is not None:
            agent.sessions(str(self.sessions_path))

        if vector.fallback_reply is not None:
            fallback_reply = vector.fallback_reply

            async def fallback() -> str:
                return fallback_reply

            agent.fallback(fallback, failures_before_open=vector.failures_before_open)

    def _configure_data(self, agent: StandardAgent) -> None:
        vector = self.vector

        # A real knowledge folder, so the ranked retriever is certified against files rather
        # than a stub that could agree with any implementation. A vector without knowledge keeps
        # the empty stub, so nothing is retrieved and no vector is disturbed by this one existing.
        if vector.knowledge_passages:
            passages = vector.knowledge_passages

            async def retrieve(query: str) -> Sequence[str]:
                return passages

            agent.on_knowledge(retrieve)
        elif not vector.knowledge:
            agent.use_knowledge(StubKnowledgeBroker())
        else:
            knowledge_path = self._base_directory / f"knowledge-{vector.name}"
            knowledge_path.mkdir(parents=True, exist_ok=True)

            for file_name, content in vector.knowledge.items():
                _write_text(knowledge_path / file_name, content)

            agent.knowledge(str(knowledge_path), max_results=vector.knowledge_max_results)

        if vector.cite_knowledge is not None:
            agent.cite_knowledge(
                cite=vector.cite_knowledge,
                prefix=vector.citation_prefix if vector.citation_prefix is not None
                else "Source: ")

    def _write_guardian_documents(self, agent: StandardAgent) -> None:
        vector = self.vector

        # Written beside the process and named relatively, so the agent's own file resolution
        # is what finds them.
        if vector.constitution:
            file_name = f"{vector.name}.constitution.md"
            _write_text(self._base_directory / file_name, vector.constitution)
            agent.constitution(file_name)

        if vector.consumption:
            file_name = f"{vector.name}.consumption.md"
            _write_text(self._base_directory / file_name, vector.consumption)
            agent.consumption(file_name)

    def _create_specialist(self, member: FleetAgent) -> RegisteredAgent:
        handed: list[str] = []
        self.agent_inputs[member.name.lower()] = handed

        specialist = (StandardAgent()
            .use_skills(StubSkillBroker())
            .use_memory(StubMemoryBroker())
            .use_knowledge(StubKnowledgeBroker())
            .use_mcp(NotConfiguredMcpBroker())
            .use_generator(RecordingGeneratorBroker(
                ScriptedGeneratorBroker(member.replies),
                handed.append)))

        if member.rule_gate:
            specialist.rule_gate(*member.rule_gate)

        return RegisteredAgent(member.name, member.description, specialist)

    def _create_stub_tool(self, name: str, output: str) -> StubTool:
        vector = self.vector
        narration = (vector.tool_narrations or {}).get(name)

        # Risk is declared by the tool, because the tool is the only thing that knows.
        declared_risk = (vector.tool_risk or {}).get(name)

        return StubTool(
            name,
            output,
            reversible=name in (vector.compensating_tools or ()),
            compensation_order=self.compensation_order,
            risk=RiskLevel[declared_risk.upper()] if declared_risk is not None
            else RiskLevel.SAFE,
            scope_is_first_word=name in (vector.tool_scope_first_word or ()),
            narration_starting=(narration.starting or "") if narration is not None else "",
            narration_observed=(narration.observed or "") if narration is not None else "",
            description=(vector.tool_descriptions or {}).get(name, ""))

    def _record_brain_input(self, model_input: str) -> None:
        self.model_inputs.append(model_input)
        self.brain_inputs.append(model_input)

    async def _screen(self, rubric: str, prompt: str) -> str:
        vector = self.vector

        if self.gate_rubric is None:
            self.gate_rubric = rubric

        self.model_inputs.append(prompt)

        if prompt == vector.prompt:
            self.prompt_screenings += 1

        # Screening reuses the Gate, so the same scripted guardian answers for the prompt and for
        # tool output. A vector may script the two differently, which is how it refuses an
        # injected result while still letting the task through.
        is_tool_output = vector.screen_tool_output and prompt != vector.prompt

        # Narration is the third thing the Gate screens (SPEC.md 6.0): text that is neither the
        # prompt nor any tool's scripted output.
        is_narration = (
            prompt != vector.prompt and prompt not in (vector.tools or {}).values())

        if is_narration and vector.gate_verdict_on_narration is not None:
            return vector.gate_verdict_on_narration

        if is_tool_output and vector.gate_verdict_on_tool_output is not None:
            return vector.gate_verdict_on_tool_output

        return vector.gate_verdict if vector.gate_verdict is not None else "allow"

    async def _evaluate(self, rubric: str, candidate: str) -> str:
        self.judge_rubric = rubric
        self.judge_input = candidate
        self.model_inputs.append(candidate)

        return self.vector.judge_score if self.vector.judge_score is not None else "1.0"

    async def _write_audit_record(self, record: AuditRecord) -> None:
        self.audit_records.append(record)

    async def _request_approval(self, effect: AgentEffect) -> ApprovalDecision:
        return (
            self._approval_decisions.popleft()
            if self._approval_decisions else ApprovalDecision.PENDING)

    async def _authorize(self, effect: AgentEffect) -> AuthorizationDecision:
        self.policy_principals.append(effect.principal)

        if effect.tool_name in (self.vector.denied_for_principal or ()):
            return AuthorizationDecision.deny(
                f"'{effect.principal}' may not use '{effect.tool_name}'")

        return AuthorizationDecision.allow()


def _select_extra_skill(content: str):
    # The name carries the content's hash, as the reference runner's does; a name is all a
    # source needs to stay distinct from the stub's.
    skill = Skill(name=f"extra-{hash(content) & 0xFFFFFFFF:x}", content=content)

    async def select_skills() -> Sequence[Skill]:
        return [skill]

    return select_skills


def _write_text(path: Path, content: str) -> None:
    # UTF-8 without a byte order mark and without newline translation, as .NET writes it.
    path.write_text(content, encoding="utf-8", newline="")
