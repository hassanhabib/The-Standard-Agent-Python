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
        # The outer run's signal rides the ambient run the way its identity does, so the nested
        # run observes the same stop the outer loop observes: cancelling the outer run stops the
        # whole tree at the next turn boundary (SPEC.md 4.10). Outside any run, there is none.
        outcome = await self._agent.run(
            handed_off,
            cancellation=outer_run.cancellation if outer_run is not None else None)

        # How the handoff ended, recorded on the OUTER run (the nested run's own ambient state
        # never flows back across the await). The string returned below cannot carry a status,
        # and a transfer needs one: the loop adopts an answer and keeps working past anything
        # else. Recorded on every handoff; the loop clears it before each act, so it only ever
        # reads the act it just performed.
        if outer_run is not None:
            outer_run.handoff_outcome = outcome

        if outcome.status is AgentStatus.RESPONDED:
            return outcome.result

        return (
            f"[did not complete] the sub-agent '{self.name}' ended "
            + f"{_status_name(outcome.status)}: {outcome.result}")


def _status_name(status: AgentStatus) -> str:
    """The status as the C# prints it: AWAITING_APPROVAL is AwaitingApproval."""
    return "".join(word.capitalize() for word in status.name.split("_"))
