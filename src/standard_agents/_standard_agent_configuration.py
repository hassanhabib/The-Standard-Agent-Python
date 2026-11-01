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
        case "ruleGate":
            agent.rule_gate(*value)

        case "maxTurns":
            agent.max_turns(value)

        case "identicalCallLimit":
            agent.identical_call_limit(value)
