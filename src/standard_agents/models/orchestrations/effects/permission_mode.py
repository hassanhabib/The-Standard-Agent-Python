# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from enum import Enum


class PermissionMode(Enum):
    """What happens to an act that nothing explicitly permitted.

    Explicit permissions (AllowTools, a policy broker, RequireApproval) always answer first.
    This is only the disposition toward everything they did not mention, which is the case that
    cannot be enumerated in advance.
    """

    # Permitted. The default, and what every release before this one did: an unlisted tool ran
    # without being asked about, which is right for a chat agent and wrong for an agent with hands.
    OPEN = 0

    # Requires approval. Ask-first: the posture an agent with hands should run under.
    ASK = 1

    # Denied. Nothing runs but what was named.
    DENY = 2
