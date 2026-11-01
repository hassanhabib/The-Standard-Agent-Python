# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


# How much an act costs to get wrong. SAFE is the default, so an agent that adopts effects
# without classifying its tools behaves exactly as it did before (SPEC.md 3.3).
class RiskLevel(Enum):
    # Reversible and cheap: a calculation, a lookup.
    SAFE = 0

    # Reversible but consequential: a draft saved, a record updated.
    SENSITIVE = 1

    # Cannot be taken back: a payment, a message sent, a record deleted.
    IRREVERSIBLE = 2
