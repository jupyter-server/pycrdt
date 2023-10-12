from __future__ import annotations

from typing import Callable

from ._pycrdt import Doc as _Doc
from ._pycrdt import TransactionEvent
from .base import BaseDoc, BaseType, integrated_types
from .transaction import Transaction


class Doc(BaseDoc):
    @property
    def client_id(self) -> int:
        return self._doc.client_id()

    def transaction(self) -> Transaction:
        if self._txn is not None:
            return self._txn
        return Transaction(self)

    def get_state(self) -> bytes:
        return self._doc.get_state()

    def get_update(self, state: bytes | None = None) -> bytes:
        if state is None:
            state = self.get_state()
        return self._doc.get_update(state)

    def apply_update(self, update: bytes) -> None:
        self._doc.apply_update(update)

    def __setitem__(self, key: str, value: BaseType) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        integrated = value._get_or_insert(key, self)
        prelim = value._integrate(self, integrated)
        value._init(prelim)

    def observe(self, callback: Callable[[TransactionEvent], None]) -> int:
        return self._doc.observe(callback)


integrated_types[_Doc] = Doc
