# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


# A tool's declared narration templates: starting is voiced before the act (supports {tool} and
# {payload} slots; a model-authored narration overrides it), observed after the result (supports
# {tool}; never overridden). Derived from the tool, so the loop can voice acts without holding
# the tools themselves.
@dataclass(frozen=True)
class ToolNarration:
    starting: str
    observed: str
