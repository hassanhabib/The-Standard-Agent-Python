# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Iterable

from standard_agents.brokers.policies.ipolicy_broker import IPolicyBroker
from standard_agents.models.orchestrations.effects.agent_effect import AgentEffect
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision,
)


# The Local mode: least privilege as a list, which is what allow_tools() has always meant. It is
# a policy broker so that the simple answer and an external policy engine travel the same seam,
# and so a denial carries a reason from the very first release.
#
# An entry says WHAT and, optionally, WHERE:
#
#   "search"                 the tool, wherever it points
#   "write_file:/project"    the tool, only where the scope starts with /project
#
# The second form exists because "may write files" is not "may write files under /project", and
# an agent with hands is defined by that difference. The scope is whatever the tool named
# through ITool.scope_of; the framework never parses arguments, because only the tool knows what
# they mean.
#
# Matching is a prefix, deliberately, and that boundary is stated rather than discovered: no
# globs, no regular expressions, no path canonicalisation. A host that needs those supplies a
# real policy engine through use_policy, and one that needs "/project" not to match
# "/project-secrets" should say "/project/".
class AllowListPolicyBroker(IPolicyBroker):
    def __init__(self, allowed_entries: Iterable[str]) -> None:
        # Keyed case-insensitively (C#: StringComparer.OrdinalIgnoreCase).
        self._allowed_scopes_by_tool: dict[str, list[str]] = {}

        for entry in allowed_entries:
            separator = entry.find(":")

            tool_name = entry if separator < 0 else entry[:separator]
            scope = "" if separator < 0 else entry[separator + 1:]

            scopes = self._allowed_scopes_by_tool.get(_fold(tool_name))

            if scopes is None:
                scopes = []
                self._allowed_scopes_by_tool[_fold(tool_name)] = scopes

            scopes.append(scope)

    async def authorize(self, effect: AgentEffect) -> AuthorizationDecision:
        allowed_scopes = self._allowed_scopes_by_tool.get(_fold(effect.tool_name))

        if allowed_scopes is None:
            return AuthorizationDecision.deny(f"tool '{effect.tool_name}' is not permitted")

        # An entry with no scope permits the tool anywhere, which is what every entry meant
        # before scopes existed, so a list written against an earlier release keeps its meaning.
        permitted = any(
            len(allowed) == 0
            or _fold(effect.scope).startswith(_fold(allowed))
            for allowed in allowed_scopes)

        return (
            AuthorizationDecision.allow()
            if permitted
            else AuthorizationDecision.deny(
                f"tool '{effect.tool_name}' is not permitted at '{effect.scope}'"))

    # Whether anything in the list speaks to this act at all. The permission MODE needs to know
    # the difference between "explicitly permitted" and "nobody mentioned it", a distinction a
    # yes/no decision cannot carry.
    def mentions(self, effect: AgentEffect) -> bool:
        return _fold(effect.tool_name) in self._allowed_scopes_by_tool


# StringComparer.OrdinalIgnoreCase: characters compared by their simple uppercase mapping.
# Python's str.upper() applies full mappings (U+00DF becomes "SS"), so each character is
# uppercased on its own and kept as it is when its mapping expands.
def _fold(value: str) -> str:
    folded: list[str] = []

    for character in value:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)
