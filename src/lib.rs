use pyo3::prelude::*;
mod doc;
mod text;
mod transaction;
use crate::doc::Doc;
use crate::text::Text;
use crate::transaction::Transaction;

/// A Python module implemented in Rust.
#[pymodule]
fn _pycrdt(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Doc>()?;
    m.add_class::<Text>()?;
    m.add_class::<Transaction>()?;
    Ok(())
}
