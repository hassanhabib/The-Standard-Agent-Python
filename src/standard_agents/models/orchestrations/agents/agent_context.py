# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.sessions.agent_session import AgentTurn
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect


@dataclass(frozen=True)
class AgentContext:
    prompt: str = ""

    # The conversation this prompt belongs to, and what was said before (SPEC.md 3.2, 4.11).
    # Empty when no session is configured, which is exactly the stateless agent that existed
    # before sessions did.
    session_id: str = ""
    history: tuple[AgentTurn, ...] = ()

    # What this run's inference resolved to (configured, then request, then framework default),
    # applied once at the boundary (docs/per-request-inference.md 2). None only for a context
    # built by hand; a tier reading it treats None as "the run carried no opinions".
    inference: ResolvedInference | None = None

    system_prompt: str = ""
    observations: tuple[str, ...] = ()

    # Where the knowledge recalled into this run came from (SPEC.md 3.2, 3.7): each non-empty
    # source once, in the order first recalled. Beside the observations rather than inside them.
    grounding_sources: tuple[str, ...] = ()

    # What a native call asked for and what came back, kept as a pair (SPEC.md 6). On the V0
    # text path this stays empty and observations remain the whole record.
    tool_exchanges: tuple[ToolExchange, ...] = ()

    # The call Direction is performing this turn, so its result can be tied back to it. Empty
    # outside the native path.
    tool_call_id: str = ""

    # The act an authority has been asked to permit and has not yet answered on (SPEC.md 4.9,
    # 4.11). It rides out to the session so a different process can show a human the act itself.
    pending_effect: AgentEffect | None = None

    intent: str = ""
    route: str = ""
    direction_type: str = ""
    payload: str = ""
    raw_reply: str = ""

    # This turn's user-voiced progress prose, peeled off the reply (SAY:) or carried by a native
    # result. Never part of the answer, the observations, or the session history.
    narration: str = ""

    # What the turn's model calls cost. The provider's own report when there is one, counted by
    # the Usage foundation when there is not (SPEC.md 3.4).
    prompt_tokens: int = 0
    completion_tokens: int = 0

    # Which of those two it was. An estimate is enough to enforce a bound and not enough to
    # reconcile one against an invoice.
    usage_is_estimated: bool = False

    # This turn's act is a transfer: the Brain handed the whole run to a registered agent. Set by
    # Inference when it reads TRANSFER:, cleared on every other intent.
    transferring: bool = False

    result: str = ""
    remember: str = ""
    status: AgentStatus = AgentStatus.WORKING
