# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
import json
import os
import unicodedata
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import aclosing, asynccontextmanager

from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.generators.v1.conversation import ToolDefinition
from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainDependencyValidationException,
    BrainServiceException,
    BrainValidationException)
from standard_agents.models.foundations.gates.exceptions import (
    GateDependencyException,
    GateDependencyValidationException,
    GateServiceException,
    GateValidationException)
from standard_agents.models.foundations.judges.exceptions import (
    JudgeDependencyException,
    JudgeDependencyValidationException,
    JudgeServiceException,
    JudgeValidationException)
from standard_agents.models.loggings.agent_run import AgentRun
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.exceptions import (
    AgentOrchestrationDependencyException,
    AgentOrchestrationDependencyValidationException,
    AgentOrchestrationServiceException,
    FailedAgentOrchestrationServiceException)
from standard_agents.services.foundations.brains.brain_service import BrainService
from standard_agents.services.foundations.usages.usage_service import UsageService
from standard_agents.services.orchestrations.decision.inferences.reply_stream_classifier import (
    ReplyStreamClassifier)
from xeptions import Xeption

_ACTION_PREFIX = "ACTION:"
_TOOL_PREFIX = "TOOL:"
_FINAL_PREFIX = "FINAL:"
_TRANSFER_PREFIX = "TRANSFER:"
_SAY_PREFIX = "SAY:"
_RETURN_RESPONSE_DIRECTION = "ReturnResponse"
_RESPOND_INTENT = "Respond"

# The task a transfer hands over when the model names only the agent. The grounded handoff
# template already carries the user's actual ask ({prompt}), so the task slot states the
# transfer's meaning rather than repeating the prompt into its own context.
_TRANSFER_TASK = "answer the user's request in full."

_JSON_WHITESPACE = " \t\n\r"
_JSON_DECODER = json.JSONDecoder()


