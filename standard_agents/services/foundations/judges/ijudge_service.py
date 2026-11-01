# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from abc import ABC, abstractmethod

from standard_agents.models.foundations.judges.judgement import Judgement


class IJudgeService(ABC):
    @abstractmethod
    async def evaluate(self, task: str, candidate: str) -> Judgement: ...
