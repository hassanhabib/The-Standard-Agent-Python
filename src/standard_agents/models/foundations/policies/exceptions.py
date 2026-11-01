# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedPolicyDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class FailedPolicyServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class InvalidPolicyException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class PolicyDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class PolicyServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class PolicyValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)
