# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    """A readiness profile: the named set of vectors an implementation must pass to claim it.

    Profiles turn "enterprise-ready" from a claim into something a build can fail.

    name: Core, Reliable, Enterprise or Critical.
    description: what an agent at this profile can be trusted to do.
    inherits: the profile this one builds on; its requirements apply too.
    requires: vector names that must pass. A named vector that does not exist is a failure, not
        a skip; otherwise a profile could be claimed by simply never writing its evidence.
    """

    name: str
    description: str | None
    inherits: str | None
    requires: list[str]
