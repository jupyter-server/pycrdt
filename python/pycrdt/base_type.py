from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Type

from ._pycrdt import Transaction

if TYPE_CHECKING:
    from .doc import Doc


class BaseType(ABC):
    _doc: Doc | None
    _prelim: Any
    _integrated: Any
    _type_name: str
    _integrated_types: dict[Any, Type[BaseType]] = {}

    def __init__(
        self,
        *,
        prelim: Any = None,
        doc: Doc | None = None,
        name: str | None = None,
        _integrated: Any = None,
    ) -> None:
        self._type_name = self.__class__.__name__.lower()
        # private API
        if _integrated is not None:
            self._doc = doc
            self._prelim = None
            self._integrated = _integrated
            return
        # public API
        if doc is None:
            if name is not None:
                raise RuntimeError(
                    "Name only supported when type integrated in a document"
                )
            self._doc = None
            self._prelim = prelim
            self._integrated = None
        else:
            if prelim is not None:
                raise RuntimeError(
                    "Initial content only supported when "
                    "type is not integrated in a document"
                )
            if name is None:
                raise RuntimeError(
                    "Name is required when type is integrated in a document"
                )
            self._doc = doc
            self._prelim = None
            self._integrated = self._get_or_insert(name, doc)

    @abstractmethod
    def _get_or_insert(self, name: str, doc: Doc) -> Any:
        ...

    @abstractmethod
    def _set(self, value: Any) -> None:
        ...

    def _current_transaction(self) -> Transaction:
        if self._doc is None:
            raise RuntimeError("Not associated with a document")
        if self._doc._txn is None:
            raise RuntimeError("No current transaction")
        return self._doc._txn._txn

    def _integrate(self, doc: Doc, integrated: Any) -> None:
        self._doc = doc
        self._prelim = None
        self._integrated = integrated

    def _do_and_integrate(
        self, action: str, other: BaseType, txn: Transaction, *args
    ) -> None:
        if not other.is_prelim:
            raise RuntimeError("Already integrated")
        method = getattr(self._integrated, f"{action}_{other.type_name}_prelim")
        integrated = method(txn, *args)
        prelim = other._prelim
        assert self._doc is not None
        other._integrate(self._doc, integrated)
        other._set(prelim)

    def _maybe_as_type(self, obj: Any) -> Any:
        for k, v in BaseType._integrated_types.items():
            if isinstance(obj, k):
                return v(doc=self._doc, _integrated=obj)
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
    def prelim(self) -> Any:
        return self._prelim

    @property
    def type_name(self) -> str:
        return self._type_name

    def observe(self, callback: Callable[[Any], None]) -> int:
        return self.integrated.observe(callback)

    def unobserve(self, subscription_id: int) -> None:
        self.integrated.unobserve(subscription_id)
