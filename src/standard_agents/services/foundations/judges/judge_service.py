# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker
from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.services.foundations.judges.ijudge_service import IJudgeService
from standard_agents.services.foundations.judges.judge_service_exceptions import try_catch
from standard_agents.services.foundations.judges.judge_service_validations import (
    validate_evaluate)


SCORE_FIELD = "SCORE"
REASON_FIELD = "REASON"
SCORE_PREFIX = SCORE_FIELD + ":"


class JudgeService(IJudgeService):
    def __init__(
        self,
        verifier_broker: IVerifierBroker,
        logging_broker: ILoggingBroker) -> None:

        self.verifier_broker = verifier_broker
        self.logging_broker = logging_broker

    # The task travels with the candidate: an answer is good or bad for a question.
    async def evaluate(self, judge_prompt: str, task: str, candidate: str) -> Judgement:
        async def returning_judgement_function() -> Judgement:
            validate_evaluate(task, candidate)
            verdict = await self.verifier_broker.verify(judge_prompt, task, candidate)

            return parse_judgement(verdict)

        return await try_catch(self.logging_broker, returning_judgement_function)


# A verdict written to the Judge's contract carries SCORE: and REASON: lines; a bare verdict is a
# score optionally followed by a reason, which is what a deterministic Judge most often returns.
def parse_judgement(verdict: str) -> Judgement:
    lines = verdict.strip().split("\n")

    if lines[0].strip().upper().startswith(SCORE_PREFIX):
        fields = {}

        for line in lines:
            key, _, value = line.partition(":")
            fields[key.strip().upper()] = value.strip()

        return Judgement(score=float(fields[SCORE_FIELD]), reason=fields.get(REASON_FIELD, ""))

    score, _, reason = verdict.strip().partition(" ")

    return Judgement(score=float(score), reason=reason.strip())
