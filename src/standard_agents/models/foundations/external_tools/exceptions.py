# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class InvalidExternalToolException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ExternalToolValidationException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)


class FailedExternalToolDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None) -> None:
        super().__init__(message, inner_exception)


class ExternalToolDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)


class FailedExternalToolServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None) -> None:
        super().__init__(message, inner_exception)


class ExternalToolServiceException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)
