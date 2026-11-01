# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Why a run stopped at a turn boundary, in the words and the codes the caller is given.

Exhaustion and cancellation are reported distinguishably from a refusal (SPEC.md 4.10): a caller
that cannot tell "I will not" from "I ran out" cannot decide whether to retry, and a cancelled
run's result is not an answer.
"""

from standard_agents.models.clients.agents.agent_failure import AgentFailure
from standard_agents.models.clients.agents.agent_failure_category import AgentFailureCategory
from standard_agents.models.clients.agents.agent_failure_codes import AgentFailureCodes

CANCELLED_MESSAGE = "The request was cancelled before it completed."

TOKEN_BUDGET_MESSAGE = (
    "The token budget for this request was exhausted before it completed.")

COST_BUDGET_MESSAGE = (
    "The cost budget for this request was exhausted before it completed.")

TIME_BUDGET_MESSAGE = (
    "The time budget for this request was exhausted before it completed.")

_BUDGET_MESSAGES = (TOKEN_BUDGET_MESSAGE, COST_BUDGET_MESSAGE, TIME_BUDGET_MESSAGE)


def circles_message(identical_call_limit: int) -> str:
    """What a run that kept asking for an act the ledger already answered says (SPEC.md 4.10)."""
    return (
        f"I asked for the same thing {identical_call_limit} times and stopped: the run was going "
        "in circles, so it ended rather than spend the rest of its turns the same way; nothing "
        "was delivered.")


def stopped_failure(
        stopped_because: str,
        result: str,
        going_in_circles_message: str) -> AgentFailure | None:
    """Which kind of stop it was, as a code for the caller that switches on codes.

    The message is the whole result the run carries, so a caller reading either one is told the
    same thing (SPEC.md 3.6, v1.14).
    """
    if stopped_because == going_in_circles_message:
        return AgentFailure(
            AgentFailureCategory.SERVICE, AgentFailureCodes.GOING_IN_CIRCLES, result)

    if stopped_because == CANCELLED_MESSAGE:
        return AgentFailure(AgentFailureCategory.SERVICE, AgentFailureCodes.CANCELLED, result)

    if stopped_because in _BUDGET_MESSAGES:
        return AgentFailure(
            AgentFailureCategory.SERVICE, AgentFailureCodes.BUDGET_EXHAUSTED, result)

    return None
