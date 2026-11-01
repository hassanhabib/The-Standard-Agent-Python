# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class ContractDependencyException(Xeption):
    pass


class ContractServiceException(Xeption):
    pass


class ContractValidationException(Xeption):
    pass


class FailedContractDependencyException(Xeption):
    pass


class FailedContractServiceException(Xeption):
    pass


class InvalidContractException(Xeption):
    pass
