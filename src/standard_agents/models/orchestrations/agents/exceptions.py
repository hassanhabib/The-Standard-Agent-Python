# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeption import Xeption


class AgentOrchestrationDependencyException(Xeption):
    pass


class AgentOrchestrationDependencyValidationException(Xeption):
    pass


class AgentOrchestrationServiceException(Xeption):
    pass


class AgentOrchestrationValidationException(Xeption):
    pass


class FailedAgentOrchestrationServiceException(Xeption):
    pass


class NullAgentContextException(Xeption):
    pass
