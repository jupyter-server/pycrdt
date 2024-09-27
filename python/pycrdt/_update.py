from ._pycrdt import get_state as _get_state
from ._pycrdt import get_update as _get_update
from ._pycrdt import merge_updates as _merge_updates


def get_state(update: bytes) -> bytes:
    """
    Returns a state from an update.

    Args:
        update: The update from which to get the state.

    Returns:
        The state corresponding to the update.
    """
    return _get_state(update)


def get_update(update: bytes, state: bytes) -> bytes:
    """
    Returns an update consisting of all changes from a given update which have not
    been seen in the given state.

    Args:
        update: The update from which to get all missing changes in the given state.
        state: The state from which to get missing changes that are in the given update.

    Returns:
        The changes from the given update not present in the given state.
    """
    return _get_update(update, state)


def merge_updates(*updates: bytes) -> bytes:
    """
    Returns an update consisting of a combination of all given updates.

    Args:
        updates: The updates to merge.

    Returns:
        The merged updates.
    """
    return _merge_updates(updates)
