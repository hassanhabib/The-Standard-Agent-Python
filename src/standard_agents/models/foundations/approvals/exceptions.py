# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class ApprovalDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class ApprovalServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class ApprovalValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class FailedApprovalDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class FailedApprovalServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class InvalidApprovalException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)
