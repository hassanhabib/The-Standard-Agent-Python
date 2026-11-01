# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import aclosing

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.foundations.gates.skill_conflict import SkillConflict
from standard_agents.models.foundations.judges.judgement import Judgement

from standard_agents.models.foundations.gates.skill_directive import SkillDirective
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus

from standard_agents.services.coordinations.decision.decision_stream import DecisionStream
from standard_agents.services.orchestrations.decision.guardians.guardian_orchestration_service \
    import GuardianOrchestrationService
from standard_agents.services.orchestrations.decision.inferences.inference_orchestration_service \
    import InferenceOrchestrationService

# A guardian that emits one of these is trying to answer rather than classify.
_FINAL_PREFIX = "FINAL:"
_SAY_PREFIX = "SAY:"


_REFUSE_VERDICT = "refuse"

_ROUTE_VERDICT = "route"
_REFUSE_DIRECTION = "Refuse"
_RETURN_RESPONSE_DIRECTION = "ReturnResponse"
_AWAIT_INPUT_DIRECTION = "AwaitInput"
_CONFLICT_PREFIX = "CONFLICT:"
_CONFLICT_OPTION_SEPARATOR = "||"
_CONFLICT_LABEL_SEPARATOR = "|"
_PREFERENCE_PREFIX = "SKILL_PREFERENCE::"

_MINIMUM_ACCEPTABLE_SCORE = 0.3


class DecisionCoordinationService:
    """The Decision nature: two regions, and the judgment between them.

    Inference asks the model and reads its answer; Guardian screens what goes in and scores what
    comes out. The loop that runs them (screen, resolve a skill conflict, decide, judge, revise)
    belongs to neither, because every step of it depends on the other region's result.
    """

    def __init__(
            self,
            *,
            inference_service: InferenceOrchestrationService,
            guardian_service: GuardianOrchestrationService,
            logging_broker: LoggingBroker,
            contract_schema: str | None = None) -> None:

        self.inference_service = inference_service
        self.guardian_service = guardian_service
        self.logging_broker = logging_broker

        # The shape every answer is held to, or empty. Configuration rather than a collaborator:
        # it is a string the host chose, and the foundation treats an empty one as no check.
        self.contract_schema = contract_schema if contract_schema is not None else ""

    async def screen(self, text: str) -> str:
        raise NotImplementedError

    async def think(self, context: AgentContext) -> AgentContext:
        context = _fresh_of_last_turn(context)
        verdict = await self.guardian_service.screen(context.prompt)
        refused = await self._refused_by_gate(context, verdict)

        if refused is not None:
            return refused

        context = await self._routed_by_gate(context, verdict)
        resolved_context, is_terminal = await self._resolve_skill_conflict(context)

        if is_terminal:
            return resolved_context

        context = resolved_context
        decided = await self.inference_service.decide(context)

        if decided.direction_type != _RETURN_RESPONSE_DIRECTION:
            return decided

        # An empty answer is nothing to judge: a judge would (rightly) reject blank input, which
        # would crash the turn. Return it as it is; the brain simply had nothing to say.
        if not decided.payload:
            return decided

        revising = await self._rejected_by_guardians(context, decided)

        if revising is not None:
            return revising

        return decided

    def think_stream(self, context: AgentContext) -> DecisionStream:
        """The streamed door.

        Draft segments are yielded as they arrive; the decided context is the stream's result
        once the enumeration completes.
        """
        return DecisionStream(
            lambda set_result: self._stream_think(context, set_result))

    async def _stream_think(
            self,
            context: AgentContext,
            set_result: Callable[[AgentContext], None]) -> AsyncIterator[AgentStreamEvent]:

        verdict = await self.guardian_service.screen(context.prompt)
        refused = await self._refused_by_gate(context, verdict)

        if refused is not None:
            set_result(refused)

            yield AgentStreamEvent(AgentStreamEventType.STATUS, "gate refused the request")

            return

        context = await self._routed_by_gate(context, verdict)
        decided = context

        def set_decided(interpreted: AgentContext) -> None:
            nonlocal decided
            decided = interpreted

        drafting = self.inference_service.decide_stream(context, set_decided)

        async with aclosing(drafting):
            async for segment in drafting:
                yield segment

        set_result(decided)

    async def _rejected_by_guardians(
            self,
            context: AgentContext,
            decided: AgentContext) -> AgentContext | None:
        """One verdict sequence for every final draft, whichever door it arrived through.

        Returns the revising context, or None when the draft stands.
        """
        judgement = await self.guardian_service.evaluate(
            task=context.prompt,
            candidate=decided.payload)

        if judgement.score < _MINIMUM_ACCEPTABLE_SCORE:
            return dataclasses.replace(
                context,
                observations=(
                    *context.observations,
                    _revision_feedback(judgement, decided.payload)),
                status=AgentStatus.REVISING)

        return None

    async def _refused_by_gate(self, context: AgentContext, verdict: str) -> AgentContext | None:
        """The Gate's refusal, handled once for both doors, or None when the Gate did not refuse."""
        if not _is_refusal(verdict):
            return None

        await self.logging_broker.log_payload("Decision", "Gate REFUSE", verdict, detail=False)

        return dataclasses.replace(

            context,
            intent=_REFUSE_DIRECTION,
            direction_type=_REFUSE_DIRECTION,
            raw_reply=verdict)

    async def _routed_by_gate(self, context: AgentContext, verdict: str) -> AgentContext:
        """Everything else the Gate's verdict carries, handled once for both doors.

        A route label rides through as data. A verdict is only ever read as a classification,
        so a Gate that emits FINAL: falls through to the Brain and its text never becomes the
        answer, but the overreach is recorded (SPEC.md 7.6): a guardian trying to answer is
        exactly the event a security review needs to see.
        """
        if _is_guardian_overreach(verdict):
            await self._log_guardian_overreach()

        await self.logging_broker.log_payload("Decision", "Gate ACCEPT", verdict, detail=False)

        return (

            dataclasses.replace(context, route=_extract_route_label(verdict))
            if _is_route(verdict)
            else context)

    async def _log_guardian_overreach(self) -> None:
        await self.logging_broker.log_process(
            "Decision",
            "Gate overreach \u2014 a guardian tried to answer or act instead of classifying; "
            "neutralized and passed to the Brain "
            "(Invariant 6: a guardian is never the Brain)")

    async def _resolve_skill_conflict(
            self,
            context: AgentContext) -> tuple[AgentContext, bool]:

        verdict = await self.guardian_service.detect_conflict(context.system_prompt)
        conflict = _parse_conflict(verdict)

        if conflict is None:
            return context, False

        key = _conflict_key(conflict)
        preferred = _find_preference(context.observations, key)

        if preferred is not None:
            return context, False

        chosen = _match_choice(context.prompt, conflict)

        if chosen is not None:
            learned_context = dataclasses.replace(
                context,
                direction_type=_RETURN_RESPONSE_DIRECTION,
                payload=f"Understood \u2014 I'll follow '{chosen.skill}' for that from now on.",
                remember=f"{_PREFERENCE_PREFIX}{key}::{chosen.skill}")

            return learned_context, True

        question_context = dataclasses.replace(
            context,
            direction_type=_AWAIT_INPUT_DIRECTION,
            payload=_build_clarification_question(conflict))

        return question_context, True


