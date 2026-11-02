# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.host.models.v1.agent_turn_v1 import AgentTurnV1
from standard_agents.host.models.v1.caller_tool_v1 import CallerToolV1
from standard_agents.host.models.v1.tool_exchange_v1 import ToolExchangeV1


@dataclass(frozen=True)
class AgentRunRequestV1:
    """What to run, in full: the wire form of PromptRequest, version 1 of the host's contract.

    Everything about a run that is data travels here: the session to continue, the caller-owned
    transcript, the tool calls the caller already executed, the tools the caller will execute,
    and the caller's inference controls. A hosted agent that composed sessions, approvals and
    caller tools could not use any of them over HTTP when the wire carried a prompt alone
    (principal review 2026-09-04, F-10).

    Deliberately absent, as on PromptRequest: executable tools, permissions, budget, redaction,
    approvals, principal. The wire has no field in which to ask for them.

    Continuing a held run is this same request: post the authority's decision, or the person's
    reply, as the prompt on the same session. Completing a caller's tool call is this same
    request too: post the exchange, naming the call id the model minted, on the same session.
    """

    prompt: str = ""
    session_id: str = ""
    history: tuple[AgentTurnV1, ...] = ()
    tool_exchanges: tuple[ToolExchangeV1, ...] = ()
    caller_tools: tuple[CallerToolV1, ...] = ()
    response_schema_json: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    seed: int | None = None
    stop: tuple[str, ...] = ()
    provider_options_json: str | None = None
    cite_knowledge: bool | None = None
