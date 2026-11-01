# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class AgentCoordinationDependencyException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class AgentCoordinationDependencyValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class AgentCoordinationValidationException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class FailedRunManagementServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)


class InvalidAgentException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class RunManagementServiceException(Xeption):
    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)
