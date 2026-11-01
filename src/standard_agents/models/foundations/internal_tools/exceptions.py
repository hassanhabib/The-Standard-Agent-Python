# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedInternalToolDependencyException(Xeption):
    pass


class FailedInternalToolServiceException(Xeption):
    pass


class InternalToolDependencyException(Xeption):
    pass


class InternalToolServiceException(Xeption):
    pass


class InternalToolValidationException(Xeption):
    pass


class InvalidInternalToolException(Xeption):
    pass
