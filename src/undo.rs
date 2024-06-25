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
    undo_manager: Option<_UndoManager>,
}

impl UndoManager {
    fn get_options(&self, capture_timeout_millis: &u64) -> Options {
        let mut options = Options::default();
        options.capture_timeout_millis = *capture_timeout_millis;
        options
    }
}

#[pymethods]
impl UndoManager {
    #[new]
    fn new() -> Self {
        UndoManager { undo_manager: None }
    }

    pub fn from_text(&self, doc: &Doc, scope: &Text, capture_timeout_millis: u64) -> Self {
        let options = self.get_options(&capture_timeout_millis);
        let undo_manager = _UndoManager::with_options(&doc.doc, &scope.text, options);
        UndoManager { undo_manager: Some(undo_manager) }
    }

    pub fn from_array(&self, doc: &Doc, scope: &Array, capture_timeout_millis: u64) -> Self {
        let options = self.get_options(&capture_timeout_millis);
        let undo_manager = _UndoManager::with_options(&doc.doc, &scope.array, options);
        UndoManager { undo_manager: Some(undo_manager) }
    }

    pub fn from_map(&self, doc: &Doc, scope: &Map, capture_timeout_millis: u64) -> Self {
        let options = self.get_options(&capture_timeout_millis);
        let undo_manager = _UndoManager::with_options(&doc.doc, &scope.map, options);
        UndoManager { undo_manager: Some(undo_manager) }
    }

    pub fn expand_scope_text(&mut self, scope: &Text) {
        self.undo_manager.as_mut().unwrap().expand_scope(&scope.text);
    }

    pub fn expand_scope_array(&mut self, scope: &Array) {
        self.undo_manager.as_mut().unwrap().expand_scope(&scope.array);
    }

    pub fn expand_scope_map(&mut self, scope: &Map) {
        self.undo_manager.as_mut().unwrap().expand_scope(&scope.map);
    }

    pub fn can_undo(&mut self)  -> bool {
        self.undo_manager.as_ref().unwrap().can_undo()
    }

    pub fn undo(&mut self)  -> PyResult<bool> {
        let Ok(res) = self.undo_manager.as_mut().unwrap().undo() else { return Err(PyRuntimeError::new_err("Cannot undo")) };
        Ok(res)
    }

    pub fn can_redo(&mut self)  -> bool {
        self.undo_manager.as_ref().unwrap().can_redo()
    }

    pub fn redo(&mut self)  -> PyResult<bool> {
        let Ok(res) = self.undo_manager.as_mut().unwrap().redo() else { return Err(PyRuntimeError::new_err("Cannot redo")) };
        Ok(res)
    }

    pub fn clear(&mut self)  -> PyResult<()> {
        let Ok(res) = self.undo_manager.as_mut().unwrap().clear() else { return Err(PyRuntimeError::new_err("Cannot clear")) };
        Ok(res)
    }
}
