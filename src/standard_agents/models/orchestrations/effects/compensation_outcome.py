# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class CompensationOutcome:
    """What became of one effect when the run was unwound (SPEC.md 4.9).

    tool_name: the tool whose act was being undone.
    undone: whether it was actually reversed. False means the effect stands: either the tool
    declared no way back, or the attempt to undo it failed.
    detail: what was done, or why it could not be.
    """

    tool_name: str
    undone: bool
    detail: str
