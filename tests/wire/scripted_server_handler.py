# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""A protocol server in a handler.

It records every request the broker sends, byte for byte, and answers from a script.
Deterministic, in-process, no port: the wire-contract tests run the real brokers against it
(principal review 2026-09-04, F-21).
"""

from __future__ import annotations

import http
import io
import threading
import urllib.request
import urllib.response
from collections.abc import Callable
from dataclasses import dataclass, field
from email.message import Message


@dataclass
class ScriptedResponse:
    """What the server answers: a status, a body, its media type and any extra headers.

    A response without a media type has no content, as an HttpResponseMessage built from a
    status alone.
    """

    status_code: int
    body: str = ""
    media_type: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


Respond = Callable[[urllib.request.Request, str], ScriptedResponse]


class ScriptedServerHandler(urllib.request.HTTPHandler):
    """Answers every http request from respond(request, body), after recording both."""

    def __init__(self, respond: Respond) -> None:
        super().__init__()
        self._respond = respond
        self.requests: list[urllib.request.Request] = []
        self.bodies: list[str] = []

    @classmethod
    def answering(cls, body: str, media_type: str = "application/json") -> ScriptedServerHandler:
        return cls(lambda request, request_body: cls.json(http.HTTPStatus.OK, body, media_type))

    @classmethod
    def answering_with(cls, status_code: int, body: str = "") -> ScriptedServerHandler:
        return cls(lambda request, request_body: cls.json(status_code, body))

    @classmethod
    def hanging(cls) -> ScriptedServerHandler:
        """Holds the connection open until the caller gives up: a provider that never answers.

        The caller gives up through the timeout it opened the request with, as a socket would.
        """
        def hang(request: urllib.request.Request, body: str) -> ScriptedResponse:
            threading.Event().wait(request.timeout)

            raise TimeoutError("timed out")

        return cls(hang)

    @staticmethod
    def json(
            status_code: int,
            body: str,
            media_type: str = "application/json") -> ScriptedResponse:
        """A response whose content is body, as StringContent(body, Encoding.UTF8, mediaType)."""
        return ScriptedResponse(status_code, body, media_type)

    def http_open(self, request: urllib.request.Request) -> urllib.response.addinfourl:
        body = (request.data or b"").decode("utf-8")
        self.requests.append(request)
        self.bodies.append(body)

        return _to_response(request, self._respond(request, body))


def header_of(request: urllib.request.Request, name: str) -> str | None:
    """The value a request carries for a header, matched ignoring case; None when absent."""
    return {key.lower(): value for key, value in request.header_items()}.get(name.lower())


def _to_response(
        request: urllib.request.Request,
        scripted: ScriptedResponse) -> urllib.response.addinfourl:

    headers = Message()

    if scripted.media_type is not None:
        headers["Content-Type"] = f"{scripted.media_type}; charset=utf-8"

    for name, value in scripted.headers.items():
        headers[name] = value

    response = urllib.response.addinfourl(
        io.BytesIO(scripted.body.encode("utf-8")),
        headers,
        request.full_url,
        scripted.status_code)

    response.msg = http.HTTPStatus(scripted.status_code).phrase

    return response
