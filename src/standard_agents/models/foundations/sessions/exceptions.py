# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedSessionDependencyException(Xeption):
    pass


class FailedSessionServiceException(Xeption):
    pass


class InvalidSessionException(Xeption):
    pass


class SessionDependencyException(Xeption):
    pass


class SessionDependencyValidationException(Xeption):
    pass


class SessionServiceException(Xeption):
    pass


class SessionValidationException(Xeption):
    pass


class StaleSessionException(Xeption):
    """A session write based on a read that is no longer current.

    Another prompt in the same session wrote first. The store refused it rather than letting the
    last writer erase a completed turn; the caller re-reads and tries again.
    """
