use pyo3::prelude::*;
use pyo3::IntoPyObjectExt;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::types::{PyBytes, PyDict, PyInt, PyList};
use yrs::{
    Doc as _Doc, ReadTxn, StateVector, SubdocsEvent as _SubdocsEvent, Transact, TransactionCleanupEvent, TransactionMut, Update
};
use yrs::updates::encoder::Encode;
use yrs::updates::decoder::Decode;
use crate::text::Text;
use crate::array::Array;
use crate::map::Map;
use crate::transaction::Transaction;
use crate::subscription::Subscription;
use crate::type_conversions::ToPython;
use crate::xml::XmlFragment;


#[pyclass]
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
    fn new(client_id: &Bound<'_, PyAny>) -> Self {
        if client_id.is_none() {
            let doc = _Doc::new();
            return Doc { doc };
        }
        let id: u64 = client_id.downcast::<PyInt>().unwrap().extract().unwrap();
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

    fn get_or_insert_xml_fragment(&mut self, name: &str) -> XmlFragment {
        self.doc.get_or_insert_xml_fragment(name).into()
    }

    fn create_transaction(&self, py: Python<'_>) -> PyResult<Py<Transaction>> {
        if let Ok(txn) = self.doc.try_transact_mut() {
            let t: Py<Transaction> = Py::new(py, Transaction::from(txn))?;
            return Ok(t);
        }
        Err(PyRuntimeError::new_err("Already in a transaction"))
    }

    fn create_transaction_with_origin(&self, py: Python<'_>, origin: i128) -> PyResult<Py<Transaction>> {
        if let Ok(txn) = self.doc.try_transact_mut_with(origin) {
            let t: Py<Transaction> = Py::new(py, Transaction::from(txn))?;
            return Ok(t);
        }
        Err(PyRuntimeError::new_err("Already in a transaction"))
    }

    fn get_state(&mut self) -> PyObject {
        let txn = self.doc.transact_mut();
        let state = txn.state_vector().encode_v1();
        drop(txn);
        Python::with_gil(|py| PyBytes::new(py, &state).into())
    }

    fn get_update(&mut self, state: &Bound<'_, PyBytes>) -> PyResult<PyObject> {
        let txn = self.doc.transact_mut();
        let state: &[u8] = state.extract()?;
        let Ok(state_vector) = StateVector::decode_v1(&state) else { return Err(PyValueError::new_err("Cannot decode state")) };
        let update = txn.encode_diff_v1(&state_vector);
        drop(txn);
        let bytes: PyObject = Python::with_gil(|py| PyBytes::new(py, &update).into());
        Ok(bytes)
    }

    fn apply_update(&mut self, txn: &mut Transaction, update: &Bound<'_, PyBytes>) -> PyResult<()> {
        let u = Update::decode_v1(update.as_bytes()).unwrap();
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap().as_mut();
        t.apply_update(u)
            .map_err(|e| PyRuntimeError::new_err(format!("Cannot apply update: {}", e)))
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

    pub fn observe(&mut self, py: Python<'_>, f: PyObject) -> PyResult<Py<Subscription>> {
        let sub = self.doc
            .observe_transaction_cleanup(move |txn, event| {
                if !event.delete_set.is_empty() || event.before_state != event.after_state {
                    Python::with_gil(|py| {
                        let event = TransactionEvent::new(py, event, txn);
                        if let Err(err) = f.call1(py, (event,)) {
                            err.restore(py)
                        }
                    })
                }
            })
            .unwrap();
        let s: Py<Subscription> = Py::new(py, Subscription::from(sub))?;
        Ok(s)
    }

    pub fn observe_subdocs(&mut self, py: Python<'_>, f: PyObject) -> PyResult<Py<Subscription>> {
        let sub = self.doc
            .observe_subdocs(move |_, event| {
                Python::with_gil(|py| {
                    let event = SubdocsEvent::new(py, event);
                    if let Err(err) = f.call1(py, (event,)) {
                        err.restore(py)
                    }
                })
            })
            .unwrap();
        let s: Py<Subscription> = Py::new(py, Subscription::from(sub))?;
        Ok(s)
    }
}

#[pyclass(unsendable)]
pub struct TransactionEvent {
    event: *const TransactionCleanupEvent,
    txn: *const TransactionMut<'static>,
    before_state: Option<Py<PyBytes>>,
    after_state: Option<Py<PyBytes>>,
    delete_set: Option<Py<PyBytes>>,
    update: Option<Py<PyBytes>>,
    transaction: Option<PyObject>,
}

impl TransactionEvent {
    fn new(py: Python<'_>, event: &TransactionCleanupEvent, txn: &TransactionMut) -> Self {
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
        transaction_event.update(py);
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
    pub fn transaction<'py>(&mut self, py: Python<'py>) -> Bound<'py, PyAny> {
        if let Some(transaction) = &self.transaction {
            transaction.clone_ref(py).into_bound(py)
        } else {
            let transaction = Transaction::from(self.txn()).into_bound_py_any(py).unwrap();
            self.transaction = Some(transaction.clone().unbind());
            transaction
        }
    }

    #[getter]
    pub fn before_state<'py>(&mut self, py: Python<'py>) -> Bound<'py, PyBytes> {
        if let Some(before_state) = &self.before_state {
            before_state.clone_ref(py).into_bound(py)
        } else {
            let before_state = self.event().before_state.encode_v1();
            let before_state = PyBytes::new(py, &before_state);
            self.before_state = Some(before_state.clone().unbind());
            before_state
        }
    }

    #[getter]
    pub fn after_state<'py>(&mut self, py: Python<'py>) -> Bound<'py, PyBytes> {
        if let Some(after_state) = &self.after_state {
            after_state.clone_ref(py).into_bound(py)
        } else {
            let after_state = self.event().after_state.encode_v1();
            let after_state = PyBytes::new(py, &after_state);
            self.after_state = Some(after_state.clone().unbind());
            after_state
        }
    }

    #[getter]
    pub fn delete_set<'py>(&mut self, py: Python<'py>) -> Bound<'py, PyBytes> {
        if let Some(delete_set) = &self.delete_set {
            delete_set.clone_ref(py).into_bound(py)
        } else {
            let delete_set = self.event().delete_set.encode_v1();
            let delete_set = PyBytes::new(py, &delete_set);
            self.delete_set = Some(delete_set.clone().unbind());
            delete_set
        }
    }

    #[getter]
    pub fn update<'py>(&mut self, py: Python<'py>) -> Bound<'py, PyBytes> {
        if let Some(update) = &self.update {
            update.clone_ref(py).into_bound(py)
        } else {
            let update = self.txn().encode_update_v1();
            let update = PyBytes::new(py, &update);
            self.update = Some(update.clone().unbind());
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
    fn new<'py>(py: Python<'py>, event: &_SubdocsEvent) -> Self {
        let added: Vec<String> = event.added().map(|d| d.guid().clone().to_string()).collect();
        let added = PyList::new(py, added).unwrap().into_py_any(py).unwrap();
        let removed: Vec<String> = event.removed().map(|d| d.guid().clone().to_string()).collect();
        let removed = PyList::new(py, removed).unwrap().into_py_any(py).unwrap();
        let loaded: Vec<String> = event.loaded().map(|d| d.guid().clone().to_string()).collect();
        let loaded = PyList::new(py, loaded).unwrap().into_py_any(py).unwrap();
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
    pub fn added(&mut self, py: Python<'_>) -> PyObject {
        self.added.clone_ref(py)
    }

    #[getter]
    pub fn removed(&mut self, py: Python<'_>) -> PyObject {
        self.removed.clone_ref(py)
    }

    #[getter]
    pub fn loaded(&mut self, py: Python<'_>) -> PyObject {
        self.loaded.clone_ref(py)
    }
}
