class Doc:
    """Collaborative document."""

    def create_transaction(self) -> Transaction:
        """Create a document transaction."""
    def get_or_insert_text(self, name: str) -> Text:
        """Create a text root type on this document, or get an existing one."""
    def get_state(self) -> bytes:
        """Get the current document state."""
    def get_update(self, state: bytes) -> bytes:
        """Get the update from the given state to the current state."""

class Transaction:
    """Document transaction"""

    def drop(self) -> None:
        """Drop the transaction, effectively committing document changes."""
    def commit(self) -> None:
        """Commit the document changes."""

class Text:
    """Collaborative text structure."""

    def len(self, txn: Transaction) -> int:
        """Returns a number of characters visible in a current text data structure."""
    def push(self, txn: Transaction, chunk: str) -> None:
        """Appends a given `chunk` of text at the end of a current text structure."""
    def remove_range(self, txn: Transaction, index: int, len: int) -> None:
        """Removes up to `len` characters from a current text structure, starting at
        given`index`."""