def _revision_feedback(judgement: Judgement, draft: str) -> str:
    if not judgement.reason:
        return f"A previous draft was rejected on review: {draft}"

    return (
        f"A previous draft was rejected on review \u2014 {judgement.reason}. "
        f"The draft was: {draft}")



def _fresh_of_last_turn(context: AgentContext) -> AgentContext:
    """This turn's outputs, cleared of the last turn's.

    Narration is a turn's output: a refusal or conflict path bypasses interpretation, and last
    turn's prose leaking out would be voiced over this turn.
    """
    return dataclasses.replace(context, narration="")


def _conflict_key(
conflict: SkillConflict) -> str:
    return "|".join(option.skill.strip().lower() for option in conflict.options)


def _find_preference(observations: Sequence[str], key: str) -> str | None:
    prefix = f"{_PREFERENCE_PREFIX}{key}::"

    record = next(
        (observation for observation in observations if observation.startswith(prefix)),
        None)

    return record[len(prefix):] if record is not None else None


def _match_choice(prompt: str, conflict: SkillConflict) -> SkillDirective | None:
    return next((option for option in conflict.options if option.skill in prompt), None)


def _parse_conflict(verdict: str | None) -> SkillConflict | None:
    if verdict is None or not verdict.startswith(_CONFLICT_PREFIX):
        return None

    options = tuple(
        _to_directive(option)
        for option in verdict[len(_CONFLICT_PREFIX):].split(_CONFLICT_OPTION_SEPARATOR))

    return SkillConflict(options)


def _to_directive(option: str) -> SkillDirective:
    skill, instruction = option.split(_CONFLICT_LABEL_SEPARATOR, 1)

    return SkillDirective(skill.strip(), instruction.strip())


def _build_clarification_question(conflict: SkillConflict) -> str:
    choices = " or ".join(option.skill for option in conflict.options)

    return f"Your skills give conflicting instructions. Should I follow: {choices}?"


def _is_refusal(verdict: str) -> bool:
    return _starts_with_ordinal_ignore_case(verdict, _REFUSE_VERDICT)


def _is_route(verdict: str) -> bool:
    return verdict.startswith(_ROUTE_VERDICT)


def _is_guardian_overreach(verdict: str) -> bool:
    """SAY: belongs here too: narration is a voice, and a guardian is never a voice."""
    return _FINAL_PREFIX in verdict or _SAY_PREFIX in verdict


def _extract_route_label(verdict: str) -> str:
    return verdict[len(_ROUTE_VERDICT):].lstrip(": ")


def _starts_with_ordinal_ignore_case(text: str, prefix: str) -> bool:
    """string.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)."""
    if len(text) < len(prefix):
        return False

    return _equals_ordinal_ignore_case(text[:len(prefix)], prefix)


def _equals_ordinal_ignore_case(text: str, other: str) -> bool:
    """string.Equals(other, StringComparison.OrdinalIgnoreCase)."""
    return _fold_ordinal_ignore_case(text) == _fold_ordinal_ignore_case(other)


def _fold_ordinal_ignore_case(value: str) -> str:
    """Fold a string the way .NET's StringComparison.OrdinalIgnoreCase compares it.

    Characters compare by their simple uppercase mapping. Python's str.upper() applies full
    mappings (U+00DF becomes "SS"), so each character is uppercased on its own and kept as it
    is when its mapping expands.
    """
    folded: list[str] = []

    for character in value:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)
