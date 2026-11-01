# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class FailedKnowledgeDependencyException(Xeption):
    pass


class FailedKnowledgeServiceException(Xeption):
    pass


class InvalidKnowledgeException(Xeption):
    pass


class KnowledgeDependencyException(Xeption):
    pass


class KnowledgeServiceException(Xeption):
    pass


class KnowledgeValidationException(Xeption):
    pass
