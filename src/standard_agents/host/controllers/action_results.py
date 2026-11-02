# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""What a controller answers with, before any of it is HTTP bytes.

A controller maps a request to one of these and the server writes it, so a controller holds no
socket code and its tests read the result the way the C# tests read an ActionResult.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from http import HTTPStatus


@dataclass(frozen=True)
class ObjectResult:
    """A value and the status it is returned with, the value formatted by the server."""

    status_code: HTTPStatus
    value: object


async def _no_body() -> AsyncIterator[str]:
    return
    yield


@dataclass(frozen=True)
class StreamResult:
    """A response written as it is produced: the status, the content type, then the body.

    The body is read once, by whoever writes it; each piece is written and flushed as it comes.
    """

    status_code: HTTPStatus = HTTPStatus.OK
    content_type: str | None = None
    body: AsyncIterator[str] = field(default_factory=_no_body)
