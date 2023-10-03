from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._pycrdt import Array as _Array
from .base_type import BaseType

if TYPE_CHECKING:
    from .doc import Doc


class Array(BaseType):
    _prelim: list | None
    _integrated: _Array

    def __init__(
        self,
        *,
        prelim: list | None = None,
        doc: "Doc" | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(
            prelim=prelim,
            doc=doc,
            name=name,
        )

    def init(self, value: list[Any]) -> None:
        with self.doc.transaction():
            self._set(value)

    def _get_or_insert(self, name: str, doc: "Doc") -> _Array:
        return doc._doc.get_or_insert_array(name)

    def _set(self, value: list[Any]) -> None:
        txn = self._current_transaction()
        for v in value:
            if isinstance(v, BaseType):
                # shared type
                self._do_and_integrate("push_back", v, txn)
            else:
                # primitive type
                self.integrated.push_back(txn, v)

    def __len__(self) -> int:
        txn = self._current_transaction()
        return self.integrated.len(txn)

    def append(self, other: Any) -> None:
        txn = self._current_transaction()
        self.integrated.push_back(txn, other)

    def __add__(self, other: list[Any]) -> Array:
        txn = self._current_transaction()
        len_other = len(other)
        if len_other == 1:
            self.integrated.push_back(txn, other[0])
        elif len_other > 1:
            length = len(self)
            self[length:length] = other
        return self

    def __radd__(self, other: list[Any]) -> Array:
        txn = self._current_transaction()
        len_other = len(other)
        if len_other == 1:
            self.integrated.push_front(txn, other[0])
        elif len_other > 1:
            self[0:0] = other
        return self

    def __setitem__(self, key: int | slice, value: Any) -> None:
        txn = self._current_transaction()
        if isinstance(key, int):
            raise RuntimeError("Single item assignment not supported")
        elif isinstance(key, slice):
            if key.step is not None:
                raise RuntimeError("Step not supported")
            if key.start != key.stop:
                raise RuntimeError("Start and stop should be equal")
            if len(self) <= key.start < 0:
                raise RuntimeError("Index out of range")
            self.integrated.insert_range(txn, key.start, value)
        else:
            raise RuntimeError(f"Index not supported: {key}")

    def __delitem__(self, key: int | slice) -> None:
        txn = self._current_transaction()
        if isinstance(key, int):
            self.integrated.remove(txn, key)
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
        txn = self._current_transaction()
        if not isinstance(key, int):
            raise RuntimeError("Slices are not supported")
        return self._maybe_as_type(self.integrated.get(txn, key))

    def __str__(self) -> str:
        txn = self._current_transaction()
        return self.integrated.to_json(txn)


BaseType._integrated_types[_Array] = Array
