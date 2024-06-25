from __future__ import annotations

from ._base import BaseType
from ._pycrdt import UndoManager as _UndoManager


class UndoManager:
    def __init__(self, scope: BaseType, capture_timeout_millis: int = 500) -> None:
        undo_manager = _UndoManager()
        method = getattr(undo_manager, f"from_{scope.type_name}")
        self._undo_manager = method(scope.doc._doc, scope._integrated, capture_timeout_millis)

    def expand_scope(self, scope: BaseType) -> None:
        method = getattr(self._undo_manager, f"expand_scope_{scope.type_name}")
        method(scope._integrated)

    def can_undo(self) -> bool:
        return self._undo_manager.can_undo()

    def undo(self) -> bool:
        return self._undo_manager.undo()

    def can_redo(self) -> bool:
        return self._undo_manager.can_redo()

    def redo(self) -> bool:
        return self._undo_manager.redo()

    def clear(self) -> None:
        self._undo_manager.clear()
