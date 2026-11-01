# Porting conventions: C# to Python

**C# decides behaviour; Python decides how the code reads.** Every type, field, default, branch,
message and wire format matches Standard.Agents. None of its accent does: this is Python a Python
developer would have written, following PEP 8 and PEP 257, that happens to behave exactly like
the C# framework.

## Python style

| C# accent | Python |
|---|---|
| `interface IMemoryBroker` | `class MemoryBroker(ABC)` in `memory_broker.py`: named for the role, no `I` |
| `class GeneratorBroker : IGeneratorBroker` (concrete and interface share a name) | the ABC keeps the role name (`GeneratorBroker`); the concrete class says what it is (`OpenAiGeneratorBroker`) |
| `IMemoryService` beside `MemoryService` (an interface that exists for DI and Moq) | no interface: `MemoryService` is the class, and tests autospec it directly. Brokers keep their ABCs, because a broker's interface is the seam an External provider implements |
| Overloads: `GenerateAsync(s, u)` and `GenerateAsync(s, u, inference)` | one method with keyword-only options: `generate(system_prompt, user_prompt, *, inference=None)` |
| `RecallMemoriesAsync` | `recall_memories` (coroutines carry no suffix) |
| `static AgentEffect For(...)` | `AgentEffect.create(...)` (a classmethod with an ordinary name) |
| `bool TryGetVerdict(prompt, out verdict)` | `get_verdict(prompt) -> str \| None` |
| `static AgentUsage None` / `Default` | class constants: `AgentUsage.EMPTY`, `RedactionRules.DEFAULT` |
| Get-only computed property | `@property` |
| XML doc comments | docstrings; `#` comments only for an inline why |
| `string.IsNullOrWhiteSpace(x)` | `not x or x.isspace()` |
| `x is false`, `x == null` | `not x`, `x is None` |
| Anonymous `{ Condition, Message }` rule objects | plain code, or `(condition, parameter, message)` tuples where rules accumulate |
| Partial classes: `MemoryService.cs`, `.Validations.cs`, `.Exceptions.cs` | one module, `memory_service.py`: the class, then private `_validate_...` functions, then the exception mapping |
| `TryCatch(async () => { ... })` | an async context manager: `async with _handling_exceptions(self.logging_broker):` around the body |
| `CancellationToken` parameters | none: cancelling the task cancels the work, and `asyncio.CancelledError` propagates |
| `IAsyncEnumerable<T>` | an async generator (`AsyncIterator[T]`) |
| `AsyncLocal<T>` | `contextvars.ContextVar` |
| `IReadOnlyList<T>` on a record | `tuple[T, ...]`, defaulting to `()` |
| C#'s folder misspellings (`Memorys`, `Policys`) | English: `memories`, `policies` |

Exception models keep their C# class names, because callers catch them by name, and live one
module per entity: `models/foundations/memories/exceptions.py`.

### Broker names

Where a C# concrete broker shared its interface's name, the ABC keeps the name and the concrete
class says what it is:

| C# | Python ABC | Python concrete |
|---|---|---|
| `IGeneratorBroker`, `GeneratorBroker` | `GeneratorBroker` | `OpenAiGeneratorBroker` |
| `IGeneratorBrokerV1`, `GeneratorBrokerV1` | `GeneratorBrokerV1` | `OpenAiGeneratorBrokerV1` |
| `IClassifierBroker`, `ClassifierBroker` | `ClassifierBroker` | `OpenAiClassifierBroker` |
| `IVerifierBroker`, `VerifierBroker` | `VerifierBroker` | `OpenAiVerifierBroker` |
| `IMcpBroker`, `McpBroker` | `McpBroker` | `HttpMcpBroker` |
| `ILoggingBroker`, `LoggingBroker` | `LoggingBroker` | `StdlibLoggingBroker` |
| `IFileBroker`, `FileBroker` | `FileBroker` | `LocalFileBroker` |
| `ITimeBroker`, `TimeBroker` | `TimeBroker` | `SystemTimeBroker` |
| `IToolBroker`, `ToolBroker` | `ToolBroker` | `InMemoryToolBroker` |
| `ITool` | `Tool` | |
| `IAgent` | `Agent` (`standard_agents.agent`) | |

