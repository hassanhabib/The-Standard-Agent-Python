# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from standard_agents.agent import Agent
from standard_agents.brokers.classifiers.classifier_broker import ClassifierBroker
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.mcps.mcp_broker import McpBroker
from standard_agents.brokers.memories.memory_broker import MemoryBroker
from standard_agents.brokers.skills.skill_broker import SkillBroker
from standard_agents.brokers.verifiers.verifier_broker import VerifierBroker
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.prompt_request import PromptRequest


class StandardAgent(Agent):
    def __init__(self) -> None:
        pass

    def use_skills(self, broker: SkillBroker) -> StandardAgent:
        raise NotImplementedError

    def use_generator(self, broker: GeneratorBroker) -> StandardAgent:
        raise NotImplementedError

    def use_memory(self, broker: MemoryBroker) -> StandardAgent:
        raise NotImplementedError

    def use_knowledge(self, broker: KnowledgeBroker) -> StandardAgent:
        raise NotImplementedError

    def use_gate(self, broker: ClassifierBroker) -> StandardAgent:
        raise NotImplementedError

    def use_judge(self, broker: VerifierBroker) -> StandardAgent:
        raise NotImplementedError

    def use_mcp(self, broker: McpBroker) -> StandardAgent:
        raise NotImplementedError

    def use_logging(self, broker: LoggingBroker) -> StandardAgent:
        raise NotImplementedError

    async def process_prompt(
            self,
            prompt: PromptRequest | str,
            *,
            session_id: str = "",
            cancellation: asyncio.Event | None = None) -> str:
        raise NotImplementedError

    async def run_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AgentOutcome:
        raise NotImplementedError

    def stream_request(
            self,
            request: PromptRequest,
            *,
            cancellation: asyncio.Event | None = None) -> AsyncIterator[AgentStreamEvent]:
        raise NotImplementedError
