# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


# A remote tool server's own account of a tool it holds (SPEC.md 4.1). input_schema is JSON.
@dataclass(frozen=True)
class RemoteTool:
    name: str
    description: str = ""
    input_schema: str = "{}"
