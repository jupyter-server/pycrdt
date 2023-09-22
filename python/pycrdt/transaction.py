from __future__ import annotations

from typing import TYPE_CHECKING

from ._pycrdt import Transaction as _Transaction

if TYPE_CHECKING:
    from .doc import Doc


class Transaction:
    _doc: "Doc"

    def __init__(self, doc: "Doc") -> None:
        self._doc = doc

    def __enter__(self) -> _Transaction:
        self._doc._txn = txn = self._doc._doc.create_transaction()
        return txn

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        # dropping the transaction will commit, no need to do it
        # self._doc._txn.commit()
        assert self._doc._txn is not None
        self._doc._txn.drop()
        self._doc._txn = None
