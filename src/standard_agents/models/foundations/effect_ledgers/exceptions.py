# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class EffectLedgerDependencyException(Xeption):
    pass


class EffectLedgerServiceException(Xeption):
    pass


class EffectLedgerValidationException(Xeption):
    pass


class FailedEffectLedgerDependencyException(Xeption):
    pass


class FailedEffectLedgerServiceException(Xeption):
    pass


class InvalidEffectLedgerException(Xeption):
    pass
