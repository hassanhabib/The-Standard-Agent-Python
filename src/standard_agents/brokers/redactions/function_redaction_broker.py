# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping

from standard_agents.brokers.redactions.redaction_broker import RedactionBroker


class FunctionRedactionBroker(RedactionBroker):
    """The Custom mode of redaction (SPEC.md 4.8): the host's own tokenize/restore pair.

    For rules a regex cannot express (an entity model, a domain dictionary, a data-residency
    policy). The decorators apply it at the wire exactly as they apply the built-in rules, so
    "every model call is redacted" stays true by construction whichever mode supplied the
    redactor.
    """

    def __init__(
            self,
            redact: Callable[[str, MutableMapping[str, str]], str],
            rehydrate: Callable[[str, Mapping[str, str]], str]) -> None:

        self._redact = redact
        self._rehydrate = rehydrate

    def redact(self, text: str, vault: MutableMapping[str, str]) -> str:
        return self._redact(text, vault)

    def rehydrate(self, text: str, vault: Mapping[str, str]) -> str:
        return self._rehydrate(text, vault)
