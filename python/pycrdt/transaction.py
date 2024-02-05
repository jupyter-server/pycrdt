from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING

from ._pycrdt import Transaction as _Transaction

if TYPE_CHECKING:  # pragma: no cover
    from .doc import Doc


class Transaction:
    _doc: Doc
    _txn: _Transaction | None
    _nb: int

    def __init__(self, doc: Doc, _txn: _Transaction | None = None) -> None:
        self._doc = doc
        self._txn = _txn
        self._nb = 0

    def __enter__(self) -> Transaction:
        self._nb += 1
        if self._txn is None:
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
            # dropping the transaction will commit, no need to do it
            # self._txn.commit()
            assert self._txn is not None
            self._txn.drop()
            self._txn = None
            self._doc._txn = None


class ReadTransaction(Transaction):
    pass
