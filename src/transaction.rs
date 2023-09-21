use pyo3::prelude::*;
use std::cell::{RefCell, RefMut};
use yrs::TransactionMut;

#[pyclass(unsendable)]
pub struct Transaction(RefCell<Option<TransactionMut<'static>>>);

impl<'doc> From<TransactionMut<'doc>> for Transaction {
    fn from(txn: TransactionMut<'doc>) -> Self {
        let t: TransactionMut<'static> = unsafe { std::mem::transmute(txn) };
        Transaction(RefCell::from(Some(t)))
    }
}

impl Transaction {
    pub fn transaction(&self) -> RefMut<'_, Option<TransactionMut<'static>>> {
        self.0.borrow_mut()
    }
}

#[pymethods]
impl Transaction {
    pub fn commit(&mut self) {
        self.transaction().as_mut().unwrap().commit();
    }

    pub fn drop(&self) {
        self.0.replace(None);
    }
}
