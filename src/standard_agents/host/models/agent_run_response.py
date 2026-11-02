# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRunResponse:
    """How the run ended, in protocol form.

    Status travels beside the result because only Responded makes the result an answer: a
    consumer that cannot tell a held run from an answered one will eventually report unfinished
    work as done.
    """

    result: str
    status: str
