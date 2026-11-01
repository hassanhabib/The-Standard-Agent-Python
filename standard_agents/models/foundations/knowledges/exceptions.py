# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class InvalidKnowledgeException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class KnowledgeValidationException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)


class FailedKnowledgeDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None) -> None:
        super().__init__(message, inner_exception)


class KnowledgeDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)


class FailedKnowledgeServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None) -> None:
        super().__init__(message, inner_exception)


class KnowledgeServiceException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)
