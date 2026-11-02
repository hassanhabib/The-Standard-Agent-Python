# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureV1:
    """Why the run stopped without an answer, in protocol form: the wire form of AgentFailure.

    The code is what a caller switches on (cancelled, budget_exhausted, turns_exhausted,
    going_in_circles), so a caller across HTTP decides whether to retry the same way a caller in
    process does, never by reading the sentence.
    """

    category: str
    code: str
    message: str
