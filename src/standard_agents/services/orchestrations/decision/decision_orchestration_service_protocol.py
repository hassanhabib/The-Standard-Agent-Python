# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import dataclasses

from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.models.orchestrations.agents.agent_context import AgentContext

ACTION_PREFIX = "ACTION:"
FINAL_PREFIX = "FINAL:"
RETURN_RESPONSE_DIRECTION = "ReturnResponse"
RESPOND_INTENT = "Respond"
REFUSE_DIRECTION = "Refuse"
REFUSE_VERDICT = "refuse"
REFUSAL_MESSAGE = "I'm not able to help with that."


def is_refusal(verdict: str) -> bool:
    return verdict.lower().startswith(REFUSE_VERDICT)


# The reference text protocol (SPEC.md 6.0): "ACTION: <tool>: <input>" to act, "FINAL: <answer>"
# to answer. A reply with neither prefix is taken as the answer itself.
def build_user_message(context: AgentContext) -> str:
    user_message = f"Task: {context.prompt}"
    observations = context.memories + context.knowledge + context.observations

    if observations:
        user_message += "\n\nObservations so far:\n"

        for observation in observations:
            user_message += f"- {observation}\n"

    return user_message


# A tool call is read from the first line only (SPEC.md 6.0). This implementation does not voice
# narration, so a SAY: line is not peeled: it is the first line, and the reply is read as is.
def interpret(context: AgentContext, reply: str) -> AgentContext:
    first_line = reply.split("\n")[0].strip()

    if first_line.upper().startswith(ACTION_PREFIX):
        tool_name, _, tool_input = first_line[len(ACTION_PREFIX):].partition(":")

        if tool_name.strip() != "":
            return dataclasses.replace(
                context,
                intent=tool_name.strip(),
                direction_type=tool_name.strip(),
                payload=tool_input.strip(),
                raw_reply=reply)

    answer = reply

    if reply.upper().startswith(FINAL_PREFIX):
        answer = reply[len(FINAL_PREFIX):].strip()

    return dataclasses.replace(
        context,
        intent=RESPOND_INTENT,
        direction_type=RETURN_RESPONSE_DIRECTION,
        payload=answer,
        raw_reply=reply)


def revision_feedback(judgement: Judgement, draft: str) -> str:
    return (
        f"A previous draft was rejected on review: {judgement.reason}. "
        + f"The draft was: {draft}")


def is_final_answer(context: AgentContext) -> bool:
    return (context.direction_type == RETURN_RESPONSE_DIRECTION
        and context.payload.strip() != "")
