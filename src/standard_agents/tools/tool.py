# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod

from standard_agents.models.orchestrations.effects.risk_level import RiskLevel


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        return ""

    @property
    def parameters(self) -> str:
        return "{}"

    # How consequential this tool is. Declared by the tool, because the tool is what knows.
    # The default is SAFE, which is what an unclassified tool was treated as before. A host can
    # raise it for tools it did not write (an MCP server cannot declare anything in code), and
    # the host's word wins, because the host is the one accountable for the deployment.
    @property
    def risk(self) -> RiskLevel:
        return RiskLevel.SAFE

    # What this tool is about to touch, given its input: a path, a host, an account. Empty when
    # the tool touches nothing addressable. Permission is not only what but where; the tool is
    # the one thing that knows what its arguments mean, so it names the target and the
    # framework carries it to the policy, the authority and the audit record.
    def scope_of(self, input: str) -> str:
        return ""

    # What the agent says to the user before performing this tool's act: a user-voiced floor
    # for turns where the model offered no narration of its own; a model-authored narration
    # takes precedence. Supports {tool} and {payload} slots. Empty means no narration.
    @property
    def narration_starting(self) -> str:
        return ""

    # What the agent says to the user after this tool's result has been observed and screened.
    # Supports the {tool} slot; never overridden by model narration. Empty means no narration.
    @property
    def narration_observed(self) -> str:
        return ""

    @abstractmethod
    async def execute(self, input: str) -> str:
        ...

    # Undoes what execute did, given the same input and what it returned. Returns what was done
    # to undo it, or None if this tool cannot be undone. A tool that cannot says so by leaving
    # this default, which is reported as an effect that stands; silently doing nothing and
    # reporting success would leave the caller believing the run was unwound when it was not.
    async def compensate(self, input: str, outcome: str) -> str | None:
        return None
