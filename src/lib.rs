use pyo3::prelude::*;
mod doc;
use crate::doc::Doc;

/// A Python module implemented in Rust.
#[pymodule]
fn _pycrdt(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Doc>()?;
    Ok(())
}
