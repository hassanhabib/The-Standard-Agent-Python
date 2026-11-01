# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class AgentCoordinationDependencyException(Xeption):
    pass


class AgentCoordinationDependencyValidationException(Xeption):
    pass


class AgentCoordinationValidationException(Xeption):
    pass


class FailedRunManagementServiceException(Xeption):
    pass


class InvalidAgentException(Xeption):
    pass


class RunManagementServiceException(Xeption):
    pass
