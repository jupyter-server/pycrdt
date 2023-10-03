use pyo3::prelude::*;
use pyo3::types::PyBytes;
use yrs::{
    Doc as _Doc,
    ReadTxn,
    Transact,
    StateVector,
};
use yrs::updates::encoder::Encode;
use yrs::updates::decoder::Decode;
use crate::text::Text;
use crate::array::Array;
use crate::map::Map;
use crate::transaction::Transaction;


#[pyclass(unsendable)]
pub struct Doc {
    doc: _Doc,
}

#[pymethods]
impl Doc {
    #[new]
    fn new() -> Self {
        let doc = _Doc::new();
        Doc {
            doc: doc,
        }
    }

    fn get_or_insert_text(&mut self, py: Python<'_>, name: &str) -> PyResult<Py<Text>> {
        let text = self.doc.get_or_insert_text(name);
        let pytext: Py<Text> = Py::new(py, Text::from(text))?;
        Ok(pytext)
    }

    fn get_or_insert_array(&mut self, py: Python<'_>, name: &str) -> PyResult<Py<Array>> {
        let shared = self.doc.get_or_insert_array(name);
        let pyshared: Py<Array > = Py::new(py, Array::from(shared))?;
        Ok(pyshared)
    }

    fn get_or_insert_map(&mut self, py: Python<'_>, name: &str) -> PyResult<Py<Map>> {
        let shared = self.doc.get_or_insert_map(name);
        let pyshared: Py<Map> = Py::new(py, Map::from(shared))?;
        Ok(pyshared)
    }

    fn create_transaction(&self, py: Python<'_>) -> PyResult<Py<Transaction>> {
        let txn = self.doc.transact_mut();
        let t: Py<Transaction> = Py::new(py, Transaction::from(txn))?;
        Ok(t)
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
