# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedPolicyDependencyException(Xeption):
    pass


class FailedPolicyServiceException(Xeption):
    pass


class InvalidPolicyException(Xeption):
    pass


class PolicyDependencyException(Xeption):
    pass


class PolicyServiceException(Xeption):
    pass


class PolicyValidationException(Xeption):
    pass
