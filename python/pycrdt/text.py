from __future__ import annotations

from typing import TYPE_CHECKING

from ._pycrdt import Text as _Text

if TYPE_CHECKING:
    from .doc import Doc


class Text:
    _doc: Doc | None
    _text: _Text

    def __init__(self, name: str, doc: Doc = None):
        self._doc = doc
        if doc is None:
            pass  # TODO: prelim
        else:
            self._text = doc._doc.get_or_insert_text(name)

    def __iadd__(self, other: str):
        if self._doc is None:
            raise RuntimeError("Not in a document")

        self._text.extend(self._doc._txn, other)
