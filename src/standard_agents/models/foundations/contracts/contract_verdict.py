# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class ContractVerdict:
    """Whether an answer is the right shape.

    It sits beside the Judge's verdict on whether it is good enough. Both are verdicts on a
    draft at the same moment, which is why this is a guardian and not a new concept.

    satisfied: whether the answer matches the schema it was held to.
    reason: what is wrong with it, in words a model can act on. This is fed back as the reason a
    draft was rejected, so "expected an object" is worth more than "invalid": a revision the
    model cannot aim at is a turn spent for nothing.
    """

    satisfied: bool
    reason: str

    # The verdict when no contract was configured: everything satisfies nothing.
    UNCONSTRAINED: ClassVar["ContractVerdict"]


ContractVerdict.UNCONSTRAINED = ContractVerdict(satisfied=True, reason="")
