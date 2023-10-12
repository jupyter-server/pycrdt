from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._pycrdt import Array as _Array
from .base import BaseDoc, BaseType, integrated_types

if TYPE_CHECKING:
    from .doc import Doc


class Array(BaseType):
    _prelim: list | None
    _integrated: _Array | None

    def __init__(
        self,
        init: list | None = None,
        *,
        _doc: Doc | None = None,
        _integrated: _Array | None = None,
    ) -> None:
        super().__init__(
            init=init,
            _doc=_doc,
            _integrated=_integrated,
        )

    def _init(self, value: list[Any] | None) -> None:
        if value is None:
            return
        with self.doc.transaction():
            for i, v in enumerate(value):
                self._set(i, v)

    def _set(self, index: int, value: Any) -> None:
        with self.doc.transaction() as txn:
            if isinstance(value, BaseDoc):
                # subdoc
                self.integrated.insert_doc(txn, index, value._doc)
            elif isinstance(value, BaseType):
                # shared type
                self._do_and_integrate("insert", value, txn, index)
            else:
                # primitive type
                self.integrated.insert(txn, index, value)

    def _get_or_insert(self, name: str, doc: Doc) -> _Array:
        return doc._doc.get_or_insert_array(name)

    def __len__(self) -> int:
        with self.doc.transaction() as txn:
            return self.integrated.len(txn)

    def append(self, value: Any) -> None:
        with self.doc.transaction():
            self += [value]

    def extend(self, value: list[Any]) -> None:
        with self.doc.transaction():
            self += value

    def __add__(self, value: list[Any]) -> Array:
        with self.doc.transaction():
            length = len(self)
            self[length:length] = value
            return self

    def __radd__(self, value: list[Any]) -> Array:
        with self.doc.transaction():
            self[0:0] = value
            return self

    def __setitem__(self, key: int | slice, value: Any | list[Any]) -> None:
        with self.doc.transaction():
            if isinstance(key, int):
                if key < 0:
                    key += len(self)
                del self[key]
                self[key:key] = [value]
            elif isinstance(key, slice):
                if key.step is not None:
                    raise RuntimeError("Step not supported")
                if key.start != key.stop:
                    raise RuntimeError("Start and stop must be equal")
                if len(self) <= key.start < 0:
                    raise RuntimeError("Index out of range")
                for i, v in enumerate(value):
                    self._set(i + key.start, v)
            else:
                raise RuntimeError(f"Index not supported: {key}")

    def __delitem__(self, key: int | slice) -> None:
        with self.doc.transaction() as txn:
            if isinstance(key, int):
                self.integrated.remove_range(txn, key, 1)
            elif isinstance(key, slice):
                if key.step is not None:
                    raise RuntimeError("Step not supported")
                if key.start is None:
                    i = 0
                elif key.start < 0:
                    raise RuntimeError("Negative start not supported")
                else:
                    i = key.start
                if key.stop is None:
                    n = len(self) - i
                elif key.stop < 0:
                    raise RuntimeError("Negative stop not supported")
                else:
                    n = key.stop - i
                self.integrated.remove_range(txn, i, n)
            else:
                raise RuntimeError(f"Index not supported: {key}")

    def __getitem__(self, key: int) -> BaseType:
        with self.doc.transaction() as txn:
            if isinstance(key, int):
                return self._maybe_as_type_or_doc(self.integrated.get(txn, key))
            elif isinstance(key, slice):
                i0 = 0 if key.start is None else key.start
                i1 = len(self) if key.stop is None else key.stop
                step = 1 if key.step is None else key.step
                return [self[i] for i in range(i0, i1, step)]

    def __str__(self) -> str:
        with self.doc.transaction() as txn:
            return self.integrated.to_json(txn)


integrated_types[_Array] = Array
