# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import glob
from pathlib import Path

from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.models.foundations.skills.skill import Skill


# Skills from a folder, found recursively, one skill per Markdown file, named by its path
# relative to the folder. Reading each file into a Skill is materialization only; frontmatter,
# ordering and selection are the SkillService's.
class FileSkillBroker(ISkillBroker):
    def __init__(self, skills_path: str, search_pattern: str = "**/*.md") -> None:
        self.skills_path = skills_path
        self.search_pattern = search_pattern

    async def select_skills(self) -> list[Skill]:
        skill_names = glob.glob(self.search_pattern, root_dir=self.skills_path, recursive=True)

        return [
            Skill(
                name=Path(skill_name).as_posix(),
                content=Path(self.skills_path, skill_name).read_text(encoding="utf-8"))
            for skill_name in skill_names
        ]
