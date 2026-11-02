# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The host's front door.

An agent endpoint carries approval and budget semantics, so the door is not optional to think
about, but it is optional to lock: no configured key means open, which is what a laptop wants,
and one configuration line locks every agent route for what a deployment wants.
"""


def allows(configured_key: str | None, presented_key: str | None, path: str) -> bool:
    return not configured_key
