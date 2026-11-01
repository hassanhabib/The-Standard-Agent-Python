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
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
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


class OpenAiGeneratorBroker(GeneratorBroker):
    """The brain over an OpenAI-compatible chat completions endpoint.

    The request is built as a JSON tree rather than through typed records, converged onto the
    construction V1 already uses, for the reason V1 already documents: growing optional record
    fields answers one request and re-opens the same question at the next one
    (docs/per-request-inference.md 5.1).

    ``handler`` is the host's handler under this broker's traffic (F-23): the opener around it
    holds nothing of its own.
    """

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

    @property
    def honors_request(self) -> bool:
        """This broker puts resolved inference options on the wire."""
        return True

    async def generate(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:

        request = self._build_request(system_prompt, user_prompt, stream=False, inference=inference)

        chat_completion_response = await self._post(_CHAT_COMPLETIONS_RELATIVE_URL, request)

        return chat_completion_response.choices[0].message.content

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:

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

                if not line.startswith(_DATA_FIELD_PREFIX):
                    continue

                data = _trim(line[len(_DATA_FIELD_PREFIX):])

                if data == _DONE_SENTINEL:
                    break

                chunk = _deserialize_chunk(data)

                content = (
                    chunk.choices[0].delta.content
                    if chunk is not None and chunk.choices
                    else None)

                if content:
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


def _write_inference(request: dict, inference: ResolvedInference | None) -> None:
    """Write the resolved options as the wire knows them.

    The values arrive already precedence-resolved at the boundary; this broker writes what it is
    given and decides nothing (docs/per-request-inference.md 4.2).
    """
    if inference is None:
        return

    if inference.seed is not None:
        request["seed"] = inference.seed

    if inference.stop:
        request["stop"] = list(inference.stop)

    # The schema that survived precedence seeds the wire, and the guardian already holds the
    # same schema, so an engine that quietly ignores response_format degrades to a guarantee
    # rather than to nothing (4.1).
    if not _is_blank(inference.response_schema_json):
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


def _deserialize_chunk(data: str) -> ChatCompletionChunk | None:
    """JsonSerializer.Deserialize<ChatCompletionChunk>: the JSON literal null reads as no chunk."""
    node = _parse_json(data)

    return None if node is None else ChatCompletionChunk.from_json_dict(node)


def _parse_json(text: str) -> Any:
    """System.Text.Json's reader: strict JSON, no NaN or Infinity, nesting no deeper than 64."""
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


def _to_json_string(node: Any) -> str:
    """JsonObject.ToJsonString: compact; a NaN or Infinity is refused rather than written."""
    return json.dumps(node, separators=(",", ":"), allow_nan=False)


class _StreamReader:
    """A StreamReader over the response body.

    UTF-8 with its byte-order mark skipped, and a line ended by "\\n", "\\r" or "\\r\\n", the
    terminator not part of the line.
    """

    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self._lines: collections.deque[str] = collections.deque()
        self._at_start = True

    async def read_line(self) -> str | None:
        while not self._lines:
            raw = await asyncio.to_thread(self._stream.readline)

            if not raw:
                return None

            if self._at_start:
                self._at_start = False

                if raw.startswith(_UTF8_BYTE_ORDER_MARK):
                    raw = raw[len(_UTF8_BYTE_ORDER_MARK):]

            self._lines.extend(_split_lines(raw.decode("utf-8", errors="replace")))

        return self._lines.popleft()


def _split_lines(text: str) -> list[str]:
    """The lines in one urllib readline, split at "\\r" as StreamReader.ReadLine also splits."""
    if not text:
        return []

    if text.endswith("\n"):
        text = text[:-1]

        if text.endswith("\r"):
            text = text[:-1]
    elif text.endswith("\r"):
        text = text[:-1]

    return text.split("\r")


def _send(
        opener: urllib.request.OpenerDirector,
        http_request: urllib.request.Request,
        timeout_seconds: float) -> Any:
    """HttpClient.SendAsync then EnsureSuccessStatusCode.

    A request that never got an answer is an HttpRequestException, as is a status outside 2xx
    (carrying that status). A timeout is not: HttpClient cancels the request, so it stays a
    TimeoutError rather than claiming a refusal.
    """
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


def _build_opener(handler: urllib.request.BaseHandler | None) -> urllib.request.OpenerDirector:
    """An opener over the host's handler, if any.

    HttpClient sends no User-Agent of its own, so urllib's default one is dropped.
    """
    opener = (
        urllib.request.build_opener() if handler is None
        else urllib.request.build_opener(handler))

    opener.addheaders = []

    return opener


def _to_base_address(api_url: str) -> str:
    """new Uri(apiUrl): an address that is not absolute is refused when the broker is built."""
    if not urllib.parse.urlsplit(api_url).scheme:
        raise ValueError("Invalid URI: The format of the URI could not be determined.")

    return api_url


def _to_timeout(timeout_seconds: int) -> float:
    """HttpClient.Timeout refuses a span that is not positive."""
    if timeout_seconds <= 0:
        raise ValueError(
            "Specified argument was out of the range of valid values. (Parameter 'value')")

    return float(timeout_seconds)


def _to_bearer(api_key: str | None) -> str:
    """AuthenticationHeaderValue("Bearer", apiKey) writes the scheme alone when there is no key."""
    return "Bearer" if not api_key else f"Bearer {api_key}"


def _is_whitespace(character: str) -> bool:
    """char.IsWhiteSpace, which string.Trim and string.IsNullOrWhiteSpace use.

    Not str.isspace: .NET does not count U+001C..U+001F as white space.
    """
    return (
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp"))


def _is_blank(text: str | None) -> bool:
    """string.IsNullOrWhiteSpace, over the .NET white-space set."""
    return text is None or all(_is_whitespace(character) for character in text)


def _trim(text: str) -> str:
    """string.Trim, over the .NET white-space set."""
    start = 0
    end = len(text)

    while start < end and _is_whitespace(text[start]):
        start += 1

    while end > start and _is_whitespace(text[end - 1]):
        end -= 1

    return text[start:end]
