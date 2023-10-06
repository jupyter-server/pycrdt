from __future__ import annotations

from ._pycrdt import Doc as _Doc
from .array import Array
from .base import BaseDoc, integrated_types
from .map import Map
from .text import Text
from .transaction import Transaction


class Doc(BaseDoc):
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

    def apply_update(self, update: bytes) -> None:
        self._doc.apply_update(update)


integrated_types[_Doc] = Doc
