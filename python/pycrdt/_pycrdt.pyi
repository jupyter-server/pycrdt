from typing import Any, Callable

class Doc:
    """Shared document."""

    def __init__(self, client_id: int | None) -> None:
        """Create a new document with an optional global client ID.
        If no client ID is passed, a random one will be generated."""

    def client_id(self) -> int:
        """Returns the document unique client identifier."""

    def guid(self) -> int:
        """Returns the document globally unique identifier."""

    def create_transaction(self) -> Transaction:
        """Create a document transaction."""

    def create_transaction_with_origin(self, origin: Any) -> Transaction:
        """Create a document transaction with an origin."""

    def get_or_insert_text(self, name: str) -> Text:
        """Create a text root type on this document, or get an existing one."""

    def get_or_insert_array(self, name: str) -> Array:
        """Create an array root type on this document, or get an existing one."""

    def get_or_insert_map(self, name: str) -> Map:
        """Create a map root type on this document, or get an existing one."""

    def get_state(self) -> bytes:
        """Get the current document state."""

    def get_update(self, state: bytes) -> bytes:
        """Get the update from the given state to the current state."""

    def apply_update(self, update: bytes) -> None:
        """Apply the update to the document."""

    def roots(self, txn: Transaction) -> dict[str, Text | Array | Map]:
        """Get top-level (root) shared types available in current document."""

    def observe(self, callback: Callable[[TransactionEvent], None]) -> Subscription:
        """Subscribes a callback to be called with the shared document change event.
        Returns a subscription that can be used to unsubscribe."""

    def observe_subdocs(self, callback: Callable[[SubdocsEvent], None]) -> Subscription:
        """Subscribes a callback to be called with the shared document subdoc change event.
        Returns a subscription that can be used to unsubscribe."""

class Subscription:
    """Observer subscription"""

    def drop(self) -> None:
        """Drop the subscription, effectively unobserving."""

class Transaction:
    """Document transaction"""

    def drop(self) -> None:
        """Drop the transaction, effectively committing document changes."""

    def commit(self) -> None:
        """Commit the document changes."""

    @property
    def origin(self) -> Any:
        """The origin of the transaction."""

class TransactionEvent:
    """Event generated by `Doc.observe` method. Emitted during transaction commit
    phase."""

    @property
    def update(self) -> bytes:
        """The emitted binary update"""

class SubdocsEvent:
    """Event generated by `Doc.observe_subdocs` method. Emitted during transaction commit
    phase."""

class TextEvent:
    """Event generated by `Text.observe` method. Emitted during transaction commit
    phase."""

class ArrayEvent:
    """Event generated by `Array.observe` method. Emitted during transaction commit
    phase."""

class MapEvent:
    """Event generated by `Map.observe` method. Emitted during transaction commit
    phase."""

class Text:
    """Shared text."""

    def len(self, txn: Transaction) -> int:
        """Returns the number of characters visible in the current shared text."""

    def insert(self, txn: Transaction, index: int, chunk: str) -> None:
        """Inserts a `chunk` of text at a given `index`."""

    def remove_range(self, txn: Transaction, index: int, len: int) -> None:
        """Removes up to `len` characters from th current shared text, starting at
        given`index`."""

    def get_string(self, txn: Transaction) -> str:
        """Returns a text representation of the current shared text."""

    def observe(self, callback: Callable[[TextEvent], None]) -> Subscription:
        """Subscribes a callback to be called with the shared text change event.
        Returns a subscription that can be used to unsubscribe."""

    def unobserve(self, subscription: Subscription) -> None:
        """Unsubscribes previously subscribed event callback identified by given
        `subscription`."""

