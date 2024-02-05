from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Type, cast

from ._pycrdt import Doc as _Doc
from ._pycrdt import Transaction as _Transaction
from .transaction import ReadTransaction, Transaction

if TYPE_CHECKING:  # pragma: no cover
    from .doc import Doc


base_types: dict[Any, Type[BaseType | BaseDoc]] = {}
event_types: dict[Any, Type[BaseEvent]] = {}


class BaseDoc:
    _doc: _Doc
    _twin_doc: BaseDoc | None
    _txn: Transaction | None
    _Model: Any

    def __init__(
        self,
        *,
        client_id: int | None = None,
        doc: _Doc | None = None,
        Model=None,
        **data,
    ) -> None:
        super().__init__(**data)
        if doc is None:
            doc = _Doc(client_id)
        self._doc = doc
        self._txn = None
        self._Model = Model


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
    def to_py(self) -> Any: ...

    @abstractmethod
    def _get_or_insert(self, name: str, doc: Doc) -> Any: ...

    @abstractmethod
    def _init(self, value: Any | None) -> None: ...

    def _forbid_read_transaction(self, txn: Transaction):
        if isinstance(txn, ReadTransaction):
            raise RuntimeError(
                "Read-only transaction cannot be used to modify document structure"
            )

    def _integrate(self, doc: Doc, integrated: Any) -> Any:
        prelim = self._prelim
        self._doc = doc
        self._prelim = None
        self._integrated = integrated
        return prelim

    def _do_and_integrate(
        self, action: str, value: BaseType, txn: _Transaction, *args
    ) -> None:
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


class BaseEvent:
    __slots__ = ()

    def __init__(self, event: Any, doc: Doc):
        slot: str
        for slot in self.__slots__:
            processed = process_event(getattr(event, slot), doc)
            setattr(self, slot, processed)

    def __str__(self):
        str_list = []
        for slot in self.__slots__:
            val = str(getattr(self, slot))
            str_list.append(f"{slot}: {val}")
        ret = ", ".join(str_list)
        return "{" + ret + "}"


def process_event(value: Any, doc: Doc) -> Any:
    if isinstance(value, list):
        for idx, val in enumerate(value):
            value[idx] = process_event(val, doc)
    elif isinstance(value, dict):
        for key, val in value.items():
            value[key] = process_event(val, doc)
    else:
        val_type = type(value)
        if val_type in base_types:
            if val_type is _Doc:
                doc_type: Type[BaseDoc] = cast(Type[BaseDoc], base_types[val_type])
                value = doc_type(doc=value)
            else:
                base_type = cast(Type[BaseType], base_types[val_type])
                value = base_type(_integrated=value, _doc=doc)
    return value
