# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""The package as The Standard's tier rules read it.

The C# suite reflects over the Standard.Agents assembly. Here every module of standard_agents is
imported and each class is read where it is defined: its module is its namespace, and
typing.get_type_hints resolves each constructor parameter to the class it names, so a rule
compares classes rather than spellings.
"""

import collections.abc
import functools
import importlib
import inspect
import pkgutil
import re
import types
import typing

import pytest

import standard_agents


class Parameter(typing.NamedTuple):
    name: str
    annotation: object


class TierMap:
    """The classes of standard_agents, and what each one takes."""

    # Observability, plus the clock. None backs a nature; none can change what the agent decides.
    # Telemetry earns the same exemption the same way: spans and metrics observe the loop and
    # steer nothing. Resilience is deliberately NOT here: it changes control flow, so it does not
    # get logging's exemption; it is applied by decorating a broker at composition.
    utility_brokers = frozenset({"LoggingBroker", "TimeBroker", "AuditBroker", "TelemetryBroker"})

    def __init__(self, package: types.ModuleType) -> None:
        modules = tuple(_modules_of(package))
        self.classes = tuple(dict.fromkeys(
            value
            for module in modules
            for value in vars(module).values()
            if inspect.isclass(value) and value.__module__ == module.__name__))

    def services_under(self, tier: str) -> tuple[type, ...]:
        return tuple(
            cls for cls in self.classes
            if not inspect.isabstract(cls)
            and f".services.{tier}" in cls.__module__
            and cls.__name__.endswith("Service"))

    def services_above_foundations(self) -> tuple[type, ...]:
        """Every tier above foundations, named explicitly.

        A tier missing from this list is a tier nobody is checking, which is how the loop
        briefly escaped the rule when it moved from Coordinations to Managements.
        """
        return (
            self.services_under("orchestrations")
            + self.services_under("coordinations")
            + self.services_under("managements"))

    def brokers(self) -> tuple[type, ...]:
        return tuple(
            cls for cls in self.classes
            if not inspect.isabstract(cls)
            and ".brokers." in cls.__module__
            and cls.__name__.endswith("Broker"))

    @staticmethod
    def broker_contracts_implemented_by(cls: type) -> tuple[type, ...]:
        """The interfaces a broker implements: the abstract broker classes it derives from."""
        return tuple(base for base in cls.__mro__[1:] if _is_broker_contract(base))

    def constructors(self, cls: type) -> tuple[tuple[Parameter, ...], ...]:
        """The C# constructor overloads, as Python's one keyword-only __init__ carries them.

        A C# overload set becomes one __init__ (docs/porting-conventions.md): the required
        parameters are in every overload, and each optional one stands for the overload that
        adds it. So MemoryService reads as one constructor over its memory broker and one over
        the file broker, as it does in C#, rather than as one constructor taking both.
        """
        initializer = cls.__init__

        if initializer is object.__init__:
            return ((),)

        hints = typing.get_type_hints(initializer)
        parameters = tuple(inspect.signature(initializer).parameters.values())[1:]

        required = tuple(
            Parameter(parameter.name, hints.get(parameter.name))
            for parameter in parameters if parameter.default is inspect.Parameter.empty)

        optional = tuple(
            Parameter(parameter.name, hints.get(parameter.name))
            for parameter in parameters if parameter.default is not inspect.Parameter.empty)

        if not optional:
            return (required,)

        return tuple(required + (parameter,) for parameter in optional)

    def broker_sets_taken_by(self, cls: type) -> tuple[frozenset[str], ...]:
        """Per CONSTRUCTOR, not per type.

        MemoryService and KnowledgeService each offer a constructor over their own broker and
        one over the file broker, and each takes exactly one. Counting across overloads would
        read that as two and be wrong.
        """
        return tuple(
            frozenset(
                self.role(_unwrap(parameter.annotation).__name__)
                for parameter in constructor
                if _is_broker_contract(_unwrap(parameter.annotation)))
            for constructor in self.constructors(cls))

    def brokers_taken_by(self, cls: type) -> frozenset[str]:
        return frozenset().union(*self.broker_sets_taken_by(cls))

    @staticmethod
    def dependencies_in(constructor: tuple[Parameter, ...]) -> tuple[type, ...]:
        """A dependency for counting purposes is another SERVICE: what the tier below supplies.

        Options, delegates and primitives are configuration rather than collaborators, and
        utility brokers are exempt everywhere.
        """
        return tuple(
            _unwrap(parameter.annotation)
            for parameter in constructor
            if _is_a_dependency(_unwrap(parameter.annotation)))

    @staticmethod
    def carries_a_delegate(annotation: object) -> bool:
        """A Callable, or a generic that carries one: Python's delegate."""
        unwrapped = _unwrap(annotation)

        if typing.get_origin(unwrapped) is collections.abc.Callable:
            return True

        if unwrapped is collections.abc.Callable or unwrapped is typing.Callable:
            return True

        return any(
            TierMap.carries_a_delegate(argument)
            for argument in _flattened(typing.get_args(unwrapped)))

    @staticmethod
    def role(broker_name: str) -> str:
        """One broker ROLE, which may be versioned.

        GeneratorBrokerV1 is the same seam as GeneratorBroker, offered under a newer contract, and
        a foundation may hold both while speaking to only one at a time.
        """
        return re.sub(r"V\d+$", "", broker_name)


def _modules_of(package: types.ModuleType) -> typing.Iterator[types.ModuleType]:
    yield package

    for module_info in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
        yield importlib.import_module(module_info.name)


def _unwrap(annotation: object) -> object:
    """`X | None` is X, as C# reads a nullable parameter as its underlying type."""
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        arguments = [
            argument for argument in typing.get_args(annotation)
            if argument is not type(None)]

        if len(arguments) == 1:
            return arguments[0]

    return annotation


def _flattened(arguments: tuple[object, ...]) -> typing.Iterator[object]:
    """Generic arguments, with Callable's parameter list opened up."""
    for argument in arguments:
        if isinstance(argument, list):
            yield from argument
        else:
            yield argument


def _is_broker_contract(annotation: object) -> bool:
    """A broker's interface: in Python, the abstract class a concrete broker implements."""
    return (
        inspect.isclass(annotation)
        and inspect.isabstract(annotation)
        and annotation.__name__.endswith("Broker"))


def _is_a_dependency(annotation: object) -> bool:
    """A service of a tier: Python's services are the classes themselves, with no interface."""
    return (
        inspect.isclass(annotation)
        and annotation.__name__.endswith("Service")
        and ".services." in annotation.__module__)


@functools.cache
def _read_tier_map() -> TierMap:
    return TierMap(standard_agents)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    tier_map = _read_tier_map()

    services_by_fixture = {
        "foundation_service": tier_map.services_under("foundations"),
        "service_above_foundations": tier_map.services_above_foundations(),
        "tier_service": (
            tier_map.services_under("foundations") + tier_map.services_above_foundations()),
    }

    for fixture_name, services in services_by_fixture.items():
        if fixture_name in metafunc.fixturenames:
            metafunc.parametrize(
                fixture_name, services, ids=[service.__name__ for service in services])


@pytest.fixture(scope="session")
def tier_map() -> TierMap:
    return _read_tier_map()
