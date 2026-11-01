# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.models.orchestrations.effects.risk_level import RiskLevel
from standard_agents.tools.tool import Tool


class StubTool(Tool):
    """A tool that returns a fixed output and records every input it was handed.

    So a vector can assert what the tool was actually called with. Without the record, a tool
    that ignores its input hides parsing bugs: corrupted input produces the same output, and the
    vector still passes (conformance issue #78).
    """

    def __init__(
            self,
            name: str,
            output: str,
            *,
            reversible: bool = False,
            compensation_order: list[str] | None = None,
            risk: RiskLevel = RiskLevel.SAFE,
            scope_is_first_word: bool = False,
            narration_starting: str = "",
            narration_observed: str = "",
            description: str = "") -> None:
        self._name = name
        self._output = output
        self._reversible = reversible
        self._compensation_order = compensation_order
        self._risk = risk
        self._scope_is_first_word = scope_is_first_word
        self._narration_starting = narration_starting
        self._narration_observed = narration_observed
        self._description = description
        self._received_inputs: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def received_inputs(self) -> Sequence[str]:
        return self._received_inputs

    @property
    def description(self) -> str:
        # Empty by default: a stub is callable but unadvertised. A vector that needs the
        # ADVERTISEMENT observable (selection, SPEC.md 4.15) declares a description, because a
        # description is the opt-in (6.1).
        return self._description

    @property
    def narration_starting(self) -> str:
        # Declared, like risk and scope: the tool is what knows what its act means in the user's
        # language (SPEC.md 6.0).
        return self._narration_starting

    @property
    def narration_observed(self) -> str:
        return self._narration_observed

    @property
    def risk(self) -> RiskLevel:
        # Declared, because permission is what AND where and only the tool knows either.
        return self._risk

    def scope_of(self, input: str) -> str:
        # One named strategy, so a runner in any language implements the same thing: the scope is
        # the first space-separated word of the input, enough to express a path.
        return input.split(" ")[0] if self._scope_is_first_word else ""

    async def execute(self, input: str) -> str:
        self._received_inputs.append(input)

        return self._output

    async def compensate(self, input: str, outcome: str) -> str | None:
        # A stub declared reversible reverses itself and writes its name to the shared order, so
        # a vector can certify that the unwind ran in reverse. One that was not keeps the
        # interface's answer, None: the case a vector needs to prove is reported as an effect
        # that stands rather than silently counted as undone (SPEC.md 4.9).
        if not self._reversible:
            return None

        if self._compensation_order is not None:
            self._compensation_order.append(self.name)

        return f"reversed {outcome}"
