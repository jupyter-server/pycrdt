from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._pycrdt import Map as _Map
from .base import BaseDoc, BaseType, integrated_types

if TYPE_CHECKING:
    from .doc import Doc


class Map(BaseType):
    _prelim: dict | None
    _integrated: _Map | None

    def __init__(
        self,
        init: dict | None = None,
        *,
        _doc: Doc | None = None,
        _integrated: _Map | None = None,
    ) -> None:
        super().__init__(
            init=init,
            _doc=_doc,
            _integrated=_integrated,
        )

    def _init(self, value: dict[str, Any] | None) -> None:
        if value is None:
            return
        with self.doc.transaction():
            for k, v in value.items():
                self._set(k, v)

    def _set(self, key: str, value: Any) -> None:
        with self.doc.transaction() as txn:
            if isinstance(value, BaseDoc):
                # subdoc
                self.integrated.insert_doc(txn, key, value._doc)
            elif isinstance(value, BaseType):
                # shared type
                self._do_and_integrate("insert", value, txn, key)
            else:
                # primitive type
                self.integrated.insert(txn, key, value)

    def _get_or_insert(self, name: str, doc: Doc) -> _Map:
        return doc._doc.get_or_insert_map(name)

    def __len__(self) -> int:
        with self.doc.transaction() as txn:
            return self.integrated.len(txn)

    def __str__(self) -> str:
        with self.doc.transaction() as txn:
            return self.integrated.to_json(txn)

    def __delitem__(self, key: str) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        txn = self._current_transaction()
        self.integrated.remove(txn, key)

    def __getitem__(self, key: str) -> None:
        with self.doc.transaction() as txn:
            if not isinstance(key, str):
                raise RuntimeError("Key must be of type string")
            return self._maybe_as_type_or_doc(self.integrated.get(txn, key))

    def __setitem__(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        with self.doc.transaction():
            self._set(key, value)

    def keys(self):
        with self.doc.transaction() as txn:
            return iter(self.integrated.keys(txn))

    def values(self):
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn):
                yield self[k]

    def items(self):
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn):
                yield k, self[k]

    def clear(self) -> None:
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn):
                del self[k]

    def update(self, value: dict[str, Any]) -> None:
        self._init(value)


integrated_types[_Map] = Map
