from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any

from ._pycrdt import Transaction as _Transaction

if TYPE_CHECKING:  # pragma: no cover
    from ._doc import Doc


class Transaction:
    _doc: Doc
    _txn: _Transaction | None
    _nb: int
    _origin_hash: int | None

    def __init__(self, doc: Doc, _txn: _Transaction | None = None, *, origin: Any = None) -> None:
        self._doc = doc
        self._txn = _txn
        self._nb = 0
        if origin is None:
            self._origin_hash = None
        else:
            self._origin_hash = hash_origin(origin)
            doc._origins[self._origin_hash] = origin

    def __enter__(self) -> Transaction:
        self._nb += 1
        if self._txn is None:
            if self._origin_hash is not None:
                self._txn = self._doc._doc.create_transaction_with_origin(self._origin_hash)
            else:
                self._txn = self._doc._doc.create_transaction()
        self._doc._txn = self
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._nb -= 1
        # only drop the transaction when exiting root context manager
        # since nested transactions reuse the root transaction
        if self._nb == 0:
            assert self._txn is not None
            if not isinstance(self, ReadTransaction):
                self._txn.commit()
                origin_hash = self._txn.origin()
                if origin_hash is not None:
                    del self._doc._origins[origin_hash]
            self._txn.drop()
            self._txn = None
            self._doc._txn = None

    @property
    def origin(self) -> Any:
        if self._txn is None:
            raise RuntimeError("No current transaction")

        origin_hash = self._txn.origin()
        if origin_hash is None:
            return None

        return self._doc._origins[origin_hash]


class ReadTransaction(Transaction):
    pass


def hash_origin(origin: Any) -> int:
    try:
        return hash(origin)
    except Exception:
        raise TypeError("Origin must be hashable")
