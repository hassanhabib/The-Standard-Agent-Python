# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


# A passage, with where it came from and how well it matched (SPEC.md §3.7).
#
# Text is what the Brain is shown, exactly what an unsourced broker returns. Score is the
# source's own measure and means nothing beside another source's: a lexical score, a full-text
# rank and a vector distance are different scales. Source is what a citation shows a person, so
# it is a title, a path or an address; empty means the origin is unknown and it is never cited.
@dataclass(frozen=True)
class KnowledgeResult:
    text: str = ""
    score: float | None = None
    source: str = ""
