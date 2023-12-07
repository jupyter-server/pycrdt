use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyLong, PyList};
use yrs::{
    Doc as _Doc,
    ReadTxn,
    Transact,
    TransactionMut,
    TransactionCleanupEvent,
    SubdocsEvent as _SubdocsEvent,
    StateVector,
    Update,
};
use yrs::updates::encoder::Encode;
use yrs::updates::decoder::Decode;
use crate::text::Text;
use crate::array::Array;
use crate::map::Map;
use crate::transaction::Transaction;
use crate::type_conversions::ToPython;


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
    fn new(client_id: &PyAny) -> Self {
        if client_id.is_none() {
            let doc = _Doc::new();
            return Doc { doc };
        }
        let id: u64 = client_id.downcast::<PyLong>().unwrap().extract().unwrap();
        let doc = _Doc::with_client_id(id);
        Doc { doc }
    }

    fn guid(&mut self) -> String {
        self.doc.guid().to_string()
    }

    fn client_id(&mut self) -> u64 {
        self.doc.client_id()
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

    fn roots(&self, py: Python<'_>, txn: &mut Transaction) -> PyObject {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();
        let result = PyDict::new(py);
        for (k, v) in t.root_refs() {
            result.set_item(k, v.into_py(py)).unwrap();
        }
        result.into()
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

    pub fn observe_subdocs(&mut self, f: PyObject) -> PyResult<u32> {
        let id: u32 = self.doc
            .observe_subdocs(move |_, event| {
                Python::with_gil(|py| {
                    let event = SubdocsEvent::new(event);
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
    event: *const TransactionCleanupEvent,
    txn: *const TransactionMut<'static>,
    before_state: Option<PyObject>,
    after_state: Option<PyObject>,
    delete_set: Option<PyObject>,
    update: Option<PyObject>,
    transaction: Option<PyObject>,
}

impl TransactionEvent {
    fn new(event: &TransactionCleanupEvent, txn: &TransactionMut) -> Self {
        let event = event as *const TransactionCleanupEvent;
        let txn = unsafe { std::mem::transmute::<&TransactionMut, &TransactionMut<'static>>(txn) };
        let mut transaction_event = TransactionEvent {
            event,
            txn,
            before_state: None,
            after_state: None,
            delete_set: None,
            update: None,
            transaction: None,
        };
        transaction_event.update();
        transaction_event
    }

    fn event(&self) -> &TransactionCleanupEvent {
        unsafe { self.event.as_ref().unwrap() }
    }
    fn txn(&self) -> &TransactionMut {
        unsafe { self.txn.as_ref().unwrap() }
    }
}

#[pymethods]
impl TransactionEvent {
    #[getter]
    pub fn transaction(&mut self) -> PyObject {
        if let Some(transaction) = self.transaction.as_ref() {
            transaction.clone()
        } else {
            let transaction: PyObject = Python::with_gil(|py| Transaction::from(self.txn()).into_py(py));
            self.transaction = Some(transaction.clone());
            transaction
        }
    }

    #[getter]
    pub fn before_state(&mut self) -> PyObject {
        if let Some(before_state) = &self.before_state {
            before_state.clone()
        } else {
            let before_state = self.event().before_state.encode_v1();
            let before_state: PyObject = Python::with_gil(|py| PyBytes::new(py, &before_state).into());
            self.before_state = Some(before_state.clone());
            before_state
        }
    }

    #[getter]
    pub fn after_state(&mut self) -> PyObject {
        if let Some(after_state) = &self.after_state {
            after_state.clone()
        } else {
            let after_state = self.event().after_state.encode_v1();
            let after_state: PyObject = Python::with_gil(|py| PyBytes::new(py, &after_state).into());
            self.after_state = Some(after_state.clone());
            after_state
        }
    }

    #[getter]
    pub fn delete_set(&mut self) -> PyObject {
        if let Some(delete_set) = &self.delete_set {
            delete_set.clone()
        } else {
            let delete_set = self.event().delete_set.encode_v1();
            let delete_set: PyObject = Python::with_gil(|py| PyBytes::new(py, &delete_set).into());
            self.delete_set = Some(delete_set.clone());
            delete_set
        }
    }

    #[getter]
    pub fn update(&mut self) -> PyObject {
        if let Some(update) = &self.update {
            update.clone()
        } else {
            let update = self.txn().encode_update_v1();
            let update: PyObject = Python::with_gil(|py| PyBytes::new(py, &update).into());
            self.update = Some(update.clone());
            update
        }
    }
}

#[pyclass(unsendable)]
pub struct SubdocsEvent {
    added: PyObject,
    removed: PyObject,
    loaded: PyObject,
}

impl SubdocsEvent {
    fn new(event: &_SubdocsEvent) -> Self {
        let added: Vec<String> = event.added().map(|d| d.guid().clone().to_string()).collect();
        let added: PyObject = Python::with_gil(|py| PyList::new(py, &added).into());
        let removed: Vec<String> = event.removed().map(|d| d.guid().clone().to_string()).collect();
        let removed: PyObject = Python::with_gil(|py| PyList::new(py, &removed).into());
        let loaded: Vec<String> = event.loaded().map(|d| d.guid().clone().to_string()).collect();
        let loaded: PyObject = Python::with_gil(|py| PyList::new(py, &loaded).into());
        SubdocsEvent {
            added,
            removed,
            loaded,
        }
    }
}

#[pymethods]
impl SubdocsEvent {
    #[getter]
    pub fn added(&mut self) -> PyObject {
        self.added.clone()
    }

    #[getter]
    pub fn removed(&mut self) -> PyObject {
        self.removed.clone()
    }

    #[getter]
    pub fn loaded(&mut self) -> PyObject {
        self.loaded.clone()
    }
}
