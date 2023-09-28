use pyo3::prelude::*;
use yrs::{
    TextRef,
    Text as _Text,
};
use crate::transaction::Transaction;


#[pyclass]
pub struct Text {
    text: TextRef,
}

impl Text {
    pub fn from_text(text: TextRef) -> Self {
        Text {
            text,
        }
    }
}

#[pymethods]
impl Text {
    fn len(&self, txn: &mut Transaction)  -> PyResult<u32> {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let len = self.text.len(t);
        Ok(len)
    }

    fn push(&self, py: Python<'_>, txn: &mut Transaction, chunk: &str)  -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        py.allow_threads(|| self.text.push(&mut t, chunk));
        Ok(())
    }

    fn remove_range(&self, txn: &mut Transaction, index: u32, len: u32)  -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        self.text.remove_range(&mut t, index, len);
        Ok(())
    }
}
