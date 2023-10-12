use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};
use pyo3::types::{PyString, PyDict, PyList};
use yrs::{
    Doc as _Doc,
    MapRef,
    Map as _Map,
    DeepObservable,
    Observable,
    TransactionMut,
};
use yrs::types::ToJson;
use yrs::types::text::TextPrelim;
use yrs::types::array::ArrayPrelim;
use yrs::types::map::{MapPrelim, MapEvent as _MapEvent};
use lib0::any::Any;
use crate::transaction::Transaction;
use crate::type_conversions::{EntryChangeWrapper, events_into_py, py_to_any, ToPython};
use crate::text::Text;
use crate::array::Array;
use crate::doc::Doc;


#[pyclass(unsendable)]
pub struct Map {
    map: MapRef,
}

impl Map {
    pub fn from(map: MapRef) -> Self {
        Map { map }
    }
}

#[pymethods]
impl Map {
    fn len(&self, txn: &mut Transaction)  -> PyResult<u32> {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let len = self.map.len(t);
        Ok(len)
    }

    fn insert(&self, txn: &mut Transaction, key: &str, value: &PyAny) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        match py_to_any(value) {
            Any::Undefined => Err(PyTypeError::new_err("Type not supported")),
            v => {
                self.map.insert(&mut t, key, v);
                Ok(())
            },
        }
    }

    fn insert_text_prelim(&self, txn: &mut Transaction, key: &str) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        let integrated = self.map.insert(&mut t, key, TextPrelim::new(""));
        let shared = Text::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_array_prelim(&self, txn: &mut Transaction, key: &str) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        let integrated = self.map.insert(&mut t, key, ArrayPrelim::<_, Any>::from([]));
        let shared = Array::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_map_prelim(&self, txn: &mut Transaction, key: &str) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        let integrated = self.map.insert(&mut t, key, MapPrelim::<Any>::new());
        let shared = Map::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_doc(&self, txn: &mut Transaction, key: &str, doc: &PyAny) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        let d1: Doc = doc.extract().unwrap();
        let d2: _Doc = d1.doc;
        let doc_ref = self.map.insert(&mut t, key, d2);
        doc_ref.load(t);
        Ok(())
    }

    fn remove(&self, txn: &mut Transaction, key: &str) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        self.map.remove(&mut t, key);
        Ok(())
    }

    fn get(&self, txn: &mut Transaction, key: &str) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let v = self.map.get(t, key);
        if v == None {
            Err(PyValueError::new_err("Key error"))
        } else {
            Python::with_gil(|py| { Ok(v.unwrap().into_py(py)) })
        }
    }

    fn keys(&self, txn: &mut Transaction) -> PyObject {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let it = self.map.keys(t);
        let mut v: Vec<String> = Vec::new();
        for k in it {
            v.push(k.into());
        }
        Python::with_gil(|py| { PyList::new(py, v).into() })
    }

    fn to_json(&mut self, txn: &mut Transaction) -> PyObject {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let mut s = String::new();
        self.map.to_json(t).to_json(&mut s);
        Python::with_gil(|py| PyString::new(py, s.as_str()).into())
    }

    pub fn observe(&mut self, f: PyObject) -> PyResult<u32> {
        let id: u32 = self.map
            .observe(move |txn, e| {
                Python::with_gil(|py| {
                    let e = MapEvent::new(e, txn);
                    if let Err(err) = f.call1(py, (e,)) {
                        err.restore(py)
                    }
                })
            })
            .into();
        Ok(id)
    }

    pub fn observe_deep(&mut self, f: PyObject) -> PyResult<u32> {
        let id: u32 = self.map
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
        self.map.unobserve(subscription_id);
        Ok(())
    }
}

#[pyclass(unsendable)]
pub struct MapEvent {
    event: *const _MapEvent,
    txn: *const TransactionMut<'static>,
    target: Option<PyObject>,
    keys: Option<PyObject>,
    path: Option<PyObject>,
}

impl MapEvent {
    pub fn new(event: &_MapEvent, txn: &TransactionMut) -> Self {
        let event = event as *const _MapEvent;
        let txn = unsafe { std::mem::transmute::<&TransactionMut, &TransactionMut<'static>>(txn) };
        MapEvent {
            event,
            txn,
            target: None,
            keys: None,
            path: None,
        }
    }

    fn event(&self) -> &_MapEvent {
        unsafe { self.event.as_ref().unwrap() }
    }

    fn txn(&self) -> &TransactionMut {
        unsafe { self.txn.as_ref().unwrap() }
    }
}

#[pymethods]
impl MapEvent {
    #[getter]
    pub fn target(&mut self) -> PyObject {
        if let Some(target) = self.target.as_ref() {
            target.clone()
        } else {
            let target: PyObject = Python::with_gil(|py| Map::from(self.event().target().clone()).into_py(py));
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
    pub fn keys(&mut self) -> PyObject {
        if let Some(keys) = &self.keys {
            keys.clone()
        } else {
            let keys: PyObject = Python::with_gil(|py| {
                let keys = self.event().keys(self.txn());
                let result = PyDict::new(py);
                for (key, value) in keys.iter() {
                    let key = &**key;
                    let value = EntryChangeWrapper(value);
                    result.set_item(key, value.into_py(py)).unwrap();
                }
                result.into()
            });

            self.keys = Some(keys.clone());
            keys
        }
    }

    fn __repr__(&mut self) -> String {
        let target = self.target();
        let keys = self.keys();
        let path = self.path();
        format!("MapEvent(target={target}, keys={keys}, path={path})")
    }
}
