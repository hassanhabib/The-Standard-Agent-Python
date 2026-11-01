# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from typing import Awaitable, Callable

from standard_agents.brokers.effects.ieffect_ledger_broker import IEffectLedgerBroker
from standard_agents.models.brokers.effects.effect_record import EffectRecord


# The Custom mode of the ledger: the four primitives as your own delegates, usually over the
# store your transactions already commit to, since an act and the note that it happened want to
# commit together.
class FunctionEffectLedgerBroker(IEffectLedgerBroker):
    def __init__(
            self,
            insert_claim: Callable[[EffectRecord], Awaitable[bool]],
            select_record: Callable[[str], Awaitable[EffectRecord | None]],
            update_record: Callable[[EffectRecord], Awaitable[None]],
            delete_record: Callable[[str], Awaitable[None]]) -> None:

        self._insert_claim = insert_claim
        self._select_record = select_record
        self._update_record = update_record
        self._delete_record = delete_record

    async def insert_claim(self, claim: EffectRecord) -> bool:
        return await self._insert_claim(claim)

    async def select_record(self, idempotency_key: str) -> EffectRecord | None:
        return await self._select_record(idempotency_key)

    async def update_record(self, record: EffectRecord) -> None:
        await self._update_record(record)

    async def delete_record(self, idempotency_key: str) -> None:
        await self._delete_record(idempotency_key)
