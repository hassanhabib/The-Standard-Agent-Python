# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import math
import os
import re
from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import asynccontextmanager

from standard_agents.brokers.files.file_broker import FileBroker, SearchOption
from standard_agents.brokers.knowledges.knowledge_broker import KnowledgeBroker
from standard_agents.brokers.knowledges.sourced_knowledge_broker import SourcedKnowledgeBroker
from standard_agents.brokers.loggings.logging_broker import LoggingBroker
from standard_agents.models.foundations.knowledges.exceptions import (
    FailedKnowledgeDependencyException,
    FailedKnowledgeServiceException,
    InvalidKnowledgeException,
    KnowledgeDependencyException,
    KnowledgeServiceException,
    KnowledgeValidationException)
from standard_agents.models.foundations.knowledges.knowledge_result import KnowledgeResult


class KnowledgeService:
    """What the agent knows that is relevant to a task, from a broker or a folder of files."""

    def __init__(
            self,
            *,
            logging_broker: LoggingBroker,
            knowledge_broker: KnowledgeBroker | None = None,
            sourced_knowledge_broker: SourcedKnowledgeBroker | None = None,
            file_broker: FileBroker | None = None,
            knowledge_path: str = "",
            search_pattern: str = "",
            max_results: int = 0,
            minimum_score: float = 0.0) -> None:

        self.knowledge_broker = knowledge_broker
        self.sourced_knowledge_broker = sourced_knowledge_broker
        self.file_broker = file_broker
        self.knowledge_path = knowledge_path
        self.search_pattern = search_pattern
        self.max_results = max_results
        self.minimum_score = minimum_score
        self.logging_broker = logging_broker

    async def retrieve_knowledge(self, query: str) -> Sequence[str]:
        async with _handling_exceptions(self.logging_broker):
            _validate_query(query)
            knowledge_results = await self._select_sourced_knowledge(query)

            return tuple(knowledge_result.text for knowledge_result in knowledge_results)

    async def retrieve_sourced_knowledge(self, query: str) -> Sequence[KnowledgeResult]:
        """The same passages, in the same order, each with its score and its source.

        A broker that cannot say where a passage came from yields passages with no source, which
        are never cited (SPEC.md 3.7, 4.2).
        """
        async with _handling_exceptions(self.logging_broker):
            _validate_query(query)

            return await self._select_sourced_knowledge(query)

    async def _select_sourced_knowledge(self, query: str) -> Sequence[KnowledgeResult]:
        """One retrieval behind both doors.

        The plain door can then never rank or filter differently from the sourced one: it is the
        same passages with what travels beside them left off.
        """
        if self.file_broker is not None:
            return await self._select_knowledge_from_files(self.file_broker, query)

        if self.sourced_knowledge_broker is not None:
            return await self.sourced_knowledge_broker.select_sourced_knowledge(query)

        documents = await self.knowledge_broker.select_knowledge(query)

        return tuple(_lift_unsourced(document) for document in documents)

    async def _select_knowledge_from_files(
            self,
            file_broker: FileBroker,
            query: str) -> Sequence[KnowledgeResult]:

        if not file_broker.directory_exists(self.knowledge_path):
            return ()

        query_terms = _terms(query)

        if not query_terms:
            return ()

        document_paths = sorted(
            file_broker.select_files(
                self.knowledge_path, self.search_pattern, SearchOption.ALL_DIRECTORIES),
            key=_ordinal)

        documents: list[str] = []
        document_sources: list[str] = []

        for document_path in document_paths:
            documents.append(await file_broker.read_file(document_path))
            document_sources.append(self._source_of(document_path))

        document_frequency = _document_frequency(documents)
        scored_passages: list[KnowledgeResult] = []

        for document, document_source in zip(documents, document_sources):
            for passage in _passages(document):
                score = _score(query_terms, passage, document_frequency, len(documents))

                # A zero score means the passage carries no query term at all, so it is never a
                # match however low the floor is set. Silence is the right answer when nothing
                # is relevant: returning the corpus instead is how a retriever becomes noise.
                if score > 0 and score >= self.minimum_score:
                    scored_passages.append(
                        KnowledgeResult(text=passage, score=score, source=document_source))

        # Stable, as OrderByDescending is: equal scores keep the order the documents were read.
        scored_passages.sort(key=lambda scored_passage: scored_passage.score, reverse=True)

        # Take(n) takes nothing for a negative n, where a negative slice would take from the end.
        return tuple(scored_passages[:max(self.max_results, 0)])

    def _source_of(self, document_path: str) -> str:
        """The document's path relative to the knowledge folder, with forward slashes.

        The same document is then cited the same way on every machine that serves it. Paths
        with different roots have no relative form, so the path is kept as it is, as
        Path.GetRelativePath keeps it.
        """
        try:
            relative_path = os.path.relpath(document_path, self.knowledge_path)
        except ValueError:
            relative_path = document_path

        return relative_path.replace("\\", "/")


