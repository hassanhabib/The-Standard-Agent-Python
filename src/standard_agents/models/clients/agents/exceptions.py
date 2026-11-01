# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from xeptions import Xeption


class InvalidAgentApiUrlException(Xeption):
    """An endpoint the agent cannot honestly call.

    The API URL is the base a route is appended to, so its shape is load-bearing: without a
    trailing slash the route resolves against the parent, and a base that already names the
    route reaches it twice. Either fails at the first prompt with a 404 that blames the provider,
    so the contradiction is refused at composition instead.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidAgentBudgetException(Xeption):
    """A budget the agent cannot honestly enforce: a cost bound with no rate to price it.

    Spend is the token count times the rate, so a dollar bound priced at zero is zero dollars
    forever, a guardrail that looks armed and never trips. The framework cannot know what a
    model costs, so it refuses the contradiction rather than composing it silently.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidAgentCompositionException(Xeption):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidAgentConfigurationException(Xeption):
    """A configuration document the agent cannot honestly compose from.

    Malformed JSON, a key it does not know, or a value of the wrong shape. Always loud and
    always named: a typo'd key silently ignored is a control the caller believes is on and is
    not.
    """

    def __init__(self, message: str, inner_exception: BaseException | None = None) -> None:
        super().__init__(message, inner_exception)
