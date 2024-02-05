from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Callable

from ._pycrdt import Map as _Map
from ._pycrdt import MapEvent as _MapEvent
from .base import BaseDoc, BaseEvent, BaseType, base_types, event_types

if TYPE_CHECKING:  # pragma: no cover
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
            self._forbid_read_transaction(txn)
            if isinstance(value, BaseDoc):
                # subdoc
                self.integrated.insert_doc(txn._txn, key, value._doc)
            elif isinstance(value, BaseType):
                # shared type
                assert txn._txn is not None
                self._do_and_integrate("insert", value, txn._txn, key)
            else:
                # primitive type
                self.integrated.insert(txn._txn, key, value)

    def _get_or_insert(self, name: str, doc: Doc) -> _Map:
        return doc._doc.get_or_insert_map(name)

    def __len__(self) -> int:
        with self.doc.transaction() as txn:
            return self.integrated.len(txn._txn)

    def __str__(self) -> str:
        with self.doc.transaction() as txn:
            return self.integrated.to_json(txn._txn)

    def to_py(self) -> dict | None:
        if self._integrated is None:
            py = self._prelim
            if py is None:
                return None
        else:
            py = dict(self)
        for key, val in py.items():
            if isinstance(val, BaseType):
                py[key] = val.to_py()
        return py

    def __delitem__(self, key: str) -> None:
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            self._check_key(key)
            self.integrated.remove(txn._txn, key)

    def __getitem__(self, key: str) -> Any:
        with self.doc.transaction() as txn:
            self._check_key(key)
            return self._maybe_as_type_or_doc(self.integrated.get(txn._txn, key))

    def __setitem__(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        with self.doc.transaction():
            self._set(key, value)

    def __iter__(self):
        return self.keys()

    def __contains__(self, item: str) -> bool:
        return item in self.keys()

    def get(self, key: str, default_value: Any | None = None) -> Any | None:
        with self.doc.transaction():
            if key in self.keys():
                return self[key]
            return default_value

    def pop(self, *args) -> Any:
        key, *default_value = args
        with self.doc.transaction():
            if key not in self.keys():
                if not default_value:
                    raise KeyError
                return default_value[0]
            res = self[key]
            del self[key]
            return res

    def _check_key(self, key: str):
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        if key not in self.keys():
            raise KeyError(key)

    def keys(self):
        with self.doc.transaction() as txn:
            return iter(self.integrated.keys(txn._txn))

    def values(self):
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn._txn):
                yield self[k]

    def items(self):
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn._txn):
                yield k, self[k]

    def clear(self) -> None:
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn._txn):
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
    with doc._read_transaction(event.transaction):
        callback(_event)


def observe_deep_callback(callback: Callable[[Any], None], doc: Doc, events: list[Any]):
    for idx, event in enumerate(events):
        events[idx] = event_types[type(event)](event, doc)
    with doc._read_transaction(event.transaction):
        callback(events)


class MapEvent(BaseEvent):
    __slots__ = "target", "keys", "path"


base_types[_Map] = Map
event_types[_MapEvent] = MapEvent
