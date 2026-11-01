# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod

from standard_agents.models.brokers.effects.effect_record import EffectRecord


# The store of which acts have run (SPEC.md 4.9), as four primitives over typed records. What a
# record means, and what to do about one that is already there, is the foundation's judgment
# (principal review 2026-09-04, F-08); this broker only keeps the records.
class EffectLedgerBroker(ABC):
    # Writes the claim if, and only if, no record exists for its key, atomically, so two runs
    # proposing the same act cannot both decide they are the first. Intent is written before the
    # act, never after. Returns True when the claim was written; False when the key already had
    # a record.
    @abstractmethod
    async def insert_claim(self, claim: EffectRecord) -> bool:
        ...

    @abstractmethod
    async def select_record(self, idempotency_key: str) -> EffectRecord | None:
        ...

    # Replaces the key's record with this one: the act's outcome, its failure, its compensation.
    @abstractmethod
    async def update_record(self, record: EffectRecord) -> None:
        ...

    @abstractmethod
    async def delete_record(self, idempotency_key: str) -> None:
        ...
