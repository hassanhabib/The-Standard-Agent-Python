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
| 6. Host | `Standard.Agents.Host` as `standard_agents.host`, standard library only (owner decision, 2026-11-02): the HTTP exposer on an asyncio server, its gates and principal resolution, `python -m standard_agents.host` | Controllers, Acceptance/Host: 36 |

After Phase 1 the capability work is independent enough to run in parallel, one session per
capability group, each in its own worktree.

## Xeption and RESTFulSense

In C# they are NuGet packages of their own. In Python they will be too (owner decision,
2026-11-01): `xeption` and `restfulsense` on PyPI, each with its own repository, tests and
Trusted Publishing, and `the-standard-agent` depending on them. Until they are published they
live in `src/xeptions` and `src/restfulsense`, and the wheel must not ship them before then.

## Known mismatches, each fixed test-first in its phase

- `StandardAgent` does not close the stdio brokers `mcp_process` starts. C# never disposes
  them either: their process trees are killed when the host exits, and a recomposition leaves
  the old ones running. Python adds `StdioMcpBroker.aclose()` and `async with`, but a host
  composing through the door cannot reach them, so a process started in one event loop
  outlives it and its transport prints "Event loop is closed" when collected. Closing them
  needs a public `StandardAgent` lifecycle (`aclose()`, `async with`), an owner decision.
- Resolved with the trace tests (Phase 3): `AgentRun.started_on` keeps its default of
  `datetime(1, 1, 1, tzinfo=timezone.utc)`, .NET's `default(DateTimeOffset)`. On a composed
  agent every outcome line follows the run's reset, which stamps the start, so the default is
  never read there and None would change nothing. It is read when the logging broker writes an
  outcome for a run it never reset (its detached fallback run, a broker driven outside the
  loop): C# writes the milliseconds elapsed since year one, about 6.4e13 in 2026, and so does
  this port. None would make that line raise a `TypeError`, or need a branch that writes
  something else, so the default stays.

## Deliberate differences, for the README at parity

Places where Python cannot or should not reproduce .NET, kept on purpose:

- On Windows, `StdioMcpBroker` resolves a bare command with `shutil.which`, which looks in the
  current directory before PATH (always before Python 3.12, and from 3.12 unless
  `NoDefaultCurrentDirectoryInExePath` is set) and defaults PATHEXT to Python's list; C#'s
  `ResolveCommand` searches PATH only, with `.EXE;.CMD;.BAT` when PATHEXT is unset.
- The effect ledger records a tool failure as `str(exception)`, which is empty for a bare
  `Exception()` where .NET's `Message` is "Exception of type 'System.Exception' was thrown."
  Reproducing it would mean naming .NET types in Python; no C# test pins it.
- Validations read blank text with `str.isspace`, which also counts U+001C to U+001F; .NET's
  `IsNullOrWhiteSpace` does not. Brokers that reproduce a wire or file format keep the .NET set.
- Lowercasing is per character, so U+0130 stays as it is; .NET's `ToLowerInvariant` gives `i` or
  `İ` depending on its globalization mode.
- Case-insensitive mappings (tool risk, tool scope) fold their keys when the service is built, so
  a caller cannot hand in a deliberately case-sensitive mapping as C# allows with a comparer.
- The decision coordination sorts conflict keys by code point where C# uses the culture's
  comparer, and formats the judge score with `.` where C#'s `F2` uses the current culture.
- Cancellation is a cooperative stop signal, as C#'s token is: every door takes
  `cancellation: asyncio.Event | None`, `AgentRun` carries it, and the loop checks `is_set()`
  where C# checks the token, so a run stops only at a turn boundary, no effect is left
  half-recorded, and the run ends with the `cancelled` failure code (pinned end to end by
  tests/acceptance/test_resilience.py and test_failure_code.py). `task.cancel()` keeps its
  ordinary Python meaning: `asyncio.CancelledError` propagates from every door and every
  foundation and is never mapped, where C# turns a dependency's own cancellation (a cancelled
  brain stream or usage count) into a dependency or service exception.
- A streamed run reads from a background task; a reader cancelled with `task.cancel()` stops the
  run at once, where C# lets it reach its next write. A set `cancellation` event is seen at the
  next turn boundary, never inside a brain stream.

- The host (`python -m standard_agents.host`) is an asyncio HTTP/1.1 server written for it,
  not Kestrel. It answers with the routes, statuses, gates, JSON names and bodies, problem
  details and server-sent events of the C# host, and differs where Kestrel and ASP.NET do
  things the standard library does not:
  - Bearer tokens are not validated. Setting `Host:Authentication:Authority` locks every agent
    route as C# does, but nothing can unlock it: the standard library has no RS256 or ES256
    verification and no OIDC metadata client, so every agent route answers 401 (and the host
    logs why) unless `create_host(..., authenticate=...)` is handed a scheme.
    `Host:Authentication:Audience` is read by nothing.
  - No HTTPS (an https URL is refused; put TLS in front), no HTTP/2, no OpenTelemetry export
    (`OTEL_EXPORTER_OTLP_ENDPOINT` is ignored), no pooled `IHttpClientFactory` handler under the
    agent's HTTP brokers (each broker builds its own), and no appsettings.json or user secrets:
    configuration is environment variables and the command line, in ASP.NET's order.
  - A whole response carries `Content-Length`; Kestrel chunks a JSON body and the middleware's
    401 text. No `Server` header is sent. A streamed response is chunked on HTTP/1.1, as
    Kestrel's is, and closed at its end on HTTP/1.0.
  - A JSON error names the path and the C# type as System.Text.Json does, without the line and
    byte position, and a malformed document is described in Python's words.
  - An unhandled exception is a 500 with no body, as ASP.NET answers outside Development;
    WebApplicationFactory runs the C# host in Development, where it would be the developer
    exception page.
  - Expect: 100-continue is answered before the gates run, where Kestrel answers only when a
    controller reads the body, so a refused request may have sent its body for nothing.
  - agent.json is looked for in the working directory, the analog of the C# host's
    AppContext.BaseDirectory.

## Python additions

What Python has that C# does not, for the README at parity. Each is optional: leaving it unused
behaves exactly as the C# does.

- Closing an agent (owner's decision, 2026-11-02). `await agent.aclose()`, or
  `async with StandardAgent(...) as agent:`, stops every MCP server process the agent started
  with `mcp_process`, and every process each server started. C#'s `StandardAgent` never stops
  them and relies on the host exiting; without a close, Python does the same, stopping them at
  interpreter exit. Closing stops only what the agent owns: a broker handed to `use_mcp` (or any
  `use_` verb) and a handler handed to `http` are the host's, as C#'s `Http(...)` remarks say of
  handlers, and are left running. A closed agent still works: closing is not configuration, so
  the composition stays, its next run starts its servers again, and a later close stops them
  again. Nothing HTTP needs closing: urllib closes each connection once its response arrives, so
  no HTTP broker holds one between requests. The one-liner is unchanged.
- The host closes the agent it composed when it stops (Ctrl+C, SIGTERM, or
  `await host.aclose()`), as the C# container disposes the singletons it created, so a
  `StandardAgent` behind it stops the MCP server processes it started.

## Version

The library is unpublished at 1.0.0.0. When it reaches parity it takes the C# version it matches
(Standard.Agents is at 6.0.0.0 today), so one number means one behaviour in both languages.
