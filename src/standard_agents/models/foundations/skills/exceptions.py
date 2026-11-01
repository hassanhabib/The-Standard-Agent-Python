# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedSkillDependencyException(Xeption):
    pass


class FailedSkillServiceException(Xeption):
    pass


class SkillDependencyException(Xeption):
    pass


class SkillServiceException(Xeption):
    pass
