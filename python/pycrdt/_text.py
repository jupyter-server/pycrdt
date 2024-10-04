from __future__ import annotations

from typing import TYPE_CHECKING, Callable, cast

from ._base import BaseEvent, BaseType, base_types, event_types
from ._pycrdt import Subscription
from ._pycrdt import Text as _Text
from ._pycrdt import TextEvent as _TextEvent

if TYPE_CHECKING:  # pragma: no cover
    from ._doc import Doc


class Text(BaseType):
    """
    A shared data type used for collaborative text editing, similar to a Python `str`.
    """

    _prelim: str | None
    _integrated: _Text | None

    def __init__(
        self,
        init: str | None = None,
        *,
        _doc: Doc | None = None,
        _integrated: _Text | None = None,
    ) -> None:
        """
        Creates a text with an optional initial value:
        ```py
        text = Text("Hello, World!")
        ```

        Args:
            init: The string from which to initialize the text.
        """
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

    def __iter__(self) -> TextIterator:
        """
        ```py
        Doc()["text"] = text = Text("***")
        for character in text:
            assert character == "*"
        ```

        Returns:
            An iterable over the characters of the text.
        """
        return TextIterator(self)

    def __contains__(self, item: str) -> bool:
        """
        Checks if the given string is in the text:
        ```py
        Doc()["text"] = text = Text("Hello, World!")
        assert "World" in text
        ```

        Args:
            item: The string to look for in the text.

        Returns:
            True if the string was found.
        """
        return item in str(self)

    def __len__(self) -> int:
        """
        ```py
        Doc()["text"] = text = Text("Hello")
        assert len(text) == 5
        ```

        Returns:
            The length of the text.
        """
        with self.doc.transaction() as txn:
            return self.integrated.len(txn._txn)

    def __str__(self) -> str:
        """
        Returns:
            The text as a Python `str`.
        """
        with self.doc.transaction() as txn:
            return self.integrated.get_string(txn._txn)

    def to_py(self) -> str | None:
        """
        Returns:
            The text as a Python `str`.
        """
        if self._integrated is None:
            return self._prelim
        return str(self)

    def __iadd__(self, value: str) -> Text:
        """
        Concatenates a string to the text:
        ```py
        Doc()["text"] = text = Text("Hello")
        text += ", World!"
        assert str(text) == "Hello, World!"
        ```

        Args:
            value: The string to concatenate.

        Returns:
            The concatenated text.
        """
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
        """
        Removes the characters at the given index or slice:
        ```py
        Doc()["text"] = text = Text("Hello, World!")
        del text[5]
        assert str(text) == "Hello World!"
        del text[5:]
        assert str(text) == "Hello"
        ```

        Args:
            key: The index or the slice of the characters to remove.

        Raises:
            RuntimeError: Step not supported.
            RuntimeError: Negative start not supported.
            RuntimeError: Negative stop not supported.
        """
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
        """
        Gets the characters at the given index or slice:
        ```py
        Doc()["text"] = text = Text("Hello, World!")
        assert text[:5] == "Hello"
        ```

        Returns:
            The characters at the given index or slice.
        """
        value = str(self)
        return value[key]

    def __setitem__(self, key: int | slice, value: str) -> None:
        """
        Replaces the characters at the given index or slice with new characters:
        ```py
        Doc()["text"] = text = Text("Hello, World!")
        text[7:12] = "Brian"
        assert text == "Hello, Brian!"
        ```

        Args:
            key: The index or slice of the characters to replace.
            value: The new characters to set.

        Raises:
            RuntimeError: Step not supported.
            RuntimeError: Negative start not supported.
            RuntimeError: Negative stop not supported.
            RuntimeError: Single item assigned value must have a length of 1.
        """
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

    def insert(self, index: int, value: str) -> None:
        """
        Inserts a string at a given index in the text.
        Doc()["text"] = text = Text("Hello World!")
        text.insert(5, ",")
        assert text == "Hello, World!"

        Args:
            index: The index where to insert the string.
            value: The string to insert in the text.
        """
        self[index:index] = value

    def observe(self, callback: Callable[[TextEvent], None]) -> Subscription:
        """
        Subscribes a callback to be called with the text event.

        Args:
            callback: The callback to call with the [TextEvent][pycrdt.TextEvent].
        """
        return super().observe(cast(Callable[[BaseEvent], None], callback))


class TextEvent(BaseEvent):
    """
    A text change event.

    Attributes:
        target (Text): The changed text.
        delta (list[dict[str, Any]]): A list of items describing the changes.
        path (list[int | str]): A list with the indices pointing to the text that was changed.
    """

    __slots__ = "target", "delta", "path"


class TextIterator:
    def __init__(self, text: Text):
        self.text = text
        self.length = len(text)
        self.idx = 0

    def __next__(self) -> str:
        if self.idx == self.length:
            raise StopIteration

        res = self.text[self.idx]
        self.idx += 1
        return res


base_types[_Text] = Text
event_types[_TextEvent] = TextEvent
