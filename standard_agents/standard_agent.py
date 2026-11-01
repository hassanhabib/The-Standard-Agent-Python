# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import logging
from collections.abc import Awaitable, Callable

from standard_agents.brokers.classifiers.iclassifier_broker import IClassifierBroker
from standard_agents.brokers.classifiers.not_configured_classifier_broker import (
    NotConfiguredClassifierBroker)
from standard_agents.brokers.generators.function_generator_broker import (
    FunctionGeneratorBroker)
from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker
from standard_agents.brokers.knowledges.not_configured_knowledge_broker import (
    NotConfiguredKnowledgeBroker)
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.memories.imemory_broker import IMemoryBroker
from standard_agents.brokers.memories.not_configured_memory_broker import (
    NotConfiguredMemoryBroker)
from standard_agents.brokers.skills.file_skill_broker import FileSkillBroker
from standard_agents.brokers.skills.function_skill_broker import FunctionSkillBroker
from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.brokers.tools.tool_broker import ToolBroker
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker
from standard_agents.brokers.verifiers.not_configured_verifier_broker import (
    NotConfiguredVerifierBroker)
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.services.coordinations.runs.irun_coordination_service import (
    IRunCoordinationService)
from standard_agents.services.coordinations.runs.run_coordination_service import (
    DEFAULT_MAX_TURNS,
    RunCoordinationService)
from standard_agents.services.foundations.brains.brain_service import BrainService
from standard_agents.services.foundations.gates.gate_service import GateService
from standard_agents.services.foundations.internal_tools.internal_tool_service import (
    InternalToolService)
from standard_agents.services.foundations.judges.judge_service import JudgeService
from standard_agents.services.foundations.knowledges.knowledge_service import KnowledgeService
from standard_agents.services.foundations.memories.memory_service import MemoryService
from standard_agents.services.foundations.returns.return_service import ReturnService
from standard_agents.services.foundations.skills.skill_service import SkillService
from standard_agents.services.orchestrations.data.data_orchestration_service import (
    DataOrchestrationService)
from standard_agents.services.orchestrations.decision.decision_orchestration_service import (
    DecisionOrchestrationService)
from standard_agents.services.orchestrations.direction.direction_orchestration_service import (
    DirectionOrchestrationService)
from standard_agents.tools.itool import ITool


async def select_no_skills() -> dict[str, str]:
    return {}


# The door. Every capability is opt-in and has a sane default, so the shortest agent is a brain
# and nothing else; each line added is one capability, never a rewrite. The configuration
# methods only record what was chosen; run composes the brokers and services from it, and the
# run itself is the one service this exposer depends on.
class StandardAgent:
    def __init__(self) -> None:
        self.generator_broker: IGeneratorBroker | None = None
        self.skill_broker: ISkillBroker = FunctionSkillBroker(select_no_skills)
        self.memory_broker: IMemoryBroker = NotConfiguredMemoryBroker()
        self.knowledge_broker: IKnowledgeBroker = NotConfiguredKnowledgeBroker()
        self.classifier_broker: IClassifierBroker = NotConfiguredClassifierBroker()
        self.verifier_broker: IVerifierBroker = NotConfiguredVerifierBroker()
        self.logging_broker: ILoggingBroker = LoggingBroker(logging.getLogger("standard_agents"))
        self.agent_tools: dict[str, ITool] = {}
        self.turn_limit = DEFAULT_MAX_TURNS

    def on_brain(self, generate: Callable[[str, str], Awaitable[str]]) -> "StandardAgent":
        self.generator_broker = FunctionGeneratorBroker(generate)

        return self

    def skills(self, path: str) -> "StandardAgent":
        self.skill_broker = FileSkillBroker(path)

        return self

    # Tools accumulate: a second tool adds to the first. Names match without regard to case.
    def tool(self, tool: ITool) -> "StandardAgent":
        self.agent_tools[tool.name.lower()] = tool

        return self

    async def run(self, prompt: str) -> AgentOutcome:
        run_coordination_service = self.compose_run_coordination_service()

        return await run_coordination_service.run(prompt)

    def compose_run_coordination_service(self) -> IRunCoordinationService:
        data_orchestration_service = DataOrchestrationService(
            skill_service=SkillService(self.skill_broker, self.logging_broker),
            memory_service=MemoryService(self.memory_broker, self.logging_broker),
            knowledge_service=KnowledgeService(self.knowledge_broker, self.logging_broker),
            logging_broker=self.logging_broker,
            tool_catalog=self.render_tool_catalog())

        decision_orchestration_service = DecisionOrchestrationService(
            brain_service=BrainService(self.generator_broker, self.logging_broker),
            gate_service=GateService(self.classifier_broker, self.logging_broker),
            judge_service=JudgeService(self.verifier_broker, self.logging_broker),
            logging_broker=self.logging_broker)

        direction_orchestration_service = DirectionOrchestrationService(
            internal_tool_service=InternalToolService(
                ToolBroker(self.agent_tools),
                self.logging_broker),
            return_service=ReturnService(self.logging_broker),
            logging_broker=self.logging_broker)

        return RunCoordinationService(
            data_orchestration_service=data_orchestration_service,
            decision_orchestration_service=decision_orchestration_service,
            direction_orchestration_service=direction_orchestration_service,
            logging_broker=self.logging_broker,
            max_turns=self.turn_limit)

    # What the brain reads at {{tools}} in its skills: one line per tool, as the tool describes it.
    def render_tool_catalog(self) -> str:
        return "\n".join(
            f"- {tool.name}: {tool.description}" for tool in self.agent_tools.values())