def _lift_unsourced(document: str) -> KnowledgeResult:
    """A plain broker never said where a passage came from (SPEC.md 4.1).

    So the lifted passage claims nothing: no score, no source, and therefore never cited.
    """
    return KnowledgeResult(text=document, score=None, source="")


def _ordinal(text: str) -> bytes:
    """The text as StringComparer.Ordinal compares it: by UTF-16 code units."""
    return text.encode("utf-16-be", errors="surrogatepass")


# Retrieval answers "what is relevant to this task", not "what exists" (SPEC.md 4.2).
#
# This is lexical scoring: terms in common, rarer terms worth more, shorter passages preferred so
# a long document cannot win by being long. It is deliberately dependency-free, because it is the
# Local mode; a broker backed by full-text search or embeddings is the External one, and the
# contract above it does not change either way (SPEC.md 9).

_PASSAGE_WORD_COUNT = 120
_PASSAGE_STRIDE_WORDS = 60

_TERM_SEPARATORS = re.compile(r"[ \t\n\r.,;:!?\"'()\[\]\-/]+")

# The characters char.IsWhiteSpace accepts: U+0009 to U+000D, U+0085 and the Zs, Zl and Zp
# categories. str.isspace also accepts U+001C to U+001F, so str.split and str.strip cannot stand
# in for string.Split(null) and string.Trim().
_WHITE_SPACE = (
    "\t\n\v\f\r\x85"
    " \xa0            "
    "  　"
    "  ")

_WHITE_SPACE_RUN = re.compile(f"[{re.escape(_WHITE_SPACE)}]+")

# Words too common to say anything about relevance. Kept short on purpose: a longer list is a
# language model of its own, and this is meant to stay readable. Held by their ignore-case keys,
# as the C# set compares them with StringComparer.OrdinalIgnoreCase.
_NOISE_TERMS = frozenset(noise_term.upper() for noise_term in (
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "did", "do", "does",
    "for", "from", "had", "has", "have", "how", "i", "in", "is", "it", "its", "me", "my",
    "of", "on", "or", "our", "so", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "to", "was", "we", "what", "when", "where", "which", "who",
    "why", "will", "with", "you", "your"))


def _terms(text: str) -> list[str]:
    lowered_terms = (
        _to_lower_invariant(term) for term in _TERM_SEPARATORS.split(text) if term)

    return [
        term for term in lowered_terms
        if _utf16_length(term) > 1 and _ignore_case_key(term) not in _NOISE_TERMS]


def _passages(document: str) -> Iterator[str]:
    """Overlapping windows, so an answer that straddles a boundary is still found whole.

    The cost is that two neighbouring passages may both match; the ranking then picks whichever
    carries more of the query.
    """
    words = [word for word in _WHITE_SPACE_RUN.split(document) if word]

    if len(words) <= _PASSAGE_WORD_COUNT:
        yield document.strip(_WHITE_SPACE)

        return

    for start in range(0, len(words), _PASSAGE_STRIDE_WORDS):
        yield " ".join(words[start:start + _PASSAGE_WORD_COUNT])

        if start + _PASSAGE_WORD_COUNT >= len(words):
            break


def _document_frequency(documents: Sequence[str]) -> dict[str, int]:
    """How many documents each term appears in, keyed by the term's ignore-case key.

    A term common to the whole corpus then counts for less than one that singles a document out.
    """
    document_frequency: dict[str, int] = {}

    for document in documents:
        for term_key in dict.fromkeys(_ignore_case_key(term) for term in _terms(document)):
            document_frequency[term_key] = document_frequency.get(term_key, 0) + 1

    return document_frequency


