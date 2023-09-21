use pyo3::prelude::*;
use yrs::{
    TextRef,
    Text as _Text,
};
use crate::transaction::Transaction;


#[pyclass(unsendable)]
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
    //#[new]
    //pub fn new(text: TextRef) -> Self {
    //    Text {
    //        text: text,
    //    }
    //}

    fn extend(&self, txn: &mut Transaction, chunk: &str)  -> PyResult<()> {
        let mut t1 = txn.transaction();
        let mut t2 = t1.as_mut().unwrap();
        self.text.push(&mut t2, chunk);
        Ok(())
    }
}
