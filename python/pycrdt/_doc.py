from __future__ import annotations

from typing import Any, Callable, Type, TypeVar, cast

from ._base import BaseDoc, BaseType, base_types
from ._pycrdt import Doc as _Doc
from ._pycrdt import SubdocsEvent, Subscription, TransactionEvent
from ._pycrdt import Transaction as _Transaction
from ._transaction import ReadTransaction, Transaction

T_BaseType = TypeVar("T_BaseType", bound=BaseType)


class Doc(BaseDoc):
    def __init__(
        self,
        init: dict[str, BaseType] = {},
        *,
        client_id: int | None = None,
        doc: _Doc | None = None,
        Model=None,
    ) -> None:
        super().__init__(client_id=client_id, doc=doc, Model=Model)
        for k, v in init.items():
            self[k] = v
        if Model is not None:
            self._twin_doc = Doc(init)

    @property
    def guid(self) -> int:
        return self._doc.guid()

    @property
    def client_id(self) -> int:
        return self._doc.client_id()

    def transaction(self, origin: Any = None) -> Transaction:
        if self._txn is not None:
            return self._txn
        return Transaction(self, origin=origin)

    def _read_transaction(self, _txn: _Transaction) -> ReadTransaction:
        return ReadTransaction(self, _txn)

    def get_state(self) -> bytes:
        return self._doc.get_state()

    def get_update(self, state: bytes | None = None) -> bytes:
        if state is None:
            state = b"\x00"
        return self._doc.get_update(state)

    def apply_update(self, update: bytes) -> None:
        if self._Model is not None:
            twin_doc = cast(Doc, self._twin_doc)
            twin_doc.apply_update(update)
            d = {k: twin_doc[k].to_py() for k in self._Model.model_fields}
            try:
                self._Model(**d)
            except Exception as e:
                self._twin_doc = Doc(dict(self))
                raise e
        self._doc.apply_update(update)

    def __setitem__(self, key: str, value: BaseType) -> None:
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        integrated = value._get_or_insert(key, self)
        prelim = value._integrate(self, integrated)
        value._init(prelim)

    def __getitem__(self, key: str) -> BaseType:
        return self._roots[key]

    def __iter__(self):
        return iter(self.keys())

    def get(self, key: str, *, type: type[T_BaseType]) -> T_BaseType:
        value = type()
        self[key] = value
        return value

    def keys(self):
        return self._roots.keys()

    def values(self):
        return self._roots.values()

    def items(self):
        return self._roots.items()

    @property
    def _roots(self) -> dict[str, BaseType]:
        with self.transaction() as txn:
            assert txn._txn is not None
            return {
                key: (
                    None
                    if val is None
                    else cast(Type[BaseType], base_types[type(val)])(_integrated=val, _doc=self)
                )
                for key, val in self._doc.roots(txn._txn).items()
            }

    def observe(self, callback: Callable[[TransactionEvent], None]) -> Subscription:
        subscription = self._doc.observe(callback)
        self._subscriptions.append(subscription)
        return subscription

    def observe_subdocs(self, callback: Callable[[SubdocsEvent], None]) -> Subscription:
        subscription = self._doc.observe_subdocs(callback)
        self._subscriptions.append(subscription)
        return subscription

    def unobserve(self, subscription: Subscription) -> None:
        self._subscriptions.remove(subscription)
        subscription.drop()


base_types[_Doc] = Doc
