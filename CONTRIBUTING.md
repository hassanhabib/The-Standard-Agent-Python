# Contributing

This library is built to [The Standard](https://github.com/hassanhabib/The-Standard) and to the
[Standard for Agents specification](https://github.com/hassanhabib/The-Standard-Agent-Specs/blob/main/SPEC.md).
The specification is the source of truth for behaviour; the C# reference implementation,
[Standard.Agents](https://github.com/hassanhabib/The-Standard-Agent), is one example of it.

## The shape of a change

- **One operation per branch.** Name it `users/<github-username>/<CATEGORY>-<entity>-<action>`,
  using the language of the layer: brokers `insert`, `select-all`, `update`, `delete`;
  foundations `add`, `retrieve-all`, `modify`, `remove`; orchestrations and coordinations the
  verb of the nature (`recall`, `think`, `act`, `run`).
- **Categories** are The Standard's: `INFRA`, `DATA`, `BROKERS`, `FOUNDATIONS`, `ORCHESTRATIONS`,
  `COORDINATIONS`, `EXPOSERS`, `ACCEPTANCE`, `DOCUMENTATION`, `CODE RUB`, `MINOR FIX`, and their
  `MAJOR` / `MEDIUM` / `MINOR` forms.
- **Pull request titles** are `CATEGORY: Description In Pascal Case`, for example
  `FOUNDATIONS: Retrieve All Memories`.

## Test-first, in pairs

Every behaviour lands as two commits:

1. `test_should_... -> FAIL`: the new test, any exception models it needs, and a stub that raises
   `NotImplementedError`. The test **must run and fail**; a collection error or an import error is
   not a failure.
2. `test_should_... -> PASS`: only the implementation that makes it pass, with **the whole suite**
   green.

Code that has no behaviour of its own (brokers, data models, configuration) lands as
`CATEGORY: Description` commits instead.

## The layers

| Layer | Folder | Rule |
|---|---|---|
| Brokers | `src/standard_agents/brokers` | One resource each. No branching, no loops: expose primitives and let the foundation iterate. |
| Foundations | `src/standard_agents/services/foundations` | One entity broker each. Validate, localize native exceptions, categorize. |
| Orchestrations | `src/standard_agents/services/orchestrations` | One per nature, two or three foundations each. Unwrap foundation categories into their own. |
| Coordination | `src/standard_agents/services/coordinations` | The loop. Sequencing and observing only. |
| Exposer | `src/standard_agents/standard_agent.py` | Composition and mapping. One service dependency. |

Each service is three modules: `x_service.py` (the routines), `x_service_validations.py` and
`x_service_exceptions.py`, imported explicitly. Exceptions for an entity live in
`models/<layer>/<entity>/exceptions.py`, and every one of them derives from `xeptions.Xeption`.

## Tests

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

- Unit tests mock every dependency with `create_autospec` and assert the exact calls with
  `mock.mock_calls == [...]`, so no other call can slip through.
- Acceptance tests in `tests/acceptance` drive the whole agent through the real brokers.
- Conformance: see the README. A change that alters a behaviour the specification governs must keep
  the claimed profile passing, and a change the specification does not yet describe is proposed to
  the specification first.

## Versioning

Releases follow The Standard's four-part version, `v<model>.<service>.<fix>.<build>`: a model change
increments the first segment, a service or routine change the second, a fix or configuration change
the third, an automated build the fourth, and a higher-order change resets every segment below it.
