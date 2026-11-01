# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class EffectLedgerDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class EffectLedgerServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class EffectLedgerValidationException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class FailedEffectLedgerDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class FailedEffectLedgerServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class InvalidEffectLedgerException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)
