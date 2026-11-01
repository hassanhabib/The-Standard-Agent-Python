# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.agent import Agent
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.tools.tool import Tool


_INPUT_PLACEHOLDER = "{input}"
_PROMPT_PLACEHOLDER = "{prompt}"


class AgentTool(Tool):
    GROUNDED_HANDOFF = "The user asked: {prompt}\n\nYour task: {input}"

    def __init__(
            self,
            name: str,
            agent: Agent,
            handoff: str = _INPUT_PLACEHOLDER,
            description: str = "",
            parameters: str = "{}") -> None:

        self._name = name
        self._agent = agent
        self._handoff = handoff
        self._description = description
        self._parameters = parameters

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> str:
        return self._parameters

    async def execute(self, input: str) -> str:
        outer_run = AgentRun.current()

        handed_off = (self._handoff
            .replace(_PROMPT_PLACEHOLDER, outer_run.prompt if outer_run is not None else "")
            .replace(_INPUT_PLACEHOLDER, input))
        outcome = await self._agent.run(handed_off, cancellation=None)

        if outcome.status is AgentStatus.RESPONDED:
            return outcome.result

        return (
            f"[did not complete] the sub-agent '{self.name}' ended "
            + f"{_status_name(outcome.status)}: {outcome.result}")


def _status_name(status: AgentStatus) -> str:
    """The status as the C# prints it: AWAITING_APPROVAL is AwaitingApproval."""
    return "".join(word.capitalize() for word in status.name.split("_"))
