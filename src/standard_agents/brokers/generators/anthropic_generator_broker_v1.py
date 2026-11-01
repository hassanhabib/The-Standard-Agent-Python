# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import codecs
import http.client
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Sequence

from restfulsense.exceptions import HttpRequestException
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    MessageRole,
    ModelToolCall,
    ToolDefinition)

_MESSAGES_RELATIVE_URL = "v1/messages"

# StringContent(json, Encoding.UTF8, "application/json") names its charset.
_JSON_CONTENT_TYPE = "application/json; charset=utf-8"

# The Messages API refuses a request without a version pin, which is the right default for a
# wire format that evolves: the shape this broker speaks is the shape it names.
_ANTHROPIC_VERSION = "2023-06-01"

# JsonDocumentOptions.MaxDepth's default, which JsonNode.Parse enforces.
_MAX_DEPTH = 64

# A JSON number token that Int32 can read: no fraction, no exponent.
_INTEGER_TOKEN = re.compile(r"-?(0|[1-9][0-9]*)")

# The characters JavaScriptEncoder.Default escapes even inside Basic Latin.
_HTML_SENSITIVE = frozenset('"&\'+<>`')

_SHORT_ESCAPES = {
    "\\": "\\\\",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
}


# Native tool calling against the Anthropic Messages API: the same GeneratorBrokerV1 seam as
# the OpenAI-compatible broker, under a different wire shape: system prompts travel as a
# top-level `system` field, tools carry `input_schema`, the model's choice comes back as
# `tool_use` content blocks, and a tool's result returns as a `tool_result` block inside a user
# message. Usage comes back reported (`input_tokens`/`output_tokens`), never guessed.
#
# Like its sibling, the request is built as a JSON tree: the tool schemas are already JSON the
# host wrote, and re-modelling them would only give us a second place for them to be wrong.
class AnthropicGeneratorBrokerV1(GeneratorBrokerV1):
    # handler is the host's handler under this broker's traffic (F-23). The handler is the
    # host's: the opener around it holds nothing of its own.
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout_seconds: int = 120,
        api_url: str = "https://api.anthropic.com/",
        handler: urllib.request.BaseHandler | None = None) -> None:

        self._base_address = _to_base_address(api_url)
        self._timeout_seconds = _to_timeout(timeout_seconds)
        self._api_key = "" if api_key is None else api_key
        self._opener = _build_opener(handler)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def generate(
            self,
            messages: Sequence[ConversationMessage],
            tools: Sequence[ToolDefinition],
            *,
            inference: ResolvedInference | None = None) -> GenerationResult:
        """Generate over the Messages API; inference options are not put on the wire."""

        request = self._build_request(messages, tools)

        http_request = urllib.request.Request(
            urllib.parse.urljoin(self._base_address, _MESSAGES_RELATIVE_URL),
            data=_to_json_string(request).encode("utf-8"),
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "Content-Type": _JSON_CONTENT_TYPE
            },
            method="POST")

        response_text = await asyncio.to_thread(
            _post,
            self._opener,
            http_request,
            self._timeout_seconds)

        body = _parse_json(response_text)

        return _read_result(body)

    def _build_request(
        self,
        messages: Sequence[ConversationMessage],
        tools: Sequence[ToolDefinition]) -> dict:

        request = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "messages": _render_messages(messages)
        }

        # System prompts are a top-level field here, not a message role; several collapse into
        # one the way the model will read them anyway, in order.
        system = "\n\n".join(
            text
            for text in (
                message.content for message in messages
                if message.role is MessageRole.SYSTEM)
            if _is_null_or_white_space(text) is False)

        if _is_null_or_empty(system) is False:
            request["system"] = system

        if len(tools) > 0:
            request["tools"] = [_tool_to_json(tool) for tool in tools]

        return request


