# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import dataclasses
import hashlib
import unicodedata
from dataclasses import dataclass

from standard_agents.models.orchestrations.effects.agent_principal import AgentPrincipal
from standard_agents.models.orchestrations.effects.risk_level import RiskLevel


_KEY_SEPARATOR = "|"


@dataclass(frozen=True)
class AgentEffect:
    """A proposed act, described.

    Direction routes a bare name and payload until a perimeter control is configured; then the
    act needs an identity, because authorization, approval and run-once are all judgments about
    an act, and an act with no identity cannot be judged the same way twice (SPEC.md 3.3, 4.9).
    """

    run_id: str = ""

    # Who is acting, as an identifier. The same value as identity.id.
    principal: str | None = None

    # Who is acting, in full (tenant, jurisdiction and delegation where the host knows them,
    # SPEC.md 4.9). None when no identity is configured.
    identity: AgentPrincipal | None = None

    tool_name: str = ""
    arguments: str = ""

    # The model-issued call id, when this effect is a caller's tool call being handed back
    # (docs/per-request-inference.md 6.2). Empty for every other kind of effect, and on the
    # text protocol, which has no ids.
    call_id: str = ""

    # What the act is about to touch (a path, a host, an account) as the tool named it
    # (Tool.ScopeOf). Empty when the tool touches nothing addressable.
    scope: str = ""

    risk_level: RiskLevel = RiskLevel.SAFE
    approval_required: bool = False

    # Identifies this act, so a repeat of the same intent is recognisable as the same act.
    # Derived, never supplied: see create.
    idempotency_key: str = ""

    @classmethod
    def create(
            cls,
            run_id: str,
            tool_name: str,
            arguments: str,
            risk_level: RiskLevel = RiskLevel.SAFE,
            approval_required: bool = False,
            principal: AgentPrincipal | None = None,
            scope: str = "") -> AgentEffect:
        """Describe an act and derive its key from what the act is.

        The key comes from the run, the tool, and a canonical form of the arguments. It is
        deliberately not a parameter (SPEC.md 4.9): a key the caller or the Brain can choose is
        a key the model can vary, and run-once degrades to advisory.
        """
        return cls(
            run_id=run_id,
            scope=scope,

            # Both views of one identity, kept in step here so they cannot disagree. The
            # identifier stays for the callers that only ever needed "who".
            principal=principal.id if principal is not None else None,
            identity=principal,
            tool_name=tool_name,
            arguments=arguments,
            risk_level=risk_level,
            approval_required=approval_required,
            idempotency_key=_derive_key(run_id, tool_name, arguments))

    def after_writes(self, writes: int) -> AgentEffect:
        """The same look, after the run has written to what it looks at.

        A different act in the ledger, so it runs and sees what the writes left, while a second
        identical look after the same writes replays as before (SPEC.md 4.9, v1.14). Still
        derived, never supplied.
        """
        return dataclasses.replace(
            self,
            idempotency_key=_derive_key(
                self.run_id,
                self.tool_name,
                f"{self.arguments}|after-writes:{writes}"))


def _derive_key(run_id: str, tool_name: str, arguments: str) -> str:
    """The idempotency key of an act.

    White-space-insensitive, and case-insensitive on the tool name, so
    "calculator: 2 + 2" and "calculator:2+2" are one act rather than two. Anything more clever
    belongs to the tool, which is the only thing that knows what its arguments mean.
    """
    canonical_arguments = " ".join(_split_on_white_space(arguments))

    canonical = _KEY_SEPARATOR.join([
        run_id,
        _lower_invariant(_strip_white_space(tool_name)),
        canonical_arguments])

    # Lowercase hex, which is load-bearing: a key derived here must match the same key
    # derived by the C# implementation.
    return hashlib.sha256(_utf8_bytes(canonical)).hexdigest()


def _is_white_space(character: str) -> bool:
    """Whether a character is white space by .NET char.IsWhiteSpace.

    That is the Zs, Zl and Zp categories plus U+0009 to U+000D and U+0085. Python's str.isspace
    also accepts U+001C to U+001F, which .NET does not, so str.split() and str.strip() would
    canonicalize differently.
    """
    if character in "\t\n\v\f\r\u0085":
        return True

    return unicodedata.category(character) in ("Zs", "Zl", "Zp")


def _split_on_white_space(value: str) -> list[str]:
    """Split as .NET string.Split(null, StringSplitOptions.RemoveEmptyEntries) does."""
    parts: list[str] = []
    current: list[str] = []

    for character in value:
        if _is_white_space(character):
            if current:
                parts.append("".join(current))
                current = []
        else:
            current.append(character)

    if current:
        parts.append("".join(current))

    return parts


def _strip_white_space(value: str) -> str:
    """Strip leading and trailing .NET white space, as .NET string.Trim() does."""
    start = 0
    end = len(value)

    while start < end and _is_white_space(value[start]):
        start += 1

    while end > start and _is_white_space(value[end - 1]):
        end -= 1

    return value[start:end]


def _lower_invariant(value: str) -> str:
    """Lowercase as .NET string.ToLowerInvariant() does: simple, per-character case mapping.

    Python's str.lower() applies full mappings (U+0130 becomes two characters) and the
    final-sigma context rule, neither of which .NET applies, so each character is lowered on
    its own.
    """
    lowered: list[str] = []

    for character in value:
        if character == "İ":
            lowered.append("i")
            continue

        candidate = character.lower()
        lowered.append(candidate if len(candidate) == 1 else character)

    return "".join(lowered)


def _utf8_bytes(value: str) -> bytes:
    """Encode as .NET Encoding.UTF8.GetBytes does.

    A surrogate pair held as two code points encodes as the one character it names, and a lone
    surrogate encodes as U+FFFD, where Python's encoder would raise.
    """
    utf16 = value.encode("utf-16-le", errors="surrogatepass")

    return utf16.decode("utf-16-le", errors="replace").encode("utf-8")
