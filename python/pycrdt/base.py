from __future__ import annotations

from abc import ABC, abstractmethod
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Type, cast

from ._pycrdt import Doc as _Doc
from ._pycrdt import Transaction as _Transaction
from .transaction import Transaction

if TYPE_CHECKING:
    from .doc import Doc


base_types: dict[Any, Type[BaseType | BaseDoc]] = {}


class BaseDoc:
    _doc: _Doc
    _txn: Transaction | None

    def __init__(
        self, *, client_id: int | None = None, doc: _Doc | None = None
    ) -> None:
        if doc is None:
            doc = _Doc(client_id)
        self._doc = doc
        self._txn = None


class BaseType(ABC):
    _doc: Doc | None
    _prelim: Any | None
    _integrated: Any
    _type_name: str

    def __init__(
        self,
        init: Any = None,
        *,
        _doc: Doc | None = None,
        _integrated: Any = None,
    ) -> None:
        self._type_name = self.__class__.__name__.lower()
        # private API
        if _integrated is not None:
            self._doc = _doc
            self._prelim = None
            self._integrated = _integrated
            return
        # public API
        self._doc = None
        self._prelim = init
        self._integrated = None

    @abstractmethod
    def _get_or_insert(self, name: str, doc: Doc) -> Any:
        ...

    @abstractmethod
    def _init(self, value: Any | None) -> None:
        ...

    def _current_transaction(self) -> _Transaction:
        if self._doc is None:
            raise RuntimeError("Not associated with a document")
        if self._doc._txn is None:
            raise RuntimeError("No current transaction")
        return self._doc._txn._txn

    def _integrate(self, doc: Doc, integrated: Any) -> Any:
        prelim = self._prelim
        self._doc = doc
        self._prelim = None
        self._integrated = integrated
        return prelim

    def _do_and_integrate(
        self, action: str, value: BaseType, txn: _Transaction, *args
    ) -> None:
        if value.is_integrated:
            raise RuntimeError("Already integrated")
        method = getattr(self._integrated, f"{action}_{value.type_name}_prelim")
        integrated = method(txn, *args)
        assert self._doc is not None
        prelim = value._integrate(self._doc, integrated)
        value._init(prelim)

    def _maybe_as_type_or_doc(self, obj: Any) -> Any:
        for k, v in base_types.items():
            if isinstance(obj, k):
                if issubclass(v, BaseDoc):
                    # create a BaseDoc
                    return v(doc=obj)
                # create a BaseType
                return v(_doc=self.doc, _integrated=obj)
        # that was a primitive value, just return it
        return obj

    @property
    def integrated(self) -> Any:
        if self._integrated is None:
            raise RuntimeError("Not integrated in a document yet")
        return self._integrated

    @property
    def doc(self) -> Doc:
        if self._doc is None:
            raise RuntimeError("Not integrated in a document yet")
        return self._doc

    @property
    def is_prelim(self) -> bool:
        return self._prelim is not None

    @property
    def is_integrated(self) -> bool:
        return self._integrated is not None

    @property
    def prelim(self) -> Any:
        return self._prelim

    @property
    def type_name(self) -> str:
        return self._type_name

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
    _event = Event(event, doc)
    callback(_event)


def observe_deep_callback(callback: Callable[[Any], None], doc: Doc, events: list[Any]):
    for idx, event in enumerate(events):
        events[idx] = Event(event, doc)
    callback(events)


class Event:
    def __init__(self, event: Any, doc: Doc):
        self._doc = doc
        attrs = [attr for attr in dir(event) if not attr.startswith("_")]
        for attr in attrs:
            processed = self._process(getattr(event, attr))
            setattr(self, attr, processed)

    def _process(self, value: Any) -> Any:
        if isinstance(value, list):
            for idx, val in enumerate(value):
                value[idx] = self._process(val)
        elif isinstance(value, dict):
            for key, val in value.items():
                value[key] = self._process(val)
        else:
            val_type = type(value)
            if val_type in base_types:
                if isinstance(val_type, _Doc):
                    doc_type = cast(Type[BaseDoc], base_types[val_type])
                    value = doc_type(doc=self._doc._doc)
                else:
                    base_type = cast(Type[BaseType], base_types[val_type])
                    value = base_type(_integrated=value, _doc=self._doc)
        return value
