use pyo3::prelude::*;
use std::cell::RefCell;
use yrs::Subscription as _Subscription;

#[pyclass(unsendable)]
pub struct Subscription(RefCell<Option<_Subscription>>);

impl From<_Subscription> for Subscription {
    fn from(sub: _Subscription) -> Self {
        let s: _Subscription = unsafe { std::mem::transmute(sub) };
        Subscription(RefCell::from(Some(s)))
    }
}

#[pymethods]
impl Subscription {
    pub fn drop(&self) {
        self.0.replace(None);
    }
}
