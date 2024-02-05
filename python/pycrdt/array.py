from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Callable

from ._pycrdt import Array as _Array
from ._pycrdt import ArrayEvent as _ArrayEvent
from .base import BaseDoc, BaseEvent, BaseType, base_types, event_types

if TYPE_CHECKING:  # pragma: no cover
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
            self._forbid_read_transaction(txn)
            if isinstance(value, BaseDoc):
                # subdoc
                self.integrated.insert_doc(txn._txn, index, value._doc)
            elif isinstance(value, BaseType):
                # shared type
                assert txn._txn is not None
                self._do_and_integrate("insert", value, txn._txn, index)
            else:
                # primitive type
                self.integrated.insert(txn._txn, index, value)

    def _get_or_insert(self, name: str, doc: Doc) -> _Array:
        return doc._doc.get_or_insert_array(name)

    def __len__(self) -> int:
        with self.doc.transaction() as txn:
            return self.integrated.len(txn._txn)

    def append(self, value: Any) -> None:
        with self.doc.transaction():
            self += [value]

    def extend(self, value: list[Any]) -> None:
        with self.doc.transaction():
            self += value

    def clear(self) -> None:
        del self[:]

    def insert(self, index, object) -> None:
        self[index:index] = [object]

    def pop(self, index: int = -1) -> Any:
        with self.doc.transaction():
            index = self._check_index(index)
            res = self[index]
            del self[index]
            return res

    def move(self, source_index: int, destination_index: int) -> None:
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            source_index = self._check_index(source_index)
            destination_index = self._check_index(destination_index)
            self.integrated.move_to(txn._txn, source_index, destination_index)

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
                key = self._check_index(key)
                del self[key]
                self[key:key] = [value]
            elif isinstance(key, slice):
                if key.step is not None:
                    raise RuntimeError("Step not supported")
                if key.start != key.stop:
                    raise RuntimeError("Start and stop must be equal")
                if key.start > len(self) or key.start < 0:
                    raise RuntimeError("Index out of range")
                for i, v in enumerate(value):
                    self._set(i + key.start, v)
            else:
                raise RuntimeError("Index must be of type integer")

    def _check_index(self, idx: int) -> int:
        if not isinstance(idx, int):
            raise RuntimeError("Index must be of type integer")
        length = len(self)
        if idx < 0:
            idx += length
        if idx < 0 or idx >= length:
            raise IndexError("Array index out of range")
        return idx

    def __delitem__(self, key: int | slice) -> None:
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            if isinstance(key, int):
                key = self._check_index(key)
                self.integrated.remove_range(txn._txn, key, 1)
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
                self.integrated.remove_range(txn._txn, i, n)
            else:
                raise TypeError(
                    f"array indices must be integers or slices, not {type(key).__name__}"
                )

    def __getitem__(self, key: int) -> BaseType:
        with self.doc.transaction() as txn:
            if isinstance(key, int):
                key = self._check_index(key)
                return self._maybe_as_type_or_doc(self.integrated.get(txn._txn, key))
            elif isinstance(key, slice):
                i0 = 0 if key.start is None else key.start
                i1 = len(self) if key.stop is None else key.stop
                step = 1 if key.step is None else key.step
                return [self[i] for i in range(i0, i1, step)]

    def __iter__(self):
        return ArrayIterator(self)

    def __contains__(self, item: Any) -> bool:
        return item in list(self)

    def __str__(self) -> str:
        with self.doc.transaction() as txn:
            return self.integrated.to_json(txn._txn)

    def to_py(self) -> list | None:
        if self._integrated is None:
            py = self._prelim
            if py is None:
                return None
        else:
            py = list(self)
        for idx, val in enumerate(py):
            if isinstance(val, BaseType):
                py[idx] = val.to_py()
        return py

    def observe(self, callback: Callable[[Any], None]) -> str:
        _callback = partial(observe_callback, callback, self.doc)
        return f"o_{self.integrated.observe(_callback)}"

    def observe_deep(self, callback: Callable[[Any], None]) -> str:
        _callback = partial(observe_deep_callback, callback, self.doc)
        return f"od{self.integrated.observe_deep(_callback)}"

    def unobserve(self, subscription_id: str) -> None:
        sid = int(subscription_id[2:])
        if subscription_id.startswith("o_"):
            self.integrated.unobserve(sid)
        else:
            self.integrated.unobserve_deep(sid)


def observe_callback(callback: Callable[[Any], None], doc: Doc, event: Any):
    _event = event_types[type(event)](event, doc)
    with doc._read_transaction(event.transaction):
        callback(_event)


def observe_deep_callback(callback: Callable[[Any], None], doc: Doc, events: list[Any]):
    for idx, event in enumerate(events):
        events[idx] = event_types[type(event)](event, doc)
    with doc._read_transaction(event.transaction):
        callback(events)


class ArrayEvent(BaseEvent):
    __slots__ = "target", "delta", "path"


class ArrayIterator:
    def __init__(self, array: Array):
        self.array = array
        self.length = len(array)
        self.idx = 0

    def __next__(self):
        if self.idx == self.length:
            raise StopIteration

        res = self.array[self.idx]
        self.idx += 1
        return res


base_types[_Array] = Array
event_types[_ArrayEvent] = ArrayEvent
