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
        inner_exception: BaseException | None = None,
        data: dict[str, list[str]] | None = None) -> None:

        super().__init__(message)
        self.message = message
        self.inner_exception = inner_exception
        self.data: dict[str, list[str]] = {}
        self.__cause__ = inner_exception

    def upsert_data_list(self, key: str, value: str) -> None:
        self.data.setdefault(key, []).append(value)

    def add_data(self, data: dict[str, list[str]]) -> None:
        raise NotImplementedError

    def throw_if_contains_errors(self) -> None:
        raise NotImplementedError

    def same_exception_as(self, other: BaseException | None) -> bool:
        raise NotImplementedError
