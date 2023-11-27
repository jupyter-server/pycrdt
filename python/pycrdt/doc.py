from __future__ import annotations

from typing import Callable

from ._pycrdt import Doc as _Doc
from ._pycrdt import SubdocsEvent, TransactionEvent
from .base import BaseDoc, BaseType, base_types
from .transaction import Transaction


class Doc(BaseDoc):
    def __init__(
        self,
        init: dict[str, BaseType] = {},
        *,
        client_id: int | None = None,
        doc: _Doc | None = None,
    ) -> None:
        super().__init__(client_id=client_id, doc=doc)
        for k, v in init.items():
            self[k] = v

    @property
    def guid(self) -> int:
        return self._doc.guid()

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
            state = b"\x00"
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

    def observe_subdocs(self, callback: Callable[[SubdocsEvent], None]) -> int:
        return self._doc.observe_subdocs(callback)


base_types[_Doc] = Doc
