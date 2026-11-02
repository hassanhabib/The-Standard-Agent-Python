# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from restfulsense import HttpRequestException
from standard_agents.brokers.contracts.contract_broker import ContractBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.contracts.contract_verdict import ContractVerdict
from standard_agents.models.foundations.contracts.exceptions import (
    ContractDependencyException,
    ContractServiceException,
    ContractValidationException,
    FailedContractDependencyException,
    FailedContractServiceException,
    InvalidContractException)


class ContractService:
    """Whether an answer is the right SHAPE: the question the client contract could never answer.

    process_prompt returns a string, so every consumer wiring an agent into a workflow wrote a
    parser, which is the thing this framework talked them out of doing everywhere else. Native
    tool calling gives structured input TO tools; the agent's own answer was always prose.

    It sits beside the Judge rather than anywhere else because it is the same kind of verdict at
    the same moment: the Judge asks whether a draft is good enough, this asks whether it is the
    right shape, and both run before a draft becomes an answer.
    """

    def __init__(self, *, contract_broker: ContractBroker, logging_broker: LoggingBroker) -> None:
        self.contract_broker = contract_broker
        self.logging_broker = logging_broker

    async def check(self, answer: str, schema: str) -> ContractVerdict:
        """Whether an answer is the shape it was held to.

        When it is not, the verdict says what a model should do about it.
        """
        async with _handling_exceptions(self.logging_broker):
            _validate_answer(answer)

            # No schema is not a failed check, it is no check. An agent given no contract is not
            # constrained by having become checkable: the same rule as counting always being on
            # while blocking is not.
            if not schema or schema.isspace():
                return ContractVerdict.UNCONSTRAINED

            complaint = await self.contract_broker.validate(answer, schema)

            if not complaint or complaint.isspace():
                return ContractVerdict.UNCONSTRAINED

            return ContractVerdict(satisfied=False, reason=complaint)


def _validate_answer(answer: str | None) -> None:
    """Empty is a legitimate answer to check; None is not.

    A model that said nothing has not satisfied a schema, and reporting that honestly is the
    point. None is a caller that lost the draft it meant to validate, and treating it as an empty
    answer would report a bug as a model failure.
    """
    if answer is None:
        raise InvalidContractException(
            message="Invalid contract, answer is required. "
                    "Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidContractException as invalid_contract_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_contract_exception)
    except json.JSONDecodeError as json_decode_error:
        # A JsonException is not an ArgumentException in .NET, so it is a service failure there;
        # here it is a ValueError, and would otherwise be read as a malformed schema below.
        raise await _create_and_log_service_exception(
            logging_broker, _create_failed_service_exception(json_decode_error))
    except ValueError:
        # A malformed SCHEMA is the host's error, not the model's, and the distinction is
        # load-bearing: reported as a model failure it would send every draft into a revision
        # chasing a fault no reply can fix, until the turn budget runs out.
        raise await _create_and_log_validation_exception(
            logging_broker,
            InvalidContractException(
                message="Invalid contract, the schema is not valid JSON. "
                        "Please correct the error and try again.")) from None
    except HttpRequestException as http_request_exception:
        raise await _create_and_log_dependency_exception(
            logging_broker,
            FailedContractDependencyException(
                message="Failed contract dependency error occurred, contact support.",
                inner_exception=http_request_exception))
    # asyncio.TimeoutError is its own class before Python 3.11.
    except (TimeoutError, asyncio.TimeoutError) as timeout_error:
        raise await _create_and_log_dependency_exception(
            logging_broker,
            FailedContractDependencyException(
                message="Failed contract dependency error occurred, contact support.",
                inner_exception=timeout_error))
    except Exception as exception:
        raise await _create_and_log_service_exception(
            logging_broker, _create_failed_service_exception(exception))


def _create_failed_service_exception(exception: Exception) -> FailedContractServiceException:
    return FailedContractServiceException(
        message="Failed contract service error occurred, contact support.",
        inner_exception=exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ContractValidationException:

    contract_validation_exception = ContractValidationException(
        message="Contract validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(contract_validation_exception)

    return contract_validation_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ContractDependencyException:

    contract_dependency_exception = ContractDependencyException(
        message="Contract dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(contract_dependency_exception)

    return contract_dependency_exception


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> ContractServiceException:

    contract_service_exception = ContractServiceException(
        message="Contract service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(contract_service_exception)

    return contract_service_exception
