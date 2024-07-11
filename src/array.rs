use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};
use pyo3::types::{PyList, PyString};
use yrs::{
    Any,
    ArrayRef,
    Array as _Array,
    Doc as _Doc,
    DeepObservable,
    Observable,
    TransactionMut,
};
use yrs::types::ToJson;
use yrs::types::text::TextPrelim;
use yrs::types::array::{ArrayPrelim, ArrayEvent as _ArrayEvent};
use yrs::types::map::MapPrelim;
use crate::transaction::Transaction;
use crate::subscription::Subscription;
use crate::type_conversions::{events_into_py, py_to_any, ToPython};
use crate::text::Text;
use crate::map::Map;
use crate::doc::Doc;


#[pyclass]
pub struct Array {
    pub array: ArrayRef,
}

impl Array {
    pub fn from(array: ArrayRef) -> Self {
        Array { array }
    }
}

#[pymethods]
impl Array {
    fn len(&self, txn: &mut Transaction)  -> PyResult<u32> {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();
        let len = self.array.len(t);
        Ok(len)
    }

    fn insert(&self, txn: &mut Transaction, index: u32, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        match py_to_any(value) {
            Any::Undefined => Err(PyTypeError::new_err("Type not supported")),
            v => {
                self.array.insert(&mut t, index, v);
                Ok(())
            },
        }
    }

    fn insert_text_prelim(&self, txn: &mut Transaction, index: u32) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        let integrated = self.array.insert(&mut t, index, TextPrelim::new(""));
        let shared = Text::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_array_prelim(&self, txn: &mut Transaction, index: u32) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        let integrated = self.array.insert(&mut t, index, ArrayPrelim::default());
        let shared = Array::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_map_prelim(&self, txn: &mut Transaction, index: u32) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        let integrated = self.array.insert(&mut t, index, MapPrelim::default());
        let shared = Map::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_doc(&self, txn: &mut Transaction, index: u32, doc: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        let d1: Doc = doc.extract().unwrap();
        let d2: _Doc = d1.doc;
        let doc_ref = self.array.insert(&mut t, index, d2);
        doc_ref.load(t);
        Ok(())
    }

    fn move_to(&self, txn: &mut Transaction, source: u32, target: u32) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        self.array.move_to(&mut t, source, target);
        Ok(())
    }

    fn remove_range(&self, txn: &mut Transaction, index: u32, len: u32) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        self.array.remove_range(&mut t, index, len);
        Ok(())
    }

    fn get(&self, txn: &mut Transaction, index: u32) -> PyResult<PyObject> {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();
        let v = self.array.get(t, index);
        if v == None {
            Err(PyValueError::new_err("Index error"))
        } else {
            Python::with_gil(|py| { Ok(v.unwrap().into_py(py)) })
        }
    }

    fn to_json(&mut self, txn: &mut Transaction) -> PyObject {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();
        let mut s = String::new();
        self.array.to_json(t).to_json(&mut s);
        Python::with_gil(|py| PyString::new_bound(py, s.as_str()).into())
    }

    pub fn observe(&mut self, py: Python<'_>, f: PyObject) -> PyResult<Py<Subscription>> {
        let sub = self.array
            .observe(move |txn, e| {
                Python::with_gil(|py| {
                    let event = ArrayEvent::new(e, txn);
                    if let Err(err) = f.call1(py, (event,)) {
                        err.restore(py)
                    }
                })
            });
        let s: Py<Subscription> = Py::new(py, Subscription::from(sub))?;
        Ok(s)
    }

    pub fn observe_deep(&mut self, py: Python<'_>, f: PyObject) -> PyResult<Py<Subscription>> {
        let sub = self.array
            .observe_deep(move |txn, events| {
                Python::with_gil(|py| {
                    let events = events_into_py(txn, events);
                    if let Err(err) = f.call1(py, (events,)) {
                        err.restore(py)
                    }
                })
            });
        let s: Py<Subscription> = Py::new(py, Subscription::from(sub))?;
        Ok(s)
    }
}

#[pyclass(unsendable)]
pub struct ArrayEvent {
    event: *const _ArrayEvent,
    txn: *const TransactionMut<'static>,
    target: Option<PyObject>,
    delta: Option<PyObject>,
    path: Option<PyObject>,
    transaction: Option<PyObject>,
}

impl ArrayEvent {
    pub fn new(event: &_ArrayEvent, txn: &TransactionMut) -> Self {
        let event = event as *const _ArrayEvent;
        let txn = unsafe { std::mem::transmute::<&TransactionMut, &TransactionMut<'static>>(txn) };
        let mut array_event = ArrayEvent {
            event,
            txn,
            target: None,
            delta: None,
            path: None,
            transaction: None,
        };
        Python::with_gil(|py| {
            array_event.target(py);
            array_event.path(py);
            array_event.delta(py);
        });
        array_event
    }

    fn event(&self) -> &_ArrayEvent {
        unsafe { self.event.as_ref().unwrap() }
    }

    fn txn(&self) -> &TransactionMut {
        unsafe { self.txn.as_ref().unwrap() }
    }
}

#[pymethods]
impl ArrayEvent {
    #[getter]
    pub fn transaction(&mut self, py: Python<'_>) -> PyObject {
        if let Some(transaction) = &self.transaction {
            transaction.clone_ref(py)
        } else {
            let transaction: PyObject = Transaction::from(self.txn()).into_py(py);
            let res = transaction.clone_ref(py);
            self.transaction = Some(transaction);
            res
        }
    }

    #[getter]
    pub fn target(&mut self, py: Python<'_>) -> PyObject {
        if let Some(target) = &self.target {
            target.clone_ref(py)
        } else {
            let target: PyObject = Array::from(self.event().target().clone()).into_py(py);
            let res = target.clone_ref(py);
            self.target = Some(target);
            res
        }
    }

    #[getter]
    pub fn path(&mut self, py: Python<'_>) -> PyObject {
        if let Some(path) = &self.path {
            path.clone_ref(py)
        } else {
            let path: PyObject = self.event().path().into_py(py);
            let res = path.clone_ref(py);
            self.path = Some(path);
            res
        }
    }

    #[getter]
    pub fn delta(&mut self, py: Python<'_>) -> PyObject {
        if let Some(delta) = &self.delta {
            delta.clone_ref(py)
        } else {
            let delta: PyObject = {
                let delta = self.event().delta(self.txn()).iter().map(|change| {
                    change.clone().into_py(py)
                });
                PyList::new_bound(py, delta).into()
            };
            let res = delta.clone_ref(py);
            self.delta = Some(delta);
            res
        }
    }

    fn __repr__(&mut self, py: Python<'_>) -> String {
        let target = self.target(py);
        let delta = self.delta(py);
        let path = self.path(py);
        format!("ArrayEvent(target={target}, delta={delta}, path={path})")
    }
}
