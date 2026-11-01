# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from restfulsense.exceptions import (
    HttpRequestException,
    HttpResponseBadRequestException,
    HttpResponseForbiddenException,
    HttpResponseInternalServerErrorException,
    HttpResponseNotFoundException,
    HttpResponseServiceUnavailableException,
    HttpResponseUnauthorizedException,
    HttpResponseUrlNotFoundException)
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.foundations.judges.exceptions import (
    FailedJudgeDependencyException,
    FailedJudgeServiceException,
    InvalidJudgeException,
    InvalidJudgeScoreException,
    JudgeDependencyException,
    JudgeDependencyValidationException,
    JudgeServiceException,
    JudgeValidationException)
from standard_agents.models.foundations.judges.judgement import Judgement

_MINIMUM_SCORE = 0.0
_MAXIMUM_SCORE = 1.0
_SCORE_LABEL = "SCORE:"
_REASON_LABEL = "REASON:"

# NumberStyles.Float under the invariant culture: ASCII white space around an optional sign, digits
# with an optional decimal point and exponent, or NaN and Infinity in any case. .NET also ignores
# trailing NUL characters.
_INVARIANT_NUMBER = re.compile(
    r"[\t\n\v\f\r ]*([+-]?(?:(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?|nan|infinity))[\t\n\v\f\r ]*\x00*",
    re.ASCII | re.IGNORECASE)


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
        async with _handling_exceptions(self.logging_broker):
            _validate_evaluate(candidate)
            verdict = await self.verifier_broker.verify(task, candidate)
            judgement = _parse_judgement(verdict)
            _validate_score(judgement.score)

            return judgement


def _validate_evaluate(candidate: str | None) -> None:
    if not candidate or candidate.isspace():
        raise InvalidJudgeException(
            message="Invalid judge input. Please correct the error and try again.")


def _parse_judgement(verdict: str | None) -> Judgement:
    text = (verdict or "").strip()
    labeled_score = _extract_labeled(text, _SCORE_LABEL)

    if labeled_score is None:
        score_text = text
    else:
        score_text = next((part for part in labeled_score.split(" ") if part), labeled_score)

    score = _parse_number(score_text)

    if score is None:
        raise InvalidJudgeScoreException(
            message="Invalid judge score. Score must be a number between 0.0 and 1.0.")

    reason = _extract_labeled(text, _REASON_LABEL) or ""

    return Judgement(score=score, reason=reason)


def _parse_number(text: str) -> float | None:
    """Reads a number the way .NET's invariant double.TryParse does, or returns None.

    float() alone is looser: it takes underscores ("0_5"), "inf", and non-ASCII digits, all of
    which the C# Judge rejects as not a number.
    """
    number_match = _INVARIANT_NUMBER.fullmatch(text)

    return float(number_match.group(1)) if number_match else None


def _extract_labeled(text: str, label: str) -> str | None:
    for line in text.split("\n"):
        trimmed_line = line.strip()

        if trimmed_line.lower().startswith(label.lower()):
            return trimmed_line[len(label):].strip()

    return None


def _validate_score(score: float) -> None:
    # Written as a range check rather than its negation so that NaN, which compares false to
    # everything, is out of range.
    if not _MINIMUM_SCORE <= score <= _MAXIMUM_SCORE:
        raise InvalidJudgeScoreException(
            message="Invalid judge score. Score must be between 0.0 and 1.0.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except (InvalidJudgeException, InvalidJudgeScoreException) as invalid_judge_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_judge_exception)
    except HttpResponseBadRequestException as http_response_bad_request_exception:
        invalid_judge_exception = InvalidJudgeException(
            message="Invalid judge request. Please correct the error and try again.")

        invalid_judge_exception.add_data(http_response_bad_request_exception.data)

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, invalid_judge_exception)
    except (
            HttpResponseUnauthorizedException,
            HttpResponseForbiddenException,
            HttpResponseNotFoundException,
            HttpResponseUrlNotFoundException,
            HttpRequestException) as critical_exception:

        raise await _create_and_log_critical_dependency_exception(
            logging_broker, critical_exception)
    except (
            HttpResponseInternalServerErrorException,
            HttpResponseServiceUnavailableException) as dependency_exception:

        raise await _create_and_log_dependency_exception(logging_broker, dependency_exception)
    except Exception as exception:
        failed_judge_service_exception = FailedJudgeServiceException(
            message="Failed judge service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_judge_service_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> JudgeValidationException:

    judge_validation_exception = JudgeValidationException(
        message="Judge validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(judge_validation_exception)

    return judge_validation_exception


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> JudgeDependencyValidationException:

    judge_dependency_validation_exception = JudgeDependencyValidationException(
        message="Judge dependency validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(judge_dependency_validation_exception)

    return judge_dependency_validation_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> JudgeDependencyException:

    judge_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(judge_dependency_exception)

    return judge_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> JudgeDependencyException:

    judge_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(judge_dependency_exception)

    return judge_dependency_exception


def _create_dependency_exception(exception: Exception) -> JudgeDependencyException:
    failed_judge_dependency_exception = FailedJudgeDependencyException(
        message="Failed judge dependency error occurred, contact support.",
        inner_exception=exception)

    return JudgeDependencyException(
        message="Judge dependency error occurred, contact support.",
        inner_exception=failed_judge_dependency_exception)


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> JudgeServiceException:

    judge_service_exception = JudgeServiceException(
        message="Judge service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(judge_service_exception)

    return judge_service_exception
