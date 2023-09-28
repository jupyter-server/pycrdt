from __future__ import annotations

from typing import TYPE_CHECKING

from ._pycrdt import Text as _Text

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
        assert self._doc is not None
        assert self._doc._txn is not None
        return self._text.len(self._doc._txn._txn)

    def __iadd__(self, other: str) -> Text:
        if self._doc is None:
            raise RuntimeError("Not in a document")

        if self._doc._txn is None:
            raise RuntimeError("No current transaction")

        self._text.push(self._doc._txn._txn, other)
        return self

    def __delitem__(self, key) -> None:
        assert self._doc is not None
        assert self._doc._txn is not None
        if isinstance(key, int):
            self._text.remove_range(self._doc._txn._txn, key, 1)
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
            self._text.remove_range(self._doc._txn._txn, i, n)
