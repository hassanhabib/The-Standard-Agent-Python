# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str = ""
    description: str = ""
    content: str = ""
