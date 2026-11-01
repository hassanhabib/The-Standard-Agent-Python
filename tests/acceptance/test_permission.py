# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""Permission, as a deployment actually needs to express it.

The perimeter already had the hard half: a human before an irreversible act, held rather than
failed, the claim released so an approval cannot arrive too late, and the act travelling with the
pause so an authority can be shown what they are permitting.

What it did not have was granularity. Permission was a list of tool NAMES, one list served two
meanings, and there was no way to say "ask me about anything you have not been told about",
which is the only workable posture for an agent touching files, because the targets cannot be
enumerated in advance.
"""

import pytest

from standard_agents.brokers.approvals.approval_broker import ApprovalDecision
from standard_agents.models.orchestrations.effects.authorization_decision import (
    AuthorizationDecision)
from standard_agents.models.orchestrations.effects.permission_mode import PermissionMode
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel
from standard_agents.standard_agent import StandardAgent
from standard_agents.tools.tool import Tool


@pytest.fixture(autouse=True)
def _in_a_scratch_directory(tmp_path, monkeypatch):
    # The default memory file and knowledge folder resolve against the working directory.
    monkeypatch.chdir(tmp_path)


class _WriteFileTool(Tool):
    def __init__(self) -> None:
        self.writes = 0

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Writes text to a path."

    @property
    def risk(self) -> RiskLevel:
        # The tool knows what it does. Risk is declared here rather than inferred from whichever
        # list the host happened to put the name in.
        return RiskLevel.SENSITIVE

    def scope_of(self, input: str) -> str:
        # The tool also knows what it is about to TOUCH. The framework cannot parse arbitrary
        # arguments, and a host should not have to reinvent that parsing in a policy delegate.
        return input.split(" ")[0]

    async def execute(self, input: str) -> str:
        self.writes += 1

        return "written"


def _agent_acting(tool: Tool, *replies: str) -> StandardAgent:
    asked = 0

    async def generate(system_prompt: str, user_prompt: str) -> str:
        nonlocal asked
        reply = replies[min(asked, len(replies) - 1)]
        asked += 1

        return reply

    return (StandardAgent()
        .tool(tool)
        .on_brain(generate)
        .max_turns(6))


# Gap 1. One list drove both risk and approval, so RiskLevel.SENSITIVE could never be produced: a
# declared level the framework was incapable of reaching, and a policy branching on it was
# writing dead code.
async def test_should_carry_the_risk_the_tool_declares():
    # given
    tool = _WriteFileTool()
    seen_risk = None

    async def authorize(effect):
        nonlocal seen_risk
        seen_risk = effect.risk_level

        return AuthorizationDecision.allow()

    agent = (_agent_acting(tool, "ACTION: write_file: /project/a.txt hello", "FINAL: done")
        .on_policy(authorize))

    # when
    await agent.process_prompt("write it")

    # then: the tool declares its own risk, and SENSITIVE must be reachable at all
    assert seen_risk == RiskLevel.SENSITIVE


# Gap 2. Permission was per tool NAME. "May write files" is not "may write files under /project",
# and nothing in the model could express the difference.
async def test_should_carry_the_scope_the_tool_is_about_to_touch():
    # given
    tool = _WriteFileTool()
    seen_scope = None

    async def authorize(effect):
        nonlocal seen_scope
        seen_scope = effect.scope

        return AuthorizationDecision.allow()

    agent = (_agent_acting(tool, "ACTION: write_file: /project/a.txt hello", "FINAL: done")
        .on_policy(authorize))

    # when
    await agent.process_prompt("write it")

    # then
    assert seen_scope == "/project/a.txt"


# Gap 2, Local mode. The allow-list should be able to say WHERE, not only WHAT.
async def test_should_deny_an_act_outside_an_allowed_scope():
    # given
    tool = _WriteFileTool()

    agent = (_agent_acting(tool, "ACTION: write_file: /etc/passwd hello", "FINAL: done")
        .allow_tools("write_file:/project"))

    # when
    await agent.process_prompt("write it")

    # then: the tool is permitted under /project and the act targeted /etc
    assert tool.writes == 0


async def test_should_allow_an_act_inside_an_allowed_scope():
    # given
    tool = _WriteFileTool()

    agent = (_agent_acting(tool, "ACTION: write_file: /project/a.txt hello", "FINAL: done")
        .allow_tools("write_file:/project"))

    # when
    await agent.process_prompt("write it")

    # then
    assert tool.writes == 1


# Gap 3. Everything was enumerated by name, so an unlisted tool was silently SAFE and silently
# permitted. Ask-first is the only workable posture when targets cannot be listed in advance, and
# it was inexpressible.
async def test_should_ask_before_an_act_that_was_never_explicitly_permitted():
    # given
    tool = _WriteFileTool()
    asked = 0

    async def deny(effect):
        nonlocal asked
        asked += 1

        return ApprovalDecision.DENIED

    agent = (_agent_acting(tool, "ACTION: write_file: /project/a.txt hello", "FINAL: done")
        .permissions(PermissionMode.ASK)
        .on_approval(deny))

    # when
    await agent.process_prompt("write it")

    # then: nothing permitted this act explicitly, and the mode says ask about anything that was
    # not
    assert asked == 1
    assert tool.writes == 0
