from enum import IntEnum


class TextOp(IntEnum):
    CONCAT = 0


class Text:
    def __init__(self, name: str, doc=None):
        self._name = name
        self._doc = doc
        if doc is not None:
            doc._doc.get_or_insert_text(name)

    def concat(self, other: str):
        if self._doc is None:
            raise RuntimeError("Not in a document")

        if self._doc._txn is None:
            raise RuntimeError("No current transaction")

        self._doc._txn._ops.append([self._name, TextOp.CONCAT, other])
