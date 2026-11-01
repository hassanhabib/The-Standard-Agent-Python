# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------


# The stand-in for System.Data.DBConcurrencyException, which Python has no equivalent of: a
# session store refusing a write that was based on a version no longer current. A session
# broker of the host's own raises it for the same refusal, and the session foundation localizes
# it as a stale session. Like the .NET type, it is not an OSError.
class DBConcurrencyException(Exception):
    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message
