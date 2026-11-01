# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.sessions.db_concurrency_exception import DBConcurrencyException
from standard_agents.brokers.sessions.session_broker import SessionBroker
from standard_agents.models.brokers.sessions.agent_session import AgentSession
from standard_agents.models.foundations.sessions.exceptions import (
    FailedSessionDependencyException,
    InvalidSessionException,
    SessionDependencyException,
    SessionDependencyValidationException,
    SessionValidationException,
    StaleSessionException)
from xeptions import Xeption


class SessionService:
    """The conversation, as a foundation rather than as a broker reached from above.

    Coordination held the session broker directly, which meant a disk full or a permission denied
    surfaced unmapped and was attributed to the loop rather than to the store. A foundation is
    what supplies the three things that call was missing: validation, exception mapping, and
    attribution (docs/architecture-alignment.md).
    """

    def __init__(
            self,
            *,
            session_broker: SessionBroker,
            logging_broker: LoggingBroker) -> None:

        self.session_broker = session_broker
        self.logging_broker = logging_broker

    async def retrieve_session(self, session_id: str) -> AgentSession | None:
        """The conversation so far, or None when this is the first prompt in it."""
        async with _handling_exceptions(self.logging_broker):
            _validate_session_id(session_id)

            # A conversation that has not started is not an error: None is the ordinary first
            # prompt, and it has to stay distinguishable from a failure to read.
            return await self.session_broker.select_session(session_id)

    async def record_session(self, session: AgentSession) -> None:
        """Writes the conversation back, replacing what was there."""
        async with _handling_exceptions(self.logging_broker):
            _validate_session(session)

            await self.session_broker.upsert_session(session)


def _validate_session_id(session_id: str | None) -> None:
    if not session_id or session_id.isspace():
        raise InvalidSessionException(
            message="Invalid session. Please correct the error and try again.")


def _validate_session(session: AgentSession | None) -> None:
    """Rejects a missing session, or one with no id.

    A session with no id cannot be read back, so writing one loses the conversation silently: the
    next prompt finds nothing and the agent forgets, with no error anywhere to explain it.
    """
    if session is None or not session.id or session.id.isspace():
        raise InvalidSessionException(
            message="Invalid session. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidSessionException as invalid_session_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_session_exception)
    except DBConcurrencyException as db_concurrency_exception:
        stale_session_exception = StaleSessionException(
            message="The session was written by another prompt since it was read; "
                "read it again and retry.",
            inner_exception=db_concurrency_exception)

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, stale_session_exception)
    except OSError as os_error:
        raise await _create_and_log_dependency_exception(logging_broker, os_error)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> SessionValidationException:

    session_validation_exception = SessionValidationException(
        message="Session validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(session_validation_exception)

    return session_validation_exception


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> SessionDependencyValidationException:

    session_dependency_validation_exception = SessionDependencyValidationException(
        message="Session dependency validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(session_dependency_validation_exception)

    return session_dependency_validation_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> SessionDependencyException:

    session_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(session_dependency_exception)

    return session_dependency_exception


def _create_dependency_exception(exception: Exception) -> SessionDependencyException:
    failed_session_dependency_exception = FailedSessionDependencyException(
        message="Failed session dependency error occurred, contact support.",
        inner_exception=exception)

    return SessionDependencyException(
        message="Session dependency error occurred, contact support.",
        inner_exception=failed_session_dependency_exception)
