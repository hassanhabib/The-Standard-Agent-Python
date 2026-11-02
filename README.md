# The Standard AI Agent Framework for Python

**`Agent = Orchestration(Data, Decision, Direction)`**

The Python twin of [Standard.Agents](https://github.com/hassanhabib/The-Standard-Agent), the C#
reference implementation of [The Standard for Agents](https://github.com/hassanhabib/The-Standard-Agent-Specs/blob/main/SPEC.md),
built to [The Standard](https://github.com/hassanhabib/The-Standard).

The C# framework decides the behaviour; Python decides how the code reads. Every model, broker,
service, message, wire format and run outcome matches Standard.Agents, and every C# unit,
acceptance, wire, client and host test has a Python twin under the same name. The code itself is
Python: abstract base classes named for their role, keyword-only options instead of overloads,
coroutines without an `Async` suffix, dataclasses, docstrings.

- **Data**: what the agent *has* (skills, memory, knowledge). Verb: **Recall**
- **Decision**: what the agent *thinks* (one brain, wrapped in a Gate and a Judge). Verb: **Think**
- **Direction**: what the agent *does* (act through a tool, call out, or return). Verb: **Act**

Orchestration is not a fourth nature. It is the loop that turns the three.

The library has no runtime dependencies and makes no network call a host did not compose. The
brain is whatever you point it at: an OpenAI-compatible endpoint (a local open-weight model
served by Ollama, vLLM or llama.cpp works as is), the Anthropic Messages API, or your own
function.

## Conformance

| | |
|---|---|
| Matches | Standard.Agents **6.0.0.0** (C#) |
| Profiles certified | **Core, Reliable, Enterprise, Critical** (SPEC.md 8) |
| Vectors | **88 of 88** pass |
| C# tests with a Python twin | **577 of 577** |
| Evidence | `python -m conformance <vectors> --profile Critical`, run in CI on every change |

The evidence is reproducible by anyone (SPEC.md 1.1). The vectors are public, in the C#
repository; a sparse checkout takes only them (a full clone of that repository fails on Windows,
where some of its test file paths exceed the default path length):

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/hassanhabib/The-Standard-Agent.git reference
git -C reference sparse-checkout set conformance
python -m conformance reference/conformance/vectors --profile Critical
```

The runner is a port of the C# runner (Standard.Agents.Conformance) and drives every field of
every vector.

## Install

```bash
pip install the-standard-agent
```

The distribution is `the-standard-agent`; the import is `standard_agents`. Python 3.10 or later.
The package is typed (`py.typed`).

## One line

```python
import asyncio

from standard_agents import StandardAgent


async def main() -> None:
    agent = StandardAgent(api_url="http://localhost:11434/v1/", api_key="", model="llama3.1")

    print(await agent.process_prompt("What is 47 * 89?"))


asyncio.run(main())
```

That is a working agent: a brain behind an OpenAI-compatible endpoint, skills from `./Skills`, a
memory in `./memory.txt`, knowledge from `./Knowledge`, and the reply protocol (`ACTION`, `TOOL`,
`TRANSFER`, `FINAL`, `SAY`) driving the loop.

## Then one capability at a time

Every capability is a method that returns the agent, so they chain, and every one is optional:
a capability you do not name behaves as if it did not exist.

```python
from datetime import timedelta
from decimal import Decimal

agent = (
    StandardAgent(api_url="http://localhost:11434/v1/", api_key="", model="llama3.1")
    .skills("skills")
    .memory("memory.txt")
    .knowledge("knowledge", max_results=3)
    .tool(CalculatorTool())
    .mcp_process("python", arguments=["weather_server.py"])
    .rule_gate("password", "api key")
    .require_approval("send_email")
    .redact()
    .sessions("sessions")
    .budget(max_tokens=20_000, max_wall_clock=timedelta(seconds=30))
    .max_turns(8)
    .log_to("trace.txt"))
```

A tool is a class:

```python
from standard_agents.tools.tool import Tool


class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic, such as 2 + 2."

    async def execute(self, input: str) -> str:
        return str(evaluate(input))
```

### The three ways to reach anything

Each capability can be named three ways (SPEC.md 4.8):

- **Configured**: the framework's own broker from a path or an endpoint: `.memory("memory.txt")`,
  `.gate(api_url=..., api_key=..., model=...)`, `.mcp("https://tools.example/mcp")`.
- **Custom**: your function, in place of the broker: `.on_brain(fn)`, `.on_memory(recall, remember)`,
  `.on_approval(fn)`. An async function for anything the C# framework awaits.
- **External**: your own implementation of the broker's abstract base class: `.use_memory(broker)`,
  `.use_generator(broker)`, `.use_mcp(broker)`.

### The agent as data

The whole agent can be a JSON document, which is what a low-code platform writes:

```python
agent = StandardAgent.from_json_file("agent.json")
```

```json
{
  "brain": { "apiUrl": "http://localhost:11434/v1/", "apiKey": "", "model": "llama3.1" },
  "skills": "skills",
  "maxTurns": 8,
  "requireApproval": ["send_email"]
}
```

`StandardAgent.document_schema_json()` returns the JSON Schema of the document.

## How a run ends

`process_prompt` returns the answer's text. `run` returns how the run ended as well as what it
produced, because a run can end answered, refused, held on an authority, waiting on the caller,
or out of turns, and only the first makes the result an answer:

```python
from standard_agents.models.orchestrations.agents.agent_status import AgentStatus

outcome = await agent.run("Send the report to Sam")

if outcome.status is AgentStatus.AWAITING_APPROVAL:
    print("Waiting on:", outcome.pending_effect)
```

Streaming carries the same run as events, and the same outcome once the stream ends:

```python
stream = agent.run_stream("What is 47 * 89?")

async for event in stream:
    print(event.type, event.content)

print(stream.outcome.status)
```

A run stops at its next turn boundary when its `cancellation` event is set, so no effect is left
half-recorded, and it ends with the `cancelled` failure code, as a C# run does when its token is
cancelled:

```python
stop = asyncio.Event()
outcome = await agent.run("Summarize the folder", cancellation=stop)
```

Cancelling the task itself (`task.cancel()`) keeps its ordinary Python meaning.

## Closing an agent

An agent that starts MCP server processes (`mcp_process`) can stop them:

```python
async with StandardAgent(api_url="http://localhost:11434/v1/", api_key="", model="llama3.1") as agent:
    print(await agent.process_prompt("What's the weather?"))
```

or `await agent.aclose()`. This is a Python addition: the C# framework never stops them and
relies on the host exiting, and an agent you never close behaves exactly that way. Closing stops
only what the agent started; a broker or handler you handed it stays yours.

## Hosting

```bash
python -m standard_agents.host --urls http://0.0.0.0:5000
```

The host exposes an agent over HTTP with the routes, gates, JSON and server-sent events of the C#
host (`POST api/V1/agents/runs`, `POST api/V1/agents/streams`, and the V0 routes beside them),
built on the standard library. Configuration, the API key gate and the identity gate are in
[the hosting guide](https://github.com/hassanhabib/The-Standard-Agent-Python/blob/main/docs/hosting.md).

## The example agent

```bash
python -m examples.calculator_agent "What is 47 * 89?"
```

```
Prompt : What is 47 * 89?
Status : RESPONDED
Answer : 47 * 89 = 4183
```

[The example](https://github.com/hassanhabib/The-Standard-Agent-Python/tree/main/examples/calculator_agent)
composes skills from a folder, a calculator tool that parses arithmetic and never calls `eval`, a
Gate that refuses requests for credentials, and a small local brain that speaks the reply
protocol, so it runs with no model and no network.

## The architecture

```
StandardAgent                                 exposer: composition and the run doors
  RunManagementService                        the loop: Recall, Think, Act, until the run ends
    DataCoordinationService                   Data: skills, memory, knowledge, sessions
      RetrievalOrchestrationService, RecollectionOrchestrationService
    DecisionCoordinationService               Decision: gate, brain, judge, contract
      InferenceOrchestrationService, GuardianOrchestrationService
    DirectionCoordinationService              Direction: tools, transfers, the perimeter
      ExecutionOrchestrationService, PerimeterOrchestrationService
        SkillService, MemoryService, KnowledgeService, SessionService, BrainService,
        GateService, JudgeService, ContractService, UsageService, InternalToolService,
        ExternalToolService, ReturnService, PolicyService, ApprovalService,
        EffectLedgerService                   foundations: validate, localize, categorize
          GeneratorBroker, ClassifierBroker, VerifierBroker, McpBroker, MemoryBroker,
          SessionBroker, LoggingBroker, ...   brokers: one resource each
```

Every service validates its inputs, maps every failure into four categories (validation,
dependency validation, dependency, service), keeps the local exception as the inner exception all
the way up, and logs the categorized exception once, before raising it.

## C# to Python

| C# (Standard.Agents) | Python (standard_agents) |
|---|---|
| `new StandardAgent(url, key, model)` | `StandardAgent(api_url=url, api_key=key, model=model)` |
| `.Memory(path)`, `.OnBrain(fn)`, `.UseGate(broker)` | `.memory(path)`, `.on_brain(fn)`, `.use_gate(broker)` |
| `StandardAgent.FromJson(json)` | `StandardAgent.from_json(json)` |
| `ProcessPromptAsync`, `RunAsync`, `RunStreamAsync` | `process_prompt`, `run`, `run_stream` |
| `CancellationToken` | `cancellation: asyncio.Event` |
| `interface IMemoryBroker` | `class MemoryBroker(ABC)` |
| `GeneratorBroker` (the OpenAI-compatible brain) | `OpenAiGeneratorBroker` |
| `ITool` | `Tool` |
| Overloads (`GenerateAsync(s, u)`, `GenerateAsync(s, u, inference)`) | one method with a keyword-only option: `generate(s, u, *, inference=None)` |
| `ValueTask<T> SelectMemoriesAsync()` | `async def select_memories(self) -> Sequence[str]` |
| `IAsyncEnumerable<T>` | an async generator |
| `record AgentContext` with `with { }` | `@dataclass(frozen=True)` with `dataclasses.replace` |
| `AgentUsage.None`, `AgentEffect.For(...)`, `TryGetVerdict` | `AgentUsage.EMPTY`, `AgentEffect.create(...)`, `get_verdict` |
| Partial classes and `TryCatch` | one module per service, and `async with _handling_exceptions(...)` |
| `Xeption`, RESTFulSense | `xeptions`, `restfulsense` |
| xUnit, Moq, FluentAssertions | pytest, `unittest.mock.create_autospec`, `mock_calls == [...]` |

## Where Python differs, on purpose

The behaviour matches C# except where Python cannot or should not reproduce .NET:

- **Text rules.** Validations read blank text with `str.isspace`, which also counts U+001C to
  U+001F. Lowercasing is per character, so U+0130 stays as it is. Brokers that reproduce a wire or
  file format keep the .NET rules.
- **Culture.** Conflict keys sort by code point, and the judge score is formatted with `.`, where
  C# uses the current culture.
- **Case-insensitive mappings** (tool risk, tool scope) fold their keys when the agent is built.
- **Failure detail.** The effect ledger records a tool failure as `str(exception)`, which is empty
  for a bare `Exception()`.
- **Cancellation.** `task.cancel()` raises `asyncio.CancelledError` from every door and is never
  mapped into a categorized exception. A streamed run cancelled by its reader stops at once.
- **Commands.** On Windows a bare MCP command is resolved with `shutil.which`.
- **The host** is a standard-library HTTP/1.1 server, not Kestrel: no HTTPS (put TLS in front),
  no HTTP/2, no bearer-token validation (with an authority configured, every agent route answers
  401 unless the host is given an authentication scheme), and configuration from environment
  variables and the command line. The hosting guide lists the rest.

## Python additions

Optional, and leaving them unused behaves exactly as C# does:

- `await agent.aclose()` and `async with StandardAgent(...)`, which stop the MCP server
  processes the agent started.
- The host closes the agent it composed when it stops.

## Versioning

Releases follow The Standard's four-part version, `<model>.<service>.<fix>.<build>`, and take the
C# version they match, so one number means one behaviour in both languages.

## Contributing

How to contribute, and the rules every change follows:
[CONTRIBUTING.md](https://github.com/hassanhabib/The-Standard-Agent-Python/blob/main/CONTRIBUTING.md).

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

## License

[The Standard Software License (TSSL)](https://github.com/hassanhabib/The-Standard-Agent-Python/blob/main/LICENSE.txt).
