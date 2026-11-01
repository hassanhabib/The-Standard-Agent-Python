# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import codecs
import http.client
import json
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from typing import Any

from restfulsense.exceptions import HttpRequestException
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.models.brokers.generators.provider_options import ProviderOptions
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    MessageRole,
    ModelToolCall,
    ToolDefinition)

_CHAT_COMPLETIONS_RELATIVE_URL = "chat/completions"

# StringContent(json, Encoding.UTF8, "application/json") names its charset.
_JSON_CONTENT_TYPE = "application/json; charset=utf-8"

# JsonDocumentOptions.MaxDepth's default, which JsonNode.Parse enforces.
_MAX_DEPTH = 64


class OpenAiGeneratorBrokerV1(GeneratorBrokerV1):
    """Native tool calling against an OpenAI-compatible endpoint.

    Tools go out as ``tools[]``, the model's choice comes back as ``tool_calls``, and usage comes
    back reported rather than guessed.

    The request is built as a JSON tree rather than through typed records, because the tool
    schemas are already JSON the host wrote and re-modelling them would only give us a second
    place for them to be wrong.

    ``handler`` is the host's handler under this broker's traffic (F-23): the opener around it
    holds nothing of its own.
    """

    def __init__(
            self,
            api_url: str,
            api_key: str,
            model: str,
            temperature: float = 0.7,
            max_tokens: int = 1024,
            timeout_seconds: int = 120,
            handler: urllib.request.BaseHandler | None = None) -> None:

        self._base_address = _to_base_address(api_url)
        self._timeout_seconds = _to_timeout(timeout_seconds)
        self._authorization = _to_bearer(api_key)
        self._opener = _build_opener(handler)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def honors_request(self) -> bool:
        """This broker puts resolved inference options on the wire."""
        return True

    async def generate(
            self,
            messages: Sequence[ConversationMessage],
            tools: Sequence[ToolDefinition],
            *,
            inference: ResolvedInference | None = None) -> GenerationResult:

        request = self._build_request(messages, tools, inference)

        http_request = urllib.request.Request(
            urllib.parse.urljoin(self._base_address, _CHAT_COMPLETIONS_RELATIVE_URL),
            data=_to_json_string(request).encode("utf-8"),
            headers={
                "Authorization": self._authorization,
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
            tools: Sequence[ToolDefinition],
            inference: ResolvedInference | None) -> dict:

        request = {
            "model": self._model,
            "temperature": self._temperature if inference is None else inference.temperature,
            "max_tokens": self._max_tokens if inference is None else inference.max_tokens,
            "messages": [_message_to_json(message) for message in messages]
        }

        # Only advertise when there is something to advertise: an empty tools array is a
        # different request than no tools at all on some providers.
        if tools:
            request["tools"] = [_tool_to_json(tool) for tool in tools]

        _write_inference(request, inference)

        return request


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


def _message_to_json(message: ConversationMessage) -> dict:
    json_message = {
        "role": message.role.name.lower(),
        "content": message.content
    }

    if message.role is MessageRole.TOOL:
        json_message["tool_call_id"] = message.tool_call_id

    if message.tool_calls:
        json_message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": call.arguments_json
                }
            }
            for call in message.tool_calls]

    return json_message


def _tool_to_json(tool: ToolDefinition) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": _parse_parameters(tool.parameters_json)
        }
    }


def _parse_parameters(parameters_json: str) -> dict:
    """A tool's parameters as an object schema the wire accepts.

    A tool's parameters are the host's JSON schema, and the wire validates that strictly: a
    hosted provider rejects the WHOLE request when any tool's parameters is not a schema of type
    object. One bad tool must never take down the turn, so anything that is not an object schema
    degrades: a schema that forgot its type but has properties is salvaged, everything else
    becomes the empty object schema (callable with no arguments).
    """
    if _is_blank(parameters_json):
        return {"type": "object"}

    try:
        schema = _parse_json(parameters_json)

        if isinstance(schema, dict):
            type_value = schema.get("type")

            # schema["type"] is JsonValue: a string, number or boolean, never null, an object
            # or an array.
            schema_type = (
                _get_string(type_value)
                if type_value is not None and not isinstance(type_value, (dict, list))
                else None)

            if schema_type == "object":
                return schema

            if schema_type is None and "properties" in schema:
                schema["type"] = "object"

                return schema
    except (ValueError, RuntimeError):
        pass

    return {"type": "object"}


