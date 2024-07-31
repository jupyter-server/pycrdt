use pyo3::prelude::*;
mod doc;
mod text;
mod array;
mod map;
mod transaction;
mod subscription;
mod type_conversions;
mod undo;
mod update;
use crate::doc::Doc;
use crate::doc::TransactionEvent;
use crate::doc::SubdocsEvent;
use crate::text::{Text, TextEvent};
use crate::array::{Array, ArrayEvent};
use crate::map::{Map, MapEvent};
use crate::transaction::Transaction;
use crate::subscription::Subscription;
use crate::undo::{StackItem, UndoManager};
use crate::update::{get_state, get_update, merge_updates};

#[pymodule]
fn _pycrdt(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Doc>()?;
    m.add_class::<TransactionEvent>()?;
    m.add_class::<SubdocsEvent>()?;
    m.add_class::<Text>()?;
    m.add_class::<TextEvent>()?;
    m.add_class::<Array>()?;
    m.add_class::<ArrayEvent>()?;
    m.add_class::<Map>()?;
    m.add_class::<MapEvent>()?;
    m.add_class::<Transaction>()?;
    m.add_class::<StackItem>()?;
    m.add_class::<Subscription>()?;
    m.add_class::<UndoManager>()?;
    m.add_function(wrap_pyfunction!(get_state, m)?)?;
    m.add_function(wrap_pyfunction!(get_update, m)?)?;
    m.add_function(wrap_pyfunction!(merge_updates, m)?)?;
    Ok(())
}
