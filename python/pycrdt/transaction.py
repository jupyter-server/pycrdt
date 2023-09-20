class Transaction:
    def __init__(self, doc) -> None:
        self._doc = doc
        self._ops = []

    def __enter__(self) -> "Transaction":
        self._doc._txn = self
        return self

    def __exit__(self, *args, **kwargs) -> None:
        for op in self._ops:
            self._doc._doc.text_concat(*op)

        self._doc._doc.process_transaction()

        self._doc._txn = None
