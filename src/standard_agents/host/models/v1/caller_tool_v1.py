# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class CallerToolV1:
    """A tool the CALLER will execute, declared so the model may name it.

    The agent never runs one: a returned call naming it ends the run waiting on the caller, with
    the call as the pending effect. Parameters are a JSON Schema, as the model reads them.
    """

    name: str
    description: str
    parameters_json: str
