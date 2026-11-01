# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import importlib.resources
import logging
from pathlib import Path
from collections.abc import Awaitable, Callable, Iterable

from standard_agents.brokers.classifiers.function_classifier_broker import (
    FunctionClassifierBroker)
from standard_agents.brokers.classifiers.iclassifier_broker import IClassifierBroker
from standard_agents.brokers.classifiers.not_configured_classifier_broker import (
    NotConfiguredClassifierBroker)
from standard_agents.brokers.generators.function_generator_broker import (
    FunctionGeneratorBroker)
from standard_agents.brokers.generators.igenerator_broker import IGeneratorBroker
from standard_agents.brokers.knowledges.function_knowledge_broker import (
    FunctionKnowledgeBroker)
from standard_agents.brokers.knowledges.iknowledge_broker import IKnowledgeBroker
from standard_agents.brokers.knowledges.not_configured_knowledge_broker import (
    NotConfiguredKnowledgeBroker)
from standard_agents.brokers.loggings.function_logging_broker import FunctionLoggingBroker
from standard_agents.brokers.loggings.ilogging_broker import ILoggingBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.brokers.mcps.function_mcp_broker import FunctionMcpBroker
from standard_agents.brokers.mcps.imcp_broker import IMcpBroker
from standard_agents.brokers.mcps.not_configured_mcp_broker import NotConfiguredMcpBroker
from standard_agents.brokers.memories.file_memory_broker import FileMemoryBroker
from standard_agents.brokers.memories.function_memory_broker import FunctionMemoryBroker
from standard_agents.brokers.memories.imemory_broker import IMemoryBroker
from standard_agents.brokers.memories.not_configured_memory_broker import (
    NotConfiguredMemoryBroker)
from standard_agents.brokers.skills.file_skill_broker import FileSkillBroker
from standard_agents.brokers.skills.function_skill_broker import FunctionSkillBroker
from standard_agents.brokers.skills.iskill_broker import ISkillBroker
from standard_agents.brokers.tools.tool_broker import ToolBroker
from standard_agents.brokers.verifiers.function_verifier_broker import (
    FunctionVerifierBroker)
from standard_agents.brokers.verifiers.iverifier_broker import IVerifierBroker
from standard_agents.brokers.verifiers.not_configured_verifier_broker import (
    NotConfiguredVerifierBroker)
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.foundations.skills.skill import Skill
from standard_agents.services.coordinations.runs.irun_coordination_service import (
    IRunCoordinationService)
from standard_agents.services.coordinations.runs.run_coordination_service import (
    DEFAULT_MAX_TURNS,
    RunCoordinationService)
from standard_agents.services.foundations.brains.brain_service import BrainService
from standard_agents.services.foundations.external_tools.external_tool_service import (
    ExternalToolService)
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
from standard_agents.standard_agent_validations import validate_brain, validate_turns
from standard_agents.tools.itool import ITool


async def select_no_skills() -> list[Skill]:
    return []


# The built-in guardian policies and contracts are Data shipped with the package (SPEC.md 4.5).
def read_guardian_prompt(name: str) -> str:
    guardian_prompts = importlib.resources.files("standard_agents.prompts.guardians")

    return guardian_prompts.joinpath(name).read_text(encoding="utf-8")


def read_data(path: str | None) -> str:
    if path is None:
        return ""

    return Path(path).read_text(encoding="utf-8")