def _read_result(body: Any) -> GenerationResult:
    message = _member(_element(_member(body, "choices"), 0), "message")
    usage = _member(body, "usage")

    tool_calls: list[ModelToolCall] = []

    calls = _member(message, "tool_calls")

    if isinstance(calls, list):
        for call in calls:
            call_id = _or_default(_get_string(_member(call, "id")), "")
            function = _member(call, "function")
            name = _or_default(_get_string(_member(function, "name")), "")
            arguments = _or_default(_get_string(_member(function, "arguments")), "{}")

            if not _is_blank(name):
                tool_calls.append(ModelToolCall(id=call_id, name=name, arguments_json=arguments))

    return GenerationResult(
        content=_or_default(_get_string(_member(message, "content")), ""),
        tool_calls=tuple(tool_calls),
        prompt_tokens=_or_default(_get_int(_member(usage, "prompt_tokens")), 0),
        completion_tokens=_or_default(_get_int(_member(usage, "completion_tokens")), 0))


def _member(node: Any, name: str) -> Any:
    """JsonNode's member indexer, node?[name].

    A missing member and the JSON literal null both read as None; indexing a node of the wrong
    kind is refused (InvalidOperationException, here RuntimeError).
    """
    if node is None:
        return None

    if not isinstance(node, dict):
        raise RuntimeError("The node must be of type 'JsonObject'.")

    return node.get(name)


def _element(node: Any, index: int) -> Any:
    """JsonNode's element indexer, node?[index].

    As _member, and an index past the end is an IndexError.
    """
    if node is None:
        return None

    if not isinstance(node, list):
        raise RuntimeError("The node must be of type 'JsonArray'.")

    return node[index]


def _get_string(node: Any) -> str | None:
    """JsonNode.GetValue<string>(): only a JSON string reads as one."""
    if node is None:
        return None

    if not isinstance(node, str):
        raise RuntimeError("The node cannot be converted to 'System.String'.")

    return node


def _get_int(node: Any) -> int | None:
    """JsonNode.GetValue<int>(): only a JSON integer within Int32 reads as one."""
    if node is None:
        return None

    # A JSON true or false is not an integer: bool is an int to isinstance.
    if isinstance(node, bool) or not isinstance(node, int) or not -2**31 <= node < 2**31:
        raise RuntimeError("The node cannot be converted to 'System.Int32'.")

    return node


def _or_default(value: Any, default: Any) -> Any:
    return default if value is None else value


def _parse_json(text: str) -> Any:
    """JsonNode.Parse: strict JSON, no NaN or Infinity, nesting no deeper than 64."""
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


def _post(
        opener: urllib.request.OpenerDirector,
        http_request: urllib.request.Request,
        timeout_seconds: float) -> str:
    """HttpClient.PostAsync, EnsureSuccessStatusCode, then ReadAsStringAsync.

    The body is buffered inside the call. A request that never got an answer is an
    HttpRequestException, as is a status outside 2xx (carrying that status). A timeout is not:
    HttpClient cancels the request, so it stays a TimeoutError rather than claiming a refusal.
    """
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


def _decode(body: bytes, charset: str | None) -> str:
    """HttpContent.ReadAsStringAsync's decoding.

    The charset the response names, UTF-8 when it names none, a UTF-8 byte-order mark skipped,
    and an undecodable byte replaced rather than refused.
    """
    encoding = codecs.lookup(charset or "utf-8").name

    if encoding == "utf-8":
        encoding = "utf-8-sig"

    return body.decode(encoding, errors="replace")


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


def _is_blank(text: str | None) -> bool:
    """string.IsNullOrWhiteSpace, over char.IsWhiteSpace's own set.

    Not str.isspace: .NET does not count U+001C..U+001F as white space.
    """
    if text is None:
        return True

    return all(
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp")
        for character in text)
