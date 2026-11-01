# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import asynccontextmanager

from restfulsense.exceptions import (
    HttpRequestException,
    HttpResponseBadRequestException,
    HttpResponseForbiddenException,
    HttpResponseInternalServerErrorException,
    HttpResponseNotFoundException,
    HttpResponseServiceUnavailableException,
    HttpResponseUnauthorizedException,
    HttpResponseUrlNotFoundException)
from standard_agents.brokers.generators.generator_broker import GeneratorBroker
from standard_agents.brokers.generators.generator_broker_v1 import GeneratorBrokerV1
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.brokers.generators.resolved_inference import ResolvedInference
from standard_agents.models.brokers.generators.v1.conversation import (
    ConversationMessage,
    GenerationResult,
    MessageRole,
    ModelToolCall,
    ToolDefinition)
from standard_agents.models.foundations.brains.exceptions import (
    BrainDependencyException,
    BrainDependencyValidationException,
    BrainServiceException,
    BrainValidationException,
    FailedBrainDependencyException,
    FailedBrainServiceException,
    InvalidBrainException,
    UnreachableBrainException)
from standard_agents.models.orchestrations.agents.agent_context import AgentContext
from standard_agents.models.orchestrations.agents.tool_exchange import ToolExchange


class BrainService:
    """One broker role, versioned.

    Redaction and retry used to be held here as two more brokers; both are now decorations
    applied to the generator at composition, so this service knows about neither and cannot
    forget either (docs/architecture-alignment.md).
    """

    def __init__(
            self,
            *,
            generator_broker: GeneratorBroker,
            logging_broker: LoggingBroker,
            generator_broker_v1: GeneratorBrokerV1 | None = None) -> None:

        self.generator_broker = generator_broker
        self.logging_broker = logging_broker
        self.generator_broker_v1 = generator_broker_v1

    @property
    def speaks_natively(self) -> bool:
        """True when a V1 brain is configured and native tool calling is available."""
        return self.generator_broker_v1 is not None

    async def generate(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> str:
        """The system and user prompts in, the model's text out.

        The run's resolved inference options ride through to the broker, which honors them or
        degrades to the plain call by its own default; either way the guardian still holds the
        answer to shape (docs/per-request-inference.md 2). None means the context was built by
        hand and carried no opinions, which is exactly the plain call.
        """
        async with _handling_exceptions(self.logging_broker):
            _validate_user_prompt(user_prompt)

            if inference is None:
                return await self.generator_broker.generate(system_prompt, user_prompt)

            await self._announce_degradation(self.generator_broker.honors_request)

            return await self.generator_broker.generate(
                system_prompt, user_prompt, inference=inference)

    async def generate_stream(
            self,
            system_prompt: str,
            user_prompt: str,
            *,
            inference: ResolvedInference | None = None) -> AsyncIterator[str]:
        """The streamed twin of generate, carrying the same options."""
        async with _handling_stream_exceptions(self.logging_broker):
            _validate_user_prompt(user_prompt)

            if inference is None:
                tokens = self.generator_broker.generate_stream(system_prompt, user_prompt)
            else:
                await self._announce_degradation(self.generator_broker.honors_request)

                tokens = self.generator_broker.generate_stream(
                    system_prompt, user_prompt, inference=inference)

        try:
            while True:
                async with _handling_stream_exceptions(self.logging_broker):
                    try:
                        token = await anext(tokens)
                    except StopAsyncIteration:
                        break

                yield token
        finally:
            # Closed however the stream ends, so the broker lets go of its response. A broker may
            # hand back any async iterator, and only an async generator has anything to close.
            close_tokens = getattr(tokens, "aclose", None)

            if close_tokens is not None:
                await close_tokens()

    async def generate_natively(
            self,
            context: AgentContext,
            tools: Sequence[ToolDefinition]) -> GenerationResult:
        """The V1 path: a conversation of typed messages in, a structured choice out.

        Called only when speaks_natively; the text protocol remains the Core contract. It exists
        because the text protocol forfeits what hosted models are trained on: a model asked to
        emit "ACTION: calculator: 2+2" is imitating a format, while the same model emitting a
        tool_call is doing the thing it was tuned for. The text protocol stays the Core contract
        because it works against any endpoint, and because a small local model often does better
        with it.

        Redaction applies here exactly as it does on the V0 path (SPEC.md 4.6): every message
        going out is redacted, and the reply is rehydrated before anyone reads it.
        """
        _validate_user_prompt(context.prompt)
        messages = tuple(_build_conversation(context))

        # The context arrives intact; it used to be flattened here and its resolution discarded
        # (docs/per-request-inference.md 2).
        if context.inference is None:
            return await self.generator_broker_v1.generate(messages, tools)

        await self._announce_degradation(self.generator_broker_v1.honors_request)

        return await self.generator_broker_v1.generate(
            messages, tools, inference=context.inference)

    async def _announce_degradation(self, honors_request: bool) -> None:
        """Say in the trace that options were not put on the wire.

        honors_request exists so the trace can say which of the two happened: options on the
        wire, or graceful degradation with shape still enforced by the guardian
        (docs/per-request-inference.md 5). Asked only when a run actually carries options: a
        plain run has nothing to degrade.
        """
        if not honors_request:
            await self.logging_broker.log_process(
                "Decision",
                "Brain → broker does not honor requests; shape enforced by guardian only",
                detail=True)


def _build_conversation(context: AgentContext) -> Iterator[ConversationMessage]:
    """The conversation the model actually sees.

    Who it is, what was said before, what it has learned this turn, and the task. Observations
    are their own message rather than appended to the task, so a tool result reads as something
    that happened rather than as part of what the user asked.
    """
    if context.system_prompt and not context.system_prompt.isspace():
        yield ConversationMessage(role=MessageRole.SYSTEM, content=context.system_prompt)

    for turn in context.history:
        yield ConversationMessage(role=MessageRole.USER, content=turn.prompt)

        # A past turn's calls belong inside that turn, between the prompt that asked for them
        # and the answer they produced. Held back and flushed after the CURRENT prompt they read
        # as this turn's evidence, which is how a finished edit becomes a claim that the file was
        # just edited (SPEC.md 4.11).
        yield from _replayed(turn.exchanges)

        yield ConversationMessage(role=MessageRole.ASSISTANT, content=turn.answer)

    yield ConversationMessage(role=MessageRole.USER, content=context.prompt)
    yield from _replayed(context.tool_exchanges)

    # What is left is everything the exchanges do not already carry: a denial, a screening
    # refusal, a V0-shaped observation. Dropping these would lose the very results the perimeter
    # withheld, which are the ones the model most needs to see.
    already_sent = [
        f"{exchange.tool_name}: {exchange.result}" for exchange in context.tool_exchanges]

    narrated = [
        observation for observation in context.observations if observation not in already_sent]

    if narrated:
        yield ConversationMessage(
            role=MessageRole.ASSISTANT,
            content="Observations so far:\n"
                + "\n".join(f"- {observation}" for observation in narrated))


def _replayed(exchanges: Sequence[ToolExchange]) -> Iterator[ConversationMessage]:
    """Native calls go back as what they were.

    The assistant's request, then the tool's answer naming the call it answers (SPEC.md 6).
    This is the shape hosted models are trained on, and it is the reason the id exists.
    Narrating "calculator: 4183" would leave the model matching answers to questions by reading.
    """
    for exchange in exchanges:
        yield ConversationMessage(
            role=MessageRole.ASSISTANT,
            tool_calls=(
                ModelToolCall(exchange.call_id, exchange.tool_name, exchange.arguments_json),))

        yield ConversationMessage(
            role=MessageRole.TOOL,
            tool_call_id=exchange.call_id,
            content=exchange.result)


def _validate_user_prompt(user_prompt: str | None) -> None:
    if not user_prompt or user_prompt.isspace():
        raise InvalidBrainException(
            message="Invalid brain input. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidBrainException as invalid_brain_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_brain_exception)
    except HttpResponseBadRequestException as http_response_bad_request_exception:
        invalid_brain_exception = InvalidBrainException(
            message="Invalid brain request. Please correct the error and try again.")

        invalid_brain_exception.add_data(http_response_bad_request_exception.data)

        raise await _create_and_log_dependency_validation_exception(
            logging_broker, invalid_brain_exception)
    except (
            HttpResponseUnauthorizedException,
            HttpResponseForbiddenException,
            HttpResponseNotFoundException,
            HttpResponseUrlNotFoundException) as critical_dependency_exception:

        raise await _create_and_log_critical_dependency_exception(
            logging_broker, critical_dependency_exception)
    except (
            HttpResponseInternalServerErrorException,
            HttpResponseServiceUnavailableException) as dependency_exception:

        raise await _create_and_log_dependency_exception(logging_broker, dependency_exception)
    except HttpRequestException as http_request_exception:
        raise await _create_and_log_unreachable_exception(
            logging_broker, http_request_exception)
    except Exception as exception:
        raise await _create_and_log_service_exception(
            logging_broker, _create_failed_service_exception(exception))


@asynccontextmanager
async def _handling_stream_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidBrainException as invalid_brain_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_brain_exception)
    except HttpRequestException as http_request_exception:
        raise await _create_and_log_unreachable_exception(
            logging_broker, http_request_exception)
    except Exception as exception:
        raise await _create_and_log_service_exception(
            logging_broker, _create_failed_service_exception(exception))


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainValidationException:

    brain_validation_exception = BrainValidationException(
        message="Brain validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(brain_validation_exception)

    return brain_validation_exception


async def _create_and_log_dependency_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainDependencyValidationException:

    brain_dependency_validation_exception = BrainDependencyValidationException(
        message="Brain dependency validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(brain_dependency_validation_exception)

    return brain_dependency_validation_exception


async def _create_and_log_unreachable_exception(
        logging_broker: LoggingBroker,
        http_request_exception: HttpRequestException) -> BrainDependencyException:
    """Nothing answered at all (SPEC.md 4.10, v1.14).

    A refused connection, a name that resolves to nothing, a request that never left the
    machine. Localised to a sentence about the address rather than "contact support", because
    the person's next step is the address and whatever should be listening at it. The native
    fault stays as the inner exception for whoever investigates, and it is still critical: a
    brain that cannot be reached is configuration.
    """
    unreachable_brain_exception = UnreachableBrainException(
        message="Nothing answered at the brain's address. Check that the address is right "
            "and that the service is running.",
        inner_exception=http_request_exception)

    brain_dependency_exception = BrainDependencyException(
        message="Brain dependency error occurred, contact support.",
        inner_exception=unreachable_brain_exception)

    await logging_broker.log_critical(brain_dependency_exception)

    return brain_dependency_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainDependencyException:

    brain_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(brain_dependency_exception)

    return brain_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainDependencyException:

    brain_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(brain_dependency_exception)

    return brain_dependency_exception


def _create_dependency_exception(exception: Exception) -> BrainDependencyException:
    failed_brain_dependency_exception = FailedBrainDependencyException(
        message="Failed brain dependency error occurred, contact support.",
        inner_exception=exception)

    return BrainDependencyException(
        message="Brain dependency error occurred, contact support.",
        inner_exception=failed_brain_dependency_exception)


def _create_failed_service_exception(exception: Exception) -> FailedBrainServiceException:
    return FailedBrainServiceException(
        message="Failed brain service error occurred, contact support.",
        inner_exception=exception)


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> BrainServiceException:

    brain_service_exception = BrainServiceException(
        message="Brain service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(brain_service_exception)

    return brain_service_exception
