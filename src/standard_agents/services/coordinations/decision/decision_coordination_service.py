# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
import re
import unicodedata
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import aclosing, asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainDependencyValidationException,
    BrainServiceException,
    BrainValidationException)
from standard_agents.models.foundations.contracts.contract_verdict import ContractVerdict
from standard_agents.models.foundations.gates.exceptions import (
    GateDependencyException,
    GateDependencyValidationException,
    GateServiceException,
    GateValidationException)
from standard_agents.models.foundations.gates.skill_conflict import SkillConflict
from standard_agents.models.foundations.gates.skill_directive import SkillDirective
from standard_agents.models.foundations.judges.exceptions import (
    JudgeDependencyException,
    JudgeDependencyValidationException,
    JudgeServiceException,
    JudgeValidationException)
from standard_agents.models.foundations.judges.judgement import Judgement
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    AgentOrchestrationValidationException,
    FailedAgentOrchestrationServiceException,
    NullAgentContextException)
from standard_agents.services.coordinations.decision.decision_stream import DecisionStream
from standard_agents.services.orchestrations.decision.guardians.guardian_orchestration_service \
    import GuardianOrchestrationService
from standard_agents.services.orchestrations.decision.inferences.inference_orchestration_service \
    import InferenceOrchestrationService
from xeptions import Xeption

# A guardian that emits one of these is trying to answer rather than classify. Invariant 6 holds
# structurally either way (a verdict is only ever read as a classification), but the attempt is
# recorded, because it is exactly the event a security review needs to see.
_ACTION_PREFIX = "ACTION:"
_TOOL_PREFIX = "TOOL:"
_FINAL_PREFIX = "FINAL:"
_TRANSFER_PREFIX = "TRANSFER:"
_SAY_PREFIX = "SAY:"

_REFUSE_VERDICT = "refuse"
_ROUTE_VERDICT = "route"
_REFUSE_DIRECTION = "Refuse"
_RETURN_RESPONSE_DIRECTION = "ReturnResponse"
_RESPOND_INTENT = "Respond"
_AWAIT_INPUT_DIRECTION = "AwaitInput"
_CONFLICT_PREFIX = "CONFLICT:"
_CONFLICT_OPTION_SEPARATOR = "||"
_CONFLICT_LABEL_SEPARATOR = "|"
_PREFERENCE_PREFIX = "SKILL_PREFERENCE::"
_REFUSAL_MESSAGE = "I'm not able to help with that."

_MINIMUM_ACCEPTABLE_SCORE = 0.3

