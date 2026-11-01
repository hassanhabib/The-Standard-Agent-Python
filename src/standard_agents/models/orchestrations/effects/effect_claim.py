# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from dataclasses import dataclass

from standard_agents.models.brokers.effects.effect_record import EffectRecord
from standard_agents.models.orchestrations.effects.effect_claim_verdict import EffectClaimVerdict


# The perimeter's answer to "may this act run": the verdict, the recorded outcome when the
# verdict is to replay it, and the prior record when there is one to reconcile.
@dataclass(frozen=True)
class EffectClaim:
    verdict: EffectClaimVerdict
    outcome: str | None
    record: EffectRecord | None
