# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import collections
import http.client
import json
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, AsyncIterator

from restfulsense.client import RESTFulApiFactoryClient
from restfulsense.exceptions import HttpRequestException
from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.models.brokers.generators.chat_completion_chunk import ChatCompletionChunk
from standard_agents.models.brokers.generators.chat_completion_response import (
    ChatCompletionResponse)
from standard_agents.models.brokers.generators.provider_options import ProviderOptions
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference

_CHAT_COMPLETIONS_RELATIVE_URL = "chat/completions"

# StringContent(json, Encoding.UTF8, "application/json") names its charset.
_JSON_CONTENT_TYPE = "application/json; charset=utf-8"
_DATA_FIELD_PREFIX = "data:"
_DONE_SENTINEL = "[DONE]"

# JsonDocumentOptions.MaxDepth's default, which System.Text.Json enforces on every read.
_MAX_DEPTH = 64

_UTF8_BYTE_ORDER_MARK = b"\xef\xbb\xbf"


# The request is built as a JSON tree rather than through typed records, converged onto the
# construction V1 already uses, for the reason V1 already documents: growing optional record
# fields answers one request and re-opens the same question at the next one
# (docs/per-request-inference.md 5.1).
class GeneratorBroker(IGeneratorBroker):
    # handler is the host's handler under this broker's traffic (F-23). The handler is the
    # host's: the opener around it holds nothing of its own.
    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: int,
        handler: urllib.request.BaseHandler | None = None) -> None:

        self._base_address = _to_base_address(api_url)
        self._timeout_seconds = _to_timeout(timeout_seconds)
        self._authorization = _to_bearer(api_key)
        self._opener = _build_opener(handler)

        self._api_client = RESTFulApiFactoryClient(
            base_url=self._base_address,
            headers={"Authorization": self._authorization},
            timeout_seconds=self._timeout_seconds)

        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    # This broker puts resolved inference options on the wire.
    @property
    def honors_request(self) -> bool:
        return True

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return await self._generate(system_prompt, user_prompt, inference=None)

    async def generate_with_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference) -> str:

        return await self._generate(system_prompt, user_prompt, inference)

    async def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference | None) -> str:

        request = self._build_request(system_prompt, user_prompt, stream=False, inference=inference)

        chat_completion_response = await self._post(_CHAT_COMPLETIONS_RELATIVE_URL, request)

        return chat_completion_response.choices[0].message.content

    def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        return self._generate_stream(system_prompt, user_prompt, inference=None)

    def generate_stream_with_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference) -> AsyncIterator[str]:

        return self._generate_stream(system_prompt, user_prompt, inference)

    async def _generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        inference: ResolvedInference | None) -> AsyncIterator[str]:

        request = self._build_request(system_prompt, user_prompt, stream=True, inference=inference)

        request_json = _to_json_string(request)

        http_request = urllib.request.Request(
            urllib.parse.urljoin(self._base_address, _CHAT_COMPLETIONS_RELATIVE_URL),
            data=request_json.encode("utf-8"),
            headers={
                "Authorization": self._authorization,
                "Content-Type": _JSON_CONTENT_TYPE
            },
            method="POST")

        # Sent once the headers are read (HttpCompletionOption.ResponseHeadersRead); a status
        # outside 2xx is refused as EnsureSuccessStatusCode refuses it.
        http_response = await asyncio.to_thread(
            _send,
            self._opener,
            http_request,
            self._timeout_seconds)

        try:
            reader = _StreamReader(http_response)

            while True:
                line = await reader.read_line()

                if line is None:
                    break

                if line.startswith(_DATA_FIELD_PREFIX) is False:
                    continue

                data = _trim(line[len(_DATA_FIELD_PREFIX):])

                if data == _DONE_SENTINEL:
                    break

                chunk = _deserialize_chunk(data)

                content = (
                    chunk.choices[0].delta.content
                    if chunk is not None and chunk.choices is not None and len(chunk.choices) > 0
                    else None)

                if _is_null_or_empty(content) is False:
                    yield content
        finally:
            http_response.close()

    def _build_request(
        self,
        system_prompt: str,
        user_prompt: str,
        stream: bool,
        inference: ResolvedInference | None) -> dict:

        request = {
            "model": self._model,

            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],

            "stream": stream,
            "temperature": self._temperature if inference is None else inference.temperature,
            "max_tokens": self._max_tokens if inference is None else inference.max_tokens
        }

        _write_inference(request, inference)

        return request

    async def _post(self, relative_url: str, content: dict) -> ChatCompletionResponse:
        return ChatCompletionResponse.from_json_dict(
            await self._api_client.post_content(relative_url, content))


# The resolved options, written as the wire knows them. The values arrive already
# precedence-resolved at the boundary; this broker writes what it is given and decides nothing
# (docs/per-request-inference.md 4.2).
def _write_inference(request: dict, inference: ResolvedInference | None) -> None:
    if inference is None:
        return

    if inference.seed is not None:
        request["seed"] = inference.seed

    if len(inference.stop) > 0:
        request["stop"] = [stop for stop in inference.stop]

    # The schema that survived precedence seeds the wire, and the guardian already holds the
    # same schema, so an engine that quietly ignores response_format degrades to a guarantee
    # rather than to nothing (4.1).
    if _is_null_or_white_space(inference.response_schema_json) is False:
        schema = _try_parse(inference.response_schema_json)

        if schema is not None:
            request["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": schema
                }
            }

    # Already sanitized at the boundary; merged under the same rule again here, because this
    # is the perimeter and one enforcement point is one forgotten call away from none.
    ProviderOptions.merge_into(request, inference.provider_options_json)