class InferenceOrchestrationService:
    """The model call, and how its answer is read.

    One foundation, but a region rather than a pass-through: choosing between the text protocol
    and native tool calling, shaping what the model is shown, and reading its reply back into an
    intent is the substance of this nature. Whether that reading was right is the Guardian's
    question, not this one's.
    """

    def __init__(
            self,
            *,
            brain_service: BrainService,
            usage_service: UsageService,
            logging_broker: LoggingBroker,
            tool_definitions: Sequence[ToolDefinition] | None = None) -> None:

        self.brain_service = brain_service
        self.usage_service = usage_service
        self.logging_broker = logging_broker
        self.tool_definitions = tool_definitions if tool_definitions is not None else ()

    async def decide(self, context: AgentContext) -> AgentContext:
        """Asks the model and reads its answer into intent, direction_type and payload.

        Uses native tool calling when a V1 brain is configured, the text protocol otherwise; the
        caller sees no difference (SPEC.md 6).
        """
        async with _handling_exceptions(self.logging_broker):
            # Which protocol answers is decided here and nowhere else. Adopting native tool
            # calling changes how a choice is read, not what the agent is (SPEC.md 6).
            if self.brain_service.speaks_natively:
                return await self._think_natively(context)

            user_message = _build_user_message(context)

            # The context carries the resolution's output from the boundary; this tier hands it
            # on and learns nothing from it (docs/per-request-inference.md 2). A context built by
            # hand carries none, and that is exactly the plain call.
            if context.inference is None:
                reply = await self.brain_service.generate(
                    system_prompt=context.system_prompt,
                    user_prompt=user_message)
            else:
                reply = await self.brain_service.generate(
                    system_prompt=context.system_prompt,
                    user_prompt=user_message,
                    inference=context.inference)

            decided = await self._measured(
                _interpret(context, _trim(reply)),
                sent=context.system_prompt + user_message,
                received=reply)

            await self._narrate_decided(decided, _trim(reply))

            return decided

    async def decide_stream(
            self,
            context: AgentContext,
            set_decided: Callable[[AgentContext], None]) -> AsyncIterator[AgentStreamEvent]:
        """The same, streamed.

        Draft segments are yielded as they arrive; the interpreted result is handed back through
        set_decided once the reply is whole. A fault in the model stream surfaces in the same
        orchestration family decide produces: the enumeration advances inside the mapping and
        yields outside it, because the failure points are the awaits.
        """
        segments = self._decide_stream_core(context, set_decided)

        async with aclosing(segments):
            while True:
                try:
                    segment = await anext(segments)
                except StopAsyncIteration:
                    break
                except Exception as exception:
                    raise await _mapped_and_logged(self.logging_broker, exception)

                yield segment

    async def _decide_stream_core(
            self,
            context: AgentContext,
            set_decided: Callable[[AgentContext], None]) -> AsyncIterator[AgentStreamEvent]:

        # The same seam decide keeps (SPEC.md 6). A V1 provider returns one structured result
        # rather than a token stream, so the draft arrives whole and is surfaced as thinking: a
        # draft is not an answer until the guardians settle it, exactly as the text path's
        # chunks are not.
        if self.brain_service.speaks_natively:
            native_decided = await self._think_natively(context)

            is_draft_answer = (
                _equals_ordinal_ignore_case(
                    native_decided.direction_type, _RETURN_RESPONSE_DIRECTION)
                and not _is_blank(native_decided.payload))

            if is_draft_answer:
                yield AgentStreamEvent(AgentStreamEventType.THINKING, native_decided.payload)

            set_decided(native_decided)

            return

        classifier = ReplyStreamClassifier()
        reply_parts: list[str] = []
        user_message = _build_user_message(context)

        # The same hand-off the batched call makes: the streamed loop carries the resolution's
        # output too, or the stream becomes the way to step around the seam (SPEC.md 7.6).
        if context.inference is None:
            tokens = self.brain_service.generate_stream(
                system_prompt=context.system_prompt,
                user_prompt=user_message)
        else:
            tokens = self.brain_service.generate_stream(
                system_prompt=context.system_prompt,
                user_prompt=user_message,
                inference=context.inference)

        async with aclosing(tokens):
            async for delta in tokens:
                reply_parts.append(delta)

                for segment in classifier.classify(delta):
                    yield _as_unsettled_draft(segment)

        for segment in classifier.flush():
            yield _as_unsettled_draft(segment)

        reply = "".join(reply_parts)

        decided = await self._measured(
            _interpret(context, _trim(reply)),
            sent=context.system_prompt + user_message,
            received=reply)

        await self._narrate_decided(decided, _trim(reply))

        set_decided(decided)

    async def _measured(self, decided: AgentContext, sent: str, received: str) -> AgentContext:
        """The provider's own usage report wins whenever there is one; counting is the fallback.

        The report is what the invoice will be drawn from. The fallback says it was counted,
        because a bound enforced on an estimate and a bound reconciled against a bill are
        different claims.
        """
        if decided.prompt_tokens > 0 or decided.completion_tokens > 0:
            return decided

        usage = await self.usage_service.measure(sent, received)

        return dataclasses.replace(
            decided,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            usage_is_estimated=usage.is_estimated)

    async def _narrate_decided(self, decided: AgentContext, reply: str) -> None:
        """One narration for the text protocol's model call, whichever door drove it."""
        await self.logging_broker.log_payload("Decision", "Brain replied", reply, detail=True)

        usage_source = "counted" if decided.usage_is_estimated else "reported"

        await self.logging_broker.log_process(
            "Decision",
            f"Brain → {decided.prompt_tokens + decided.completion_tokens} tokens "
            f"({usage_source})",
            detail=True)

        await self.logging_broker.log_process(
            "Decision", f"Interpreted → {decided.direction_type}")

    async def _think_natively(self, context: AgentContext) -> AgentContext:
        """Native tool calling (SPEC.md 6): the model's choice arrives as structured data.

        Everything after interpretation (the Judge, the revision loop, Direction's perimeter)
        sees the same AgentContext the text protocol produces.
        """
        result = await self.brain_service.generate_natively(context, self._merged_tools(context))

        await self.logging_broker.log_process(
            "Decision",
            f"Brain → {len(result.tool_calls)} native tool call(s)"
            if result.has_tool_calls
            else "Brain → answered",
            detail=True)

        # A provider's own usage report wins, but an endpoint can omit it entirely, so a count
        # keeps the bound working against every endpoint. The narration is the SAY: line's V1
        # twin and rides the context whichever branch below returns.
        measured = await self._measured(
            dataclasses.replace(
                context,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                narration=result.narration),
            sent=context.system_prompt + _build_user_message(context),
            received=result.content)

        if not result.has_tool_calls:
            return dataclasses.replace(
                measured,
                intent=_RESPOND_INTENT,
                direction_type=_RETURN_RESPONSE_DIRECTION,
                payload=result.content,
                tool_call_id="",
                raw_reply=result.content)

        # One call per turn, deliberately: authorization, approval and run-once are judgments
        # about a single act (SPEC.md 4.9). The rest are re-proposed on the next turn if still
        # wanted.
        tool_call = result.tool_calls[0]

        await self.logging_broker.log_process(
            "Decision", f"Interpreted → {tool_call.name} (native)")

        return dataclasses.replace(
            measured,
            intent=tool_call.name,
            direction_type=tool_call.name,
            payload=tool_call.arguments_json,
            tool_call_id=tool_call.id,
            raw_reply=result.content)

    def _merged_tools(self, context: AgentContext) -> tuple[ToolDefinition, ...]:
        """The configured tools and the caller's, side by side (design 6.1).

        The boundary already dropped any caller tool sharing a configured name. Under selection
        (SPEC.md 4.15) the agent's own tools narrow to the offered subset; caller tools are the
        caller's vocabulary and are never selected away.
        """
        configured = (*self.tool_definitions, *self._remote_tool_definitions())
        offered_tools = _offered_tools()

        if offered_tools is not None:
            configured = tuple(
                tool for tool in configured if _is_offered(tool.name, offered_tools))

        caller_tools = context.inference.caller_tools if context.inference is not None else ()

        if not caller_tools:
            return configured

        return (*configured, *caller_tools)

    def _remote_tool_definitions(self) -> tuple[ToolDefinition, ...]:
        """The described remote tools this run discovered, after the agent's own.

        A remote name the agent already carries is the local tool's.
        """
        run = AgentRun.current()
        remote_tools = run.remote_tools if run is not None else ()

        return tuple(
            ToolDefinition(tool.name, tool.description, tool.input_schema_json)
            for tool in remote_tools
            if not _is_blank(tool.description)
            if not any(
                _equals_ordinal_ignore_case(local_tool.name, tool.name)
                for local_tool in self.tool_definitions))


