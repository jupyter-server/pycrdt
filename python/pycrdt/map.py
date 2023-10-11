from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._pycrdt import Map as _Map
from .base import BaseDoc, BaseType, integrated_types

if TYPE_CHECKING:
    from .doc import Doc


class Map(BaseType):
    _prelim: dict | None
    _integrated: _Map | None
    _keys: dict[str, None]

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
        self._keys = dict()

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
            self._keys[key] = None

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
        del self._keys[key]

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

    def __iter__(self):
        return self._keys.keys()

    def keys(self):
        return self._keys.keys()

    def values(self):
        for k in self.keys():
            yield self[k]

    def items(self):
        for k in self.keys():
            yield k, self[k]

    def update(self, value: dict[str, Any]) -> None:
        self._init(value)

    def clear(self) -> None:
        with self.doc.transaction():
            keys = list(self.keys())
            for k in keys:
                del self[k]
        self._keys.clear()


integrated_types[_Map] = Map