# The API alternates user and assistant turns, and a tool's result is a `tool_result` block
# inside a USER message that must directly follow the assistant `tool_use` it answers, so
# consecutive tool results merge into one user message rather than each claiming a turn of its
# own.
def _render_messages(messages: Sequence[ConversationMessage]) -> list:
    rendered: list = []
    pending_tool_results: list = []

    for message in messages:
        if message.role is MessageRole.TOOL:
            pending_tool_results.append({
                "type": "tool_result",
                "tool_use_id": message.tool_call_id,
                "content": message.content
            })

            continue

        pending_tool_results = _flush_tool_results(rendered, pending_tool_results)

        if message.role is MessageRole.SYSTEM:
            continue

        rendered.append({
            "role": message.role.name.lower(),
            "content": _render_content(message)
        })

    _flush_tool_results(rendered, pending_tool_results)

    return rendered


# The pending results land as one user message, and a fresh list replaces them (the C# ref).
def _flush_tool_results(rendered: list, pending_tool_results: list) -> list:
    if len(pending_tool_results) == 0:
        return pending_tool_results

    rendered.append({
        "role": "user",
        "content": pending_tool_results
    })

    return []


def _render_content(message: ConversationMessage) -> Any:
    if len(message.tool_calls) == 0:
        return message.content

    blocks: list = []

    if _is_null_or_white_space(message.content) is False:
        blocks.append({
            "type": "text",
            "text": message.content
        })

    for call in message.tool_calls:
        blocks.append({
            "type": "tool_use",
            "id": call.id,
            "name": call.name,
            "input": _parse_json_or_empty(call.arguments_json)
        })

    return blocks


def _tool_to_json(tool: ToolDefinition) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": _parse_schema(tool.parameters_json)
    }


# Same posture as the sibling broker: a schema that does not parse degrades to an argument-less
# tool rather than failing the whole turn on one bad schema.
def _parse_schema(parameters_json: str) -> Any:
    parsed = _parse_json_or_empty(parameters_json)

    if isinstance(parsed, dict) and ("type" in parsed) is False:
        parsed["type"] = "object"

    return parsed


def _parse_json_or_empty(text: str) -> Any:
    if _is_null_or_white_space(text):
        return {}

    try:
        node = _parse_json(text)

        return {} if node is None else node
    except ValueError:
        return {}


def _read_result(body: Any) -> GenerationResult:
    usage = _member(body, "usage")

    text: list[str] = []
    tool_calls: list[ModelToolCall] = []

    blocks = _member(body, "content")

    if isinstance(blocks, list):
        for block in blocks:
            block_type = _get_string(_member(block, "type"))

            if block_type == "text":
                text.append(_or_default(_get_string(_member(block, "text")), ""))

            elif block_type == "tool_use":
                id = _or_default(_get_string(_member(block, "id")), "")
                name = _or_default(_get_string(_member(block, "name")), "")

                input = _member(block, "input")
                arguments = "{}" if input is None else _to_json_string(input)

                if _is_null_or_white_space(name) is False:
                    tool_calls.append(ModelToolCall(id=id, name=name, arguments_json=arguments))

    return GenerationResult(
        content="".join(text),
        tool_calls=tuple(tool_calls),
        prompt_tokens=_or_default(_get_int(_member(usage, "input_tokens")), 0),
        completion_tokens=_or_default(_get_int(_member(usage, "output_tokens")), 0))


# JsonNode's indexers. A missing member and the JSON literal null both read as None; indexing a
# node of the wrong kind is refused (InvalidOperationException, here RuntimeError).
def _member(node: Any, name: str) -> Any:
    if node is None:
        return None

    if not isinstance(node, dict):
        raise RuntimeError("The node must be of type 'JsonObject'.")

    return node.get(name)


# JsonNode.GetValue<string>(): only a JSON string reads as one.
def _get_string(node: Any) -> str | None:
    if node is None:
        return None

    if not isinstance(node, str) or isinstance(node, _RawNumber):
        raise RuntimeError("The node cannot be converted to 'System.String'.")

    return node


# JsonNode.GetValue<int>(): only a JSON integer token within Int32 reads as one.
def _get_int(node: Any) -> int | None:
    if node is None:
        return None

    if not isinstance(node, _RawNumber) or _INTEGER_TOKEN.fullmatch(node) is None:
        raise RuntimeError("The node cannot be converted to 'System.Int32'.")

    value = int(node)

    if not -2**31 <= value < 2**31:
        raise RuntimeError("The node cannot be converted to 'System.Int32'.")

    return value


