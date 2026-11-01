# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

from __future__ import annotations

import threading

from standard_agents.brokers.effects.effect_ledger_broker import EffectLedgerBroker
from standard_agents.models.brokers.effects.effect_record import EffectRecord


# The built-in ledger: one process, one lifetime. Run-once holds within the instance; nothing
# here survives it, which is what effect_ledger(path) and use_effect_ledger(...) are for.
class InMemoryEffectLedgerBroker(EffectLedgerBroker):
    def __init__(self) -> None:
        # C#: a ConcurrentDictionary; the lock makes each operation atomic, as its operations are.
        self._records_by_key: dict[str, EffectRecord] = {}
        self._records_lock = threading.Lock()

    async def insert_claim(self, claim: EffectRecord) -> bool:
        with self._records_lock:
            if claim.idempotency_key in self._records_by_key:
                return False

            self._records_by_key[claim.idempotency_key] = claim

            return True

    async def select_record(self, idempotency_key: str) -> EffectRecord | None:
        with self._records_lock:
            return self._records_by_key.get(idempotency_key)

    async def update_record(self, record: EffectRecord) -> None:
        with self._records_lock:
            self._records_by_key[record.idempotency_key] = record

    async def delete_record(self, idempotency_key: str) -> None:
        with self._records_lock:
            self._records_by_key.pop(idempotency_key, None)
