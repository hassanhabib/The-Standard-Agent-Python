# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.orchestrations.agents.exchange import Exchange


# A prompt that was answered, with the calls it made to be able to answer (SPEC.md 3.2).
@dataclass(frozen=True)
class Turn:
    prompt: str
    answer: str
    exchanges: tuple[Exchange, ...] = ()
