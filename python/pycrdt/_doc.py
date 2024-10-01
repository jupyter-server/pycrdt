from __future__ import annotations

from typing import Any, Callable, Iterable, Type, TypeVar, cast

from ._base import BaseDoc, BaseType, base_types
from ._pycrdt import Doc as _Doc
from ._pycrdt import SubdocsEvent, Subscription, TransactionEvent
from ._pycrdt import Transaction as _Transaction
from ._transaction import NewTransaction, ReadTransaction, Transaction

T_BaseType = TypeVar("T_BaseType", bound=BaseType)


class Doc(BaseDoc):
    """
    A shared document.

    All shared types live within the scope of their corresponding documents.
    All updates are generated on a per-document basis.
    All operations on shared types happen in a transaction, whose lifetime is also bound to a
    document.
    """

    def __init__(
        self,
        init: dict[str, BaseType] = {},
        *,
        client_id: int | None = None,
        doc: _Doc | None = None,
        Model=None,
        allow_multithreading: bool = False,
    ) -> None:
        """
        Args:
            init: The initial root types of the document.
            client_id: An optional client ID for the document.
            allow_multithreading: Whether to allow the document to be used in different threads.
        """
        super().__init__(
            client_id=client_id, doc=doc, Model=Model, allow_multithreading=allow_multithreading
        )
        for k, v in init.items():
            self[k] = v
        if Model is not None:
            self._twin_doc = Doc(init)

    @property
    def guid(self) -> int:
        """The GUID of the document."""
        return self._doc.guid()

    @property
    def client_id(self) -> int:
        """The document client ID."""
        return self._doc.client_id()

    def transaction(self, origin: Any = None) -> Transaction:
        """
        Creates a new transaction or gets the current one, if any.
        If an origin is passed and there is already an ongoing transaction,
        the passed origin must be the same as the origin of the current transaction.

        This method must be used with a context manager:

        ```py
        with doc.transaction():
            ...
        ```

        Args:
            origin: An optional origin to set on this transaction.

        Raises:
            RuntimeError: Nested transactions must have same origin as root transaction.

        Returns:
            A new transaction or the current one.
        """
        if self._txn is not None:
            if origin is not None:
                if origin != self._txn.origin:
                    raise RuntimeError(
                        "Nested transactions must have same origin as root transaction"
                    )
            return self._txn
        return Transaction(self, origin=origin)

    def new_transaction(self, origin: Any = None, timeout: float | None = None) -> NewTransaction:
        """
        Creates a new transaction.
        Unlike [transaction()][pycrdt.Doc.transaction], this method will not reuse an ongoing
        transaction.
        If there is already an ongoing transaction, this method will wait (with an optional timeout)
        until the current transaction has finished.
        There are two ways to do so:

        - Use an async context manager:
        ```py
        async with doc.new_transaction():
            ...
        ```
        In this case you most likely access the document in the same thread, which means that
        the [Doc][pycrdt.Doc.__init__] can be created with `allow_multithreading=False`.

        - Use a (sync) context manager:
        ```py
        with doc.new_transaction():
            ...
        ```
        In this case you want to use multithreading, as the ongoing transaction must
        run in another thread (otherwise this will deadlock), which means that
        the [Doc][pycrdt.Doc.__init__] must have been created with `allow_multithreading=True`.

        Args:
            origin: An optional origin to set on this transaction.
            timeout: An optional timeout (in seconds) to acquire a new transaction.

        Raises:
            RuntimeError: Already in a transaction.
            TimeoutError: Could not acquire transaction.

        Returns:
            A new transaction.
        """
        return NewTransaction(self, origin=origin, timeout=timeout)

    def _read_transaction(self, _txn: _Transaction) -> ReadTransaction:
        return ReadTransaction(self, _txn)

    def get_state(self) -> bytes:
        """
        Returns:
            The current document state.
        """
        return self._doc.get_state()

    def get_update(self, state: bytes | None = None) -> bytes:
        """
        Args:
            state: The optional document state from which to get the update.

        Returns:
            The update from the given document state (if any), or from the document creation.
        """
        if state is None:
            state = b"\x00"
        return self._doc.get_update(state)

    def apply_update(self, update: bytes) -> None:
        """
        Args:
            update: The update to apply to the document.
        """
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
        """
        Sets a document root type:
        ```py
        doc["text"] = Text("Hello")
        ```

        Args:
            key: The name of the root type.
            value: The root type.

        Raises:
            RuntimeError: Key must be of type string.
        """
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        integrated = value._get_or_insert(key, self)
        prelim = value._integrate(self, integrated)
        value._init(prelim)

    def __getitem__(self, key: str) -> BaseType:
        """
        Gets the document root type corresponding to the given key:
        ```py
        text = doc["text"]
        ```

        Args:
            key: The key of the root type to get.

        Returns:
            The document root type.
        """
        return self._roots[key]

    def __iter__(self) -> Iterable[str]:
        """
        Returns:
            An iterable over the keys of the document root types.
        """
        return iter(self.keys())

    def get(self, key: str, *, type: type[T_BaseType]) -> T_BaseType:
        """
        Gets the document root type corresponding to the given key.
        If it already exists, it will be cast to the given type (if different),
        otherwise a new root type is created.
        ```py
        doc.get("text", type=Text)
        ```

        Returns:
            The root type corresponding to the given key, cast to the given type.
        """
        value = type()
        self[key] = value
        return value

    def keys(self) -> Iterable[str]:
        """
        Returns:
            An iterable over the names of the document root types.
        """
        return self._roots.keys()

    def values(self) -> Iterable[BaseType]:
        """
        Returns:
            An iterable over the document root types.
        """
        return self._roots.values()

    def items(self) -> Iterable[tuple[str, BaseType]]:
        """
        Returns:
            An iterable over the key-value pairs of document root types.
        """
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
        """
        Subscribes a callback to be called with the document change event.

        Args:
            callback: The callback to call with the [TransactionEvent][pycrdt.TransactionEvent].

        Returns:
            The subscription that can be used to [unobserve()][pycrdt.Doc.unobserve].
        """
        subscription = self._doc.observe(callback)
        self._subscriptions.append(subscription)
        return subscription

    def observe_subdocs(self, callback: Callable[[SubdocsEvent], None]) -> Subscription:
        """
        Subscribes a callback to be called with the document subdoc change event.

        Args:
            callback: The callback to call with the [SubdocsEvent][pycrdt.SubdocsEvent].

        Returns:
            The subscription that can be used to [unobserve()][pycrdt.Doc.unobserve].
        """
        subscription = self._doc.observe_subdocs(callback)
        self._subscriptions.append(subscription)
        return subscription

    def unobserve(self, subscription: Subscription) -> None:
        """
        Unsubscribes to changes using the given subscription.

        Args:
            subscription: The subscription to unregister.
        """
        self._subscriptions.remove(subscription)
        subscription.drop()


base_types[_Doc] = Doc
