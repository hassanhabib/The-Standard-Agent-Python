# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The host's front door.

An agent endpoint carries approval and budget semantics, so the door is not optional to think
about, but it is optional to lock: no configured key means open, which is what a laptop wants,
and one configuration line locks every agent route for what a deployment wants.
"""

import hmac


def allows(configured_key: str | None, presented_key: str | None, path: str) -> bool:
    return (
        not configured_key
        or path.upper() == "/API/HOME"
        or _keys_match(configured_key, presented_key))


def _keys_match(configured_key: str, presented_key: str | None) -> bool:
    # Fixed-time on the bytes, because a comparison that returns at the first wrong character
    # hands an attacker the key one character at a time.
    return (
        presented_key is not None
        and hmac.compare_digest(configured_key.encode("utf-8"), presented_key.encode("utf-8")))
