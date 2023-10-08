use pyo3::prelude::*;
use pyo3::types::PyBytes;
use yrs::{
    Doc as _Doc,
    ReadTxn,
    Transact,
    TransactionMut,
    TransactionCleanupEvent,
    StateVector,
    Update,
};
use yrs::updates::encoder::Encode;
use yrs::updates::decoder::Decode;
use crate::text::Text;
use crate::array::Array;
use crate::map::Map;
use crate::transaction::Transaction;


#[pyclass(unsendable)]
#[derive(Clone)]
pub struct Doc {
    pub doc: _Doc,
}

impl Doc {
    pub fn from(doc: _Doc) -> Self {
        Doc { doc }
    }
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

    fn apply_update(&mut self, update: &PyBytes) -> PyResult<()> {
        let mut txn = self.doc.transact_mut();
        let bytes: &[u8] = FromPyObject::extract(update)?;
        let u = Update::decode_v1(&bytes).unwrap();
        txn.apply_update(u);
        drop(txn);
        Ok(())
    }

    pub fn observe(&mut self, f: PyObject) -> PyResult<u32> {
        let id: u32 = self.doc
            .observe_transaction_cleanup(move |txn, event| {
                Python::with_gil(|py| {
                    let event = TransactionEvent::new(event, txn);
                    if let Err(err) = f.call1(py, (event,)) {
                        err.restore(py)
                    }
                })
            })
            .unwrap()
            .into();
        Ok(id)
    }
}

#[pyclass(unsendable)]
pub struct TransactionEvent {
    before_state: PyObject,
    after_state: PyObject,
    delete_set: PyObject,
    update: PyObject,
}

impl TransactionEvent {
    fn new(event: &TransactionCleanupEvent, txn: &TransactionMut) -> Self {
        // Convert all event data into Python objects eagerly, so that we don't have to hold
        // on to the transaction.
        let before_state = event.before_state.encode_v1();
        let before_state: PyObject = Python::with_gil(|py| PyBytes::new(py, &before_state).into());
        let after_state = event.after_state.encode_v1();
        let after_state: PyObject = Python::with_gil(|py| PyBytes::new(py, &after_state).into());
        let delete_set = event.delete_set.encode_v1();
        let delete_set: PyObject = Python::with_gil(|py| PyBytes::new(py, &delete_set).into());
        let update = txn.encode_update_v1();
        let update = Python::with_gil(|py| PyBytes::new(py, &update).into());
        TransactionEvent {
            before_state,
            after_state,
            delete_set,
            update,
        }
    }
}

#[pymethods]
impl TransactionEvent {
    #[getter]
    pub fn before_state(&mut self) -> PyObject {
        self.before_state.clone()
    }

    #[getter]
    pub fn after_state(&mut self) -> PyObject {
        self.after_state.clone()
    }

    #[getter]
    pub fn delete_set(&mut self) -> PyObject {
        self.delete_set.clone()
    }

    pub fn get_update(&self) -> PyObject {
        self.update.clone()
    }
}
