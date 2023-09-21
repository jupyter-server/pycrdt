from ._pycrdt import Transaction as _Transaction


class Transaction:
    def __init__(self, doc) -> None:
        self._doc = doc

    def __enter__(self) -> "Transaction":
        self._doc._txn = txn = self._doc._doc.create_transaction()
        return txn

    def __exit__(self, *args, **kwargs) -> None:
        # dropping the transaction will commit
        # self._doc._txn.commit()
        self._doc._txn.drop()
        self._doc._txn = None
