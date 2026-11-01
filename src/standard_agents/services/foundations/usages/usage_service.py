# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.usages.usage_broker import UsageBroker
from standard_agents.models.foundations.usages.agent_usage import AgentUsage


class UsageService:
    """What a model call consumed, the question Decision could not answer.

    Inference could say what the model SAID and not what it COST. On the native protocol the
    provider reports usage in its response and the numbers were lifted out as they went past; on
    the text protocol there was nobody to ask, so the token counts stayed zero and a token or cost
    budget never tripped at all. A budget that silently does not apply is worse than no budget,
    because it is claimed in the profile.

    Measuring belongs to Decision because a token is the model's unit. Deciding whether to
    CONTINUE belongs to the loop, which is where the budget already lives.
    """

    def __init__(self, *, usage_broker: UsageBroker, logging_broker: LoggingBroker) -> None:
        self.usage_broker = usage_broker
        self.logging_broker = logging_broker

    async def measure(self, prompt: str, completion: str) -> AgentUsage:
        """What one model call consumed, counted locally.

        Returned with is_estimated set, because a counted number is an estimate of what the
        provider will bill.
        """
        prompt_tokens = await self.usage_broker.count_tokens(prompt)
        completion_tokens = await self.usage_broker.count_tokens(completion)

        return AgentUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            is_estimated=True)
