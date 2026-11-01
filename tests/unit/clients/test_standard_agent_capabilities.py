# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# SPEC.md 4.8: every capability MUST be reachable three ways: Local (in the core, point at a
# resource), External (a provider package, passed as a broker) and Custom (host-authored code).
#
# This is the principle most likely to erode quietly: nothing about adding a capability with one
# mode fails a build, and by the time anyone notices there are six of them. So it is a test rather
# than a convention. A missing mode is a failure; a mode that genuinely does not apply is waived
# here, in code, with its reason, which makes waiving it a reviewed change rather than an
# omission nobody sees.

from dataclasses import dataclass

import pytest

from standard_agents.standard_agent import StandardAgent


@dataclass(frozen=True)
class Capability:
    name: str
    local: str | None
    external: str
    custom: str
    waiver: str | None = None


# The matrix. Every capability the agent exposes, and the method that reaches it each way.
CAPABILITIES = (
    Capability("Skills", local="skills", external="use_skills", custom="on_skills"),
    Capability("Memory", local="memory", external="use_memory", custom="on_memory"),
    Capability("Knowledge", local="knowledge", external="use_knowledge", custom="on_knowledge"),

    # Brain has no Local mode, and this is the one documented N/A in the matrix. Local means "in
    # the core, no dependency" (SPEC.md 4.8), and running a model in-process inherently needs an
    # inference runtime, which cannot live in a dependency-free core. The External mode covers
    # it. This is an omission with a reason, which 4.8 permits; silence would not be.
    Capability(
        "Brain", local=None, external="use_generator", custom="on_brain",
        waiver=(
            "Local N/A: in-process inference needs a runtime, and the core is "
            + "dependency-free by design. External covers it (LlamaSharp).")),
    Capability(
        "NativeBrain", local=None, external="use_native_brain", custom="on_native_brain",
        waiver="Local N/A: same reason as Brain, native tool calling still needs a model."),

    Capability("Gate", local="rule_gate", external="gate", custom="on_gate"),
    Capability("Judge", local="rule_judge", external="judge", custom="on_judge"),
    Capability("Tools", local="tool", external="mcp", custom="tool"),
    Capability("Trace", local="log_to", external="use_logging", custom="use_logging"),
    Capability("Audit", local="audit", external="use_audit", custom="on_audit"),
    Capability("Policy", local="allow_tools", external="use_policy", custom="on_policy"),
    Capability(
        "Approval", local="require_approval", external="use_approvals", custom="on_approval"),
    Capability("Resilience", local="resilience", external="use_resilience", custom="fallback"),
    Capability("Sessions", local="sessions", external="use_sessions", custom="on_sessions"),
    Capability(
        "EffectLedger", local="effect_ledger", external="use_effect_ledger",
        custom="on_effect_ledger"),
    Capability("Usage", local="usage", external="use_usage", custom="on_usage"),

    # Observability the collector's way: spans and metrics beside the trace's prose and the
    # audit's records. Local is the in-box activity source; Custom is a callable for pipelines no
    # listener reaches.
    Capability("Telemetry", local="telemetry", external="use_telemetry", custom="on_telemetry"),
    Capability("Contract", local="contract", external="use_contract", custom="on_contract"),

    # The fleet: other agents, reachable as a registry the way every resource is: a local folder
    # of agent documents, a provider's registry, or a callable. A registered agent materializes
    # as a tool, so the perimeter that governs acts governs handoffs.
    Capability("Agents", local="agents", external="use_agents", custom="on_agents"),

    # Found missing in the 2026-08-23 sweep: a full capability nature (its own broker seam, four
    # decorators, a rule-backed default) absent from this matrix entirely, with one mode on the
    # client. The matrix could not see it because nothing ties the matrix to the surface; the
    # waiver test below closes the half of that hole that is closeable from inside the matrix.
    Capability("Redaction", local="redact", external="use_redaction", custom="on_redaction"),
)

PUBLIC_METHOD_NAMES = {
    name for name, member in vars(StandardAgent).items()
    if callable(member) and not name.startswith("_")
}


def unwaived_modes():
    for capability in CAPABILITIES:
        if capability.local is not None:
            yield capability.name, "Local", capability.local

        yield capability.name, "External", capability.external
        yield capability.name, "Custom", capability.custom


@pytest.mark.parametrize(("capability_name", "mode", "expected_method_name"), unwaived_modes())
def test_should_expose_every_capability_local_external_and_custom(
        capability_name,
        mode,
        expected_method_name):

    # given, when, then: SPEC.md 4.8 makes a capability with a missing mode incomplete
    assert expected_method_name in PUBLIC_METHOD_NAMES, (
        f"{capability_name} must be reachable {mode} through .{expected_method_name}(...)")


# The "pending" waivers are retired: Skills, Memory and Knowledge all have callable forms now. What
# remains is not debt but a documented impossibility: SPEC.md 4.8 permits a mode to be omitted
# where it is genuinely meaningless, provided the reason is stated, and a Brain that runs
# in-process cannot exist in a core that has no inference dependency.
#
# The distinction is the whole point: a waiver saying "not yet" is debt, and a waiver saying "not
# possible, here is why" is a design decision. Only the second kind may survive a release, and
# every omitted mode still has to say which it is.
def test_should_only_waive_capability_modes_that_cannot_exist():
    # given
    expected_waived_capabilities = ["Brain", "NativeBrain"]

    # when
    actual_waived = [capability for capability in CAPABILITIES if capability.waiver is not None]

    # then: the only permitted omission is one that cannot exist, and every other capability
    # must answer Local, External and Custom
    assert sorted(capability.name for capability in actual_waived) == sorted(
        expected_waived_capabilities)

    # A waiver reading 'pending' is debt, and a bare 'N/A' is a verdict without a reason: the
    # reason is what makes waiving a reviewed decision.
    assert all(
        "N/A" in capability.waiver
        and ":" in capability.waiver
        and len(capability.waiver.split(":")[-1].strip()) > 10
        for capability in actual_waived)


# The sharpest hole the sweep found in this file: a capability declared with no Local and no
# waiver was silently unasserted: the Local row was skipped and the waiver-set equivalence still
# passed, so the omission was exactly the one nobody sees. Derived, not enumerated: any future
# row that skips a mode without saying why fails here.
def test_should_waive_every_mode_it_skips():
    # given, when
    silent_omissions = [
        capability for capability in CAPABILITIES
        if capability.local is None and capability.waiver is None]

    # then: a mode that genuinely does not apply is waived in code with its reason; an unwaived
    # omission is the erosion this matrix exists to prevent
    assert silent_omissions == []
