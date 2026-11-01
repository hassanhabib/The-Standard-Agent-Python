# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


# A composition the agent cannot run. Raised at the door, before any nature is composed, so a
# missing brain is a configuration mistake the host sees, not a failure deep inside a run.
class InvalidAgentConfigurationException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)
