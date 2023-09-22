class Doc:
    """Collaborative document.
    """
    def create_transaction(self) -> Transaction:
        """Create a document transaction.
        """

    def get_or_insert_text(self, name: str) -> Text:
        """Create a text root type on this document, or get an existing one.
        """

    def get_state(self) -> bytes:
        """Get the current document state.
        """

    def get_update(self, state: bytes) -> bytes:
        """Get the update from the given state to the current state.
        """


class Transaction:
    """Document transaction
    """
    def drop(self) -> None:
        """Drop the transaction, effectively committing document changes.
        """


class Text:
    """Collaborative text structure.
    """
    def extend(self, txn: Transaction, chunk: str) -> None:
        """Extend the text structure with more text.
        """
