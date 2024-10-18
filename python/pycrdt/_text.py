from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._base import BaseEvent, BaseType, base_types, event_types
from ._pycrdt import Text as _Text
from ._pycrdt import TextEvent as _TextEvent

if TYPE_CHECKING:  # pragma: no cover
    from ._doc import Doc


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
            self.integrated.insert(txn._txn, 0, value)

    def _get_or_insert(self, name: str, doc: Doc) -> _Text:
        return doc._doc.get_or_insert_text(name)

    def __iter__(self):
        return TextIterator(self)

    def __contains__(self, item: str) -> bool:
        return item in str(self)

    def __len__(self) -> int:
        with self.doc.transaction() as txn:
            return self.integrated.len(txn._txn)

    def __str__(self) -> str:
        with self.doc.transaction() as txn:
            return self.integrated.get_string(txn._txn)

    def to_py(self) -> str | None:
        if self._integrated is None:
            return self._prelim
        return str(self)

    def __iadd__(self, value: str) -> Text:
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            self.integrated.insert(txn._txn, len(self), value)
            return self

    def _check_slice(self, key: slice) -> tuple[int, int]:
        if key.step is not None:
            raise RuntimeError("Step not supported")
        if key.start is None:
            start = 0
        elif key.start < 0:
            raise RuntimeError("Negative start not supported")
        else:
            start = key.start
        if key.stop is None:
            stop = len(self)
        elif key.stop < 0:
            raise RuntimeError("Negative stop not supported")
        else:
            stop = key.stop
        return start, stop

    def __delitem__(self, key: int | slice) -> None:
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            if isinstance(key, int):
                self.integrated.remove_range(txn._txn, key, 1)
            elif isinstance(key, slice):
                start, stop = self._check_slice(key)
                length = stop - start
                if length > 0:
                    self.integrated.remove_range(txn._txn, start, length)
            else:
                raise RuntimeError(f"Index not supported: {key}")

    def __getitem__(self, key: int | slice) -> str:
        value = str(self)
        return value[key]

    def __setitem__(self, key: int | slice, value: str) -> None:
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            if isinstance(key, int):
                value_len = len(value)
                if value_len != 1:
                    raise RuntimeError(
                        f"Single item assigned value must have a length of 1, not {value_len}"
                    )
                del self[key]
                self.integrated.insert(txn._txn, key, value)
            elif isinstance(key, slice):
                start, stop = self._check_slice(key)
                length = stop - start
                if length > 0:
                    self.integrated.remove_range(txn._txn, start, length)
                self.integrated.insert(txn._txn, start, value)
            else:
                raise RuntimeError(f"Index not supported: {key}")

    def clear(self) -> None:
        """Remove the entire range of characters."""
        del self[:]

    def insert(self, index: int, value: str, attrs: dict[str, Any] | None = None) -> None:
        """Insert 'value' at character position 'index'."""
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            self.integrated.insert(
                txn._txn, index, value, iter(attrs.items()) if attrs is not None else None
            )

    def insert_embed(self, index: int, value: Any, attrs: dict[str, Any] | None = None) -> None:
        """Insert 'value' as an embed at character position 'index'."""
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            self.integrated.insert_embed(
                txn._txn, index, value, iter(attrs.items()) if attrs is not None else None
            )

    def format(self, start: int, stop: int, attrs: dict[str, Any]) -> None:
        """Formats existing text with attributes"""
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            start, stop = self._check_slice(slice(start, stop))
            length = stop - start
            if length > 0:
                self.integrated.format(txn._txn, start, length, iter(attrs.items()))

    def diff(self) -> list[tuple[Any, dict[str, Any] | None]]:
        with self.doc.transaction() as txn:
            return self.integrated.diff(txn._txn)


class TextEvent(BaseEvent):
    __slots__ = "target", "delta", "path"


class TextIterator:
    def __init__(self, text: Text):
        self.text = text
        self.length = len(text)
        self.idx = 0

    def __next__(self):
        if self.idx == self.length:
            raise StopIteration

        res = self.text[self.idx]
        self.idx += 1
        return res


base_types[_Text] = Text
event_types[_TextEvent] = TextEvent
