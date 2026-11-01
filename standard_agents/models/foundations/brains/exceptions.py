# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class InvalidBrainException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class BrainValidationException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)


class FailedBrainDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None) -> None:
        super().__init__(message, inner_exception)


class BrainDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)


class FailedBrainServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None) -> None:
        super().__init__(message, inner_exception)


class BrainServiceException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)
