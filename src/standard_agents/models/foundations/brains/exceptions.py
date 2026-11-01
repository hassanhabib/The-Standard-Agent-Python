# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class BrainDependencyException(Xeption):
    pass


class BrainDependencyValidationException(Xeption):
    pass


class BrainServiceException(Xeption):
    pass


class BrainValidationException(Xeption):
    pass


class FailedBrainDependencyException(Xeption):
    pass


class FailedBrainServiceException(Xeption):
    pass


class InvalidBrainException(Xeption):
    pass


class UnreachableBrainException(Xeption):
    """Nothing answered at all (SPEC.md §4.10, v1.14).

    A refused connection, a name that resolves to nothing, a request that never left the
    machine. The person's next step is the address and whatever should be listening at it, not
    support, so this is the sentence they are shown. The native fault is kept as the inner
    exception for whoever investigates.
    """