# What string.ReplaceLineEndings recognizes as a line ending: CRLF, CR, LF, FF, NEL, LS and PS.
_LINE_ENDINGS = re.compile(r"\r\n|[\r\n\f\x85\u2028\u2029]")


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
        """Screens a piece of untrusted text and returns the Gate's verdict.

        Decision owns the guardians, so anything that needs screening asks Decision for it
        rather than reaching into Decision's foundations. The loop screens what a tool returned
        before it can become an observation: an instruction arriving inside data is the same
        category of thing as an instruction arriving in a prompt.
        """
        return await self.guardian_service.screen(text)

    async def think(self, context: AgentContext) -> AgentContext:
        """Screens, resolves a skill conflict, decides, and judges the draft (SPEC.md 7.6)."""
        async with _handling_exceptions(self.logging_broker):
            _validate_context(context)

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

            if not _equals_ordinal_ignore_case(decided.direction_type, _RETURN_RESPONSE_DIRECTION):
                return decided

            # An empty answer is nothing to judge: a judge would (rightly) reject blank input,
            # which would crash the turn. Return it as it is; the brain had nothing to say.
            if _is_blank(decided.payload):
                return decided

            rejected = await self._rejected_by_guardians(context, decided)

            if rejected is not None:
                revising, _ = rejected

                return revising

            # Every guardian has passed, so this draft is an answer. It cannot be carrying a
            # stale REVISING: both doors clear the last turn's verdict on entry, so REVISING only
            # ever leaves this service when a guardian set it this turn.
            return decided

    def think_stream(self, context: AgentContext) -> DecisionStream:
        """The streamed door, mapped like the batched one.

        Draft segments are yielded as they arrive; the decided context is the stream's result
        once the enumeration completes. A fault surfaces in the same family think produces,
        whichever door the prompt entered by.
        """
        return DecisionStream(
            lambda set_result: self._mapped_stream(self._stream_think(context, set_result)))

    async def _mapped_stream(
            self,
            stream: AsyncIterator[AgentStreamEvent]) -> AsyncIterator[AgentStreamEvent]:
        """Advances the stream inside the mapping and yields outside it.

        The failure points are the awaits, and a generator cannot wrap its yields in the
        mapping.
        """
        async with aclosing(stream):
            while True:
                try:
                    segment = await anext(stream)
                except StopAsyncIteration:
                    break
                except Exception as exception:
                    raise await _mapped_and_logged(self.logging_broker, exception)

                yield segment

    async def _stream_think(
            self,
            context: AgentContext,
            set_result: Callable[[AgentContext], None]) -> AsyncIterator[AgentStreamEvent]:

        context = _fresh_of_last_turn(context)
        verdict = await self.guardian_service.screen(context.prompt)
        refused = await self._refused_by_gate(context, verdict)

        if refused is not None:
            set_result(refused)

            yield AgentStreamEvent(AgentStreamEventType.STATUS, "gate refused the request")

            return

        context = await self._routed_by_gate(context, verdict)
        resolved_context, is_terminal = await self._resolve_skill_conflict(context)

        if is_terminal:
            set_result(resolved_context)

            yield AgentStreamEvent(
                AgentStreamEventType.STATUS,
                "skills conflict; asking for clarification"
                if resolved_context.direction_type == _AWAIT_INPUT_DIRECTION
                else "learned your skill preference")

            return

        context = resolved_context
        decided = context

        def set_decided(interpreted: AgentContext) -> None:
            nonlocal decided
            decided = interpreted

        drafting = self.inference_service.decide_stream(context, set_decided)

        async with aclosing(drafting):
            async for segment in drafting:
                yield segment

        if not _equals_ordinal_ignore_case(decided.direction_type, _RETURN_RESPONSE_DIRECTION):
            set_result(decided)

            yield AgentStreamEvent(
                AgentStreamEventType.STATUS, f"using tool: {decided.direction_type}")

            return

        if _is_blank(decided.payload):
            set_result(decided)

            return

        # The identical verdict sequence the batched door runs: one copy, so neither door can
        # hold a guardian the other lacks.
        rejected = await self._rejected_by_guardians(context, decided)

        if rejected is not None:
            revising, status_note = rejected
            set_result(revising)

            yield AgentStreamEvent(AgentStreamEventType.STATUS, status_note)

            return

        # The shape check, exactly as the batched path runs it. The streamed loop used to skip
        # it, which made streaming the way to receive an answer the Contract would have refused,
        # and a control a caller can step around by changing method is not a control
        # (SPEC.md 7.6).
        shape = await self.guardian_service.check_shape(
            decided.payload,
            self._contract_schema_for(context))

        if not shape.satisfied:
            await self.logging_broker.log_process(
                "Decision", f"Contract → REJECTED: {shape.reason}")

            set_result(dataclasses.replace(
                context,
                observations=(*context.observations, _shape_feedback(shape, decided.payload)),
                status=AgentStatus.REVISING))

            yield AgentStreamEvent(
                AgentStreamEventType.STATUS, "contract rejected the draft; revising")

            return

        set_result(
            dataclasses.replace(decided, status=AgentStatus.WORKING)
            if decided.status is AgentStatus.REVISING
            else decided)

    async def _rejected_by_guardians(
            self,
            context: AgentContext,
            decided: AgentContext) -> tuple[AgentContext, str] | None:
        """One verdict sequence for every final draft, whichever door it arrived through.

        The Judge on the merits, then the Contract on the shape, in that order, deliberately: a
        draft that is wrong on the merits should be told that, not told its punctuation is off,
        and two rejections in one turn would spend a turn teaching the model the lesser of them
        (SPEC.md 7.6). This is the only copy, and the logging lives here too, so the two doors
        cannot drift in what the trace shows.

        Returns the revising context carrying the rejection feedback and a status note for the
        stream to narrate, or None when the draft stands.
        """
        judgement = await self.guardian_service.evaluate(
            task=context.prompt,
            candidate=decided.payload)

        judge_outcome = (
            f"REJECT: {judgement.reason}".rstrip(": ")
            if judgement.score < _MINIMUM_ACCEPTABLE_SCORE
            else "ACCEPT")

        await self.logging_broker.log_process(
            "Decision", f"Judge → scored {judgement.score:.2f} → {judge_outcome}")

        if judgement.score < _MINIMUM_ACCEPTABLE_SCORE:
            revising = dataclasses.replace(
                context,
                observations=(
                    *context.observations,
                    _revision_feedback(judgement, decided.payload)),
                status=AgentStatus.REVISING,

                # The rejected draft still cost a model call, and the loop bills the turn from
                # the context this method hands back: a revision loop the budget cannot see is
                # exactly where a run burns tokens fastest (SPEC.md 4.10).
                prompt_tokens=decided.prompt_tokens,
                completion_tokens=decided.completion_tokens,
                usage_is_estimated=decided.usage_is_estimated)

            return revising, "judge rejected the draft; revising"

        shape = await self.guardian_service.check_shape(
            decided.payload,
            self._contract_schema_for(context))

        if not shape.satisfied:
            # A rejection the trace does not explain is a turn nobody can account for.
            await self.logging_broker.log_process(
                "Decision", f"Contract → REJECTED: {shape.reason}")

            revising = dataclasses.replace(
                context,
                observations=(*context.observations, _shape_feedback(shape, decided.payload)),
                status=AgentStatus.REVISING,
                prompt_tokens=decided.prompt_tokens,
                completion_tokens=decided.completion_tokens,
                usage_is_estimated=decided.usage_is_estimated)

            return revising, "contract rejected the draft; revising"

        return None

    def _contract_schema_for(self, context: AgentContext) -> str:
        """The schema that survived precedence, riding the context from the boundary.

        The configured schema remains only for a context built by hand, where it says exactly
        what the boundary would have seeded (docs/per-request-inference.md 4.1).
        """
        response_schema_json = (
            context.inference.response_schema_json if context.inference is not None else None)

        return (
            response_schema_json
            if response_schema_json is not None
            else self.contract_schema)

    async def _refused_by_gate(self, context: AgentContext, verdict: str) -> AgentContext | None:
        """The Gate's refusal, handled once for both doors, or None when the Gate did not refuse.

        The verdict never becomes the answer: it is recorded as the raw reply and the reply is
        the fixed refusal message. Logged here so both doors narrate the same line.
        """
        if not _is_refusal(verdict):
            return None

        await self.logging_broker.log_payload(
            "Decision", "Gate REFUSE", _trim(_replace_line_endings(verdict)), detail=False)

        return dataclasses.replace(
            context,
            intent=_REFUSE_DIRECTION,
            direction_type=_REFUSE_DIRECTION,
            payload=_REFUSAL_MESSAGE,
            raw_reply=verdict)

    async def _routed_by_gate(self, context: AgentContext, verdict: str) -> AgentContext:
        """Everything else the Gate's verdict carries, handled once for both doors.

        A verdict is only ever read as a classification, so a Gate that emits FINAL: or ACTION:
        falls through to the Brain and its text never becomes the answer, but the overreach is
        recorded (SPEC.md 7.6): a guardian trying to answer is exactly the event a security
        review needs to see. A route label rides through as data, on both doors, so a routing
        Gate steers skill selection for batched and streaming callers alike.
        """
        if _is_guardian_overreach(verdict):
            await self._log_guardian_overreach()

        await self.logging_broker.log_payload(
            "Decision",
            "Gate ROUTE" if _is_route(verdict) else "Gate ACCEPT",
            _trim(_replace_line_endings(verdict)),
            detail=False)

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

        if _is_blank(context.system_prompt):
            return context, False

        verdict = await self.guardian_service.detect_conflict(context.system_prompt)
        conflict = _parse_conflict(verdict)

        if conflict is None:
            return context, False

        key = _conflict_key(conflict)
        preferred = _find_preference(context.observations, key)

        if preferred is not None:
            resolved_context = dataclasses.replace(
                context,
                observations=(
                    *context.observations,
                    f"The user resolved a skill conflict in favor of '{preferred}'; "
                    "follow it and ignore the conflicting instruction."))

            return resolved_context, False

        chosen = _match_choice(context.prompt, conflict)

        if chosen is not None:
            learned_context = dataclasses.replace(
                context,
                intent=_RESPOND_INTENT,
                direction_type=_RETURN_RESPONSE_DIRECTION,
                payload=f"Understood \u2014 I'll follow '{chosen.skill}' for that from now on.",
                remember=f"{_PREFERENCE_PREFIX}{key}::{chosen.skill}",
                raw_reply=verdict)

            return learned_context, True

        question_context = dataclasses.replace(
            context,
            intent=_AWAIT_INPUT_DIRECTION,
            direction_type=_AWAIT_INPUT_DIRECTION,
            payload=_build_clarification_question(conflict),
            raw_reply=verdict)

        return question_context, True


