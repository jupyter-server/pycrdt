from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Callable

from ._pycrdt import Map as _Map
from ._pycrdt import MapEvent as _MapEvent
from .base import BaseDoc, BaseEvent, BaseType, base_types, event_types

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

    def __getitem__(self, key: str) -> Any:
        with self.doc.transaction() as txn:
            if not isinstance(key, str):
                raise RuntimeError("Key must be of type string")
            return self._maybe_as_type_or_doc(self.integrated.get(txn, key))

    def __setitem__(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        with self.doc.transaction():
            self._set(key, value)

    def get(self, key: str, default_value: Any | None = None) -> Any | None:
        with self.doc.transaction():
            if key in self.keys():
                return self[key]
            return default_value

    def pop(self, key: str, default_value: Any | None = None) -> Any:
        with self.doc.transaction():
            if key not in self.keys():
                if (
                    default_value is None
                ):  # FIXME: how to know if default_value was passed?
                    raise KeyError
                return default_value
            res = self[key]
            del self[key]
            return res

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
    callback(_event)


def observe_deep_callback(callback: Callable[[Any], None], doc: Doc, events: list[Any]):
    for idx, event in enumerate(events):
        events[idx] = event_types[type(event)](event, doc)
    callback(events)


class MapEvent(BaseEvent):
    __slots__ = "target", "keys", "path"


base_types[_Map] = Map
event_types[_MapEvent] = MapEvent
