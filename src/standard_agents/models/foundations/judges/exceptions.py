# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedJudgeDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class FailedJudgeServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class InvalidJudgeException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidJudgeScoreException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class JudgeDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class JudgeDependencyValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class JudgeServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class JudgeValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)
