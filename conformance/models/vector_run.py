# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from standard_agents.models.brokers.audits.audit_record import AuditRecord
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus

from conformance.brokers.scripted_native_generator_broker import ScriptedNativeGeneratorBroker
from conformance.tools.stub_tool import StubTool


@dataclass(frozen=True)
class VectorRun:
    """Everything one vector's run produced and everything its doubles observed.

    agent_inputs is keyed by the fleet member's name folded to lower case: a handoff is
    certified under the name a vector writes, whatever its case.
    """

    result: str
    prompt_results: list[str]
    tools: dict[str, StubTool]
    gate_rubric: str | None
    judge_rubric: str | None
    judge_input: str | None
    model_inputs: list[str]
    brain_inputs: list[str]
    prompt_screenings: int
    audit_records: list[AuditRecord]
    compensation_order: list[str]
    native_generator: ScriptedNativeGeneratorBroker | None
    policy_principals: list[str | None]
    mcp_server_calls: list[int]
    agent_inputs: dict[str, list[str]]
    status: AgentStatus | None
    pending_effect_tool: str | None
    broker_inferences: Sequence[ResolvedInference]
    streamed_events: list[AgentStreamEvent]
    session_turn_count: int | None
    failure_code: str | None
