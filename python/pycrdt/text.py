class Text:
    def __init__(self, name: str, doc=None):
        self._doc = doc
        if doc is None:
            pass  # TODO
        else:
            self._text = doc._doc.get_or_insert_text(name)

    def extend(self, chunk: str):
        if self._doc is None:
            raise RuntimeError("Not in a document")

        self._text.extend(self._doc._txn, chunk)
