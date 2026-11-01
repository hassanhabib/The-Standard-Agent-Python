# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from conformance.models.document_binding import bind
from conformance.models.profile import Profile


def profile_requirements(profile_name: str, profiles_path: Path) -> list[str]:
    """A profile's requirements: its own plus everything it inherits.

    So certifying Reliable certifies Core too: a level is a floor, never a substitute. Names are
    compared without regard to case, and each is listed once, where it first appears.
    """
    requirements: list[str] = []
    next_profile_name: str | None = profile_name

    while next_profile_name is not None:
        profile_file = profiles_path / f"{next_profile_name.lower()}.json"

        if not profile_file.is_file():
            raise FileNotFoundError(
                f"No such readiness profile: '{next_profile_name}'. Expected {profile_file}.")

        profile = bind(
            Profile,
            json.loads(profile_file.read_text(encoding="utf-8-sig"), parse_float=Decimal))

        requirements.extend(profile.requires)
        next_profile_name = profile.inherits

    distinct: dict[str, str] = {}

    for requirement in requirements:
        distinct.setdefault(requirement.lower(), requirement)

    return list(distinct.values())
