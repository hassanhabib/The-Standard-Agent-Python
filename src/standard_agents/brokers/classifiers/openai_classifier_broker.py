# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import urllib.parse

from restfulsense.client import RESTFulApiFactoryClient
from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.models.brokers.classifiers.chat_completion_request import (
    ChatCompletionRequest)
from standard_agents.models.brokers.classifiers.chat_completion_response import (
    ChatCompletionResponse)
from standard_agents.models.brokers.classifiers.chat_message import ChatMessage

_CHAT_COMPLETIONS_RELATIVE_URL = "chat/completions"


class OpenAiClassifierBroker(ClassifierBroker):
    def __init__(
            self,
            api_url: str,
            api_key: str,
            model: str,
            temperature: float,
            max_tokens: int,
            timeout_seconds: int,
            system_prompt: str) -> None:

        self._api_client = RESTFulApiFactoryClient(
            base_url=_to_base_address(api_url),
            headers={"Authorization": _to_bearer(api_key)},
            timeout_seconds=_to_timeout(timeout_seconds))

        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._system_prompt = system_prompt

    async def classify(self, input: str) -> str:
        return await self.assess(self._system_prompt, input)

    async def assess(self, system_prompt: str, input: str) -> str:
        chat_completion_request = ChatCompletionRequest(
            model=self._model,
            messages=(
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=input)),
            stream=False,
            temperature=self._temperature,
            max_tokens=self._max_tokens)

        chat_completion_response = await self._post(
            _CHAT_COMPLETIONS_RELATIVE_URL,
            chat_completion_request)

        return chat_completion_response.choices[0].message.content

    async def _post(
            self,
            relative_url: str,
            content: ChatCompletionRequest) -> ChatCompletionResponse:

        return ChatCompletionResponse.from_json_dict(
            await self._api_client.post_content(relative_url, content.to_json_dict()))


def _to_base_address(api_url: str) -> str:
    """The API address, refused when it is not absolute, as new Uri(apiUrl) refuses it."""
    if not urllib.parse.urlsplit(api_url).scheme:
        raise ValueError("Invalid URI: The format of the URI could not be determined.")

    return api_url


def _to_timeout(timeout_seconds: int) -> float:
    """The timeout in seconds, refused when not positive, as HttpClient.Timeout refuses it."""
    if timeout_seconds <= 0:
        raise ValueError(
            "Specified argument was out of the range of valid values. (Parameter 'value')")

    return float(timeout_seconds)


def _to_bearer(api_key: str | None) -> str:
    """The Authorization header: the scheme alone when there is no key.

    AuthenticationHeaderValue("Bearer", apiKey) writes it that way.
    """
    return f"Bearer {api_key}" if api_key else "Bearer"
