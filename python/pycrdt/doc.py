from __future__ import annotations

from ._pycrdt import Doc as _Doc
from .array import Array
from .map import Map
from .text import Text
from .transaction import Transaction


class Doc:
    _doc: _Doc
    _txn: Transaction | None

    def __init__(self) -> None:
        self._doc = _Doc()
        self._txn = None

    def get_text(self, name: str) -> Text:
        return Text(name=name, doc=self)

    def get_array(self, name: str) -> Array:
        return Array(name=name, doc=self)

    def get_map(self, name: str) -> Map:
        return Map(name=name, doc=self)

    def transaction(self) -> Transaction:
        if self._txn is not None:
            return self._txn
        return Transaction(self)

    def get_state(self) -> bytes:
        return self._doc.get_state()

    def get_update(self, state: bytes) -> bytes:
        return self._doc.get_update(state)
