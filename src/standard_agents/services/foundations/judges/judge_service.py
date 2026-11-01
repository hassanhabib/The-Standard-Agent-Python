# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.foundations.judges.judgement import Judgement

_SCORE_LABEL = "SCORE:"
_REASON_LABEL = "REASON:"


class JudgeService:
    """Scores a candidate answer as an answer to its task, from the verifier's verdict."""

    def __init__(
            self,
            *,
            verifier_broker: VerifierBroker,
            logging_broker: LoggingBroker) -> None:

        self.verifier_broker = verifier_broker
        self.logging_broker = logging_broker

    async def evaluate(self, task: str, candidate: str) -> Judgement:
        verdict = await self.verifier_broker.verify(task, candidate)

        return _parse_judgement(verdict)


def _parse_judgement(verdict: str) -> Judgement:
    text = verdict.strip()
    labeled_score = _extract_labeled(text, _SCORE_LABEL)

    if labeled_score is None:
        score_text = text
    else:
        score_text = next((part for part in labeled_score.split(" ") if part), labeled_score)

    score = float(score_text)
    reason = _extract_labeled(text, _REASON_LABEL) or ""

    return Judgement(score=score, reason=reason)


def _extract_labeled(text: str, label: str) -> str | None:
    for line in text.split("\n"):
        trimmed_line = line.strip()

        if trimmed_line.lower().startswith(label.lower()):
            return trimmed_line[len(label):].strip()

    return None
