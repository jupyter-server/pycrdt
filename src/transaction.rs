use pyo3::prelude::*;
use std::cell::{RefCell, RefMut};
use yrs::TransactionMut;

pub enum Cell<'a, T> {
    Owned(T),
    Borrowed(&'a T),
}

impl<'a, T> AsRef<T> for Cell<'a, T> {
    fn as_ref(&self) -> &T {
        match self {
            Cell::Owned(v) => v,
            Cell::Borrowed(v) => *v,
        }
    }
}

impl<'a, T> AsMut<T> for Cell<'a, T> {
    fn as_mut(&mut self) -> &mut T {
        match self {
            Cell::Owned(v) => v,
            Cell::Borrowed(_) => {
                panic!("Transactions executed in context of observer callbacks cannot be used to modify document structure")
            }
        }
    }
}

#[pyclass(unsendable)]
pub struct Transaction(RefCell<Option<Cell<'static, TransactionMut<'static>>>>);

impl<'doc> From<TransactionMut<'doc>> for Transaction {
    fn from(txn: TransactionMut<'doc>) -> Self {
        let t: TransactionMut<'static> = unsafe { std::mem::transmute(txn) };
        Transaction(RefCell::from(Some(Cell::Owned(t))))
    }
}

impl<'doc> From<&TransactionMut<'doc>> for Transaction {
    fn from(txn: &TransactionMut<'doc>) -> Self {
        let t: &TransactionMut<'static> = unsafe { std::mem::transmute(txn) };
        Transaction(RefCell::from(Some(Cell::Borrowed(t))))
    }
}

impl Transaction {
    pub fn transaction(&self) -> RefMut<'_, Option<Cell<'static, TransactionMut<'static>>>> {
        self.0.borrow_mut()
    }
}

#[pymethods]
impl Transaction {
    pub fn commit(&mut self) {
        self.transaction().as_mut().unwrap().as_mut().commit();
    }

    pub fn drop(&self) {
        self.0.replace(None);
    }
}
