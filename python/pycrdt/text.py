from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._pycrdt import Text as _Text
from ._pycrdt import TextEvent, Transaction

if TYPE_CHECKING:
    from .doc import Doc


class Text:
    _doc: Doc | None
    _text: _Text

    def __init__(self, name: str, doc: Doc | None = None) -> None:
        self._doc = doc
        if doc is None:
            pass  # TODO: prelim
        else:
            self._text = doc._doc.get_or_insert_text(name)

    def __len__(self) -> int:
        txn = self._current_transaction()
        return self._text.len(txn)

    def _current_transaction(self) -> Transaction:
        if self._doc is None:
            raise RuntimeError("Not in a document")
        if self._doc._txn is None:
            raise RuntimeError("No current transaction")
        return self._doc._txn._txn

    def __iadd__(self, other: str) -> Text:
        txn = self._current_transaction()
        self._text.push(txn, other)
        return self

    def __delitem__(self, key: int | slice) -> None:
        txn = self._current_transaction()
        if isinstance(key, int):
            self._text.remove_range(txn, key, 1)
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
            self._text.remove_range(txn, i, n)
        else:
            raise RuntimeError(f"Index not supported: {key}")

    def __setitem__(self, key: int | slice, value: str) -> None:
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
            self._text.insert(txn, key.start, value)
        else:
            raise RuntimeError(f"Index not supported: {key}")

    def observe(self, callback: Callable[[TextEvent], None]) -> int:
        return self._text.observe(callback)

    def unobserve(self, subscription_id: int) -> None:
        self._text.unobserve(subscription_id)
