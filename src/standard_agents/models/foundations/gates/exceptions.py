# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedGateDependencyException(Xeption):
    pass


class FailedGateServiceException(Xeption):
    pass


class GateDependencyException(Xeption):
    pass


class GateDependencyValidationException(Xeption):
    pass


class GateServiceException(Xeption):
    pass


class GateValidationException(Xeption):
    pass


class InvalidGateException(Xeption):
    pass
