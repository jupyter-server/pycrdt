from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._pycrdt import Map as _Map
from .base import BaseDoc, BaseType, integrated_types

if TYPE_CHECKING:
    from .doc import Doc


class Map(BaseType):
    _prelim: dict | None
    _integrated: _Map | None

    def _get_or_insert(self, name: str, doc: "Doc") -> _Map:
        return doc._doc.get_or_insert_map(name)

    def init(self, value: dict[str, Any]) -> None:
        with self.doc.transaction():
            self._set(value)

    def _set(self, value: dict[str, Any]) -> None:
        txn = self._current_transaction()
        for k, v in value.items():
            if isinstance(v, BaseDoc):
                # subdoc
                self.integrated.insert_doc(txn, k, v._doc)
            elif isinstance(v, BaseType):
                # shared type
                self._do_and_integrate("insert", v, txn, k)
            else:
                # primitive type
                self.integrated.insert(txn, k, v)

    def __len__(self) -> int:
        txn = self._current_transaction()
        return self.integrated.len(txn)

    def __str__(self) -> str:
        txn = self._current_transaction()
        return self.integrated.to_json(txn)

    def __delitem__(self, key: str) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        txn = self._current_transaction()
        self.integrated.remove(txn, key)

    def __getitem__(self, key: str) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        txn = self._current_transaction()
        return self._maybe_as_type_or_doc(self.integrated.get(txn, key))

    def __setitem__(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        txn = self._current_transaction()
        self.integrated.insert(txn, key, value)


integrated_types[_Map] = Map