def _score(
        query_terms: Sequence[str],
        passage: str,
        document_frequency: dict[str, int],
        document_count: int) -> float:
    """How many query terms appear, each weighted by its rarity, over the root of the length.

    Rarity is what makes "refund" count for more than "policy" when every document mentions
    policy; the length penalty is what stops a long passage winning simply by containing more
    words.
    """
    passage_terms = _terms(passage)

    if not passage_terms:
        return 0.0

    passage_term_keys = {_ignore_case_key(term) for term in passage_terms}
    score = 0.0

    for query_term_key in dict.fromkeys(_ignore_case_key(term) for term in query_terms):
        if query_term_key not in passage_term_keys:
            continue

        seen_in = document_frequency.get(query_term_key, 1)
        score += math.log(1 + document_count / seen_in)

    return score / math.sqrt(len(passage_terms))


def _to_lower_invariant(text: str) -> str:
    """Lowercases each character on its own, keeping it as it is when its mapping expands."""
    lowered: list[str] = []

    for character in text:
        lower = character.lower()
        lowered.append(lower if len(lower) == 1 else character)

    return "".join(lowered)


def _ignore_case_key(text: str) -> str:
    """The text as StringComparer.OrdinalIgnoreCase compares it.

    Each character is upper-cased by its simple (one character) mapping, never a culture's.
    """
    folded: list[str] = []

    for character in text:
        upper = character.upper()
        folded.append(upper if len(upper) == 1 else character)

    return "".join(folded)


def _utf16_length(text: str) -> int:
    """The text's length as string.Length counts it: in UTF-16 code units."""
    return len(text.encode("utf-16-le", errors="surrogatepass")) // 2


def _validate_query(query: str | None) -> None:
    if not query or query.isspace():
        raise InvalidKnowledgeException(
            message="Invalid knowledge query. Please correct the error and try again.")


@asynccontextmanager
async def _handling_exceptions(logging_broker: LoggingBroker) -> AsyncIterator[None]:
    try:
        yield
    except InvalidKnowledgeException as invalid_knowledge_exception:
        raise await _create_and_log_validation_exception(
            logging_broker, invalid_knowledge_exception)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as critical_error:
        raise await _create_and_log_critical_dependency_exception(
            logging_broker, critical_error)
    except OSError as os_error:
        raise await _create_and_log_dependency_exception(logging_broker, os_error)
    except Exception as exception:
        failed_knowledge_service_exception = FailedKnowledgeServiceException(
            message="Failed knowledge service error occurred, contact support.",
            inner_exception=exception)

        raise await _create_and_log_service_exception(
            logging_broker, failed_knowledge_service_exception)


async def _create_and_log_validation_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> KnowledgeValidationException:

    knowledge_validation_exception = KnowledgeValidationException(
        message="Knowledge validation error occurred, fix the error and try again.",
        inner_exception=exception)

    await logging_broker.log_error(knowledge_validation_exception)

    return knowledge_validation_exception


async def _create_and_log_critical_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> KnowledgeDependencyException:

    knowledge_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_critical(knowledge_dependency_exception)

    return knowledge_dependency_exception


async def _create_and_log_dependency_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> KnowledgeDependencyException:

    knowledge_dependency_exception = _create_dependency_exception(exception)
    await logging_broker.log_error(knowledge_dependency_exception)

    return knowledge_dependency_exception


def _create_dependency_exception(exception: Exception) -> KnowledgeDependencyException:
    failed_knowledge_dependency_exception = FailedKnowledgeDependencyException(
        message="Failed knowledge dependency error occurred, contact support.",
        inner_exception=exception)

    return KnowledgeDependencyException(
        message="Knowledge dependency error occurred, contact support.",
        inner_exception=failed_knowledge_dependency_exception)


async def _create_and_log_service_exception(
        logging_broker: LoggingBroker,
        exception: Exception) -> KnowledgeServiceException:

    knowledge_service_exception = KnowledgeServiceException(
        message="Knowledge service error occurred, contact support.",
        inner_exception=exception)

    await logging_broker.log_error(knowledge_service_exception)

    return knowledge_service_exception
