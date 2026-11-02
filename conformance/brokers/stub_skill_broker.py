# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.models.foundations.skills.skill import Skill


class StubSkillBroker(SkillBroker):
    """One skill, the same for every vector."""

    async def select_skills(self) -> Sequence[Skill]:
        return [Skill(name="test", content="You are a test agent.")]
