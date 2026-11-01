# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, MutableMapping

from standard_agents.brokers.redactions.redaction_broker import RedactionBroker
from standard_agents.models.foundations.brains.redaction_rule import RedactionRule


class RuleRedactionBroker(RedactionBroker):
    """Redaction at the model boundary (SPEC.md 4.6), extracted from the Brain.

    Extracted so every model the agent drives can share it. The Gate screens the raw task and
    the Judge reads the task and the draft, so both see exactly the values redaction exists to
    hide, and a guardian may run on a different host than the Brain, which makes an unredacted
    guardian a wider exposure, not a narrower one.

    The rules are Data (RedactionRules.DEFAULT); this broker is the liaison to the regex engine
    that applies them, and holds no policy of its own.
    """

    def __init__(self, rules: Iterable[RedactionRule]) -> None:
        self._rules = tuple(rules)

    def redact(self, text: str, vault: MutableMapping[str, str]) -> str:
        if not self._rules or not text:
            return text

        redacted_text = text

        for rule in self._rules:
            redacted_text = re.sub(
                rule.pattern,
                lambda match, rule=rule: _tokenize(rule, match.group(0), vault),
                redacted_text)

        return redacted_text

    def rehydrate(self, text: str, vault: Mapping[str, str]) -> str:
        """Replace every token in the text with its value from the vault.

        Mirrors .NET's string.Replace(oldValue, newValue): ordinal, an empty oldValue refused
        with its ArgumentException message, a None newValue removing what it matched.
        """
        rehydrated_text = text

        for key, value in vault.items():
            if not key:
                raise ValueError(
                    "The value cannot be an empty string. (Parameter 'oldValue')")

            rehydrated_text = rehydrated_text.replace(key, "" if value is None else value)

        return rehydrated_text


def _tokenize(
        rule: RedactionRule,
        value: str,
        vault: MutableMapping[str, str]) -> str:
    """Return the vault's token for this value, minting one when the value is new.

    One token per distinct value, so the same email redacts to the same placeholder twice and
    the model can still reason about it being the same person.
    """
    existing_token = next(
        (entry_key for entry_key, entry_value in vault.items() if entry_value == value),
        None)

    if existing_token is not None:
        return existing_token

    token = "{{" + rule.label + "_" + str(len(vault)) + "}}"
    vault[token] = value

    return token