def _shape_feedback(verdict: ContractVerdict, draft: str) -> str:
    """Aimed, not scolding.

    A revision the model cannot act on is a turn spent for nothing, so the validator's complaint
    is repeated verbatim rather than summarised into "invalid".
    """
    return (
        f"A previous draft was rejected because {verdict.reason}. Reply with JSON matching the "
        f"required shape and nothing else. The draft was: {draft}")


def _revision_feedback(judgement: Judgement, draft: str) -> str:
    if _is_blank(judgement.reason):
        return f"A previous draft was rejected on review: {draft}"

    return (
        f"A previous draft was rejected on review \u2014 {judgement.reason}. "
        f"The draft was: {draft}")


def _fresh_of_last_turn(context: AgentContext) -> AgentContext:
    """This turn's outputs, cleared of the last turn's, once, at both doors.

    Status and cost are Decision's outputs: what this turn's guardians concluded, and what this
    turn's model calls consumed. The incoming context may still carry the previous turn's,
    because interpretation builds every decided context from the one it was given, and either
    leaking back out is a shipped defect: a stale REVISING made the loop skip Direction and
    spin, and a stale token count made the measurement read "the provider already reported" on
    every turn after the first. Narration is a turn's output too: a refusal or conflict path
    bypasses interpretation, and last turn's prose leaking out would be voiced over this turn.
    """
    return dataclasses.replace(
        context,
        status=(
            AgentStatus.WORKING
            if context.status is AgentStatus.REVISING
            else context.status),
        prompt_tokens=0,
        completion_tokens=0,
        usage_is_estimated=False,
        narration="")


