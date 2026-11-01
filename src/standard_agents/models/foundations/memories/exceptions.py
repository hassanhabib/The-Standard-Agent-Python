# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedMemoryDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class FailedMemoryServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class InvalidMemoryException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class MemoryDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class MemoryServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class MemoryValidationException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)