def _or_default(value: Any, default: Any) -> Any:
    return default if value is None else value


# A number as it was written, the way a parsed JsonNode keeps the raw token and writes it back:
# a tool's arguments reach the caller exactly as the model wrote their numbers.
class _RawNumber(str):
    pass


# JsonNode.Parse: strict JSON, no NaN or Infinity, nesting no deeper than 64.
def _parse_json(text: str) -> Any:
    try:
        node = json.loads(
            text,
            parse_int=_RawNumber,
            parse_float=_RawNumber,
            parse_constant=_reject_constant)
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


# JsonNode.ToJsonString with default options: compact, written with JavaScriptEncoder.Default.
def _to_json_string(node: Any) -> str:
    if node is None:
        return "null"

    if node is True:
        return "true"

    if node is False:
        return "false"

    if isinstance(node, _RawNumber):
        return str(node)

    if isinstance(node, int):
        return str(node)

    if isinstance(node, float):
        return _format_double(node)

    if isinstance(node, str):
        return _escape(node)

    if isinstance(node, (list, tuple)):
        return "[" + ",".join(_to_json_string(item) for item in node) + "]"

    if isinstance(node, dict):
        return "{" + ",".join(
            _escape(key) + ":" + _to_json_string(value)
            for key, value in node.items()) + "}"

    raise TypeError(f"Cannot write {type(node).__name__} as JSON.")


# A double as System.Text.Json writes it: the shortest round-trip form, no ".0" on a whole
# number, an upper-case exponent, and NaN or Infinity refused.
def _format_double(value: float) -> str:
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(".NET number values such as positive and negative infinity cannot be "
            "written as valid JSON.")

    text = repr(value)

    if text.endswith(".0"):
        text = text[:-2]

    return text.replace("e", "E")


# JavaScriptEncoder.Default: printable Basic Latin passes except the HTML-sensitive characters;
# everything else is escaped, as \uXXXX in upper-case hex, surrogate pairs as two escapes.
def _escape(text: str) -> str:
    parts = ['"']

    for character in text:
        code = ord(character)

        if character in _SHORT_ESCAPES:
            parts.append(_SHORT_ESCAPES[character])
        elif 0x20 <= code <= 0x7E and character not in _HTML_SENSITIVE:
            parts.append(character)
        elif code > 0xFFFF:
            code -= 0x10000
            parts.append(f"\\u{0xD800 + (code >> 10):04X}")
            parts.append(f"\\u{0xDC00 + (code & 0x3FF):04X}")
        else:
            parts.append(f"\\u{code:04X}")

    parts.append('"')

    return "".join(parts)


# HttpClient.PostAsync (the body buffered inside the call), EnsureSuccessStatusCode, then
# ReadAsStringAsync. A request that never got an answer is an HttpRequestException, as is a
# status outside 2xx (carrying that status). A timeout is not: HttpClient cancels the request,
# so it stays a TimeoutError rather than claiming a refusal.
def _post(
    opener: urllib.request.OpenerDirector,
    http_request: urllib.request.Request,
    timeout_seconds: float) -> str:

    try:
        with opener.open(http_request, timeout=timeout_seconds) as http_response:
            body = http_response.read()
            charset = http_response.headers.get_content_charset()
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

    return _decode(body, charset)


# HttpContent.ReadAsStringAsync: the charset the response names, UTF-8 when it names none, a
# UTF-8 byte-order mark skipped, and an undecodable byte replaced rather than refused.
def _decode(body: bytes, charset: str | None) -> str:
    encoding = codecs.lookup(charset or "utf-8").name

    if encoding == "utf-8":
        encoding = "utf-8-sig"

    return body.decode(encoding, errors="replace")


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


def _is_null_or_empty(text: str | None) -> bool:
    return text is None or len(text) == 0


# string.IsNullOrWhiteSpace, with char.IsWhiteSpace's own set.
def _is_null_or_white_space(text: str | None) -> bool:
    if text is None:
        return True

    return all(
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp")
        for character in text)
