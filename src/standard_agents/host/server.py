# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The host's HTTP/1.1 server, on asyncio streams and nothing else."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HttpRequest:
    """One request as the server read it: what an authentication scheme and a route look at."""

    method: str
    path: str
    headers: dict[str, str]
    body: bytes = b""


class AgentHost:
    """The host: the routes, the gates in front of them, and the agent behind them."""
