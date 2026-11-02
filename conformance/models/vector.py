# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from conformance.models.expectation import Expectation
from conformance.models.fleet_agent import FleetAgent
from conformance.models.native_reply import NativeReply
from conformance.models.request_spec import RequestSpec


@dataclass(frozen=True)
class ToolNarrationSpec:
    """A stub tool's declared narration templates, as a vector writes them."""

    REJECTS_UNKNOWN_PROPERTIES: ClassVar[bool] = True

    starting: str | None = None
    observed: str | None = None


@dataclass(frozen=True)
class Vector:
    """One conformance vector: what the scripted run is given, and what it must show.

    A typo'd field must fail loudly, not silently delete the assertion or the input it carried: a
    vector that asserts less than it appears to reads as coverage (SPEC.md 1.1).
    """

    REJECTS_UNKNOWN_PROPERTIES: ClassVar[bool] = True

    name: str
    description: str | None
    generator_replies: list[str]
    tools: dict[str, str] | None
    prompt: str
    expect: Expectation

    # Guardian inputs. constitution / consumption are inline markdown the harness writes to a
    # file beside the process and points the real constitution() / consumption() verbs at, so the
    # file-resolution path is exercised, not bypassed. gate_verdict / judge_score drive the
    # scripted guardians (default "allow" / "1.0"), letting a vector force a refusal.
    constitution: str | None = None
    consumption: str | None = None
    gate_verdict: str | None = None
    judge_score: str | None = None

    # Multi-run vectors. The decision log's durability (SPEC.md 4.7) and run isolation (4.4) are
    # only observable across more than one run, so a vector may drive several prompts through
    # one agent instead of one. prompts overrides prompt when present; concurrent runs them all
    # at once rather than in order, which is the only way to certify that one run's bookkeeping
    # never leaks into another's.
    prompts: list[str] | None = None
    concurrent: bool = False

    # Turns on boundary redaction (SPEC.md 4.6) so a vector can certify that no model call
    # carries a sensitive value in the clear.
    redact: bool = False

    # Perimeter controls (SPEC.md 4.9). require_approval names the acts an authority must
    # permit; screen_tool_output turns on screening of untrusted inbound;
    # gate_verdict_on_tool_output is the verdict the scripted Gate returns for tool output
    # specifically, so a vector can refuse a tool result while still accepting the prompt.
    require_approval: list[str] | None = None
    screen_tool_output: bool = False
    gate_verdict_on_tool_output: str | None = None

    # Resilience and budget (SPEC.md 4.10). cancel_before_start cancels the run before the first
    # turn; transient_failures makes the scripted Brain fail that many times with a dependency
    # failure before succeeding, so retry can be certified without a real network.
    cancel_before_start: bool = False
    transient_failures: int = 0
    retries: int = 0
    max_turns: int | None = None

    # Budget, retrieval and degradation (SPEC.md 4.2, 4.10). Wall-clock was once the only bound a
    # vector could express, which meant the TOKEN and COST bounds were certified by nothing.
    budget_max_wall_clock_seconds: float | None = None
    budget_max_tokens: int | None = None

    # Permission. tool_risk classifies a stub tool; tool_scope_first_word names the one scope
    # strategy a runner in any language can implement identically: the first space-separated
    # word of the input, which is enough to carry a path. permission_mode is the disposition
    # toward an act nothing explicitly permitted.
    tool_risk: dict[str, str] | None = None
    tool_scope_first_word: list[str] | None = None
    permission_mode: str | None = None
    allow_tools: list[str] | None = None
    budget_max_cost_usd: Decimal | None = None
    budget_cost_per_thousand_tokens: Decimal = Decimal(0)
    knowledge: dict[str, str] | None = None
    fallback_reply: str | None = None
    failures_before_open: int = 3
    knowledge_max_results: int = 3

    # Sessions (SPEC.md 4.11). When set, every prompt in the vector runs in this conversation.
    session_id: str | None = None

    # Compensation (SPEC.md 4.9). compensate_on_failure turns the unwind on; compensating_tools
    # names the tools that know how to reverse themselves. A tool left out keeps the interface
    # default and must be reported as an effect that stands.
    compensate_on_failure: bool = False
    compensating_tools: list[str] | None = None

    # Cross-process resumption (SPEC.md 4.9, 4.11). new_instance_per_prompt builds a brand-new
    # agent for each prompt, so nothing but the files on disk survives between them;
    # durable_effect_ledger puts run-once in a folder rather than in the instance's memory.
    # Together they are the only way to certify that an effect outcome survives a crash.
    new_instance_per_prompt: bool = False
    durable_effect_ledger: bool = False

    # A scripted authority, "pending", "approved", "denied", answered in order, so a vector can
    # hold an act on one run and permit it on the next. That is the shape of every real
    # approval: the answer arrives after the agent already stopped.
    approval_decisions: list[str] | None = None

    # Native tool calling (SPEC.md 6). When set, the Brain is a V1 generator and its replies are
    # structured choices rather than lines of text.
    native_replies: list[NativeReply] | None = None

    # Identity (SPEC.md 4.9). Who the host says is acting. Set it and the policy broker must be
    # told; leave it and the effect must claim no identity rather than invent one.
    principal: str | None = None

    # Tools this principal may not act with, refused by policy on the identity alone. This is a
    # scripted policy engine, not the allow-list: the allow-list cannot express "not for them".
    denied_for_principal: list[str] | None = None

    # Memories the run recalls (SPEC.md 4.2), which is also how a POISONED memory is certified:
    # an injected instruction rides the same seam a remembered preference would, and the
    # perimeter must hold whether or not the Brain is fooled by it.
    memories: list[str] | None = None

    # Plural integrations (SPEC.md 4.8 v1.5). mcp_servers scripts remote tool servers in
    # REGISTRATION ORDER, each entry that server's catalog, {tool_name: reply}, because order is
    # the contract: routing is by declared ownership, first registered wins a contested name.
    # extra_skills adds skill sources after the harness's stub, in order, because accumulation is
    # only observable with more than one source.
    mcp_servers: list[dict[str, str]] | None = None

    # What a scripted server declares its tools take, {tool_name: input_schema_json}. A tool
    # with no entry takes an open object, as a real server that declares no schema would
    # (SPEC.md 6.1: what a tool takes is part of what advertises it).
    mcp_tool_schemas: dict[str, str] | None = None
    extra_skills: list[str] | None = None

    # Composition from data (SPEC.md 4.8 v1.4). When set, the vector certifies composition
    # alone: the document must refuse with the named text and no run ever happens, so
    # generator_replies and prompt are carried empty.
    configuration_json: str | None = None

    # The fleet (SPEC.md 4.8 v1.6). Each entry is a registered agent the outer agent may hand
    # work to, or transfer the whole run to, with a scripted brain of its own, created once per
    # vector so its script keeps its place across instance rebuilds.
    agents: list[FleetAgent] | None = None

    # Per-request inference (docs/per-request-inference.md). request carries what one caller
    # asked for; requests drives one request per prompt, concurrently, against a single
    # composition. contract_schema configures the deployment's contract;
    # configured_temperature / configured_max_tokens hard-configure the brain's knobs so
    # "configured wins" is certifiable. broker_honors_request = False swaps in the scripted Brain
    # that never opted in, so graceful degradation is certified against the interface's real
    # defaults. streamed runs the request through the streamed loop, which enforces every control
    # the batched one does.
    request: RequestSpec | None = None
    requests: list[RequestSpec] | None = None
    contract_schema: str | None = None
    configured_temperature: float | None = None
    configured_max_tokens: int | None = None
    broker_honors_request: bool = True
    streamed: bool = False

    # The streamed outcome (SPEC.md 4.14): run the request through the third door, the
    # enumeration's events AND the structured outcome its completion carries, so status and
    # pending-effect expectations certify on the streamed door too.
    streamed_outcome: bool = False

    # Narration (SPEC.md 6.0). tool_narrations gives a stub tool its declared templates;
    # gate_verdict_on_narration is the verdict the scripted Gate returns for model narration:
    # screened text that is neither the prompt nor a tool's output.
    tool_narrations: dict[str, ToolNarrationSpec] | None = None
    gate_verdict_on_narration: str | None = None

    # Selection (SPEC.md 4.15): a scripted selector returning this fixed set, whatever the task.
    # None means no selector, so every described tool is offered. An empty list is a valid
    # selection: the run is offered nothing. tool_descriptions gives stub tools descriptions,
    # the advertisement opt-in (6.1), so what a run was OFFERED becomes observable in the catalog
    # the Brain reads.
    select_tools: list[str] | None = None

    # Whether the offering BINDS at the Direction perimeter (SPEC.md 4.15, enforced): an act
    # naming an advertised tool the run was not offered is denied rather than reachable.
    enforce_selection: bool = False
    tool_descriptions: dict[str, str] | None = None

    # How many times a run may ask for an act the ledger already answered (SPEC.md 4.10, v1.14).
    identical_call_limit: int | None = None

    # Citation (SPEC.md 4.2, v1.18). cite_knowledge is what the deployment configured, None for
    # no opinion, and citation_prefix what each line starts with. knowledge_passages are served
    # by a plain broker that cannot say where a passage came from, so a vector can certify that
    # a passage with no source is never cited; the knowledge folder is the sourced one.
    cite_knowledge: bool | None = None
    citation_prefix: str | None = None
    knowledge_passages: list[str] | None = None
