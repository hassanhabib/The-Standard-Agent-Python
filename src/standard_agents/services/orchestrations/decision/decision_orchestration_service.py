# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.services.foundations.brains.ibrain_service import IBrainService
from standard_agents.services.foundations.gates.igate_service import IGateService
from standard_agents.services.foundations.judges.ijudge_service import IJudgeService
from standard_agents.services.orchestrations.decision.decision_orchestration_service_exceptions import (
    try_catch)
from standard_agents.services.orchestrations.decision.decision_orchestration_service_validations import (
    validate_context)
from standard_agents.services.orchestrations.decision.decision_orchestration_service_protocol import (
    build_user_message,
    REFUSAL_MESSAGE,
    REFUSE_DIRECTION,
    interpret,
    is_final_answer,
    is_refusal,
    revision_feedback)
from standard_agents.services.orchestrations.decision.idecision_orchestration_service import (
    IDecisionOrchestrationService)

MINIMUM_ACCEPTABLE_SCORE = 0.3


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
        async def returning_context_function() -> AgentContext:
            validate_context(context)

            return await self.think_through(context)

        return await try_catch(self.logging_broker, returning_context_function)

    # Screen, then think, then review: the Gate before the brain sees the request, the Judge
    # before the user sees the answer.
    async def think_through(self, context: AgentContext) -> AgentContext:
        verdict = await self.gate_service.screen(context.prompt)

        # The Gate's reason is for the trace, not the user: a refusal says what it will not do,
        # never what the screen looked for.
        if is_refusal(verdict):
            await self.logging_broker.log_process("Decision", f"Gate refused: {verdict}")

            return dataclasses.replace(
                context,
                direction_type=REFUSE_DIRECTION,
                payload=REFUSAL_MESSAGE)

        user_message = build_user_message(context)
        reply = await self.brain_service.generate(context.system_prompt, user_message)
        decided = interpret(context, reply.strip())

        if is_final_answer(decided) is False:
            return decided

        judgement = await self.judge_service.evaluate(context.prompt, decided.payload)

        if judgement.score >= MINIMUM_ACCEPTABLE_SCORE:
            return decided

        # A rejected draft is never delivered. This turn decides nothing, so Direction has nothing
        # to act on; the brain sees why on the next turn, and the revision spends a turn of the
        # loop's budget (SPEC.md 4.2).
        await self.logging_broker.log_process(
            "Decision", f"Judge scored {judgement.score:.2f}: rejected, revising")

        return dataclasses.replace(
            context,
            observations=context.observations + (
                revision_feedback(judgement, decided.payload),),
            direction_type="",
            payload="",
            raw_reply=decided.raw_reply)
