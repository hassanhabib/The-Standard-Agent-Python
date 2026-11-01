# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""What StandardAgent's composition derives from what it was given, as pure functions."""

from __future__ import annotations

from collections.abc import Iterable

from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.coordinations.agents.tool_narration import ToolNarration
from standard_agents.tools.tool import Tool


def render_tool_catalog(tools: Iterable[Tool]) -> str:
    """The catalog a "{{tools}}" marker in the agent's Data expands into.

    Only tools that carry a description are listed: a description is the opt-in (SPEC.md 6.1),
    and a tool with none is callable but not advertised. Derived from the registered tools, so
    it never drifts from what is actually there.
    """
    return "\n".join(_catalog_line(tool) for tool in advertised(tools))


def render_tool_catalog_entries(tools: Iterable[Tool]) -> dict[str, str]:
    """The same catalog, per tool, keyed by name.

    So a run under selection (SPEC.md 4.15) can be shown only what it was offered. Derived from
    the same rendering as the whole catalog, so the two can never disagree about a tool's line.
    """
    return {tool.name: _catalog_line(tool) for tool in advertised(tools)}


def render_tool_definitions(tools: Iterable[Tool]) -> list[ToolDefinition]:
    """The tools a native brain is offered, by the same opt-in the text catalog uses.

    A tool without a description stays callable but unadvertised, so declaring tools as data
    does not quietly widen what the Brain may reach for.
    """
    return [
        ToolDefinition(tool.name, tool.description, tool.parameters)
        for tool in advertised(tools)]


def render_tool_narrations(tools: Iterable[Tool]) -> dict[str, ToolNarration]:
    """What each tool declared it says, keyed by name.

    Derived from the tools exactly as risk and scope are: the tool is what knows what its act
    means in the user's language, and derived data cannot drift.
    """
    return {
        tool.name: ToolNarration(tool.narration_starting, tool.narration_observed)
        for tool in tools
        if not _is_blank(tool.narration_starting) or not _is_blank(tool.narration_observed)}


def advertised(tools: Iterable[Tool]) -> list[Tool]:
    """What the model may be told about, in ONE place.

    The rule (SPEC.md 6.1: a description is the opt-in, and a tool without one stays callable
    but unadvertised) holds for the text catalog Data renders into the prompt and for the
    definitions Decision hands a native brain alike; two copies of a rule about what the model
    may see is two chances to widen it by half.
    """
    return [tool for tool in tools if not _is_blank(tool.description)]


def compose_guardian_rubric(*parts: str) -> str:
    """A guardian rubric from its parts in order, skipping any that are empty.

    Constitution first (the law), then the policy (what to screen or score), then the contract
    (the output protocol the broker parses). The contract stays last so it is never displaced,
    whatever the policy above it.
    """
    return "\n\n".join(part for part in parts if not _is_blank(part))


def _catalog_line(tool: Tool) -> str:
    return f"- {tool.name} \u2014 {tool.description} parameters: {tool.parameters}"


def _is_blank(text: str | None) -> bool:
    return not text or text.isspace()
