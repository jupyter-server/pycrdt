from ._pycrdt import Doc as _Doc
from .text import Text
from .transaction import Transaction


class Doc:
    _doc: _Doc
    _data: dict[str, Text]
    _txn: Transaction | None

    def __init__(self) -> None:
        self._doc = _Doc()
        self._data = {}
        self._txn = None

    def get_text(self, name: str) -> Text:
        if name in self._data:
            if not isinstance(self._data[name], Text):
                raise RuntimeError("Not a Text")
        else:
            text = Text(name, self)
            self._data[name] = text
        return self._data[name]

    def transaction(self) -> Transaction:
        return Transaction(self)

    def get_state(self) -> bytes:
        return self._doc.get_state()

    def get_update(self, state: bytes) -> bytes:
        return self._doc.get_update(state)
