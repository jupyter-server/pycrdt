use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};
use pyo3::types::{PyList, PyString};
use yrs::{
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
use lib0::any::Any;
use crate::transaction::Transaction;
use crate::type_conversions::{events_into_py, py_to_any, ToPython};
use crate::text::Text;
use crate::map::Map;
use crate::doc::Doc;


#[pyclass(unsendable)]
pub struct Array {
    array: ArrayRef,
}

impl Array {
    pub fn from(array: ArrayRef) -> Self {
        Array { array }
    }
}

#[pymethods]
impl Array {
    fn len(&self, txn: &mut Transaction)  -> PyResult<u32> {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let len = self.array.len(t);
        Ok(len)
    }

    fn insert(&self, txn: &mut Transaction, index: u32, value: &PyAny) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
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
        let mut t = _t.as_mut().unwrap();
        let integrated = self.array.insert(&mut t, index, TextPrelim::new(""));
        let shared = Text::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_array_prelim(&self, txn: &mut Transaction, index: u32) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        let integrated = self.array.insert(&mut t, index, ArrayPrelim::<_, Any>::from([]));
        let shared = Array::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_map_prelim(&self, txn: &mut Transaction, index: u32) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        let integrated = self.array.insert(&mut t, index, MapPrelim::<Any>::new());
        let shared = Map::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_doc(&self, txn: &mut Transaction, index: u32, doc: &PyAny) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        let d1: Doc = doc.extract().unwrap();
        let d2: _Doc = d1.doc;
        let doc_ref = self.array.insert(&mut t, index, d2);
        doc_ref.load(t);
        Ok(())
    }

    fn remove_range(&self, txn: &mut Transaction, index: u32, len: u32) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        self.array.remove_range(&mut t, index, len);
        Ok(())
    }

    fn get(&self, txn: &mut Transaction, index: u32) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let v = self.array.get(t, index);
        if v == None {
            Err(PyValueError::new_err("Index error"))
        } else {
            Python::with_gil(|py| { Ok(v.unwrap().into_py(py)) })
        }
    }

    fn to_json(&mut self, txn: &mut Transaction) -> PyObject {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let mut s = String::new();
        self.array.to_json(t).to_json(&mut s);
        Python::with_gil(|py| PyString::new(py, s.as_str()).into())
    }

    pub fn observe(&mut self, f: PyObject) -> PyResult<u32> {
        let id: u32 = self.array
            .observe(move |txn, e| {
                Python::with_gil(|py| {
                    let event = ArrayEvent::new(e, txn);
                    if let Err(err) = f.call1(py, (event,)) {
                        err.restore(py)
                    }
                })
            })
            .into();
        Ok(id)
    }

    pub fn observe_deep(&mut self, f: PyObject) -> PyResult<u32> {
        let id: u32 = self.array
            .observe_deep(move |txn, events| {
                Python::with_gil(|py| {
                    let events = events_into_py(txn, events);
                    if let Err(err) = f.call1(py, (events,)) {
                        err.restore(py)
                    }
                })
            })
            .into();
        Ok(id)
    }

    pub fn unobserve(&mut self, subscription_id: u32) -> PyResult<()> {
        self.array.unobserve(subscription_id);
        Ok(())
    }
}

#[pyclass(unsendable)]
pub struct ArrayEvent {
    event: *const _ArrayEvent,
    txn: *const TransactionMut<'static>,
    target: Option<PyObject>,
    delta: Option<PyObject>,
    path: Option<PyObject>,
}

impl ArrayEvent {
    pub fn new(event: &_ArrayEvent, txn: &TransactionMut) -> Self {
        let event = event as *const _ArrayEvent;
        let txn = unsafe { std::mem::transmute::<&TransactionMut, &TransactionMut<'static>>(txn) };
        ArrayEvent {
            event,
            txn,
            target: None,
            delta: None,
            path: None,
        }
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
    pub fn target(&mut self) -> PyObject {
        if let Some(target) = self.target.as_ref() {
            target.clone()
        } else {
            let target: PyObject = Python::with_gil(|py| Array::from(self.event().target().clone()).into_py(py));
            self.target = Some(target.clone());
            target
        }
    }

    #[getter]
    pub fn path(&mut self) -> PyObject {
        if let Some(path) = &self.path {
            path.clone()
        } else {
            let path: PyObject = Python::with_gil(|py| self.event().path().into_py(py));
            self.path = Some(path.clone());
            path
        }
    }

    #[getter]
    pub fn delta(&mut self) -> PyObject {
        if let Some(delta) = &self.delta {
            delta.clone()
        } else {
            let delta: PyObject = Python::with_gil(|py| {
                let delta = self.event().delta(self.txn()).iter().map(|change| {
                    Python::with_gil(|py| change.clone().into_py(py))
                });

                PyList::new(py, delta).into()
            });
            self.delta = Some(delta.clone());
            delta
        }
    }

    fn __repr__(&mut self) -> String {
        let target = self.target();
        let delta = self.delta();
        let path = self.path();
        format!("ArrayEvent(target={target}, delta={delta}, path={path})")
    }
}
