# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses

from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.models.orchestrations.agents.agent_context import AgentContext

ACTION_PREFIX = "ACTION:"
FINAL_PREFIX = "FINAL:"
SAY_PREFIX = "SAY:"
RETURN_RESPONSE_DIRECTION = "ReturnResponse"


# The text protocol the brain answers in, the same as the C# framework's: an optional
# "SAY: <progress>" line, then exactly one "ACTION: <tool>: <input>" or "FINAL: <answer>". A reply
# with neither prefix is taken as the answer itself.
def build_user_message(context: AgentContext) -> str:
    user_message = f"Task: {context.prompt}"
    observations = context.memories + context.knowledge + context.observations

    if observations:
        user_message += "\n\nObservations so far:\n"

        for observation in observations:
            user_message += f"- {observation}\n"

    return user_message


def peel_narration(reply: str) -> tuple[str, str]:
    leading = reply.lstrip()

    if leading.upper().startswith(SAY_PREFIX) is False:
        return "", reply

    narration_line, _, choice = leading.partition("\n")

    return narration_line[len(SAY_PREFIX):].strip(), choice.strip()


def interpret(context: AgentContext, reply: str) -> AgentContext:
    narration, choice = peel_narration(reply)
    first_line = choice.split("\n")[0].strip()

    if first_line.upper().startswith(ACTION_PREFIX):
        tool_name, _, tool_input = first_line[len(ACTION_PREFIX):].partition(":")

        if tool_name.strip() != "":
            return dataclasses.replace(
                context,
                direction_type=tool_name.strip(),
                payload=tool_input.strip(),
                narration=narration,
                raw_reply=reply)

    answer = choice

    if choice.upper().startswith(FINAL_PREFIX):
        answer = choice[len(FINAL_PREFIX):].strip()

    return dataclasses.replace(
        context,
        direction_type=RETURN_RESPONSE_DIRECTION,
        payload=answer,
        narration=narration,
        raw_reply=reply)


def revision_feedback(judgement: Judgement, draft: str) -> str:
    return (
        f"A previous draft was rejected on review: {judgement.reason}. "
        + f"The draft was: {draft}")


def is_final_answer(context: AgentContext) -> bool:
    return (context.direction_type == RETURN_RESPONSE_DIRECTION
        and context.payload.strip() != "")
