use pyo3::prelude::*;
mod doc;
mod text;
mod transaction;
mod type_conversions;
use crate::doc::Doc;
use crate::text::{Text, TextEvent};
use crate::transaction::Transaction;

#[pymodule]
fn _pycrdt(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Doc>()?;
    m.add_class::<Text>()?;
    m.add_class::<TextEvent>()?;
    m.add_class::<Transaction>()?;
    Ok(())
}
