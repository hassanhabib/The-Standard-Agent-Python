# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

import threading
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from standard_agents.models.brokers.mcps.mcp_tool import McpTool
from standard_agents.models.clients.agents.agent_outcome import AgentOutcome
from standard_agents.models.loggings.performed_effect import PerformedEffect
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel


_current: ContextVar["AgentRun | None"] = ContextVar("agent_run_current", default=None)


class AgentRun:
    """One prompt's run: its identity and its counters.

    SPEC.md 4.4 requires run state to be per invocation, never per instance: one agent serves
    many prompts at once, and an implementation that keeps a run's identity or counters in
    shared fields lets a second prompt silently corrupt the first's record.

    The run is carried as ambient per-flow state in a ContextVar. Coordination calls begin() at
    the top of a prompt; everything that prompt awaits reads the same run through current(),
    while a concurrent prompt sees only its own.
    """

    def __init__(self, id: str) -> None:
        """Use begin() or detached() rather than constructing a run directly."""
        self._verdicts: dict[str, str] = {}
        self._verdicts_lock = threading.Lock()

        # Keyed case-insensitively, by _ordinal_ignore_case_key.
        self._grants: set[str] = set()
        self._grants_lock = threading.Lock()

        self._performed_effects: list[PerformedEffect] = []
        self._performed_effects_lock = threading.Lock()

        # Keyed exactly (ordinal).
        self._replays: dict[str, int] = {}
        self._replays_lock = threading.Lock()

        self._sequence = 0
        self._sequence_lock = threading.Lock()
        self._process_index = 0
        self._process_index_lock = threading.Lock()

        self._id = id
        self._cancellation_token: object | None = None
        self._replays_of_latest_ask = 0

        # When the run started, stamped by the trace so the run reads one clock. Until then it
        # is .NET's default(DateTimeOffset), 0001-01-01T00:00:00+00:00.
        self.started_on: datetime = datetime(1, 1, 1, tzinfo=timezone.utc)

        # What the user originally asked this run, riding the run the way its token does, so a
        # handoff can ground a sub-agent in the real goal ({prompt} in a handoff template).
        # Empty outside a prompt.
        self.prompt: str = ""

        # How the most recent handoff this run performed ended: recorded by AgentTool when the
        # nested agent returns, cleared by the loop before every act.
        self.handoff_outcome: AgentOutcome | None = None

        # What this run is OFFERED (SPEC.md 4.15): the selected subset of the agent's described
        # tools. None means no selection ran: every described tool is offered.
        self.offered_tools: tuple[str, ...] | None = None

        # The remote tools this run discovered on its servers, set by the loop once per run
        # before selection. Empty when there are none.
        self.remote_tools: tuple[McpTool, ...] = ()

    @staticmethod
    def current() -> "AgentRun | None":
        """The run active on this flow, or None outside a run."""
        return _current.get()

    @property
    def id(self) -> str:
        """Identifies exactly one prompt; never reused (SPEC.md 3.3)."""
        return self._id

    @property
    def cancellation_token(self) -> object | None:
        """The token that stops this run, or None when the caller supplied none.

        It rides the run the way its identity does, so anything the run reaches (a nested
        agent included) can observe the same stop the outer loop observes at its turn
        boundaries (SPEC.md 4.10).
        """
        return self._cancellation_token

    @classmethod
    def begin(
            cls,
            resumed_id: str | None = None,
            cancellation_token: object | None = None) -> "AgentRunScope":
        """Start a run on the calling flow and return the scope that ends it.

        Call it from the coordination loop, before anything the run should be credited with.

        resumed_id: the identity of a run this one continues, or None to start a new one. A
        resumed run keeps the interrupted run's identity so the effects it already performed
        are recognised as its own rather than proposed again (SPEC.md 4.9, 4.11).
        cancellation_token: the token that stops this run, carried on the run so a nested agent
        can observe the same stop the outer loop observes.
        """
        enclosing_run = _current.get()

        run = cls(resumed_id or uuid.uuid4().hex)
        run._cancellation_token = cancellation_token
        _current.set(run)

        return AgentRunScope(enclosing_run)

    @classmethod
    def detached(cls) -> "AgentRun":
        """A run that is not on any flow.

        For a trace driven outside the coordination loop, so it still numbers its records
        rather than faulting.
        """
        return cls(uuid.uuid4().hex)

    def next_sequence(self) -> int:
        """The next record number for this run: monotonic, starting at zero."""
        with self._sequence_lock:
            self._sequence += 1

            return self._sequence - 1

    def next_process_index(self) -> int:
        """The next process number within the current step."""
        with self._process_index_lock:
            self._process_index += 1

            return self._process_index - 1

    def get_verdict(self, prompt: str) -> str | None:
        """The guardian verdict this run already gave this prompt, or None.

        Verdicts are remembered for the life of the run, so an unchanged prompt is screened
        once rather than once per turn (SPEC.md 4.10).
        """
        with self._verdicts_lock:
            return self._verdicts.get(prompt)

    def remember_verdict(self, prompt: str, verdict: str) -> None:
        with self._verdicts_lock:
            self._verdicts[prompt] = verdict

    def was_granted(self, tool_name: str, scope: str) -> bool:
        """Whether an authority has already permitted this tool at this scope during this run.

        A grant is for what it was granted for: the key is the tool AND the scope and the match
        is exact (case-insensitive). It lives on the run, so the run ending evicts it.
        """
        with self._grants_lock:
            return _ordinal_ignore_case_key(_grant_key(tool_name, scope)) in self._grants

    def remember_grant(self, tool_name: str, scope: str) -> None:
        """Remember that an authority permitted this tool at this scope."""
        with self._grants_lock:
            self._grants.add(_ordinal_ignore_case_key(_grant_key(tool_name, scope)))

    @property
    def performed_effects(self) -> tuple[PerformedEffect, ...]:
        """What this run actually performed, in order.

        Kept so the run can be unwound: compensation needs to know what happened, and only the
        run knows (SPEC.md 4.9).
        """
        with self._performed_effects_lock:
            return tuple(self._performed_effects)

    def record_performed(self, effect: PerformedEffect) -> None:
        with self._performed_effects_lock:
            self._performed_effects.append(effect)

        # An act that ran is not a repeat, whatever came before it.
        self._replays_of_latest_ask = 0

    def record_replay(self, idempotency_key: str) -> int:
        """Record that the run-once ledger answered this act again (SPEC.md 4.9, v1.14).

        Returns how many times it has now done so in this run. Kept by the act's key, so a look
        after a write, which carries a different key, starts its own count.
        """
        with self._replays_lock:
            replayed = self._replays.get(idempotency_key, 0) + 1
            self._replays[idempotency_key] = replayed
            self._replays_of_latest_ask = replayed

            return replayed

    @property
    def replays_of_latest_ask(self) -> int:
        """How many times the ledger has answered the most recent ask that reached it.

        Zero when that ask was performed (SPEC.md 4.10, v1.14).
        """
        return self._replays_of_latest_ask

    def writes_to(self, scope: str) -> int:
        """How many acts this run has performed on a scope that were not SAFE.

        What a look at that scope would see has changed that many times since the run began
        (SPEC.md 4.9, v1.14).
        """
        with self._performed_effects_lock:
            return sum(
                1 for performed in self._performed_effects
                if performed.risk_level is not RiskLevel.SAFE
                and performed.scope == scope)

    def reset_process_index(self) -> None:
        """Restart process numbering, called when a step begins."""
        with self._process_index_lock:
            self._process_index = 0


class AgentRunScope:
    """Restores whatever run was active before.

    A nested agent (the fractal: an agent used as a tool of another agent) returns its caller's
    run rather than leaving it cleared. dispose() ends the scope; it is also a context manager.
    """

    def __init__(self, enclosing_run: AgentRun | None) -> None:
        self._enclosing_run = enclosing_run

    def dispose(self) -> None:
        _current.set(self._enclosing_run)

    def __enter__(self) -> "AgentRunScope":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.dispose()


def _grant_key(tool_name: str, scope: str) -> str:
    return f"{tool_name} {scope}"


def _ordinal_ignore_case_key(value: str) -> str:
    """Fold a key the way .NET StringComparer.OrdinalIgnoreCase compares it.

    Characters compare by their simple uppercase mapping. Python's str.upper() applies full
    mappings (U+00DF becomes "SS"), so each character is uppercased on its own and kept as it
    is when its mapping expands.
    """
    folded: list[str] = []

    for character in value:
        candidate = character.upper()
        folded.append(candidate if len(candidate) == 1 else character)

    return "".join(folded)
