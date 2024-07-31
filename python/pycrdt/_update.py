from ._pycrdt import get_state as _get_state
from ._pycrdt import get_update as _get_update
from ._pycrdt import merge_updates as _merge_updates


def get_state(update: bytes) -> bytes:
    """Returns a state from an update."""
    return _get_state(update)


def get_update(update: bytes, state: bytes) -> bytes:
    """Returns an update consisting of all changes from a given update which have not
    been seen in the given state.
    """
    return _get_update(update, state)


def merge_updates(*updates: bytes) -> bytes:
    """Returns an update consisting of a combination of all given updates."""
    return _merge_updates(updates)
