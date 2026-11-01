# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedJudgeDependencyException(Xeption):
    pass


class FailedJudgeServiceException(Xeption):
    pass


class InvalidJudgeException(Xeption):
    pass


class InvalidJudgeScoreException(Xeption):
    pass


class JudgeDependencyException(Xeption):
    pass


class JudgeDependencyValidationException(Xeption):
    pass


class JudgeServiceException(Xeption):
    pass


class JudgeValidationException(Xeption):
    pass
