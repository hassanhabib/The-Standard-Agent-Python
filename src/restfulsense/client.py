# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from restfulsense.exceptions import HttpRequestException
from restfulsense.validation_service import read_as_string, validate_http_response

# The brokers name application/json as the media type; .NET's StringContent adds the charset.
_JSON_CONTENT_TYPE = "application/json; charset=utf-8"


@dataclass(frozen=True)
class _HttpResponse:
    status_code: int
    content_type: str | None
    body: bytes


class RESTFulApiFactoryClient:
    """The Python stand-in for RESTFulSense's RESTFulApiFactoryClient.

    It plays the client over an HttpClient whose BaseAddress, default headers and Timeout the
    broker set: one POST, the status validated into the matching RESTFulSense exception, the
    body handed back as parsed JSON.
    """

    def __init__(
            self,
            base_url: str,
            headers: dict[str, str] | None = None,
            timeout_seconds: float = 100.0,
            opener: urllib.request.OpenerDirector | None = None) -> None:

        # HttpClient.BaseAddress takes an absolute address only, and Timeout a positive one.
        if not urllib.parse.urlsplit(base_url).scheme:
            raise ValueError("Invalid URI: The format of the URI could not be determined.")

        if timeout_seconds <= 0:
            raise ValueError("The timeout must be greater than zero.")

        self._base_url = base_url
        self._headers = dict(headers or {})
        self._timeout_seconds = timeout_seconds

        # The opener is the transport, as the HttpClient is in C#: a host that owns its handler
        # hands over an opener built on it. HttpClient sends no User-Agent of its own, so the
        # opener built here sends none either.
        if opener is None:
            opener = urllib.request.build_opener()
            opener.addheaders = []

        self._opener = opener

    async def post_content(self, relative_url: str, content: dict) -> dict:
        request_json = json.dumps(content, separators=(",", ":"))
        url = self._combine(relative_url)

        response = await asyncio.to_thread(self._send, url, request_json.encode("utf-8"))
        response_content = read_as_string(response.body, response.content_type)
        validate_http_response(response.status_code, response.content_type, response_content)

        return json.loads(response_content) if response_content else {}

    def _combine(self, relative_url: str) -> str:
        """Join a relative address to the base address by RFC 3986, as HttpClient does.

        A base address without a trailing slash drops its last segment.
        """
        return urllib.parse.urljoin(self._base_url, relative_url)

    def _send(self, url: str, request_body: bytes) -> _HttpResponse:
        request = urllib.request.Request(url, data=request_body, method="POST")

        for name, value in self._headers.items():
            request.add_header(name, value)

        request.add_header("Content-Type", _JSON_CONTENT_TYPE)

        try:
            try:
                response = self._opener.open(request, timeout=self._timeout_seconds)
            except urllib.error.HTTPError as http_error:
                response = http_error

            with response:
                return _HttpResponse(
                    status_code=response.code,
                    content_type=response.headers.get("Content-Type"),
                    body=response.read())

        # No answer arrived: refused, unresolved, reset, or timed out.
        except urllib.error.URLError as url_error:
            raise HttpRequestException(str(url_error.reason)) from url_error

        except (OSError, http.client.HTTPException) as transport_error:
            raise HttpRequestException(str(transport_error)) from transport_error
