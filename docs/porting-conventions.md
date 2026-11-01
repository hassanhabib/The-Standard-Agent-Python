# Porting conventions: C# to Python

Every port follows these, so a Python file can be laid beside its C# original and read line for
line. Where a convention and the C# disagree, the C# behaviour wins; the convention only decides
spelling.

## Paths and names

| C# | Python |
|---|---|
| `Standard.Agents/Models/Foundations/Memorys/Exceptions/*.cs` | `src/standard_agents/models/foundations/memorys/exceptions.py` (one module per Exceptions folder) |
| `Standard.Agents/Models/Clients/Agents/AgentOutcome.cs` | `src/standard_agents/models/clients/agents/agent_outcome.py` |
| `Standard.Agents/Services/Foundations/Memorys/MemoryService.cs` | `src/standard_agents/services/foundations/memorys/memory_service.py` |
| `MemoryService.Validations.cs`, `MemoryService.Exceptions.cs` | `memory_service_validations.py`, `memory_service_exceptions.py` (functions the service imports) |
| `IMemoryService` | `class IMemoryService(ABC)` in `imemory_service.py` |
| `RecallMemoriesAsync` | `recall_memories` |
| Folder spellings | kept as C# spells them, in snake_case: `Memorys` is `memorys`, `Policys` is `policys` |

## Tests

| C# | Python |
|---|---|
| `Standard.Agents.Tests.Unit/Services/Foundations/Memorys/MemoryServiceTests.cs` | `tests/unit/services/foundations/memorys/memory_service_tests.py`, class `MemoryServiceTests` (setup and helpers) |
| `MemoryServiceTests.Logic.Remember.cs` | `test_memory_service_logic_remember.py`, class `TestMemoryServiceLogicRemember(MemoryServiceTests)` |
| `ShouldRememberAsync` | `test_should_remember` (the name `tools/parity.py` matches) |
| `[Theory]` with `[InlineData]` / `[MemberData]` | `@pytest.mark.parametrize` |
| `Mock<IMemoryBroker>` | `create_autospec(IMemoryBroker, instance=True)` |
| `Setup(...).ReturnsAsync(x)` / `.ThrowsAsync(e)` | `mock.method.return_value = x` / `mock.method.side_effect = e` |
| `Verify(..., Times.Once)` then `VerifyNoOtherCalls()` | `assert mock.mock_calls == [call.method(...)]` |
| `It.Is(SameExceptionAs(expected))` | `expected.same_exception_as(actual)` |
| `Should().BeEquivalentTo(expected)` | `assert actual == expected` (dataclass equality), or `same_exception_as` for exceptions |
| `DeepClone()` | `copy.deepcopy` |
| `Tynamix.ObjectFiller` random values | `uuid.uuid4().hex`, `random` |
| `[Fact] async Task` | a plain test that runs the coroutine with `asyncio.run` |

## Native exceptions

A .NET exception a foundation catches maps to the Python one that the same failure raises.

| .NET | Python |
|---|---|
| `FileNotFoundException` | `FileNotFoundError` |
| `DirectoryNotFoundException` | `FileNotFoundError` raised for a missing directory, and `NotADirectoryError` |
| `UnauthorizedAccessException` | `PermissionError` |
| `IOException` | `OSError` (catch it after the more specific ones, as C# does) |
| `KeyNotFoundException` | `KeyError` |
| `ArgumentException`, `FormatException` | `ValueError` |
| `JsonException` | `json.JSONDecodeError`, and `ValueError` where a value has the wrong shape |
| `TaskCanceledException`, `OperationCanceledException` | `asyncio.CancelledError` |
| `HttpRequestException` | `restfulsense.HttpRequestException`, which wraps `urllib.error.URLError` and `OSError` from the transport |
| RESTFulSense `HttpResponse*Exception` | the same names in the `restfulsense` package |

## Libraries beside the package

The C# framework takes two libraries from NuGet. Each is ported as a package of its own in
`src/`, outside `standard_agents`, so the framework depends on them the way C# does:

- `xeptions`: `Xeption`, with `upsert_data_list`, `add_data`, `throw_if_contains_errors` and
  `same_exception_as`.
- `restfulsense`: an HTTP client over `urllib`, raising one exception type per status code, so a
  broker stays a single call and the status-code mapping lives in the library, as it does in C#.

## Text

No em dashes (U+2014) in anything written: commas, colons, periods or parentheses instead. Text the
C# framework ships as Data (rubrics, protocol text) is carried over with that one change.
