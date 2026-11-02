# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class ExternalToolDependencyException(Xeption):
    pass


class ExternalToolDependencyValidationException(Xeption):
    pass


class ExternalToolServiceException(Xeption):
    pass


class ExternalToolValidationException(Xeption):
    pass


class FailedExternalToolDependencyException(Xeption):
    pass


class FailedExternalToolServiceException(Xeption):
    pass


class InvalidExternalToolException(Xeption):
    pass
