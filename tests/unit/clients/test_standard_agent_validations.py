# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import pytest

from standard_agents.models.clients.agents.exceptions import InvalidAgentApiUrlException
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
