# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class ApprovalDependencyException(Xeption):
    pass


class ApprovalServiceException(Xeption):
    pass


class ApprovalValidationException(Xeption):
    pass


class FailedApprovalDependencyException(Xeption):
    pass


class FailedApprovalServiceException(Xeption):
    pass


class InvalidApprovalException(Xeption):
    pass
