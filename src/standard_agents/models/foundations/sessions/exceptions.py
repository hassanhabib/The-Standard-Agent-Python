# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedSessionDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class FailedSessionServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class InvalidSessionException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class SessionDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class SessionDependencyValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class SessionServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class SessionValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class StaleSessionException(Xeption):
    """A session write based on a read that is no longer current.

    Another prompt in the same session wrote first. The store refused it rather than letting the
    last writer erase a completed turn; the caller re-reads and tries again.
    """

    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)
