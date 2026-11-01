# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable

from standard_agents.brokers.contracts.contract_broker import ContractBroker


class FunctionContractBroker(ContractBroker):
    """The Custom mode's substrate: host-supplied validation, for rules a schema cannot express.

    A total that must equal the sum of its lines, an account that must exist.
    """

    def __init__(self, validate: Callable[[str, str], Awaitable[str | None]]) -> None:
        self._validate = validate

    async def validate(self, answer: str, schema: str) -> str | None:
        return await self._validate(answer, schema)
