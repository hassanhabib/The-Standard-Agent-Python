# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import unicodedata
from enum import Enum, auto

from standard_agents.models.clients.agents.agent_stream_event import AgentStreamEvent
from standard_agents.models.clients.agents.agent_stream_event_type import AgentStreamEventType

_ACTION_PREFIX = "ACTION:"
_FINAL_PREFIX = "FINAL:"
_TRANSFER_PREFIX = "TRANSFER:"
_SAY_PREFIX = "SAY:"


class _Channel(Enum):
    UNDECIDED = auto()
    THINKING = auto()
    RESPONDING = auto()


class ReplyStreamClassifier:
    """Sorts one streamed reply into thinking and response as its deltas arrive.

    The reply is buffered until its opening says which it is: an act (ACTION: or TRANSFER:)
    streams as thinking, anything else as a response, with a FINAL: marker splitting the head
    that leads to it from the answer after it.
    """

    def __init__(self) -> None:
        self._pending = ""
        self._channel = _Channel.UNDECIDED
        self._narration_swallowed = False

    def classify(self, delta: str) -> tuple[AgentStreamEvent, ...]:
        if self._channel is _Channel.THINKING:
            return (AgentStreamEvent(AgentStreamEventType.THINKING, delta),)

        if self._channel is _Channel.RESPONDING:
            return (AgentStreamEvent(AgentStreamEventType.RESPONSE, delta),)

        self._pending += delta

        return self._decide(is_final=False)

    def flush(self) -> tuple[AgentStreamEvent, ...]:
        if self._channel is _Channel.UNDECIDED:
            return self._decide(is_final=True)

        return ()

    def _decide(self, is_final: bool) -> tuple[AgentStreamEvent, ...]:
        buffered = self._pending
        leading = _trim_start(buffered)

        # A leading SAY: line is swallowed whole, never streamed: it is narration, and narration
        # is screened by the loop before it is voiced. Checked before the length-based commit
        # below, because "SAY: Let m" reaches nine characters and would otherwise commit as an
        # answer starting to stream.
        if not self._narration_swallowed and _starts_with_ordinal_ignore_case(
                leading, _SAY_PREFIX):

            # The newline that ends the SAY line, not one hiding in the leading whitespace.
            newline_index = buffered.find("\n", len(buffered) - len(leading))

            if newline_index < 0:
                if is_final:
                    self._pending = ""

                return ()

            self._pending = buffered[newline_index + 1:]
            self._narration_swallowed = True

            return self._decide(is_final)

        # Buffered until the longest act prefix could be ruled out: deciding at ACTION's length
        # would read the first seven characters of "TRANSFER:" as an answer starting to stream.
        can_decide = (
            _utf16_length(leading) >= len(_TRANSFER_PREFIX)
            or "\n" in buffered
            or is_final)

        if not can_decide:
            return ()

        self._pending = ""

        if (_starts_with_ordinal_ignore_case(leading, _ACTION_PREFIX)
                or _starts_with_ordinal_ignore_case(leading, _TRANSFER_PREFIX)):

            self._channel = _Channel.THINKING

            return (AgentStreamEvent(AgentStreamEventType.THINKING, buffered),)

        self._channel = _Channel.RESPONDING
        final_index = _index_of_ordinal_ignore_case(buffered, _FINAL_PREFIX)

        if final_index < 0:
            return (AgentStreamEvent(AgentStreamEventType.RESPONSE, buffered),)

        head = buffered[:final_index + len(_FINAL_PREFIX)]
        answer = _trim_start(buffered[final_index + len(_FINAL_PREFIX):])
        events = [AgentStreamEvent(AgentStreamEventType.THINKING, head)]

        if answer:
            events.append(AgentStreamEvent(AgentStreamEventType.RESPONSE, answer))

        return tuple(events)


def _utf16_length(text: str) -> int:
    """string.Length: the count of UTF-16 code units, so a character beyond the BMP counts two."""
    return len(text.encode("utf-16-le", errors="surrogatepass")) // 2


def _is_whitespace(character: str) -> bool:
    """char.IsWhiteSpace, which string.TrimStart uses.

    Not str.isspace: .NET does not count U+001C..U+001F as white space.
    """
    return (
        character in "\t\n\v\f\r\x85"
        or unicodedata.category(character) in ("Zs", "Zl", "Zp"))


def _trim_start(text: str) -> str:
    """string.TrimStart, over the .NET white-space set."""
    start = 0

    while start < len(text) and _is_whitespace(text[start]):
        start += 1

    return text[start:]


def _starts_with_ordinal_ignore_case(text: str, prefix: str) -> bool:
    """string.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)."""
    if len(text) < len(prefix):
        return False

    return _fold_ordinal_ignore_case(text[:len(prefix)]) == _fold_ordinal_ignore_case(prefix)


def _index_of_ordinal_ignore_case(text: str, value: str) -> int:
    """string.IndexOf(value, StringComparison.OrdinalIgnoreCase).

    Folding keeps one character for each character, so an index into the folded text is an
    index into the text.
    """
    return _fold_ordinal_ignore_case(text).find(_fold_ordinal_ignore_case(value))


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
