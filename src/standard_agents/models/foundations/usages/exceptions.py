# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedUsageDependencyException(Xeption):
    pass


class FailedUsageServiceException(Xeption):
    pass


class InvalidUsageException(Xeption):
    pass


class UsageDependencyException(Xeption):
    pass


class UsageDependencyValidationException(Xeption):
    pass


class UsageServiceException(Xeption):
    pass


class UsageValidationException(Xeption):
    pass
