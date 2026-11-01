# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class InvalidReturnException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ReturnValidationException(Xeption):
    def __init__(self, message: str, inner_exception: Xeption | None) -> None:
        super().__init__(message, inner_exception)
