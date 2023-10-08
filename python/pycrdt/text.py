from __future__ import annotations

from typing import TYPE_CHECKING

from ._pycrdt import Text as _Text
from .base import BaseType, integrated_types

if TYPE_CHECKING:
    from .doc import Doc


class Text(BaseType):
    _prelim: str | None
    _integrated: _Text | None

    def __init__(
        self,
        init: str | None = None,
        *,
        _doc: Doc | None = None,
        _integrated: _Text | None = None,
    ) -> None:
        super().__init__(
            init=init,
            _doc=_doc,
            _integrated=_integrated,
        )

    def _init(self, value: str | None) -> None:
        if value is None:
            return
        with self.doc.transaction() as txn:
            self.integrated.insert(txn, 0, value)

    def _get_or_insert(self, name: str, doc: Doc) -> _Text:
        return doc._doc.get_or_insert_text(name)

    def __len__(self) -> int:
        with self.doc.transaction() as txn:
            return self.integrated.len(txn)

    def __str__(self) -> str:
        with self.doc.transaction():
            txn = self._current_transaction()
            return self.integrated.get_string(txn)

    def __iadd__(self, value: str) -> Text:
        with self.doc.transaction() as txn:
            self.integrated.insert(txn, len(self), value)
            return self

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

    def __setitem__(self, key: int | slice, value: str) -> None:
        with self.doc.transaction() as txn:
            if isinstance(key, int):
                raise RuntimeError("Single item assignment not supported")
            elif isinstance(key, slice):
                if key.step is not None:
                    raise RuntimeError("Step not supported")
                if key.start != key.stop:
                    raise RuntimeError("Start and stop should be equal")
                if len(self) <= key.start < 0:
                    raise RuntimeError("Index out of range")
                self.integrated.insert(txn, key.start, value)
            else:
                raise RuntimeError(f"Index not supported: {key}")


integrated_types[_Text] = Text
