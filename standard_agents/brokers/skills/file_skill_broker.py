# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import glob
from pathlib import Path

from standard_agents.brokers.skills.iskill_broker import ISkillBroker


class FileSkillBroker(ISkillBroker):
    def __init__(self, skills_path: str, search_pattern: str = "**/*.md") -> None:
        self.skills_path = skills_path
        self.search_pattern = search_pattern

    async def select_skill_names(self) -> list[str]:
        return glob.glob(self.search_pattern, root_dir=self.skills_path, recursive=True)

    async def select_skill_content(self, skill_name: str) -> str:
        return Path(self.skills_path, skill_name).read_text(encoding="utf-8")
