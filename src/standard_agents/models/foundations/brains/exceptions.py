# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class BrainDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class BrainDependencyValidationException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class BrainServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class BrainValidationException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class FailedBrainDependencyException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class FailedBrainServiceException(Xeption):
    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)


class InvalidBrainException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnreachableBrainException(Xeption):
    """
    Nothing answered at all: a refused connection, a name that resolves to nothing, a request that
    never left the machine (SPEC.md §4.10, v1.14). The person's next step is the address and
    whatever should be listening at it, not support, so this is the sentence they are shown. The
    native fault is kept as the inner exception for whoever investigates.
    """

    def __init__(
        self,
        message: str,
        inner_exception: BaseException | None = None,
    ) -> None:
        super().__init__(message, inner_exception)
