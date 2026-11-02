# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------


class DBConcurrencyException(Exception):
    """A session store refusing a write that was based on a version no longer current.

    The stand-in for .NET's System.Data.DBConcurrencyException, which Python has no equivalent
    of. A session broker of the host's own raises it for the same refusal, and the session
    foundation localizes it as a stale session. Like the .NET type, it is not an OSError.
    """

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message
