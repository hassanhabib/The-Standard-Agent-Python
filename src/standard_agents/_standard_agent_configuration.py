# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The agent document: JSON read into the same verbs code calls (StandardAgent.from_json)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from standard_agents.standard_agent import StandardAgent


def apply_document(agent: StandardAgent, document_json: str) -> None:
    """Configures the agent with every entry of the document, in the document's order."""
    document = json.loads(document_json)

    for key, value in document.items():
        _apply(agent, key, value)


def _apply(agent: StandardAgent, key: str, value: Any) -> None:
    match key:
        # Identity rides in the document, so the file IS the agent: a registry reads the name a
        # handoff calls and the description that advertises it from the same JSON that composes
        # it. Each key preserves the other, so their order cannot matter.
        case "name":
            agent.identity(value, description=agent.description)

        case "description":
            agent.identity(agent.name, description=value)

        case "ruleGate":
            agent.rule_gate(*value)

        case "maxTurns":
            agent.max_turns(value)

        case "identicalCallLimit":
            agent.identical_call_limit(value)

        # true or false is the deployment's decision; text is that decision made with the words
        # each citation line starts with (SPEC.md 4.2).
        case "citeKnowledge" if isinstance(value, str):
            agent.cite_knowledge(prefix=value)

        case "citeKnowledge":
            agent.cite_knowledge(cite=value)
