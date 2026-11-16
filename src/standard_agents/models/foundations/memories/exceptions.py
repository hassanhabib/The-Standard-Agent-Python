# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeption import Xeption


class FailedMemoryDependencyException(Xeption):
    pass


class FailedMemoryServiceException(Xeption):
    pass


class InvalidMemoryException(Xeption):
    pass


class MemoryDependencyException(Xeption):
    pass


class MemoryServiceException(Xeption):
    pass


class MemoryValidationException(Xeption):
    pass
