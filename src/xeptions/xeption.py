# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

# The Python stand-in for the Xeption library the C# framework takes from NuGet: an exception
# that carries a message, the exception it localizes, and a data dictionary that validations
# accumulate into before they break the circuit. It is a library, not framework code, which is
# why it lives beside standard_agents rather than inside it.


class Xeption(Exception):
    def __init__(
        self,
        message: str = "",
        inner_exception: BaseException | None = None) -> None:

        super().__init__(message)
        self.message = message
        self.inner_exception = inner_exception
        self.data: dict[str, list[str]] = {}
        self.__cause__ = inner_exception

    def upsert_data_list(self, key: str, value: str) -> None:
        self.data.setdefault(key, []).append(value)

    def add_data(self, data: dict[str, list[str]]) -> None:
        for key, values in data.items():
            for value in values:
                self.upsert_data_list(key, value)

    def throw_if_contains_errors(self) -> None:
        if self.data:
            raise self

    # Equivalence, not identity: the same type, message and data, all the way down the chain of
    # inner exceptions. A native inner exception carries no data, so its type and arguments are
    # what make it the same.
    def same_exception_as(self, other: BaseException | None) -> bool:
        if type(other) is not type(self):
            return False

        if other.message != self.message or other.data != self.data:
            return False

        return same_inner_exception(self.inner_exception, other.inner_exception)


def same_inner_exception(
    expected_exception: BaseException | None,
    actual_exception: BaseException | None) -> bool:

    if isinstance(expected_exception, Xeption):
        return expected_exception.same_exception_as(actual_exception)

    if expected_exception is None or actual_exception is None:
        return expected_exception is actual_exception

    return (type(expected_exception) is type(actual_exception)
        and expected_exception.args == actual_exception.args)