class Array:
    """Shared array."""

    def len(self, txn: Transaction) -> int:
        """Returns the number of elements in the current array."""

    def insert(self, txn: Transaction, index: int, value: Any) -> None:
        """Inserts `value` at the given `index`."""

    def move_to(self, txn: Transaction, source: int, target: int) -> None:
        """Moves element found at `source` index into `target` index position.."""

    def remove_range(self, txn: Transaction, index: int, len: int) -> None:
        """Removes 'len' elements starting at provided `index`."""

    def get(self, txn: Transaction, index: int) -> Any:
        """Retrieves a value stored at a given `index`."""

    def to_json(self, txn: Transaction) -> str:
        """Returns a JSON representation of the current array."""

    def observe(self, callback: Callable[[TextEvent], None]) -> Subscription:
        """Subscribes a callback to be called with the array change event.
        Returns a subscription that can be used to unsubscribe."""

    def observe_deep(self, callback: Callable[[TextEvent], None]) -> Subscription:
        """Subscribes a callback to be called with the array change event
        and its nested elements.
        Returns a subscription that can be used to unsubscribe."""

    def unobserve(self, subscription: Subscription) -> None:
        """Unsubscribes previously subscribed event callback identified by given
        `subscription`."""

class Map:
    """Shared map."""

    def len(self, txn: Transaction) -> int:
        """Returns a number of characters visible in a current text data structure."""

    def insert(self, txn: Transaction, key: str, value: Any) -> None:
        """Inserts `value` at the given `key`."""

    def remove(self, txn: Transaction, key: str) -> None:
        """Removes the `key` entry."""

    def get(self, txn: Transaction, key: str) -> Any:
        """Retrieves a value stored under a given `key`."""

    def to_json(self, txn: Transaction) -> str:
        """Returns a JSON representation of the current map."""

    def observe(self, callback: Callable[[TextEvent], None]) -> Subscription:
        """Subscribes a callback to be called with the map change event.
        Returns a subscription that can be used to unsubscribe."""

    def observe_deep(self, callback: Callable[[TextEvent], None]) -> Subscription:
        """Subscribes a callback to be called with the map change event
        and its nested elements.
        Returns a subscription that can be used to unsubscribe."""

    def unobserve(self, subscription: Subscription) -> None:
        """Unsubscribes previously subscribed event callback identified by given
        `subscription`."""

class UndoManager:
    """Undo manager."""

    def __init__(self, doc: Doc, capture_timeout_millis: int = 500) -> None:
        """Creates an undo manager."""

    def expand_scope(self, scope: Text | Array | Map) -> None:
        """Extends a list of shared types tracked by current undo manager by a given scope."""

    def include_origin(self, origin: int) -> None:
        """Extends a list of origins tracked by current undo manager by a given origin."""

    def exclude_origin(self, origin: int) -> None:
        """Removes an origin from the list of origins tracked by current undo manager."""

    def can_undo(self) -> bool:
        """Whether there is any change to undo."""

    def undo(self) -> bool:
        """Undo last action tracked by current undo manager."""

    def can_redo(self) -> bool:
        """Whether there is any change to redo."""

    def redo(self) -> bool:
        """Redo last action previously undone by current undo manager."""

    def clear(self) -> None:
        """Clear all items stored within current undo manager."""

    def undo_stack(self) -> list[StackItem]:
        """Returns the undo manager's undo stack."""

    def redo_stack(self) -> list[StackItem]:
        """Returns the undo manager's redo stack."""

class StackItem:
    """A unit of work for the undo manager, consisting of
    compressed information about all updates and
    deletions tracked by it.
    """

class Update:
    """
    Alternative update for state and update.

    See https://docs.yjs.dev/api/document-updates#alternative-update-api
    """

    @staticmethod
    def merge_update(updates: list[bytes]) -> bytes:
        """
        Merge several document updates into a single document update
        while removing duplicate information.

        The merged document update is always smaller than the separate updates
        because of the compressed encoding.
        """

    @staticmethod
    def encode_state_vector_from_update(update: bytes) -> bytes:
        """
        Computes the state vector from a document update and encodes it into an update.
        """

    @staticmethod
    def diff_update(update: bytes, state_vector: bytes) -> bytes:
        """
        Encode the missing differences to another update message.
        """
