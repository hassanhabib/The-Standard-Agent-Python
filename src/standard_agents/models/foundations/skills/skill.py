# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


# One discrete skill (SPEC.md 4.2): an identity, an optional description, and a body. A skill
# with a description is advertised in the skill catalog; the description is the opt-in.
@dataclass(frozen=True)
class Skill:
    name: str
    content: str
    description: str = ""
