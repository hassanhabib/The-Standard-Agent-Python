# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The second lock on the front door.

When the deployment configured authentication, an agent route wants an authenticated user; the
heartbeat stays open either way, and a deployment that configured nothing is as open as before
(principal review 2026-09-04, F-10).
"""


def allows(authentication_configured: bool, user_is_authenticated: bool, path: str) -> bool:
    return not authentication_configured or path.upper() == "/API/HOME" or user_is_authenticated
