# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition


# The output of precedence (configured, then request, then framework default), resolved once at
# the boundary (docs/per-request-inference.md 2, 4). This is what rides the context and reaches
# the brokers; PromptRequest never travels below the entry, so a tier handed this record cannot
# see a value precedence discarded. That is what makes the dangerous state (a model constrained
# to one schema and validated against another) unreachable rather than avoided.
@dataclass(frozen=True)
class ResolvedInference:
    # The framework's third rung, applied by resolution at the boundary and nowhere else.
    # Brokers receive concrete values and decide nothing.
    DEFAULT_TEMPERATURE: ClassVar[float] = 0.7
    DEFAULT_MAX_TOKENS: ClassVar[int] = 1024

    # Concrete, not nullable: precedence has already run, so the framework default has already
    # been applied. No tier below the entry ever supplies a default.
    temperature: float = 0.7
    max_tokens: int = 1024

    # Nullable where "absent from the wire" is itself the meaning.
    seed: int | None = None
    stop: tuple[str, ...] = ()

    # The schema that SURVIVED precedence: configured when a Contract exists, the request's
    # otherwise. There is no field for the losing schema.
    response_schema_json: str | None = None

    # The caller's tools: vocabulary for the model, never capability for the agent. Direction
    # classifies a call naming one as a terminal answer addressed to the caller.
    caller_tools: tuple[ToolDefinition, ...] = ()

    # Opaque to the core; the broker merges it under the core-owned-keys rule (4.4): every key
    # the core writes is non-overridable, stripped on collision and logged.
    provider_options_json: str | None = None