def _conflict_key(conflict: SkillConflict) -> str:
    return "|".join(sorted(
        _to_lower_invariant(_trim(option.skill)) for option in conflict.options))


def _find_preference(observations: Sequence[str], key: str) -> str | None:
    prefix = f"{_PREFERENCE_PREFIX}{key}::"

    record = next(
        (
            observation
            for observation in reversed(observations)
            if _starts_with_ordinal_ignore_case(observation, prefix)),
        None)

    return record[len(prefix):] if record is not None else None


def _match_choice(prompt: str, conflict: SkillConflict) -> SkillDirective | None:
    return next(
        (
            option
            for option in conflict.options
            if _contains_ordinal_ignore_case(prompt, option.skill)),
        None)


def _parse_conflict(verdict: str | None) -> SkillConflict | None:
    """The options of a CONFLICT: verdict, or None when it is not a conflict between two or more.

    A verdict that never arrived reads as no conflict.
    """
    trimmed = _trim(verdict if verdict is not None else "")

    if not _starts_with_ordinal_ignore_case(trimmed, _CONFLICT_PREFIX):
        return None

    options = tuple(
        _to_directive(option)
        for option in _split_trimmed(trimmed[len(_CONFLICT_PREFIX):], _CONFLICT_OPTION_SEPARATOR)
        if option)

    return SkillConflict(options) if len(options) >= 2 else None


def _to_directive(option: str) -> SkillDirective:
    parts = [_trim(part) for part in option.split(_CONFLICT_LABEL_SEPARATOR, 1)]

    return (
        SkillDirective(parts[0], parts[1])
        if len(parts) == 2
        else SkillDirective(option, option))


def _build_clarification_question(conflict: SkillConflict) -> str:
    choices = " or ".join(option.skill for option in conflict.options)

    return f"Your skills give conflicting instructions. Should I follow: {choices}?"


def _is_refusal(verdict: str) -> bool:
    return _starts_with_ordinal_ignore_case(_trim_start(verdict), _REFUSE_VERDICT)


def _is_route(verdict: str) -> bool:
    return _starts_with_ordinal_ignore_case(_trim_start(verdict), _ROUTE_VERDICT)


def _is_guardian_overreach(verdict: str) -> bool:
    """SAY: belongs here too: narration is a voice, and a guardian is never a voice."""
    return any(
        _contains_ordinal_ignore_case(verdict, prefix)
        for prefix in (_FINAL_PREFIX, _ACTION_PREFIX, _TOOL_PREFIX, _TRANSFER_PREFIX, _SAY_PREFIX))


def _extract_route_label(verdict: str) -> str:
    label = _trim_start(verdict)[len(_ROUTE_VERDICT):]

    return _trim(_replace_line_endings(label.lstrip(": ")))


def _split_trimmed(text: str, separator: str) -> list[str]:
    """text.Split(separator, StringSplitOptions.TrimEntries)."""
    return [_trim(part) for part in text.split(separator)]


def _replace_line_endings(text: str) -> str:
    """string.ReplaceLineEndings(" ")."""
    return _LINE_ENDINGS.sub(" ", text)


