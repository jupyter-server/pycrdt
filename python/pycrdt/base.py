from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Type

from ._pycrdt import Doc as _Doc
from ._pycrdt import Transaction as _Transaction
from .transaction import Transaction

if TYPE_CHECKING:
    from .doc import Doc


integrated_types: dict[Any, Type[BaseType | BaseDoc]] = {}


class BaseDoc:
    _doc: _Doc
    _txn: Transaction | None

    def __init__(self, doc: _Doc | None = None) -> None:
        if doc is None:
            doc = _Doc()
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
        for k, v in integrated_types.items():
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

    def observe(self, callback: Callable[[Any], None]) -> int:
        return self.integrated.observe(callback)

    def observe_deep(self, callback: Callable[[Any], None]) -> int:
        return self.integrated.observe_deep(callback)

    def unobserve(self, subscription_id: int) -> None:
        self.integrated.unobserve(subscription_id)
