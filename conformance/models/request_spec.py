# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolExchangeSpec:
    """One call a prior turn made, and what it returned."""

    call_id: str
    tool_name: str
    arguments_json: str
    result: str


@dataclass(frozen=True)
class TurnSpec:
    """One prior exchange in the caller-owned transcript, oldest first.

    A turn carries what it DID as well as what it said. Without exchanges a vector could only
    say that a prior turn's text reached the Brain; a caller re-posting a conversation had
    nowhere to put a finished call but the request's own tool exchanges, this turn's in-flight
    work, where it certifies as evidence for the prompt being asked now (SPEC.md 4.11, 6).
    """

    prompt: str
    answer: str
    exchanges: list[ToolExchangeSpec] | None = None


@dataclass(frozen=True)
class CallerToolSpec:
    """A tool the CALLER will execute, declared so the model may name it.

    The agent never runs one (design 6): a call naming it is a terminal answer addressed to the
    caller.
    """

    name: str
    description: str = ""
    parameters_json: str = "{}"


@dataclass(frozen=True)
class RequestSpec:
    """What one caller asked for, per request (docs/per-request-inference.md 3).

    Every field is optional because "unset" must be representable: precedence depends on
    distinguishing a value the caller chose from one they never mentioned.
    """

    temperature: float | None = None
    max_tokens: int | None = None
    seed: int | None = None
    stop: list[str] | None = None
    response_schema_json: str | None = None
    provider_options_json: str | None = None
    caller_tools: list[CallerToolSpec] | None = None

    # Whether this caller asked for citation (SPEC.md 4.2): what the deployment configured wins.
    cite_knowledge: bool | None = None

    # The caller-owned transcript (design 3): the exposed protocols are stateless and the client
    # re-posts the conversation. When a session exists it wins.
    history: list[TurnSpec] | None = None
