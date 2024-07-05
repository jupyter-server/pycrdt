from __future__ import annotations

from typing import TYPE_CHECKING

from ._base import BaseType
from ._pycrdt import UndoManager as _UndoManager

if TYPE_CHECKING:  # pragma: no cover
    from ._doc import Doc


class UndoManager:
    def __init__(
        self,
        *,
        doc: Doc | None = None,
        scopes: list[BaseType] = [],
        capture_timeout_millis: int = 500,
    ) -> None:
        if doc is None:
            if not scopes:
                raise RuntimeError("UndoManager must be created with doc or scopes")
            doc = scopes[0].doc
        elif scopes:
            raise RuntimeError("UndoManager must be created with doc or scopes")
        self._undo_manager = _UndoManager(doc._doc, capture_timeout_millis)
        for scope in scopes:
            self.expand_scope(scope)

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