def _as_unsettled_draft(segment: AgentStreamEvent) -> AgentStreamEvent:
    """A draft is not an answer until the Judge has settled it, so a response streams as thinking.

    Filtering a stream to response therefore equals what the batched call returns (SPEC.md 4.3).
    """
    if segment.type is AgentStreamEventType.RESPONSE:
        return dataclasses.replace(segment, type=AgentStreamEventType.THINKING)

    return segment


def _build_user_message(context: AgentContext) -> str:
    """What the model is shown: the conversation so far, the task, and the observations.

    Lines end with os.linesep, as StringBuilder.AppendLine ends them with Environment.NewLine.
    """
    newline = os.linesep
    user_message: list[str] = []

    # What was said before, oldest first, so a follow-up resolves against it (SPEC.md 4.11).
    if context.history:
        user_message.append(f"Conversation so far:{newline}{newline}")

        for turn in context.history:
            user_message.append(f"User: {turn.prompt}{newline}")
            user_message.append(f"You: {turn.answer}{newline}")

        user_message.append(newline)

    user_message.append(f"Task: {context.prompt}")

    if context.observations:
        user_message.append(f"{newline}{newline}Observations so far:{newline}")

        for observation in context.observations:
            user_message.append(f"- {observation}{newline}")

    return "".join(user_message)


def _peeled_narration(reply: str) -> tuple[str, str]:
    """A leading SAY: line is narration, never the choice (SPEC.md 6.0).

    At most one is peeled before the first-line rule applies, so "SAY: ...\\nACTION: ..." still
    acts. Returns the narration and the choice.
    """
    leading = _trim_start(reply)

    if not _starts_with_ordinal_ignore_case(leading, _SAY_PREFIX):
        return "", reply

    newline_index = leading.find("\n")

    if newline_index < 0:
        return _trim(leading[len(_SAY_PREFIX):]), ""

    narration = _trim(leading[len(_SAY_PREFIX):newline_index])
    choice = _trim(leading[newline_index + 1:])

    return narration, choice


