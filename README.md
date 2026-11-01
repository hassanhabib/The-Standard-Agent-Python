# The Standard AI Agent Framework for Python

**`Agent = Orchestration(Data, Decision, Direction)`**

A Python implementation of [The Standard for Agents](https://github.com/hassanhabib/The-Standard-Agent-Specs/blob/main/SPEC.md),
built to [The Standard](https://github.com/hassanhabib/The-Standard). The specification is the
source of truth; the C# reference implementation,
[Standard.Agents](https://github.com/hassanhabib/The-Standard-Agent), is one realization of it.

- **Data**: what the agent *has* (skills, memory, knowledge). Verb: **Recall**
- **Decision**: what the agent *thinks* (one brain, wrapped in a Gate and a Judge). Verb: **Think**
- **Direction**: what the agent *does* (act through a tool, call out, or return). Verb: **Act**

Orchestration is not a fourth nature. It is the loop that turns the three.

The library has no runtime dependencies and makes no network calls of its own. The brain is
whatever you compose: a local open-weight model behind `use_generator`, or your own function
behind `on_brain`.

## Conformance

| | |
|---|---|
| Specification | SPEC.md **v1.18** |
| Profile claimed | **Core** (SPEC.md 8.1) |
| At version | **1.0.0.0** |
| Evidence | `python -m conformance <vectors> --profile Core`, run in CI on every change |

The evidence is reproducible by anyone (SPEC.md 1.1): the vectors are public, in the reference
implementation's repository.

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/hassanhabib/The-Standard-Agent.git reference
git -C reference sparse-checkout set conformance
python -m conformance reference/conformance/vectors --profile Core
```

The sparse checkout takes only the vectors; a full clone of the reference repository fails on
Windows, where some of its test file paths exceed the default path length.

Today the runner can drive 13 of the 88 vectors and the rest are reported `UNSUPPORTED`, never
run half-configured. Of the 13, ten pass: the six Core vectors, plus `gate-refusal-short-circuits`,
`constitution-binds-guardians`, `consumption-replaces-policy` and `judge-receives-the-task`. Three
fail, as expected for Full capabilities that are not built: `structured-tool-call` (6.1) and
`duplicate-effect-executes-once` and `a-replay-says-it-already-ran` (run-once, 4.9). No profile
above Core is claimed.

## Install

```bash
pip install -e ".[test]"
```

Python 3.10 or later. The package is typed (`py.typed`).

## One line, then one capability at a time

```python
import asyncio
from standard_agents import StandardAgent

async def brain(system_prompt: str, user_prompt: str) -> str:
    ...  # call your local model; reply "ACTION: <tool>: <input>" or "FINAL: <answer>"

agent = StandardAgent().on_brain(brain)

answer = asyncio.run(agent.process_prompt("What is 47 * 89?"))
```

Everything else is opt-in, with a default that behaves as if the capability were absent:

```python
agent = (StandardAgent()
    .skills("skills")                  # who it is: Markdown, found recursively (Data)
    .memory("memory.txt")              # one memory per line (Data)
    .on_knowledge(search_documents)    # grounding for this prompt (Data)
    .on_gate(screen)                   # screen the request before the brain sees it (Decision)
    .on_judge(review)                  # review the answer before the user sees it (Decision)
    .constitution("constitution.md")   # one law above both guardians (Decision)
    .tool(CalculatorTool())            # what it can do (Direction)
    .on_mcp(call_remote_tool)          # where an act it does not own is sent (Direction)
    .max_turns(7)
    .log_to("log.txt")                 # turn-by-turn trace, every line naming its run
    .on_brain(brain))

outcome = asyncio.run(agent.run("What is 47 * 89?"))
outcome.status   # AgentStatus.RESPONDED, REFUSED, AWAITING_INPUT, AWAITING_APPROVAL or FAILED
outcome.result   # the answer, or what the run says instead of one
```

Use `run` when how the run ended matters: a refusal and an answer read alike as text.

### The three ways to reach a capability (SPEC.md 4.8)

| Capability | Local | External (a broker) | Custom (a function) |
|---|---|---|---|
| Skills | `skills(path)` | `use_skills` | `on_skills` |
| Memory | `memory(path)` | `use_memory` | `on_memory` |
| Trace | `log_to(path)` | `use_logging` | `on_log` |
| Brain | not offered: running a model needs a runtime (a dependency) or an endpoint (a network), and Local may require neither | `use_generator` | `on_brain` |
| Knowledge | not built: a folder needs ranked retrieval (4.2) | `use_knowledge` | `on_knowledge` |
| Gate, Judge | not offered: a rule that branches is logic, which The Standard keeps out of brokers; a rule guardian is one line of `on_gate` / `on_judge` | `use_gate`, `use_judge` | `on_gate`, `on_judge` |
| Remote tools | not built: a built-in client must speak the protocol's real transports (4.8) | `use_mcp` | `on_mcp` |

A test keeps this table honest: a capability missing a mode with no recorded reason fails the
build.

### The reply protocol (SPEC.md 6.0)

`ACTION: <tool>: <input>` to act, read from the first line only; `FINAL: <answer>` to answer, and an
answer may span lines; a reply with neither is the answer itself. This library does not voice
narration, so a `SAY:` line is not peeled: it is read as the reply's first line, as 6.0 requires of
an implementation without narration.

Skills write the tool catalog in where they put `{{tools}}`, and the index of described skills
where they put `{{skills}}`. Only a tool or skill with a description is advertised; an undescribed
tool is still callable.

### The guardians (SPEC.md 4.5)

Each guardian's rubric is assembled from up to three layers, in order: an optional constitution, a
policy (built in, or replaced in both guardians by `consumption(path)`), and the framework-owned
contract, which is always present. The built-in policies and contracts ship as package Data in
`standard_agents/prompts/guardians`. The Gate answers `accept`, `route: <label>` or
`refuse: <reason>`; the Judge answers `SCORE:` and `REASON:`, and a score outside 0.0 to 1.0 is
rejected. A draft the Judge rejects is never delivered: that turn decides nothing, the reason goes
into the observations, and the next turn revises.

## The example agent

```bash
python -m examples.calculator_agent "What is 47 * 89?"
```

```
Prompt : What is 47 * 89?
Status : RESPONDED
Answer : 47 * 89 = 4183
```

[examples/calculator_agent](examples/calculator_agent): skills from a folder, a calculator tool
that parses arithmetic and never calls `eval`, a Gate that refuses requests for credentials, and a
small local brain that speaks the ACTION / FINAL protocol, so it runs with no model and no network.

## The architecture

```
StandardAgent                                    exposer: composition, run, process_prompt
  RunCoordinationService                         the loop: Recall, Think, Act, until the run ends
    DataOrchestrationService      (Data)         skills, memories, knowledge
    DecisionOrchestrationService  (Decision)     gate, brain, judge
    DirectionOrchestrationService (Direction)    internal tools, external tools, return
      SkillService, MemoryService, KnowledgeService,
      GateService, BrainService, JudgeService,
      InternalToolService, ExternalToolService,
      ReturnService                              foundations: validate, localize, categorize
        ISkillBroker, IMemoryBroker, IKnowledgeBroker,
        IClassifierBroker, IGeneratorBroker, IVerifierBroker,
        IToolBroker, IMcpBroker, ILoggingBroker  brokers: one resource each
```

Every service validates its own inputs, maps every exception into four categories (validation,
dependency validation, dependency, service), keeps the local exception as the inner exception all
the way up, and logs the categorized exception once, before raising it. Each run has its own
identity, a local of the call, so one instance serves concurrent prompts.

## Where the C# reference implementation and the specification differ

This library follows the specification at each of these points.

| Point | SPEC.md | C# Standard.Agents | This library |
|---|---|---|---|
| Status | 3.1: a closed set of six | adds a seventh, `Revising` | the six; a rejected draft leaves the turn with no decision |
| Who writes status | 3.2: Direction | Decision writes `Revising` | only Direction |
| Gate broker | 4.1: `classify(systemPrompt, input)` | `ClassifyAsync(input)`, the rubric bound at construction (`AssessAsync(systemPrompt, input)` also exists) | `classify(system_prompt, input)` |
| Judge broker | 4.1: `verify(systemPrompt, task, candidate)` | `VerifyAsync(task, candidate)`, the rubric bound at construction | `verify(system_prompt, task, candidate)` |
| Custom Judge | 4.8: no more than the capability's own contract | `OnJudge(rubric, candidate)`, the task folded into the candidate text | `on_judge(rubric, task, candidate)` |
| Recall into observations | 4.3: recall MAY seed observations | appends recalled memories and passages on every turn | adds each recalled item once |

Where both fall short of the specification:

- **Invariant 2** (prompts live in Data, never hardcoded): both write the user-message framing
  (`Task:`, `Observations so far:`) and the revision feedback sentence in code, in Decision.
- **The loop's trace reset** (5): the reference loop resets its trace at the start of each run;
  this library writes a run identity on every turn instead and never resets, because truncating a
  shared trace under concurrent runs (4.4) would erase another run's lines.

## What is not built

Everything below is a Full or optional capability (SPEC.md 8.2), and none is claimed:
structured `TOOL:` calls (6.1), provider-native tool calls (6.2), transfer and the fleet (6.3,
4.8), narration and the streamed outcome (6.0, 4.14), the perimeter (effects, policy, approval,
run-once, compensation, untrusted inbound, 4.9), redaction and allow-lists (4.6), the decision log
(4.7), resilience, budgets, cancellation and failure codes (4.10, 3.6), sessions and memory writes
(4.11), telemetry (4.12), per-request inference (4.13), selection (4.15), sourced knowledge and
citation (3.7, 4.2), ranked local knowledge (4.2), guardian overreach neutralization (Invariant 6),
the Gate's `route:` verdict steering skill selection (`retrieve_skills(route)` exists; nothing
feeds it a route yet), and composition from a data document (4.8).

## C# to Python

| C# (Standard.Agents) | Python (standard_agents) |
|---|---|
| `interface IStorageBroker` | `class IStorageBroker(ABC)` with `@abstractmethod` |
| `ValueTask<T> SelectAsync()` | `async def select(self) -> T`; coroutines carry no `Async` suffix |
| `PascalCase` members | `snake_case` members, `PascalCase` classes (PEP 8) |
| `partial class XService` across three files | `x_service.py`, `x_service_validations.py`, `x_service_exceptions.py`: plain functions the service imports, so there is no inheritance to chase |
| `TryCatch(async () => { ... })` | `await try_catch(logging_broker, returning_function)` over a nested `async def` |
| `throw await CreateAndLog...Async(e)` | `raise await create_and_log_...(logging_broker, e)` |
| `Xeption` (NuGet) | `xeptions.Xeption`, a library beside the package |
| One file per exception class | one `exceptions.py` per entity, on the same folder path |
| `record AgentContext` with `with { }` | `@dataclass(frozen=True)` with `dataclasses.replace` |
| `enum AgentStatus { Working, ... }` | `class AgentStatus(Enum): WORKING = 0 ...` |
| A coordination over two orchestrations per nature, under a management service | one orchestration per nature, under one coordination: with the core set of foundations the Florance pattern puts each one level lower |
| `AgentOrchestration*Exception` shared by the natures | `DataOrchestration*`, `DecisionOrchestration*`, `DirectionOrchestration*`, `RunCoordination*` |
| xUnit, Moq, FluentAssertions | pytest, `unittest.mock.create_autospec`; `mock_calls == [...]` is Verify plus VerifyNoOtherCalls |

## Stability and versioning

Releases follow The Standard's four-part version, `v<model>.<service>.<fix>.<build>`. The public
contracts are the `StandardAgent` composition surface, `AgentOutcome`, `AgentStatus`, `ITool`, and
the broker interfaces under `standard_agents.brokers`; a change to any of them is a model change
and increments the first segment. Nothing has been published to a package index yet.

## Tests

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

How to contribute, and the rules every change follows: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[The Standard Software License (TSSL)](LICENSE.txt).