Every other concrete broker already said what it was (`FunctionMemoryBroker`,
`FileSessionBroker`, `RetryingGeneratorBroker`) and keeps its C# name.

### JSON stays a string where C# keeps it a string

`arguments_json`, `input_schema_json`, `McpBroker.call(name, arguments_json) -> str` and their
kin carry JSON text, as in C#, so the ported tests, the conformance vectors and the wire bytes stay
one to one (owner decision, 2026-11-01).

## Paths

| C# | Python |
|---|---|
| `Standard.Agents/Models/Clients/Agents/AgentOutcome.cs` | `src/standard_agents/models/clients/agents/agent_outcome.py` |
| `Standard.Agents/Services/Foundations/Memorys/MemoryService*.cs` | `src/standard_agents/services/foundations/memories/memory_service.py` |
| `Standard.Agents/Brokers/Memorys/IMemoryBroker.cs` | `src/standard_agents/brokers/memories/memory_broker.py` |

## Tests

pytest, written the way pytest is meant to be written:

| C# | Python |
|---|---|
| `MemoryServiceTests.cs` (constructor building mocks and the service) | `tests/unit/services/foundations/memories/conftest.py` with fixtures: `memory_broker`, `logging_broker`, `memory_service`, and factory fixtures for random data (`create_random_string`) |
| `MemoryServiceTests.Logic.Remember.cs`, `.Logic.RecallMemories.cs`, ... | one module per kind, not per method: `test_memory_service_logic.py`, `test_memory_service_validations.py`, `test_memory_service_exceptions.py`. The split is The Standard's; the file-per-method layout is only how C# organizes partial classes |
| `[Fact] public async Task ShouldRememberAsync()` | `async def test_should_remember(memory_service, memory_broker):` (pytest-asyncio, auto mode); the name is what `tools/parity.py` matches |
| `[Theory]` with `[InlineData]` / `[MemberData]` | `@pytest.mark.parametrize` |
| `new Mock<IMemoryBroker>()` | `create_autospec(MemoryBroker, instance=True)` |
| `.ReturnsAsync(x)` / `.ThrowsAsync(e)` | `.return_value = x` / `.side_effect = e` |
| `Verify(..., Times.Once)` and `VerifyNoOtherCalls()` | `assert memory_broker.mock_calls == [call.insert_memory(memory)]` |
| `Assert.ThrowsAsync<T>` | `with pytest.raises(T) as raised:` |
| `BeEquivalentTo` on an exception | `assert raised.value.same_exception_as(expected)`; `==` for dataclasses |
| `It.Is(SameExceptionAs(expected))` in a `Verify` | `call.log_error(same_exception_as(expected))`, where the `same_exception_as` fixture is a small matcher class in `conftest.py` |
| `DeepClone()` | `copy.deepcopy` |
| Tynamix random values | small helpers in `conftest.py` over `uuid` and `random` |

## Native exceptions

A .NET exception a foundation catches maps to the Python one that the same failure raises.

| .NET | Python |
|---|---|
| `FileNotFoundException` | `FileNotFoundError` |
| `DirectoryNotFoundException` | `FileNotFoundError` raised for a missing directory, and `NotADirectoryError` |
| `UnauthorizedAccessException` | `PermissionError` |
| `IOException` | `OSError` (caught after the more specific ones, as C# does) |
| `KeyNotFoundException` | `KeyError` |
| `ArgumentException`, `FormatException` | `ValueError` |
| `InvalidOperationException` | `RuntimeError` |
| `JsonException` | `json.JSONDecodeError`, and `ValueError` where a value has the wrong shape |
| `TaskCanceledException`, `OperationCanceledException` | `asyncio.CancelledError` (a timeout is `TimeoutError`) |
| `HttpRequestException` | `restfulsense.HttpRequestException` |
| RESTFulSense `HttpResponse*Exception` | the same names in `restfulsense` |

## Libraries beside the package

- `xeptions`: `Xeption`, with `upsert_data_list`, `add_data`, `throw_if_contains_errors` and
  `same_exception_as`.
- `restfulsense`: `RESTFulApiFactoryClient` over `urllib` and one exception type per status code,
  so a broker stays a single call and the status-code mapping lives in the library, as in C#.

## Text

No em dashes (U+2014) in anything written: commas, colons, periods or parentheses instead.
