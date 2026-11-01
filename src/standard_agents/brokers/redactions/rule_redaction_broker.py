# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import re
from typing import Iterable, Mapping, MutableMapping

from standard_agents.brokers.redactions.redaction_broker import RedactionBroker
from standard_agents.models.foundations.brains.redaction_rule import RedactionRule


# Redaction at the model boundary (SPEC.md 4.6), extracted from the Brain so every model the
# agent drives can share it. The Gate screens the raw task and the Judge reads the task and the
# draft, so both see exactly the values redaction exists to hide, and a guardian may run on a
# different host than the Brain, which makes an unredacted guardian a wider exposure, not a
# narrower one.
#
# The rules are Data (RedactionRules.DEFAULT); this broker is the liaison to the regex engine
# that applies them, and holds no policy of its own.
class RuleRedactionBroker(RedactionBroker):
    def __init__(self, rules: Iterable[RedactionRule]) -> None:
        self._rules = tuple(rules)

    def redact(self, text: str, vault: MutableMapping[str, str]) -> str:
        if len(self._rules) == 0 or text is None or len(text) == 0:
            return text

        redacted_text = text

        for rule in self._rules:
            redacted_text = re.sub(
                rule.pattern,
                lambda match, rule=rule: _tokenize(rule, match.group(0), vault),
                redacted_text)

        return redacted_text

    # string.Replace(oldValue, newValue): ordinal, an empty oldValue refused, a null newValue
    # removing what it matched.
    def rehydrate(self, text: str, vault: Mapping[str, str]) -> str:
        rehydrated_text = text

        for key, value in vault.items():
            if len(key) == 0:
                raise ValueError(
                    "The value cannot be an empty string. (Parameter 'oldValue')")

            rehydrated_text = rehydrated_text.replace(key, "" if value is None else value)

        return rehydrated_text


# One token per distinct value, so the same email redacts to the same placeholder twice and
# the model can still reason about it being the same person.
def _tokenize(
    rule: RedactionRule,
    value: str,
    vault: MutableMapping[str, str]) -> str:

    existing_token = next(
        (entry_key for entry_key, entry_value in vault.items() if entry_value == value),
        None)

    if existing_token is not None:
        return existing_token

    token = "{{" + rule.label + "_" + str(len(vault)) + "}}"
    vault[token] = value

    return token
