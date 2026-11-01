# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from decimal import Decimal

import pytest

from standard_agents.models.clients.agents.exceptions import (
    InvalidAgentApiUrlException,
    InvalidAgentBudgetException)
from standard_agents.standard_agent import StandardAgent

# Found in the 2026-09-04 principal review (F-12): hosting.md taught an endpoint that already
# named chat/completions, and the broker appends that route to whatever base it is given, so the
# copied example reached v1/chat/chat/completions. The neighbouring mistake is as silent: a base
# without its trailing slash resolves the route against the parent, so 'https://host/v1' reaches
# 'https://host/chat/completions'. Both fail at the first prompt with a 404 that blames the
# provider. The shape is refused at composition instead.
INVALID_API_URLS = [
    "invalid-url",
    "https://api.peerllm.com/v1",
    "http://localhost:11434/v1/chat/completions",
    "https://api.peerllm.com/v1/chat/completions/",
]

INVALID_API_URL_MESSAGE = (
    "Invalid agent API URL. An endpoint is the base the route is appended to: an absolute "
    + "http(s) URL ending with '/', such as https://api.peerllm.com/v1/, that does not "
    + "name chat/completions itself.")


@pytest.mark.parametrize("invalid_api_url", INVALID_API_URLS)
def test_should_throw_invalid_agent_api_url_exception_on_brain_if_api_url_is_invalid(
        invalid_api_url):

    # given
    expected_invalid_agent_api_url_exception = InvalidAgentApiUrlException(
        message=INVALID_API_URL_MESSAGE)

    # when
    with pytest.raises(InvalidAgentApiUrlException) as raised:
        StandardAgent().brain(api_url=invalid_api_url, api_key="key", model="model")

    # then
    assert raised.value.same_exception_as(expected_invalid_agent_api_url_exception)


@pytest.mark.parametrize("invalid_api_url", INVALID_API_URLS)
def test_should_throw_invalid_agent_api_url_exception_on_native_brain_if_api_url_is_invalid(
        invalid_api_url):

    # given
    expected_invalid_agent_api_url_exception = InvalidAgentApiUrlException(
        message=INVALID_API_URL_MESSAGE)

    # when
    with pytest.raises(InvalidAgentApiUrlException) as raised:
        StandardAgent().native_brain(api_url=invalid_api_url, api_key="key", model="model")

    # then
    assert raised.value.same_exception_as(expected_invalid_agent_api_url_exception)


@pytest.mark.parametrize("invalid_api_url", INVALID_API_URLS)
def test_should_throw_invalid_agent_api_url_exception_on_gate_if_api_url_is_invalid(
        invalid_api_url):

    # given
    expected_invalid_agent_api_url_exception = InvalidAgentApiUrlException(
        message=INVALID_API_URL_MESSAGE)

    # when
    with pytest.raises(InvalidAgentApiUrlException) as raised:
        StandardAgent().gate(api_url=invalid_api_url, api_key="key", model="model")

    # then
    assert raised.value.same_exception_as(expected_invalid_agent_api_url_exception)



@pytest.mark.parametrize("invalid_api_url", INVALID_API_URLS)
def test_should_throw_invalid_agent_api_url_exception_on_judge_if_api_url_is_invalid(
        invalid_api_url):

    # given
    expected_invalid_agent_api_url_exception = InvalidAgentApiUrlException(
        message=INVALID_API_URL_MESSAGE)

    # when
    with pytest.raises(InvalidAgentApiUrlException) as raised:
        StandardAgent().judge(api_url=invalid_api_url, api_key="key", model="model")

    # then
    assert raised.value.same_exception_as(expected_invalid_agent_api_url_exception)


# Found in the 2026-09-04 principal review (F-01): cost is priced off the token count times the
# rate, and the rate defaulted to zero. A cost bound with no rate computed zero dollars forever and
# never tripped: a guardrail the host believed was armed and was not. The framework cannot know a
# model's price, so it cannot fill the rate in; what it can do is refuse the contradiction of a
# dollar bound on a model declared free.
@pytest.mark.parametrize("invalid_cost_per_thousand_tokens", [Decimal("0"), Decimal("-0.002")])
def test_should_throw_invalid_agent_budget_exception_on_budget_if_cost_bound_has_no_rate(
        invalid_cost_per_thousand_tokens):

    # given
    expected_invalid_agent_budget_exception = InvalidAgentBudgetException(
        message=(
            "Invalid agent budget: a cost bound (maxCostUsd) needs a positive "
            + "costPerThousandTokens. Cost is the token count times that rate, so at "
            + "zero the bound can never trip. Pass your model's rate, or bound by "
            + "maxTokens instead."))

    # when
    with pytest.raises(InvalidAgentBudgetException) as raised:
        StandardAgent().budget(
            max_cost_usd=Decimal("0.25"),
            cost_per_thousand_tokens=invalid_cost_per_thousand_tokens)

    # then
    assert raised.value.same_exception_as(expected_invalid_agent_budget_exception)
