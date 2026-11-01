# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Conversation and resumption (SPEC.md 4.11): what the loop writes into a session.

Invariant 4 still holds: the instance is stateless across prompts. What persists is the session,
and it lives in a broker outside the agent, which is what lets a pause be resumed by a different
process, long after the instance that created it is gone.
"""

from standard_agents.models.brokers.sessions.agent_session import AgentSession, AgentTurn
from standard_agents.models.foundations.sessions.exceptions import StaleSessionException
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus


def resumed_run_id(session: AgentSession | None) -> str | None:
    """The interrupted run a prompt in this session continues, or None for a fresh run.

    A session that never delivered an answer was interrupted (killed, cancelled, out of turns,
    or waiting on an authority). The next prompt continues that run, so the effects it already
    performed keep their idempotency keys and are replayed rather than performed twice
    (SPEC.md 4.9, 4.11).
    """
    if session is not None and session.run_id and not is_delivered(session.status):
        return session.run_id

    return None


def is_delivered(status: AgentStatus) -> bool:
    """Whether the caller got a conclusion: an answer, or a refusal that is itself an answer."""
    return status in (AgentStatus.RESPONDED, AgentStatus.REFUSED)


def checkpoint(session_id: str, existing: AgentSession | None, run_id: str) -> AgentSession:
    """The start-of-run checkpoint: who is working the session, not what was said.

    History is carried through untouched. This prompt has no answer yet, and writing one here
    would tell the next prompt the agent said something it never said.
    """
    return AgentSession(
        id=session_id,
        history=_history_of(existing),
        status=AgentStatus.WORKING,
        pending_question=(
            existing.pending_question
            if existing is not None and existing.pending_question is not None
            else ""),
        run_id=run_id)


def completed(context: AgentContext, existing: AgentSession | None, run_id: str) -> AgentSession:
    """The session once this prompt completed, with its turn appended."""
    return AgentSession(
        id=context.session_id,

        # What the turn DID travels with what it said. Recording the answer alone was lossy in a
        # way nothing errored on: the history reloaded, the run completed, and the calls that
        # produced the answer were simply gone (SPEC.md 4.11, SPEC.md 6).
        history=(
            *_history_of(existing),
            AgentTurn(context.prompt, context.result, exchanges=context.tool_exchanges)),

        status=context.status,
        run_id=run_id,

        # What the agent is waiting on, so a later prompt can see it was mid-question rather
        # than mid-nothing.
        pending_question=(
            context.result
            if context.status in (AgentStatus.AWAITING_INPUT, AgentStatus.AWAITING_APPROVAL)
            else ""),

        # Set only by the branch that holds an act, and the context belongs to this run alone,
        # so a run that did not hold anything carries nothing, and the session stops advertising
        # a held act as soon as one is permitted and performed.
        pending_effect=context.pending_effect)


def is_stale_session_write(exception: BaseException) -> bool:
    """Whether a session write was refused as stale.

    The refusal arrives wrapped by every tier it crossed; what it IS sits at the bottom.
    """
    current: BaseException | None = exception

    while current is not None:
        if isinstance(current, StaleSessionException):
            return True

        current = current.__cause__

    return False


def _history_of(existing: AgentSession | None) -> tuple[AgentTurn, ...]:
    if existing is None or existing.history is None:
        return ()

    return existing.history