def _is_whitespace(character: str) -> bool:
    """char.IsWhiteSpace, which string.Trim and string.IsNullOrWhiteSpace use.

    Not str.isspace: .NET does not count U+001C..U+001F as white space.
    """
    return (
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp"))


def _is_blank(text: str) -> bool:
    """string.IsNullOrWhiteSpace, over the .NET white-space set."""
    return all(_is_whitespace(character) for character in text)


def _trim_start(text: str) -> str:
    """string.TrimStart, over the .NET white-space set."""
    start = 0

    while start < len(text) and _is_whitespace(text[start]):
        start += 1

    return text[start:]


def _trim(text: str) -> str:
    """string.Trim, over the .NET white-space set."""
    trimmed = _trim_start(text)
    end = len(trimmed)

    while end > 0 and _is_whitespace(trimmed[end - 1]):
        end -= 1

    return trimmed[:end]


def _to_lower_invariant(text: str) -> str:
    """string.ToLowerInvariant: each character by its own lowercase mapping.

    Python's str.lower() applies full mappings (U+0130 becomes two characters), so a character
    whose mapping expands is kept as it is.
    """
    lowered: list[str] = []

    for character in text:
        candidate = character.lower()
        lowered.append(candidate if len(candidate) == 1 else character)

    return "".join(lowered)


def _contains_ordinal_ignore_case(text: str, value: str) -> bool:
    """string.Contains(value, StringComparison.OrdinalIgnoreCase)."""
    return _fold_ordinal_ignore_case(value) in _fold_ordinal_ignore_case(text)


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


def _validate_context(context: AgentContext | None) -> None:
    if context is None:
        raise NullAgentContextException(message="Agent context is null.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except NullAgentContextException as null_agent_context_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, null_agent_context_exception)

    # The regions localize their own foundations' failures, so what arrives here is already in
    # this family and already logged. Wrapping it again would nest and log the same failure
    # twice.
    except (
            AgentOrchestrationDependencyValidationException,
            AgentOrchestrationDependencyException,
            AgentOrchestrationServiceException):

        raise
    except (
            GateValidationException,
            GateDependencyValidationException,
            BrainValidationException,
            BrainDependencyValidationException,
            JudgeValidationException,
            JudgeDependencyValidationException) as validation_exception:

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, _local_exception(validation_exception))
    except (
            GateDependencyException,
            GateServiceException,
            BrainDependencyException,
            BrainServiceException,
            JudgeDependencyException,
            JudgeServiceException) as dependency_exception:

        raise await _create_and_log_dependency_exception(
            logging_broker, _local_exception(dependency_exception))
    except Exception as exception:
        failed_agent_orchestration_service_exception = FailedAgentOrchestrationServiceException(
            message="Failed agent orchestration service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_agent_orchestration_service_exception)


async def _mapped_and_logged(logging_broker: LoggingBroker, exception: Exception) -> Exception:
    """The mapping _handling_exceptions applies, on an exception already caught.

    What the streamed door needs, since a generator cannot wrap its yields in the mapping.
    Implemented by raising through the mapping itself, so there is one copy of it and the two
    doors cannot grow different families.
    """
    try:
        async with _handling_exceptions(logging_broker):
            raise exception
    except Exception as mapped_exception:
        return mapped_exception

    return exception


def _local_exception(categorized_exception: Xeption) -> Xeption | None:
    """The foundation's local exception, the one a categorized exception wraps."""
    inner_exception = categorized_exception.inner_exception

    return inner_exception if isinstance(inner_exception, Xeption) else None


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentOrchestrationValidationException:

    agent_orchestration_validation_exception = AgentOrchestrationValidationException(
        message="Agent orchestration validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(agent_orchestration_validation_exception)

    return agent_orchestration_validation_exception


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentOrchestrationDependencyValidationException:

    agent_orchestration_dependency_validation_exception = (
        AgentOrchestrationDependencyValidationException(
            message="Agent orchestration dependency validation error occurred, "
                    "fix the error and try again.",
            inner_exception=exception))

    await logging_broker.log_error(agent_orchestration_dependency_validation_exception)

    return agent_orchestration_dependency_validation_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Xeption | None) -> AgentOrchestrationDependencyException:

    agent_orchestration_dependency_exception = AgentOrchestrationDependencyException(
        message="Agent orchestration dependency error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(agent_orchestration_dependency_exception)

    return agent_orchestration_dependency_exception


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Xeption) -> AgentOrchestrationServiceException:

    agent_orchestration_service_exception = AgentOrchestrationServiceException(
        message="Agent orchestration service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(agent_orchestration_service_exception)

    return agent_orchestration_service_exception
