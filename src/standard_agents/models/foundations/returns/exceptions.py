# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedReturnServiceException(Xeption):
    pass


class InvalidReturnException(Xeption):
    pass


class ReturnServiceException(Xeption):
    pass


class ReturnValidationException(Xeption):
    pass
