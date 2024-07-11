use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyTypeError};
use pyo3::types::{PyString, PyDict, PyList};
use yrs::{
    Any,
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
use crate::transaction::Transaction;
use crate::subscription::Subscription;
use crate::type_conversions::{EntryChangeWrapper, events_into_py, py_to_any, ToPython};
use crate::text::Text;
use crate::array::Array;
use crate::doc::Doc;


#[pyclass]
pub struct Map {
    pub map: MapRef,
}

impl Map {
    pub fn from(map: MapRef) -> Self {
        Map { map }
    }
}

#[pymethods]
impl Map {
    fn len(&self, txn: &mut Transaction)  -> PyResult<u32> {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();
        let len = self.map.len(t);
        Ok(len)
    }

    fn insert(&self, txn: &mut Transaction, key: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
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
        let mut t = _t.as_mut().unwrap().as_mut();
        let integrated = self.map.insert(&mut t, key, TextPrelim::new(""));
        let shared = Text::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_array_prelim(&self, txn: &mut Transaction, key: &str) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        let integrated = self.map.insert(&mut t, key, ArrayPrelim::default());
        let shared = Array::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_map_prelim(&self, txn: &mut Transaction, key: &str) -> PyResult<PyObject> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        let integrated = self.map.insert(&mut t, key, MapPrelim::default());
        let shared = Map::from(integrated);
        Python::with_gil(|py| { Ok(shared.into_py(py)) })
    }

    fn insert_doc(&self, txn: &mut Transaction, key: &str, doc: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        let d1: Doc = doc.extract().unwrap();
        let d2: _Doc = d1.doc;
        let doc_ref = self.map.insert(&mut t, key, d2);
        doc_ref.load(t);
        Ok(())
    }

    fn remove(&self, txn: &mut Transaction, key: &str) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        self.map.remove(&mut t, key);
        Ok(())
    }

    fn get(&self, txn: &mut Transaction, key: &str) -> PyResult<PyObject> {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();
        let v = self.map.get(t, key);
        if v == None {
            Err(PyValueError::new_err("Key error"))
        } else {
            Python::with_gil(|py| { Ok(v.unwrap().into_py(py)) })
        }
    }

    fn keys(&self, txn: &mut Transaction) -> PyObject {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();
        let it = self.map.keys(t);
        let mut v: Vec<String> = Vec::new();
        for k in it {
            v.push(k.into());
        }
        Python::with_gil(|py| { PyList::new_bound(py, v).into() })
    }

    fn to_json(&mut self, txn: &mut Transaction) -> PyObject {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();
        let mut s = String::new();
        self.map.to_json(t).to_json(&mut s);
        Python::with_gil(|py| PyString::new_bound(py, s.as_str()).into())
    }

    pub fn observe(&mut self, py: Python<'_>, f: PyObject) -> PyResult<Py<Subscription>> {
        let sub = self.map
            .observe(move |txn, e| {
                Python::with_gil(|py| {
                    let e = MapEvent::new(e, txn);
                    if let Err(err) = f.call1(py, (e,)) {
                        err.restore(py)
                    }
                })
            });
        let s: Py<Subscription> = Py::new(py, Subscription::from(sub))?;
        Ok(s)
    }

    pub fn observe_deep(&mut self, py: Python<'_>, f: PyObject) -> PyResult<Py<Subscription>> {
        let sub = self.map
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
pub struct MapEvent {
    event: *const _MapEvent,
    txn: *const TransactionMut<'static>,
    target: Option<PyObject>,
    keys: Option<PyObject>,
    path: Option<PyObject>,
    transaction: Option<PyObject>,
}

impl MapEvent {
    pub fn new(event: &_MapEvent, txn: &TransactionMut) -> Self {
        let event = event as *const _MapEvent;
        let txn = unsafe { std::mem::transmute::<&TransactionMut, &TransactionMut<'static>>(txn) };
        let mut map_event = MapEvent {
            event,
            txn,
            target: None,
            keys: None,
            path: None,
            transaction: None,
        };
        Python::with_gil(|py| {
            map_event.target(py);
            map_event.path(py);
            map_event.keys(py);
        });
        map_event
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
            let target: PyObject = Map::from(self.event().target().clone()).into_py(py);
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
    pub fn keys(&mut self, py: Python<'_>) -> PyObject {
        if let Some(keys) = &self.keys {
            keys.clone_ref(py)
        } else {
            let keys: PyObject = {
                let keys = self.event().keys(self.txn());
                let result = PyDict::new_bound(py);
                for (key, value) in keys.iter() {
                    let key = &**key;
                    let value = EntryChangeWrapper(value);
                    result.set_item(key, value.into_py(py)).unwrap();
                }
                result.into()
            };
            let res = keys.clone_ref(py);
            self.keys = Some(keys);
            res
        }
    }

    fn __repr__(&mut self, py: Python<'_>) -> String {
        let target = self.target(py);
        let keys = self.keys(py);
        let path = self.path(py);
        format!("MapEvent(target={target}, keys={keys}, path={path})")
    }
}
