# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class NullAgentContextException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DecisionOrchestrationValidationException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)


class DecisionOrchestrationDependencyValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None) -> None:
        super().__init__(message, inner_exception)


class DecisionOrchestrationDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None) -> None:
        super().__init__(message, inner_exception)
