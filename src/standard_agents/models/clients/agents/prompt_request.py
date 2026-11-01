# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.brokers.sessions.agent_session import AgentTurn
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange


# What one caller asked for, on one request (docs/per-request-inference.md 3). Exists at the
# entry's signature and never travels below it: the loop carries ResolvedInference, the output
# of precedence, so no tier can ever see a value precedence discarded.
# A record, not an interface: a request does not do anything, it is something. Deliberately
# absent: executable tools, permissions, budget, redaction, approvals, principal. caller_tools
# grants the model vocabulary, never the agent capability.
@dataclass(frozen=True)
class PromptRequest:
    prompt: str = ""

    # Session identity is data about the request and rides the record. Cancellation does not:
    # it is runtime control, not a statement about the request, so the entry keeps it as a
    # parameter.
    session_id: str = ""

    # The caller-owned transcript: what was said before, oldest first. When a session exists it
    # wins: the deployment's record of the conversation beats the caller's retelling of it.
    history: tuple[AgentTurn, ...] = ()

    # Tool calls the caller already executed and is answering: the second half of the yield.
    tool_exchanges: tuple[ToolExchange, ...] = ()

    # The shape the answer must take. None means the caller expressed no opinion.
    response_schema_json: str | None = None

    # Nullable throughout, because "unset" must be representable: precedence depends on
    # distinguishing a value the caller chose from one they never mentioned.
    temperature: float | None = None
    max_tokens: int | None = None
    seed: int | None = None
    stop: tuple[str, ...] = ()

    # Tools the CALLER will execute, declared so the model may name them. The agent never runs
    # one. A returned call naming one is a terminal answer addressed to the caller, not an act.
    caller_tools: tuple[ToolDefinition, ...] = ()

    # What the core cannot model and should not try to (chat_template_kwargs, thinking, grammar).
    # Carried opaquely, never read by the core, handed to the broker whole.
    provider_options_json: str | None = None

    # Whether this answer ends with the sources of the knowledge recalled into its run (SPEC.md
    # 4.2). None means the caller expressed no opinion. What the deployment configured wins.
    cite_knowledge: bool | None = None
