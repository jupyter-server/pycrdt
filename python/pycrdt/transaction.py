from __future__ import annotations

from typing import TYPE_CHECKING

from ._pycrdt import Transaction as _Transaction

if TYPE_CHECKING:
    from .doc import Doc


class Transaction:
    _doc: Doc
    _txn: _Transaction
    _nb: int

    def __init__(self, doc: Doc) -> None:
        self._doc = doc
        self._nb = 0

    def __enter__(self) -> _Transaction:
        self._nb += 1
        if self._doc._txn is None:
            self._doc._txn = self
            self._txn = self._doc._doc.create_transaction()
        return self._txn

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        self._nb -= 1
        # only drop the transaction when exiting root context manager
        # since nested transactions reuse the root transaction
        if self._nb == 0:
            # dropping the transaction will commit, no need to do it
            # self._txn.commit()
            self._txn.drop()
            self._doc._txn = None
