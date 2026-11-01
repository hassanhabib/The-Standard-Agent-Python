# Porting plan: a 100% match with Standard.Agents (C#)

The owner's target, set 2026-11-01:

- **The C# framework wins, exactly.** Where the C# reference implementation and SPEC.md disagree
  (a `Revising` status, guardian brokers that bind their rubric at construction, the Custom Judge's
  arguments, recall that appends every turn), this library mirrors C#. The README records each
  point where the specification says otherwise.
- **Done means** all 88 conformance vectors pass, the four readiness profiles (Core, Reliable,
  Enterprise, Critical) certify, and every C# unit and acceptance test has a Python twin.
- **Network brokers ship**, built on the standard library only: the OpenAI-compatible and Anthropic
  brains, and MCP clients over HTTP and standard input and output. The library still makes no call
  a host did not compose.

Publishing to PyPI is on hold until the target is met.

## How progress is measured

```bash
python tools/parity.py ../The-Standard-Agent/Standard.Agents.Tests.Unit --missing
python -m conformance ../The-Standard-Agent/conformance/vectors --profile Critical
```

`parity.py` matches every C# `[Fact]` and `[Theory]` to a Python test by name
(`ShouldAddMemoryAsync` is `test_should_add_memory`). Ported tests take the C# name exactly, so the
Python suite reads like the C# one. At the start: 2 of 577.

## Phases

Each phase lands as a series of PRs, one operation each, with FAIL/PASS commits. A phase is done
when its tests are at parity and the whole suite is green.

| Phase | Scope | C# tests |
|---|---|---|
| 1. Skeleton | The C# models (`AgentContext` in full, `AgentStatus` with `Revising`, `AgentOutcome`, `AgentFailure`, `PromptRequest`, `AgentStreamEvent`, effects, sessions, usage), the C# logging broker, and the C# tiers: foundations, then the Retrieval, Recollection, Inference, Guardian, Execution and Perimeter orchestrations, the Data, Decision and Direction coordinations, and `RunManagementService` | Services: 241 |
| 2. The door | `StandardAgent` in full, `IAgent`, `AgentTool`, `RememberTool`, composition from JSON, tier discipline | Clients, Tools, Architecture, Packaging: 92 |
| 3. Capabilities | Acceptance, one capability per PR in the C# order: revision, retrieval and citation, memory opt-out, rules, sessions and resumption, perimeter, permissions, approvals, the effect ledger, compensation, identity, redaction, budgets, resilience, failure codes, the decision log, traces, telemetry, per-request inference, caller tools, contracts, selection, narration, streamed outcome, native tool calls | Acceptance: 179 |
| 4. Wire | Standard-library clients and their wire contracts: OpenAI-compatible text and native, Anthropic native, provider options, MCP over HTTP (JSON and event-stream replies, sessions, pagination), MCP over standard input and output | Wire: 40 |
| 5. Certification | The conformance runner driving every vector field; Core, Reliable, Enterprise and Critical certified in CI | 88 vectors |
| 6. Host (not yet chosen) | `Standard.Agents.Host`: the OpenAI-compatible HTTP exposer, its gates and principal resolution | Controllers, Acceptance/Host: 36 |

After Phase 1 the capability work is independent enough to run in parallel, one session per
capability group, each in its own worktree.

## Xeption and RESTFulSense

In C# they are NuGet packages of their own. In Python they will be too (owner decision,
2026-11-01): `xeption` and `restfulsense` on PyPI, each with its own repository, tests and
Trusted Publishing, and `the-standard-agent` depending on them. Until they are published they
live in `src/xeptions` and `src/restfulsense`, and the wheel must not ship them before then.

## Known mismatches, each fixed test-first in its phase

- `HttpMcpBroker` reads an event-stream data line as blank with `str.isspace`, which also counts
  U+001C to U+001F; .NET's `IsNullOrWhiteSpace` does not (Phase 4, MCP over HTTP).
- Resolved with `RunManagementService` (Phase 1): cancellation. C# stops a run only at a turn
  boundary, so no effect is left half-recorded, and the run then ends normally with the
  `cancelled` failure code. The Python form is a cooperative stop signal: every door takes
  `cancellation: asyncio.Event | None`, `AgentRun` carries it as `cancellation`, and the loop
  checks `is_set()` where C# checks the token, with the same outcome. `task.cancel()` keeps its
  ordinary Python meaning: `asyncio.CancelledError` propagates from every door and is never
  mapped, so a dependency's own cancellation reaches the caller as a cancellation where C# maps
  it to a service error on the batched door. The foundations do the same: C# turns a cancelled
  brain stream or usage count into a dependency or service exception, while the Python lets
  `asyncio.CancelledError` propagate.
- `mcp_json.parse` has no depth limit. `JsonNode.Parse` refuses nesting deeper than 64, so the
  external tool service sends such input wrapped as `{"input": ...}` in C# and as given in
  Python (Phase 4).
- `StdioMcpBroker` raises `TypeError` when given a command without arguments (`list(None)`),
  has no `async with` lifecycle (cleanup rides `atexit`), finds child processes through `/proc`
  only, and resolves the command by hand where `shutil.which` would do (Phase 4).
- Type hints that do not hold: the MCP tool list models type fields that may be None as
  non-optional, and `HttpMcpBroker._post` returns `tuple[Any, str]` where a `type[T]` gives `T`
  (Phase 4).
- Resolved with the trace tests (Phase 3): `AgentRun.started_on` keeps its default of
  `datetime(1, 1, 1, tzinfo=timezone.utc)`, .NET's `default(DateTimeOffset)`. On a composed
  agent every outcome line follows the run's reset, which stamps the start, so the default is
  never read there and None would change nothing. It is read when the logging broker writes an
  outcome for a run it never reset (its detached fallback run, a broker driven outside the
  loop): C# writes the milliseconds elapsed since year one, about 6.4e13 in 2026, and so does
  this port. None would make that line raise a `TypeError`, or need a branch that writes
  something else, so the default stays.
- The direction coordination records a tool failure on the ledger as `str(exception)`, which is
  empty for a bare `Exception()`; .NET's message there is "Exception of type 'System.Exception'
  was thrown." (Phase 3, the effect ledger).

## Deliberate differences, for the README at parity

Places where Python cannot or should not reproduce .NET, kept on purpose:

- Validations read blank text with `str.isspace`, which also counts U+001C to U+001F; .NET's
  `IsNullOrWhiteSpace` does not. Brokers that reproduce a wire or file format keep the .NET set.
- Lowercasing is per character, so U+0130 stays as it is; .NET's `ToLowerInvariant` gives `i` or
  `İ` depending on its globalization mode.
- Case-insensitive mappings (tool risk, tool scope) fold their keys when the service is built, so
  a caller cannot hand in a deliberately case-sensitive mapping as C# allows with a comparer.
- The decision coordination sorts conflict keys by code point where C# uses the culture's
  comparer, and formats the judge score with `.` where C#'s `F2` uses the current culture.
- A streamed run reads from a background task; a reader cancelled with `task.cancel()` stops the
  run at once, where C# lets it reach its next write. A set `cancellation` event is seen at the
  next turn boundary, never inside a brain stream.

## Version

The library is unpublished at 1.0.0.0. When it reaches parity it takes the C# version it matches
(Standard.Agents is at 6.0.0.0 today), so one number means one behaviour in both languages.
