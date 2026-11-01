# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass


# Internal to the library (C#: internal sealed record).
# temperature and max_tokens are nullable because "configured" must be representable: precedence
# (docs/per-request-inference.md 4.2) has to distinguish a value the host chose from one the
# host never mentioned. The framework default is the resolution's third rung, applied at the
# boundary; the moment these fields defaulted here, "hard configured wins" silently became
# "defaulted wins" and a request's temperature could never take effect.
@dataclass(frozen=True)
class InferenceSettings:
    api_url: str
    api_key: str
    model: str
    temperature: float | None
    max_tokens: int | None
    timeout_seconds: int
