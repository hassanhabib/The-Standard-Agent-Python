# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.foundations.brains.ibrain_service import IBrainService
from standard_agents.services.foundations.gates.igate_service import IGateService
from standard_agents.services.foundations.judges.ijudge_service import IJudgeService
from standard_agents.services.orchestrations.decision.decision_orchestration_service_protocol import (
    build_user_message,
    interpret,
    is_final_answer)
from standard_agents.services.orchestrations.decision.idecision_orchestration_service import (
    IDecisionOrchestrationService)


class DecisionOrchestrationService(IDecisionOrchestrationService):
    def __init__(
        self,
        brain_service: IBrainService,
        gate_service: IGateService,
        judge_service: IJudgeService,
        logging_broker: ILoggingBroker) -> None:

        self.brain_service = brain_service
        self.gate_service = gate_service
        self.judge_service = judge_service
        self.logging_broker = logging_broker

    async def think(self, context: AgentContext) -> AgentContext:
        await self.gate_service.screen(context.prompt)
        user_message = build_user_message(context)
        reply = await self.brain_service.generate(context.system_prompt, user_message)
        decided = interpret(context, reply.strip())

        if is_final_answer(decided) is False:
            return decided

        await self.judge_service.evaluate(context.prompt, decided.payload)

        return decided
