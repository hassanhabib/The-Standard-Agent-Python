# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The same agent definition as a service.

Five lines on a laptop, the same five lines behind HTTP: composition here is configuration,
never new concepts, so the appliance guarantee holds at the exposure layer too.

`python -m standard_agents.host` reads the configuration the C# host reads, by the same names:
environment variables (Host__ApiKey is Host:ApiKey) and then the command line
(--Host:ApiKey=psk-live-7, or --urls http://0.0.0.0:8080), the later source winning.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from collections.abc import Awaitable, Callable, Mapping, Sequence

from standard_agents.agent import Agent
from standard_agents.host.http_context import HttpContextAccessor
from standard_agents.host.security.claims import ClaimsPrincipal
from standard_agents.host.security.http_principal_resolver import HttpPrincipalResolver
from standard_agents.host.server import AgentHost, HttpRequest
from standard_agents.models.clients.agents.exceptions import InvalidAgentConfigurationException
from standard_agents.standard_agent import StandardAgent

_DEFAULT_URLS = "http://localhost:5000"
_BRAIN_KEYS = ("brain", "nativeBrain", "nativeBrainAnthropic")
_LOGGER = logging.getLogger("standard_agents.host")


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the host until Ctrl+C, or answer --schema or --validate [path] and exit."""
    arguments = list(sys.argv[1:] if arguments is None else arguments)

    # --schema prints the JSON Schema of the agent document, emitted from the same table the
    # document is validated against, for editors and pipelines (F-24).
    if "--schema" in arguments:
        print(StandardAgent.document_schema_json())

        return 0

    if "--validate" in arguments:
        return _validate(arguments)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")

    try:
        asyncio.run(_serve(read_configuration(arguments, os.environ)))
    except KeyboardInterrupt:
        pass

    return 0


def read_configuration(
        arguments: Sequence[str],
        environment: Mapping[str, str]) -> dict[str, str]:
    """The configuration ASP.NET's default builder reads, in its order, the later winning.

    DOTNET_ and ASPNETCORE_ variables with the prefix removed (ASPNETCORE_URLS is urls), then
    every environment variable with "__" read as ":", then the command line: --key=value,
    --key value, /key=value, /key value and key=value.
    """
    configuration: dict[str, str] = {}

    for prefix in ("DOTNET_", "ASPNETCORE_"):
        for name, value in environment.items():
            if name.upper().startswith(prefix):
                _set(configuration, name[len(prefix):].replace("__", ":"), value)

    for name, value in environment.items():
        _set(configuration, name.replace("__", ":"), value)

    for key, value in _command_line(arguments):
        _set(configuration, key, value)

    return configuration


def create_host(
        configuration: Mapping[str, str] | None = None,
        *,
        agent_factory: Callable[[HttpPrincipalResolver], Agent] | None = None,
        authenticate: Callable[[HttpRequest], Awaitable[ClaimsPrincipal | None]] | None = None,
) -> AgentHost:
    """The host, composed from configuration as Program.cs composes it.

    configuration holds the keys the C# host reads, named as it names them (Host:ApiKey,
    Agent:Config, urls), compared ignoring case. agent_factory registers the agent: it is
    handed the host's principal resolver and called when the first request needs the agent;
    without one, the agent is composed from the configuration. authenticate is the
    authentication scheme: it reads a request and returns who it is, or None for an anonymous
    request.
    """
    settings = _Settings(configuration or {})

    # Who is acting comes from the request's authenticated user, translated per act into the
    # principal the policy decides on and the audit stamps (principal review 2026-09-04, F-10).
    # The wire has no field in which a caller can claim to be someone; the scheme establishes
    # them.
    http_context_accessor = HttpContextAccessor()
    principals = HttpPrincipalResolver(http_context_accessor)

    # Naming an issuer (Host:Authentication:Authority) is what configures authentication, and
    # then every agent route wants an authenticated user. Name nothing and the door is as open
    # as before, with no principal handed to the agent.
    authority = settings.get("Host:Authentication:Authority")
    authentication_configured = not _is_blank(authority)

    if authentication_configured and authenticate is None:
        _LOGGER.warning(
            "Host:Authentication:Authority is set, and this host has no scheme that can "
            "validate a bearer token: every agent route answers 401 until create_host is "
            "given an authenticate scheme.")

    compose_agent = agent_factory or (lambda resolver: _compose_agent(settings, resolver))

    return AgentHost(
        lambda: compose_agent(principals),
        urls=_urls(settings),
        api_key=settings.get("Host:ApiKey"),
        authentication_configured=authentication_configured,
        authenticate=authenticate,
        http_context_accessor=http_context_accessor)


async def _serve(configuration: Mapping[str, str]) -> None:
    # Ctrl+C cancels this task through asyncio.run; SIGTERM, which a container stop sends,
    # does the same where the platform lets a loop handle it.
    if sys.platform != "win32":
        asyncio.get_running_loop().add_signal_handler(
            signal.SIGTERM, asyncio.current_task().cancel)

    async with create_host(configuration) as host:
        for url in host.urls:
            _LOGGER.info("Now listening on: %s", url)

        _LOGGER.info("Application started. Press Ctrl+C to shut down.")

        try:
            await asyncio.Event().wait()
        finally:
            _LOGGER.info("Application is shutting down...")


def _validate(arguments: list[str]) -> int:
    """A validate-only run: compose the document and say whether it composes.

    Names the entry when it does not, without standing the host up: the check a deployment
    pipeline runs before a green heartbeat could mislead it (principal review 2026-09-04,
    F-24).
    """
    following = arguments[arguments.index("--validate") + 1:]
    document_path = following[0] if following else os.path.join(os.getcwd(), "agent.json")

    try:
        with open(document_path, encoding="utf-8-sig") as document:
            StandardAgent.from_json(document.read())
    except (InvalidAgentConfigurationException, OSError) as exception:
        print(f"{document_path} does not compose: {exception}", file=sys.stderr)

        return 1

    print(f"{document_path} composes.")

    return 0


def _compose_agent(settings: _Settings, principals: HttpPrincipalResolver) -> StandardAgent:
    """One agent, one instance, serving every caller; zero configuration still runs.

    Without a Brain the host stands, heartbeats, and answers with what to configure rather
    than crashing at startup. The agent as data: Agent:Config names a JSON document, or an
    agent.json in the working directory is picked up on its own, so a low-code platform writes
    a file and has an agent. When the document is the source, the document is the whole truth.
    """
    configured_path = settings.get("Agent:Config") or ""

    agent_json_path = (
        os.path.join(os.getcwd(), "agent.json") if _is_blank(configured_path)
        else configured_path)

    if not _is_blank(configured_path) or os.path.exists(agent_json_path):
        return _compose_document_agent(agent_json_path, principals)

    url = settings.get("Agent:Url")

    if _is_blank(url):
        agent = StandardAgent().on_brain(_no_brain_configured)
    else:
        agent = StandardAgent(
            url,
            _value_or(settings.get("Agent:ApiKey"), ""),
            _value_or(settings.get("Agent:Model"), ""))

    skills_path = settings.get("Agent:Skills")

    if not _is_blank(skills_path):
        agent.skills(skills_path)

    # One instance serves every caller, so a memory would be one memory for all of them: one
    # caller's facts in another caller's context. It exists only when the configuration names
    # it (principal review 2026-09-04, F-05).
    memory_path = settings.get("Agent:Memory")

    if _is_blank(memory_path):
        agent.without_memory()
    else:
        agent.memory(memory_path)

    # Always on: the spans exist only when something listens.
    agent.telemetry(agent_name=_value_or(settings.get("Agent:Name"), "standard-agent"))

    return agent.principal(principals.resolve)


def _compose_document_agent(path: str, principals: HttpPrincipalResolver) -> StandardAgent:
    with open(path, encoding="utf-8-sig") as document_file:
        agent_json = document_file.read()

    configured = StandardAgent.from_json(agent_json)
    document = json.loads(agent_json)
    keys = document if isinstance(document, dict) else {}

    # The document must name a memory to get one; otherwise the agent recalls nothing and
    # offers no way to store (F-05).
    if "memory" not in keys:
        configured.without_memory()

    # The same zero-config grace the classic path has: a document with no brain still stands,
    # heartbeats, and answers with what to add, never a 500 at the first prompt.
    if not any(key in keys for key in _BRAIN_KEYS):
        configured.on_brain(_no_brain_in_document)

    return configured.principal(principals.resolve)


async def _no_brain_configured(system_prompt: str, user_prompt: str) -> str:
    return (
        "FINAL: No Brain is configured. Provide an agent.json (or set Agent:Config), or "
        "set Agent:Url, Agent:ApiKey and Agent:Model, then restart the host.")


async def _no_brain_in_document(system_prompt: str, user_prompt: str) -> str:
    return (
        'FINAL: No Brain is configured. Add "brain", "nativeBrain" or '
        '"nativeBrainAnthropic" to agent.json, then restart the host.')


class _Settings:
    """Configuration read as ASP.NET reads it: keys compared ignoring case."""

    def __init__(self, configuration: Mapping[str, str]) -> None:
        self._values = {key.upper(): value for key, value in configuration.items()}

    def get(self, key: str) -> str | None:
        return self._values.get(key.upper())


def _command_line(arguments: Sequence[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    remaining = iter(arguments)

    for argument in remaining:
        if argument.startswith("--"):
            body = argument[2:]
        elif argument.startswith("/"):
            body = argument[1:]
        elif "=" in argument and not argument.startswith("-"):
            body = argument
        else:
            continue

        if "=" in body:
            key, value = body.split("=", 1)
        else:
            value = next(remaining, None)

            if value is None:
                continue

            key = body

        pairs.append((key, value))

    return pairs


def _set(configuration: dict[str, str], key: str, value: str) -> None:
    """Set a key, replacing any spelling of it that differs only in case."""
    for existing_key in [name for name in configuration if name.upper() == key.upper()]:
        del configuration[existing_key]

    configuration[key] = value


def _is_blank(value: str | None) -> bool:
    return not value or value.isspace()


def _value_or(value: str | None, default: str) -> str:
    return value if value is not None else default


def _urls(settings: _Settings) -> tuple[str, ...]:
    urls = settings.get("urls") or _DEFAULT_URLS

    return tuple(url.strip() for url in urls.split(";") if url.strip())
