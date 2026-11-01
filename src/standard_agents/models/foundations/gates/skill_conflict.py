# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.foundations.gates.skill_directive import SkillDirective


@dataclass(frozen=True)
class SkillConflict:
    options: tuple[SkillDirective, ...]
