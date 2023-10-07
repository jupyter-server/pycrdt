use pyo3::prelude::*;
use pyo3::types::{PyList, PyString};
use yrs::{
    GetString,
    Observable,
    TextRef,
    Text as _Text,
    TransactionMut,
};
use yrs::types::text::TextEvent as _TextEvent;
use crate::transaction::Transaction;
use crate::type_conversions::ToPython;


#[pyclass(unsendable)]
pub struct Text {
    text: TextRef,
}

impl Text {
    pub fn from(text: TextRef) -> Self {
        Text {
            text,
        }
    }
}

#[pymethods]
impl Text {
    fn len(&self, txn: &mut Transaction)  -> PyResult<u32> {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let len = self.text.len(t);
        Ok(len)
    }

    fn insert(&self, txn: &mut Transaction, index: u32, chunk: &str) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        self.text.insert(&mut t, index, chunk);
        Ok(())
    }

    fn remove_range(&self, txn: &mut Transaction, index: u32, len: u32) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap();
        self.text.remove_range(&mut t, index, len);
        Ok(())
    }

    fn get_string(&mut self, txn: &mut Transaction) -> PyObject {
        let mut _t = txn.transaction();
        let t = _t.as_mut().unwrap();
        let s = self.text.get_string(t);
        Python::with_gil(|py| PyString::new(py, &s).into())
    }

    fn observe(&mut self, f: PyObject) -> PyResult<u32> {
        let id: u32 = self.text.observe(move |txn, e| {
            Python::with_gil(|py| {
                let e = TextEvent::new(e, txn);
                if let Err(err) = f.call1(py, (e,)) {
                    err.restore(py)
                }
            });
        })
        .into();
        Ok(id)
    }

    fn unobserve(&self, subscription_id: u32) -> PyResult<()> {
        self.text.unobserve(subscription_id);
        Ok(())
    }
}

#[pyclass(unsendable)]
pub struct TextEvent {
    event: *const _TextEvent,
    txn: *const TransactionMut<'static>,
    target: Option<PyObject>,
    delta: Option<PyObject>,
    path: Option<PyObject>,
}

impl TextEvent {
    pub fn new(event: &_TextEvent, txn: &TransactionMut) -> Self {
        let event = event as *const _TextEvent;
        let txn = unsafe { std::mem::transmute::<&TransactionMut, &TransactionMut<'static>>(txn) };
        TextEvent {
            event,
            txn,
            target: None,
            delta: None,
            path: None,
        }
    }

    fn event(&self) -> &_TextEvent {
        unsafe { self.event.as_ref().unwrap() }
    }

    fn txn(&self) -> &TransactionMut {
        unsafe { self.txn.as_ref().unwrap() }
    }
}

#[pymethods]
impl TextEvent {
    #[getter]
    pub fn target(&mut self) -> PyObject {
        if let Some(target) = self.target.as_ref() {
            target.clone()
        } else {
            let target: PyObject = Python::with_gil(|py| Text::from(self.event().target().clone()).into_py(py));
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
                let delta =
                    self.event()
                        .delta(self.txn())
                        .into_iter()
                        .map(|d| d.clone().into_py(py));
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
        format!("TextEvent(target={target}, delta={delta}, path={path})")
    }
}