def _interpret(context: AgentContext, reply: str) -> AgentContext:
    """Reads the reply back into an intent (SPEC.md 6)."""
    narration, choice = _peeled_narration(reply)
    first_line = _trim(choice.split("\n")[0])

    if _starts_with_ordinal_ignore_case(first_line, _TOOL_PREFIX):
        tool_call = _parse_tool_call(first_line[len(_TOOL_PREFIX):])

        if tool_call is not None:
            called_tool, arguments = tool_call

            return dataclasses.replace(
                context,
                intent=called_tool,
                direction_type=called_tool,
                payload=arguments,
                raw_reply=reply,
                narration=narration,
                transferring=False)

    # TRANSFER: the model hands the whole run to a registered agent. Same act pipeline as
    # ACTION, different ending: an answer from the specialist ends the run as the answer. Absent
    # a task after the name, the transfer's own meaning is the task.
    if _starts_with_ordinal_ignore_case(first_line, _TRANSFER_PREFIX):
        handover = _split_trimmed(first_line[len(_TRANSFER_PREFIX):])
        agent_name = handover[0]

        task = (
            handover[1]
            if len(handover) > 1 and not _is_blank(handover[1])
            else _TRANSFER_TASK)

        # A bare "TRANSFER:" with no agent behind it is not a transfer: the reply is the answer.
        if not _is_blank(agent_name):
            return dataclasses.replace(
                context,
                intent=agent_name,
                direction_type=agent_name,
                payload=task,
                raw_reply=reply,
                narration=narration,
                transferring=True)

    if _starts_with_ordinal_ignore_case(first_line, _ACTION_PREFIX):
        tool_call_parts = _split_trimmed(first_line[len(_ACTION_PREFIX):])
        tool_name = tool_call_parts[0]
        tool_input = tool_call_parts[1] if len(tool_call_parts) > 1 else ""

        # Small models parrot the protocol template: "ACTION:" with no tool name behind it is
        # not a tool call, and routing an empty name into Direction would fault.
        if not _is_blank(tool_name):
            return dataclasses.replace(
                context,
                intent=tool_name,
                direction_type=tool_name,
                payload=tool_input,
                raw_reply=reply,
                narration=narration,
                transferring=False)

    answer = (
        _trim(choice[len(_FINAL_PREFIX):])
        if _starts_with_ordinal_ignore_case(choice, _FINAL_PREFIX)
        else choice)

    return dataclasses.replace(
        context,
        intent=_RESPOND_INTENT,
        direction_type=_RETURN_RESPONSE_DIRECTION,
        payload=answer,
        raw_reply=reply,
        narration=narration,
        transferring=False)


def _parse_tool_call(text: str) -> tuple[str, str] | None:
    """The tool and the raw arguments of a TOOL: line's JSON object, or None.

    Arguments are the member's text exactly as it arrived (JsonElement.GetRawText), and "{}"
    when there is none.
    """
    try:
        root = json.loads(text, parse_constant=_reject_json_constant)
    except json.JSONDecodeError:
        return None

    if not isinstance(root, dict):
        return None

    tool_name = root.get("tool")

    if not isinstance(tool_name, str) or _is_blank(tool_name):
        return None

    arguments = _raw_member(text, "arguments")

    return tool_name, arguments if arguments is not None else "{}"


def _reject_json_constant(constant: str) -> None:
    """NaN and Infinity are not JSON to System.Text.Json."""
    raise json.JSONDecodeError(f"'{constant}' is an invalid JSON literal.", constant, 0)


def _raw_member(text: str, name: str) -> str | None:
    """JsonElement.TryGetProperty(name) then GetRawText, over text already parsed as an object.

    Names match exactly, and the last member wins when a name repeats, as JsonElement does.
    """
    index = _skip_json_whitespace(text, _skip_json_whitespace(text, 0) + 1)

    if text[index] == "}":
        return None

    found: str | None = None

    while True:
        member_name, index = json.decoder.scanstring(text, index + 1)
        index = _skip_json_whitespace(text, index)
        start = _skip_json_whitespace(text, index + 1)
        _, end = _JSON_DECODER.raw_decode(text, start)

        if member_name == name:
            found = text[start:end]

        index = _skip_json_whitespace(text, end)

        if text[index] == "}":
            return found

        index = _skip_json_whitespace(text, index + 1)


def _skip_json_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index] in _JSON_WHITESPACE:
        index += 1

    return index


def _split_trimmed(text: str) -> list[str]:
    """text.Split(':', 2, StringSplitOptions.TrimEntries)."""
    return [_trim(part) for part in text.split(":", 1)]


def _offered_tools() -> Sequence[str] | None:
    run = AgentRun.current()

    return run.offered_tools if run is not None else None


def _is_offered(tool_name: str, offered_tools: Sequence[str]) -> bool:
    """offered.Contains(name, StringComparer.OrdinalIgnoreCase)."""
    return any(
        _equals_ordinal_ignore_case(offered_tool, tool_name) for offered_tool in offered_tools)


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


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except (
            BrainValidationException,
            GateValidationException,
            JudgeValidationException,
            BrainDependencyValidationException,
            GateDependencyValidationException,
            JudgeDependencyValidationException) as validation_exception:

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, _local_exception(validation_exception))
    except (
            BrainDependencyException,
            BrainServiceException,
            GateDependencyException,
            GateServiceException,
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
