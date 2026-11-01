# The Standard AI Agent Framework for Python

**`Agent = Orchestration(Data, Decision, Direction)`**

The Python port of [The Standard AI Agent Framework](https://github.com/hassanhabib/The-Standard-Agent),
built to [The Standard](https://github.com/hassanhabib/The-Standard): brokers, foundation services,
orchestrations, a coordination and an exposer, every exception localized and categorized, and every
routine written test-first (each test has a `-> FAIL` commit before its `-> PASS` commit).

- **Data**: what the agent *has* (skills, memory, knowledge). Verb: **Recall**
- **Decision**: what the agent *thinks* (one brain, wrapped in a Gate and a Judge). Verb: **Think**
- **Direction**: what the agent *does* (act through a tool, or return). Verb: **Act**

Orchestration is not a fourth nature. It is the loop that turns the three.

The framework has no runtime dependencies and makes no network calls. The brain is whatever you
compose: a local open-weight model behind `use_generator`, or your own function behind `on_brain`.

## Install

```bash
pip install -e ".[test]"
```

Python 3.10 or later.

## One line, then one capability at a time

```python
import asyncio
from standard_agents import StandardAgent

async def brain(system_prompt: str, user_prompt: str) -> str:
    ...  # call your local model here; reply "ACTION: <tool>: <input>" or "FINAL: <answer>"

agent = StandardAgent().on_brain(brain)

answer = asyncio.run(agent.process_prompt("What is 47 * 89?"))
```

Everything else is opt-in, with a default that behaves as if the capability were absent:

```python
agent = (StandardAgent()
    .skills("skills")                  # who it is: Markdown, read in name order (Data)
    .memory("memory.txt")              # one memory per line (Data)
    .on_knowledge(search_journal)      # grounding for this prompt (Data)
    .on_gate(screen)                   # screen the request before the brain sees it (Decision)
    .on_judge(review)                  # review the answer before the user sees it (Decision)
    .tool(CalculatorTool())            # what it can do (Direction)
    .max_turns(7)
    .log_to("log.txt")                 # turn-by-turn trace
    .on_brain(brain))

outcome = asyncio.run(agent.run("What is 47 * 89?"))
outcome.status   # AgentStatus.RESPONDED, REFUSED, AWAITING_INPUT or FAILED
outcome.result   # the answer, or what the run says instead of one
```

Use `run` when how the run ended matters: a refusal and an answer read alike as text.

### The three ways to reach anything

| Mode | Verb | Example |
|---|---|---|
| Local | a path | `.skills("skills")`, `.memory("memory.txt")`, `.log_to("log.txt")` |
| Custom | `on_*`, your own async function | `.on_brain(fn)`, `.on_skills(fn)`, `.on_memory(fn)`, `.on_knowledge(fn)`, `.on_gate(fn)`, `.on_judge(fn)` |
| External | `use_*`, a broker that implements the interface | `.use_generator(broker)`, `.use_skills(...)`, `.use_memory(...)`, `.use_knowledge(...)`, `.use_gate(...)`, `.use_judge(...)`, `.use_logging(...)` |

### The reply protocol

The brain answers in the same text protocol the C# framework uses: an optional `SAY: <progress>`
line, then exactly one `ACTION: <tool>: <input>` or `FINAL: <answer>`. A reply with neither prefix is
taken as the answer. Skills write the tool catalog in wherever they put `{{tools}}`.

## The example agent

```bash
python -m examples.calculator_agent "What is 47 * 89?"
```

```
Prompt : What is 47 * 89?
Status : RESPONDED
Answer : 47 * 89 = 4183
```

[examples/calculator_agent](examples/calculator_agent) is the C# demo in Python: skills from a folder,
a calculator tool that parses arithmetic and never calls `eval`, a Gate that refuses requests for
credentials, and a small local brain that speaks the ACTION / FINAL protocol, so it runs with no
model and no network. Swap the brain for a model with `use_generator` and nothing else changes.

## The architecture

```
StandardAgent                                    exposer: composition, run, process_prompt
  RunCoordinationService                         the loop: Recall, Think, Act, until the run ends
    DataOrchestrationService      (Data)         skills, memories, knowledge
    DecisionOrchestrationService  (Decision)     gate, brain, judge
    DirectionOrchestrationService (Direction)    internal tools, return
      SkillService, MemoryService, KnowledgeService,
      GateService, BrainService, JudgeService,
      InternalToolService, ReturnService         foundations: validate, localize, categorize
        ISkillBroker, IMemoryBroker, IKnowledgeBroker,
        IClassifierBroker, IGeneratorBroker, IVerifierBroker,
        IToolBroker, ILoggingBroker              brokers: no logic, one resource each
```

Every service validates its own inputs, maps every exception it can see into four categories
(validation, dependency validation, dependency, service), keeps the local exception as the inner
exception all the way up, and logs the categorized exception once, before raising it.

## C# to Python mapping

| C# (Standard.Agents) | Python (standard_agents) | Why it differs, when it does |
|---|---|---|
| `interface IStorageBroker` | `class IStorageBroker(ABC)` with `@abstractmethod` | Python has no interfaces; an abstract base class is the local interface. |
| `ValueTask<T> SelectAsync()` | `async def select(self) -> T` | Every public member stays asynchronous (Standard 1.5.1). Python names coroutines without an `Async` suffix. |
| `PascalCase` methods, `camelCase` locals | `snake_case` everywhere, `PascalCase` classes | PEP 8. The words are the same: `retrieve_all_memories` is `RetrieveAllMemoriesAsync`. |
| `partial class XService` across `XService.cs`, `.Validations.cs`, `.Exceptions.cs` | `x_service.py`, `x_service_validations.py`, `x_service_exceptions.py` | Python has no partial classes. The split is kept as three modules of plain functions the service imports, rather than mixins, so there is no inheritance to chase. |
| `TryCatch(async () => { ... })` | `await try_catch(logging_broker, returning_function)` with a nested `async def` | Python lambdas cannot be `async`; a nested function is the same shape. |
| `throw await CreateAndLogValidationExceptionAsync(e)` | `raise await create_and_log_validation_exception(logging_broker, e)` | Same. |
| `Xeption` (NuGet) | `xeptions.Xeption`, beside the package | Ported, with `upsert_data_list`, `add_data`, `throw_if_contains_errors` and `same_exception_as`. It is a library, so it lives outside `standard_agents`. |
| One file per exception class under `Models/.../Exceptions/` | One `exceptions.py` per entity under `models/.../{entity}/` | Python groups related classes in a module; the folder path is the same. |
| `record AgentContext` with `with { ... }` | `@dataclass(frozen=True) AgentContext` with `dataclasses.replace` | Same immutability, Python idiom. Lists are tuples. |
| `enum AgentStatus { Working, ... }` | `class AgentStatus(Enum): WORKING = 0 ...` | PEP 8 constant names. |
| `ITool` with default members | `ITool(ABC)`: abstract `name` and `execute`, `description` defaults to `""` | Same. |
| `ToolBroker(IEnumerable<ITool>)` builds a dictionary | `ToolBroker(dict[str, ITool])`, keyed by composition | The broker holds no loop; the exposer keys tools by lower-case name as they are added. |
| `FileSkillBroker.SelectSkillsAsync()` loops and parses frontmatter | `select_skill_names()` and `select_skill_content(name)`; `SkillService` iterates | The broker rule forbids loops and branches in a broker; the C# broker breaks it, so the port moves the iteration up to the foundation. |
| `RecollectionOrchestration` + `RetrievalOrchestration` under `DataCoordinationService` (and likewise for Decision and Direction) | One `DataOrchestrationService`, `DecisionOrchestrationService`, `DirectionOrchestrationService` | The Florance pattern decides the level, not the name. With the core set of foundations, each nature has two or three, so each nature is one orchestration. |
| `RunManagementService` over three coordinations | `RunCoordinationService` over three orchestrations | One level lower for the same reason. |
| Shared `AgentOrchestration*Exception` across the natures | `DataOrchestration*`, `DecisionOrchestration*`, `DirectionOrchestration*`, `RunCoordination*` | No shared exceptions across autonomous flows. |
| `StandardAgent` fluent builder | `StandardAgent` fluent builder | Same door, same three verbs. |
| xUnit, Moq, FluentAssertions, Tynamix.ObjectFiller, DeepCloner | pytest, `unittest.mock.create_autospec`, plain `assert`, `uuid`/`random`, `copy.deepcopy` | `assert mock.mock_calls == [call...]` is `Verify(...)` and `VerifyNoOtherCalls()` in one line. |
| `XServiceTests` partial test classes | `XServiceTests` setup class; `TestXServiceLogicMethod(XServiceTests)` per file | One level of inheritance, the Python form of the shared partial constructor. |
| `ShouldThrowValidationExceptionOnAddIf...AndLogItAsync` | `test_should_raise_validation_exception_on_add_if_..._and_log_it` | Python raises rather than throws. |
| Local brain: `Standard.Agents.Decision.Brains.LlamaSharp` | Any `IGeneratorBroker` composed with `use_generator` | Provider packages stay outside the core, as in C#. |

## What was ported, and what was not

**Ported**, with tests at every layer: the Tri-Nature loop; skills (Local, Custom, External), memory
(read), knowledge (Custom, External), the Gate, the Judge with revision, internal tools, return,
refusal, the turn limit, the trace log, configuration validation, and the Xeption library.

**Not ported in this release**, each because it is its own capability in C#, with its own brokers and
services, and porting it well is a release of its own rather than a corner of this one:

| C# capability | Status |
|---|---|
| HTTP brains (`Brain(apiUrl, apiKey, model)`), native tool calling (V1 generators) | Not ported. The port makes no network calls; a local model is an `IGeneratorBroker` provider. |
| Streaming (`StreamPromptAsync`, narration channel) | Not ported. `SAY:` narration is parsed into the context but not streamed. |
| MCP servers, remote tools, agents as tools, transfer | Not ported. A tool name the agent does not own is never acted on; the brain is told so. |
| Writing memories (`RememberTool`), sessions, caller-owned history | Not ported. Memory is recalled, not written. |
| Local knowledge folders with ranking, citations | Not ported. Knowledge enters through `on_knowledge` or `use_knowledge`. |
| Contract guardian (response schemas), constitution, consumption skills | Not ported. |
| Redaction, policy, approvals, principals, effect ledger, compensation | Not ported. |
| Budgets, usage measurement, resilience and retries, telemetry, audit | Not ported. |
| Per-request inference options (`PromptRequest`) | Not ported. |
| Gate verdict caching per run, `route:` verdicts, skill conflict detection | Not ported. The Gate screens the prompt each turn. |
| ReturnService catch-all | Not ported: nothing in that routine can raise into it, so no test could reach it. |

## Building a planning agent on it

The framework is built so an agent like a planning agent over a local PyTorch model sits on it
without changing it:

- **The model** becomes a broker of its own in the agent's project, over the local PyTorch model, with
  primitives such as "imagine the outcomes of these act lines" and "score the goal after this
  journal". Any loop (decoding, beam search) belongs in a service above it, not in the broker.
- **The world** (the journal of acts and outcomes, and carrying out acts) becomes a broker too: read
  through Data (`use_knowledge`, `use_memory`) and acted on through Direction (an `ITool`).
- **Planning** becomes an orchestration in that project, over the model and world foundations,
  following the same validation and exception rules as the services here.
- **The text brain** the loop talks to is then an `IGeneratorBroker` that asks the planning
  orchestration for the next act and answers `ACTION: act: <line>` or `FINAL: <outcome>`.

## Tests

```bash
python -m pytest -q
```

Unit tests mock every dependency and assert the exact calls (`mock_calls == [...]`) so no other call
can slip through. Acceptance tests in `tests/acceptance` drive the whole agent through the real
brokers, with only the brain stood in. Brokers are not unit-tested, per The Standard; the
acceptance tests exercise them.

## License

[The Standard Software License (TSSL)](LICENSE.txt).