def _try_parse(text: str) -> Any:
    try:
        return _parse_json(text)
    except ValueError:
        return None


# JsonSerializer.Deserialize<ChatCompletionChunk>: the JSON literal null reads as no chunk.
def _deserialize_chunk(data: str) -> ChatCompletionChunk | None:
    node = _parse_json(data)

    return None if node is None else ChatCompletionChunk.from_json_dict(node)


# System.Text.Json's reader: strict JSON, no NaN or Infinity, nesting no deeper than 64.
def _parse_json(text: str) -> Any:
    try:
        node = json.loads(text, parse_constant=_reject_constant)
    except RecursionError:
        raise ValueError(f"The maximum configured depth of {_MAX_DEPTH} has been exceeded.")

    _ensure_depth(node, depth=0)

    return node


def _reject_constant(constant: str) -> Any:
    raise ValueError(f"'{constant}' is an invalid JSON literal.")


def _ensure_depth(node: Any, depth: int) -> None:
    if isinstance(node, (dict, list)):
        depth += 1

        if depth > _MAX_DEPTH:
            raise ValueError(f"The maximum configured depth of {_MAX_DEPTH} has been exceeded.")

        children = node.values() if isinstance(node, dict) else node

        for child in children:
            _ensure_depth(child, depth)


# JsonObject.ToJsonString: compact; a NaN or Infinity is refused rather than written.
def _to_json_string(node: Any) -> str:
    return json.dumps(node, separators=(",", ":"), allow_nan=False)


# A StreamReader over the response body: UTF-8 with its byte-order mark skipped, and a line
# ended by "\n", "\r" or "\r\n", the terminator not part of the line.
class _StreamReader:
    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self._lines: collections.deque[str] = collections.deque()
        self._at_start = True

    async def read_line(self) -> str | None:
        while len(self._lines) == 0:
            raw = await asyncio.to_thread(self._stream.readline)

            if len(raw) == 0:
                return None

            if self._at_start:
                self._at_start = False

                if raw.startswith(_UTF8_BYTE_ORDER_MARK):
                    raw = raw[len(_UTF8_BYTE_ORDER_MARK):]

            self._lines.extend(_split_lines(raw.decode("utf-8", errors="replace")))

        return self._lines.popleft()


def _split_lines(text: str) -> list[str]:
    if len(text) == 0:
        return []

    if text.endswith("\n"):
        text = text[:-1]

        if text.endswith("\r"):
            text = text[:-1]
    elif text.endswith("\r"):
        text = text[:-1]

    return text.split("\r")


# HttpClient.SendAsync then EnsureSuccessStatusCode. A request that never got an answer is an
# HttpRequestException, as is a status outside 2xx (carrying that status). A timeout is not:
# HttpClient cancels the request, so it stays a TimeoutError rather than claiming a refusal.
def _send(
    opener: urllib.request.OpenerDirector,
    http_request: urllib.request.Request,
    timeout_seconds: float) -> Any:

    try:
        return opener.open(http_request, timeout=timeout_seconds)
    except urllib.error.HTTPError as http_error:
        http_error.close()

        raise HttpRequestException(
            message=(
                "Response status code does not indicate success: "
                f"{http_error.code} ({http_error.reason})."),
            status_code=http_error.code) from http_error
    except urllib.error.URLError as url_error:
        if isinstance(url_error.reason, TimeoutError):
            raise TimeoutError(str(url_error.reason)) from url_error

        raise HttpRequestException(message=str(url_error.reason)) from url_error
    except TimeoutError:
        raise
    except (OSError, http.client.HTTPException) as error:
        raise HttpRequestException(message=str(error)) from error


# HttpClient sends no User-Agent of its own, so urllib's default one is dropped.
def _build_opener(handler: urllib.request.BaseHandler | None) -> urllib.request.OpenerDirector:
    opener = (
        urllib.request.build_opener() if handler is None
        else urllib.request.build_opener(handler))

    opener.addheaders = []

    return opener


# new Uri(apiUrl): an address that is not absolute is refused when the broker is built.
def _to_base_address(api_url: str) -> str:
    if not urllib.parse.urlsplit(api_url).scheme:
        raise ValueError("Invalid URI: The format of the URI could not be determined.")

    return api_url


# HttpClient.Timeout refuses a span that is not positive.
def _to_timeout(timeout_seconds: int) -> float:
    if timeout_seconds <= 0:
        raise ValueError(
            "Specified argument was out of the range of valid values. (Parameter 'value')")

    return float(timeout_seconds)


# AuthenticationHeaderValue("Bearer", apiKey) writes the scheme alone when there is no key.
def _to_bearer(api_key: str | None) -> str:
    return "Bearer" if not api_key else f"Bearer {api_key}"


def _is_null_or_empty(text: str | None) -> bool:
    return text is None or len(text) == 0


# char.IsWhiteSpace's own set, which string.Trim and string.IsNullOrWhiteSpace use.
def _is_white_space(character: str) -> bool:
    return (
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp"))


def _is_null_or_white_space(text: str | None) -> bool:
    return text is None or all(_is_white_space(character) for character in text)


def _trim(text: str) -> str:
    start = 0
    end = len(text)

    while start < end and _is_white_space(text[start]):
        start += 1

    while end > start and _is_white_space(text[end - 1]):
        end -= 1

    return text[start:end]
