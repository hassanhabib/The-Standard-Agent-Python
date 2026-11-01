# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedGateDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class FailedGateServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class GateDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class GateDependencyValidationException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class GateServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class GateValidationException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class InvalidGateException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)
