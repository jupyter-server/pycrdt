use pyo3::prelude::*;
mod doc;
mod text;
mod array;
mod map;
mod transaction;
mod type_conversions;
use crate::doc::Doc;
use crate::doc::TransactionEvent;
use crate::text::{Text, TextEvent};
use crate::array::{Array, ArrayEvent};
use crate::map::{Map, MapEvent};
use crate::transaction::Transaction;

#[pymodule]
fn _pycrdt(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Doc>()?;
    m.add_class::<TransactionEvent>()?;
    m.add_class::<Text>()?;
    m.add_class::<TextEvent>()?;
    m.add_class::<Array>()?;
    m.add_class::<ArrayEvent>()?;
    m.add_class::<Map>()?;
    m.add_class::<MapEvent>()?;
    m.add_class::<Transaction>()?;
    Ok(())
}
