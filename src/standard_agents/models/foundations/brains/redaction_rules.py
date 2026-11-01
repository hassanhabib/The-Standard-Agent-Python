# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from typing import ClassVar

from standard_agents.models.foundations.brains.redaction_rule import RedactionRule


class RedactionRules:
    # The patterns are the .NET verbatim strings unchanged: every construct they use
    # (\w, \d, \b, character classes, {n}, ?, +) has the same syntax in Python re.
    # Semantics differ only at the Unicode edges: .NET \w (and so \b) also matches
    # nonspacing marks (Mn) and every connector punctuation (Pc), while Python str \w
    # matches str.isalnum() characters and "_" only. \d is Unicode Nd in both.
    DEFAULT: ClassVar[tuple[RedactionRule, ...]] = (
        RedactionRule(
            label="EMAIL",
            pattern=r"[\w.+-]+@[\w-]+\.[\w.-]+",
        ),
        RedactionRule(
            label="SSN",
            pattern=r"\b\d{3}-\d{2}-\d{4}\b",
        ),
        RedactionRule(
            label="CREDIT_CARD",
            pattern=r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b",
        ),
        RedactionRule(
            label="PHONE",
            pattern=r"\b\d{3}[-.]\d{3}[-.]\d{4}\b",
        ),
    )
