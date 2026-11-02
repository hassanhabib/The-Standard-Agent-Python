# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import urllib.parse

from restfulsense.client import RESTFulApiFactoryClient
from standard_agents.brokers.verifiers.function_verifier_broker import FunctionVerifierBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.brokers.verifiers.chat_completion_request import (
    ChatCompletionRequest)
from standard_agents.models.brokers.verifiers.chat_completion_response import (
    ChatCompletionResponse)
from standard_agents.models.brokers.verifiers.chat_message import ChatMessage

_CHAT_COMPLETIONS_RELATIVE_URL = "chat/completions"


class OpenAiVerifierBroker(VerifierBroker):
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

    async def verify(self, task: str, candidate: str) -> str:
        chat_completion_request = ChatCompletionRequest(
            model=self._model,
            messages=(
                ChatMessage(role="system", content=self._system_prompt),
                ChatMessage(
                    role="user",
                    content=FunctionVerifierBroker.format_verdict_request(task, candidate))),
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
    """Refuse an address that is not absolute when the broker is built, as .NET's new Uri does."""
    if not urllib.parse.urlsplit(api_url).scheme:
        raise ValueError("Invalid URI: The format of the URI could not be determined.")

    return api_url


def _to_timeout(timeout_seconds: int) -> float:
    """Refuse a timeout that is not positive, as .NET's HttpClient.Timeout does."""
    if timeout_seconds <= 0:
        raise ValueError(
            "Specified argument was out of the range of valid values. (Parameter 'value')")

    return float(timeout_seconds)


def _to_bearer(api_key: str | None) -> str:
    """The Authorization header value; the scheme alone when there is no key.

    As .NET's AuthenticationHeaderValue("Bearer", apiKey) writes it.
    """
    return "Bearer" if not api_key else f"Bearer {api_key}"