# Constitution, then policy, then contract; an absent layer contributes nothing.
def compose_rubric(constitution: str, policy: str, contract: str) -> str:
    layers = [layer.strip() for layer in (constitution, policy, contract)]

    return "\n\n".join(layer for layer in layers if layer != "")


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
        self.mcp_broker: IMcpBroker = NotConfiguredMcpBroker()
        self.logging_broker: ILoggingBroker = LoggingBroker(logging.getLogger("standard_agents"))
        self.agent_tools: dict[str, ITool] = {}
        self.turn_limit = DEFAULT_MAX_TURNS
        self.constitution_path: str | None = None
        self.consumption_path: str | None = None

    def on_brain(self, generate: Callable[[str, str], Awaitable[str]]) -> "StandardAgent":
        self.generator_broker = FunctionGeneratorBroker(generate)

        return self

    def skills(self, path: str) -> "StandardAgent":
        self.skill_broker = FileSkillBroker(path)

        return self

    def on_skills(self, select_skills: Callable[[], Awaitable[list[Skill]]]) -> "StandardAgent":
        self.skill_broker = FunctionSkillBroker(select_skills)

        return self

    def on_memory(self, select_all_memories: Callable[[], Awaitable[list[str]]]) -> "StandardAgent":
        self.memory_broker = FunctionMemoryBroker(select_all_memories)

        return self

    def memory(self, path: str) -> "StandardAgent":
        self.memory_broker = FileMemoryBroker(path)

        return self

    def on_knowledge(
        self,
        select_knowledge: Callable[[str], Awaitable[list[str]]]) -> "StandardAgent":

        self.knowledge_broker = FunctionKnowledgeBroker(select_knowledge)

        return self

    def on_gate(self, screen: Callable[[str, str], Awaitable[str]]) -> "StandardAgent":
        self.classifier_broker = FunctionClassifierBroker(screen)

        return self

    def on_judge(
        self,
        evaluate: Callable[[str, str, str], Awaitable[str]]) -> "StandardAgent":

        self.verifier_broker = FunctionVerifierBroker(evaluate)

        return self

    # External: a provider's broker. A local open-weight model (PyTorch, llama.cpp) is composed
    # here, as an IGeneratorBroker of its own.
    def use_generator(self, generator_broker: IGeneratorBroker) -> "StandardAgent":
        self.generator_broker = generator_broker

        return self

    def use_skills(self, skill_broker: ISkillBroker) -> "StandardAgent":
        self.skill_broker = skill_broker

        return self

    def use_memory(self, memory_broker: IMemoryBroker) -> "StandardAgent":
        self.memory_broker = memory_broker

        return self

    def use_knowledge(self, knowledge_broker: IKnowledgeBroker) -> "StandardAgent":
        self.knowledge_broker = knowledge_broker

        return self

    def use_gate(self, classifier_broker: IClassifierBroker) -> "StandardAgent":
        self.classifier_broker = classifier_broker

        return self

    def use_judge(self, verifier_broker: IVerifierBroker) -> "StandardAgent":
        self.verifier_broker = verifier_broker

        return self

    # Remote tools: where an act on a name the agent does not own is sent (SPEC.md 4.3). External
    # takes the host's broker; Custom takes a function that answers each call.
    def use_mcp(self, mcp_broker: IMcpBroker) -> "StandardAgent":
        self.mcp_broker = mcp_broker

        return self

    def on_mcp(self, call: Callable[[str, str], Awaitable[str]]) -> "StandardAgent":
        self.mcp_broker = FunctionMcpBroker(call)

        return self

    # Tools accumulate: a second tool adds to the first. Names match without regard to case.
    def tool(self, tool: ITool) -> "StandardAgent":
        self.agent_tools[tool.name.lower()] = tool

        return self

    def tools(self, tools: Iterable[ITool]) -> "StandardAgent":
        for tool in tools:
            self.tool(tool)

        return self

    # The turn-by-turn trace, written to a file of the host's choosing. The logger is named after
    # the path, so two agents tracing to two files never write into each other's.
    # One law above both guardians: prepended to the Gate's rubric and the Judge's alike.
    def constitution(self, path: str) -> "StandardAgent":
        self.constitution_path = path

        return self

    # A consumption skill replaces the built-in policy in both guardians. The contract, the
    # output the brokers parse, stays: a replacement policy can never break the parsing.
    def consumption(self, path: str) -> "StandardAgent":
        self.consumption_path = path

        return self

    def log_to(self, path: str) -> "StandardAgent":
        logger = logging.getLogger(f"standard_agents.trace.{path}")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not logger.handlers:
            file_handler = logging.FileHandler(path, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(file_handler)

        self.logging_broker = LoggingBroker(logger)

        return self

    def on_log(self, write: Callable[[str], Awaitable[None]]) -> "StandardAgent":
        self.logging_broker = FunctionLoggingBroker(write)

        return self

    def use_logging(self, logging_broker: ILoggingBroker) -> "StandardAgent":
        self.logging_broker = logging_broker

        return self

    # A bound on how many Recall, Think, Act turns one prompt may take.
    def max_turns(self, turns: int) -> "StandardAgent":
        validate_turns(turns)
        self.turn_limit = turns

        return self

    async def run(self, prompt: str) -> AgentOutcome:
        validate_brain(self.generator_broker)
        run_coordination_service = self.compose_run_coordination_service()

        return await run_coordination_service.run(prompt)

    # The one-line door: a prompt in, the answer's text out. Use run when how the run ended
    # matters, because a refusal and an answer read alike as text.
    async def process_prompt(self, prompt: str) -> str:
        outcome = await self.run(prompt)

        return outcome.result

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
            logging_broker=self.logging_broker,
            gate_rubric=self.compose_guardian_rubric("gate"),
            judge_rubric=self.compose_guardian_rubric("judge"))

        direction_orchestration_service = DirectionOrchestrationService(
            internal_tool_service=InternalToolService(
                ToolBroker(self.agent_tools),
                self.logging_broker),
            external_tool_service=ExternalToolService(self.mcp_broker, self.logging_broker),
            return_service=ReturnService(self.logging_broker),
            logging_broker=self.logging_broker)

        return RunCoordinationService(
            data_orchestration_service=data_orchestration_service,
            decision_orchestration_service=decision_orchestration_service,
            direction_orchestration_service=direction_orchestration_service,
            logging_broker=self.logging_broker,
            max_turns=self.turn_limit)

    def compose_guardian_rubric(self, guardian: str) -> str:
        constitution = read_data(self.constitution_path)
        policy = read_data(self.consumption_path) or read_guardian_prompt(f"{guardian}.policy.md")
        contract = read_guardian_prompt(f"{guardian}.contract.md")

        return compose_rubric(constitution, policy, contract)

    # What the brain reads at {{tools}} in its skills: one line per tool, as the tool describes it.
    # Only a described tool is advertised (SPEC.md 6.1); an undescribed one stays callable.
    def render_tool_catalog(self) -> str:
        return "\n".join(
            f"- {tool.name}: {tool.description}"
            for tool in self.agent_tools.values()
            if tool.description.strip() != "")
