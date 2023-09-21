from ._pycrdt import Doc as _Doc
from ._pycrdt import Transaction as _Transaction
from .text import Text
from .transaction import Transaction


class Doc:
    _doc: _Doc
    _txn: _Transaction | None

    def __init__(self) -> None:
        self._doc = _Doc()
        self._txn = None

    def get_text(self, name: str) -> Text:
        text = Text(name, self)
        return text

    def transaction(self) -> Transaction:
        return Transaction(self)

    def get_state(self) -> bytes:
        return self._doc.get_state()

    def get_update(self, state: bytes) -> bytes:
        return self._doc.get_update(state)
