use pyo3::prelude::*;
use pyo3::types::PyBytes;
use yrs::{
    Doc as _Doc, ReadTxn, Text, TextRef, Transact,
    StateVector,
};
use yrs::updates::encoder::{Encode};
use std::collections::HashMap;
use yrs::updates::decoder::Decode;

struct Op {
    name: String,
    code: u8,
    other: String,
}

#[pyclass(unsendable)]
pub struct Doc {
    doc: _Doc,
    ops: Vec<Op>,
    texts: HashMap<String, TextRef>,
}

#[pymethods]
impl Doc {
    #[new]
    fn new() -> Self {
        let doc = _Doc::new();
        let ops = Vec::new();
        let texts: HashMap<String, TextRef> = HashMap::new();
        Doc {
            doc: doc,
            ops: ops,
            texts: texts,
        }
    }

    fn get_or_insert_text(&mut self, name: &str) -> PyResult<()> {
        let text = self.doc.get_or_insert_text(name);
        self.texts.insert(String::from(name), text);
        Ok(())
    }

    fn text_concat(&mut self, name: &str, code: u8, other: &str) -> PyResult<()> {
        let op = Op {
            name: String::from(name),
            code: code,
            other: String::from(other),
        };
        self.ops.push(op);
        Ok(())
    }

    fn process_transaction(&mut self) -> PyResult<()> {
        let mut txn = self.doc.transact_mut();
        for op in &self.ops {
            let text = self.texts.get(&op.name).unwrap();
            text.push(&mut txn, op.other.as_str());
        }
        drop(txn);
        Ok(())
    }

    fn get_state(&mut self) -> PyObject {
        let txn = self.doc.transact_mut();
        let state = txn.state_vector().encode_v1();
        drop(txn);
        Python::with_gil(|py| PyBytes::new(py, &state).into())
    }

    fn get_update(&mut self, state: &PyBytes) -> PyResult<PyObject> {
        let txn = self.doc.transact_mut();
        let state: &[u8] = FromPyObject::extract(state)?;
        let update = txn.encode_diff_v1(&StateVector::decode_v1(&state).unwrap());
        drop(txn);
        let bytes: PyObject = Python::with_gil(|py| PyBytes::new(py, &update).into());
        Ok(bytes)
    }
}
