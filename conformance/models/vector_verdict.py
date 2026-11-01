# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VectorVerdict:
    """Every check one vector's run was held to: a flag for the four the report explains from
    the vector, and the failure sentence (None when it conforms) for the rest."""

    result_conformant: bool
    per_prompt_results_conformant: bool
    tool_input_conformant: bool
    agent_input_conformant: bool
    rubric_failure: str | None
    audit_failure: str | None
    guardian_input_failure: str | None
    request_failure: str | None
    narration_failure: str | None
    usage_failure: str | None

    @property
    def conformant(self) -> bool:
        return (
            self.result_conformant
            and self.per_prompt_results_conformant
            and self.tool_input_conformant
            and self.rubric_failure is None
            and self.audit_failure is None
            and self.guardian_input_failure is None
            and self.request_failure is None
            and self.agent_input_conformant
            and self.narration_failure is None
            and self.usage_failure is None)
