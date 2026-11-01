# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedInternalToolDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class FailedInternalToolServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class InternalToolDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class InternalToolServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class InternalToolValidationException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class InvalidInternalToolException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)
