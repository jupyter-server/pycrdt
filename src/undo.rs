use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use yrs::{
    UndoManager as _UndoManager,
};
use yrs::undo::Options;
use crate::doc::Doc;
use crate::text::Text;
use crate::array::Array;
use crate::map::Map;


#[pyclass(unsendable)]
pub struct UndoManager {
    undo_manager: _UndoManager,
}

#[pymethods]
impl UndoManager {
    #[new]
    fn new(doc: &Doc, capture_timeout_millis: u64) -> Self {
        let mut options = Options::default();
        options.capture_timeout_millis = capture_timeout_millis;
        let undo_manager = _UndoManager::with_options(&doc.doc, options);
        UndoManager { undo_manager }
    }

    pub fn expand_scope_text(&mut self, scope: &Text) {
        self.undo_manager.expand_scope(&scope.text);
    }

    pub fn expand_scope_array(&mut self, scope: &Array) {
        self.undo_manager.expand_scope(&scope.array);
    }

    pub fn expand_scope_map(&mut self, scope: &Map) {
        self.undo_manager.expand_scope(&scope.map);
    }

    pub fn can_undo(&mut self)  -> bool {
        self.undo_manager.can_undo()
    }

    pub fn undo(&mut self)  -> PyResult<bool> {
        let Ok(res) = self.undo_manager.undo() else { return Err(PyRuntimeError::new_err("Cannot undo")) };
        Ok(res)
    }

    pub fn can_redo(&mut self)  -> bool {
        self.undo_manager.can_redo()
    }

    pub fn redo(&mut self)  -> PyResult<bool> {
        let Ok(res) = self.undo_manager.redo() else { return Err(PyRuntimeError::new_err("Cannot redo")) };
        Ok(res)
    }

    pub fn clear(&mut self)  -> PyResult<()> {
        let Ok(res) = self.undo_manager.clear() else { return Err(PyRuntimeError::new_err("Cannot clear")) };
        Ok(res)
    }
}
