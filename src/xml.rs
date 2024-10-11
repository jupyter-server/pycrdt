
use pyo3::types::{PyAnyMethods, PyDict, PyIterator, PyList, PyString, PyTuple};
use pyo3::{pyclass, pymethods, Bound, IntoPy as _, PyObject, PyResult, Python};
use yrs::types::text::YChange;
use yrs::types::xml::{XmlEvent as _XmlEvent, XmlTextEvent as _XmlTextEvent};
use yrs::{
    DeepObservable, GetString as _, Observable as _, Text as _, TransactionMut, Xml as _, XmlElementPrelim, XmlElementRef, XmlFragment as _, XmlFragmentRef, XmlOut, XmlTextPrelim, XmlTextRef
};

use crate::subscription::Subscription;
use crate::type_conversions::{events_into_py, py_to_attrs, EntryChangeWrapper};
use crate::{transaction::Transaction, type_conversions::ToPython};

/// Implements methods common to `XmlFragment`, `XmlElement`, and `XmlText`.
macro_rules! impl_xml_methods {
    (
        $typ:ident[
            $inner:ident
            // For `XmlFragment` and `XmlElement`, implements methods from `yrs::types::xml::XmlFragment`
            $(, fragment: $finner:ident)?
            // For `XmlElement` and `XmlText`, implements methods from `yrs::types::xml::Xml`
            $(, xml: $xinner:ident)?
        ] {
            // Methods specific to the type
            $($extra:tt)*
        }
    ) => {
        #[pymethods]
        impl $typ {
            fn parent(&self, py: Python<'_>) -> PyObject {
                self.$inner.parent().into_py(py)
            }

            fn get_string(&self, txn: &mut Transaction) -> String {
                let mut t0 = txn.transaction();
                let t1 = t0.as_mut().unwrap();
                let t = t1.as_ref();
                self.$inner.get_string(t)
            }

            fn len(&self, txn: &mut Transaction)  -> u32 {
                let mut t0 = txn.transaction();
                let t1 = t0.as_mut().unwrap();
                let t = t1.as_ref();
                self.$inner.len(t)
            }

            $(
                fn get(&self, py: Python<'_>, txn: &mut Transaction, index: u32) -> PyObject {
                    let mut t0 = txn.transaction();
                    let t1 = t0.as_mut().unwrap();
                    let t = t1.as_ref();
                    self.$finner.get(t, index).into_py(py)
                }

                fn remove_range(&self, txn: &mut Transaction, index: u32, len: u32) {
                    let mut _t = txn.transaction();
                    let mut t = _t.as_mut().unwrap().as_mut();
                    self.$finner.remove_range(&mut t, index, len);
                }

                fn insert_str(&self, txn: &mut Transaction, index: u32, text: &str) -> XmlText {
                    let mut _t = txn.transaction();
                    let mut t = _t.as_mut().unwrap().as_mut();
                    self.$finner.insert(&mut t, index, XmlTextPrelim::new(text)).into()
                }

                fn insert_element_prelim(&self, txn: &mut Transaction, index: u32, tag: &str) -> XmlElement {
                    let mut _t = txn.transaction();
                    let mut t = _t.as_mut().unwrap().as_mut();
                    self.$finner.insert(&mut t, index, XmlElementPrelim::empty(tag)).into()
                }
            )?

            $(
                fn attributes(&self, txn: &mut Transaction) -> Vec<(String, String)> {
                    let mut t0 = txn.transaction();
                    let t1 = t0.as_mut().unwrap();
                    let t = t1.as_ref();
                    self.$xinner.attributes(t).map(|(k,v)| (String::from(k), v)).collect()
                }

                fn attribute(&self, txn: &mut Transaction, name: &str) -> Option<String> {
                    let mut t0 = txn.transaction();
                    let t1 = t0.as_mut().unwrap();
                    let t = t1.as_ref();
                    self.$xinner.get_attribute(t, name)
                }
            
                fn insert_attribute(&self, txn: &mut Transaction, name: &str, value: &str) {
                    let mut _t = txn.transaction();
                    let mut t = _t.as_mut().unwrap().as_mut();
                    self.$xinner.insert_attribute(&mut t, name, value);
                }

                fn remove_attribute(&self, txn: &mut Transaction, name: &str) {
                    let mut _t = txn.transaction();
                    let mut t = _t.as_mut().unwrap().as_mut();
                    self.$xinner.remove_attribute(&mut t, &name);
                }

                fn siblings(&self, py: Python<'_>, txn: &mut Transaction) -> Vec<PyObject> {
                    let mut t0 = txn.transaction();
                    let t1 = t0.as_mut().unwrap();
                    let t = t1.as_ref();
                    self.$xinner.siblings(t).map(|node| node.into_py(py)).collect()
                }
            )?

            $($extra)*
        }

        impl std::hash::Hash for $typ {
            fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
                let branch: &yrs::branch::Branch = self.$inner.as_ref();
                branch.id().hash(state)
            }
        }
    };
}

#[pyclass(eq, frozen, hash)]
#[derive(PartialEq, Eq)]
pub struct XmlFragment {
    pub fragment: XmlFragmentRef,
}

impl From<XmlFragmentRef> for XmlFragment {
    fn from(value: XmlFragmentRef) -> Self {
        XmlFragment { fragment: value }
    }
}

impl_xml_methods!(XmlFragment[fragment, fragment: fragment] {
    fn observe(&self, f: PyObject) -> Subscription {
        self.fragment.observe(move |txn, e| {
            Python::with_gil(|py| {
                let e = unsafe { XmlEvent::from_xml_event(e, txn, py) };
                if let Err(err) = f.call1(py, (e,)) {
                    err.restore(py)
                }
            });
        }).into()
    }

    fn observe_deep(&self, f: PyObject) -> Subscription {
        self.fragment.observe_deep(move |txn, events| {
            Python::with_gil(|py| {
                let events = events_into_py(txn, events);
                if let Err(err) = f.call1(py, (events,)) {
                    err.restore(py);
                }
            })
        }).into()
    }
});

#[pyclass(eq, frozen, hash)]
#[derive(PartialEq, Eq)]
pub struct XmlElement {
    pub element: XmlElementRef,
}

impl From<XmlElementRef> for XmlElement {
    fn from(value: XmlElementRef) -> Self {
        XmlElement { element: value }
    }
}

impl_xml_methods!(XmlElement[element, fragment: element, xml: element] {
    fn tag(&self) -> Option<String> {
        self.element.try_tag().map(|s| String::from(&**s))
    }

    fn observe(&self, f: PyObject) -> Subscription {
        self.element.observe(move |txn, e| {
            Python::with_gil(|py| {
                let e = unsafe { XmlEvent::from_xml_event(e, txn, py) };
                if let Err(err) = f.call1(py, (e,)) {
                    err.restore(py)
                }
            });
        }).into()
    }

    fn observe_deep(&self, f: PyObject) -> Subscription {
        self.element.observe_deep(move |txn, events| {
            Python::with_gil(|py| {
                let events = events_into_py(txn, events);
                if let Err(err) = f.call1(py, (events,)) {
                    err.restore(py);
                }
            })
        }).into()
    }
});

#[pyclass(eq, frozen, hash)]
#[derive(PartialEq, Eq)]
pub struct XmlText {
    pub text: XmlTextRef,
}

impl From<XmlTextRef> for XmlText {
    fn from(value: XmlTextRef) -> Self {
        XmlText { text: value }
    }
}

impl_xml_methods!(XmlText[text, xml: text] {
    #[pyo3(signature = (txn, index, text, attrs=None))]
    fn insert(&self, txn: &mut Transaction, index: u32, text: &str, attrs: Option<Bound<'_, PyIterator>>) -> PyResult<()> {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        if let Some(attrs) = attrs {
            let attrs = py_to_attrs(attrs)?;
            self.text.insert_with_attributes(&mut t, index, text, attrs);
        } else {
            self.text.insert(&mut t, index, text);
        }
        Ok(())
    }

    fn remove_range(&self, txn: &mut Transaction, index: u32, len: u32) {
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        self.text.remove_range(&mut t, index, len);
    }

    fn format(&self, txn: &mut Transaction, index: u32, len: u32, attrs: Bound<'_, PyIterator>) -> PyResult<()> {
        let attrs = py_to_attrs(attrs)?;
        let mut _t = txn.transaction();
        let mut t = _t.as_mut().unwrap().as_mut();
        self.text.format(&mut t, index, len, attrs);
        Ok(())
    }

    fn diff<'py>(&self, py: Python<'py>, txn: &mut Transaction) -> Bound<'py, PyList> {
        let mut t0 = txn.transaction();
        let t1 = t0.as_mut().unwrap();
        let t = t1.as_ref();

        let iter = self.text.diff(t, YChange::identity)
            .into_iter()
            .map(|diff| {
                let attrs = diff.attributes.map(|attrs| {
                    let pyattrs = PyDict::new_bound(py);
                    for (name, value) in attrs.into_iter() {
                        pyattrs.set_item(
                            PyString::intern_bound(py, &*name),
                            value.into_py(py),
                        ).unwrap();
                    }
                    pyattrs.into_any().unbind()
                }).unwrap_or_else(|| py.None());

                PyTuple::new_bound(py, [
                    diff.insert.into_py(py),
                    attrs,
                ])
            });

        PyList::new_bound(
            py,
            iter
        )
    }

    fn observe(&self, f: PyObject) -> Subscription {
        self.text.observe(move |txn, e| {
            Python::with_gil(|py| {
                let e = unsafe { XmlEvent::from_xml_text_event(e, txn, py) };
                if let Err(err) = f.call1(py, (e,)) {
                    err.restore(py)
                }
            });
        }).into()
    }

    fn observe_deep(&self, f: PyObject) -> Subscription {
        self.observe(f)
    }
});



#[pyclass(unsendable)]
pub struct XmlEvent {
    txn: *const TransactionMut<'static>,
    transaction: Option<PyObject>,
    #[pyo3(get)]
    children_changed: PyObject,
    #[pyo3(get)]
    target: PyObject,
    #[pyo3(get)]
    path: PyObject,
    #[pyo3(get)]
    delta: PyObject,
    #[pyo3(get)]
    keys: PyObject,
}

impl XmlEvent {
    pub unsafe fn from_xml_event(event: &_XmlEvent, txn: &TransactionMut, py: Python<'_>) -> Self {
        Self {
            txn: unsafe { std::mem::transmute::<&TransactionMut, &TransactionMut<'static>>(txn) },
            transaction: None,
            children_changed: event.children_changed().into_py(py),
            target: event.target().clone().into_py(py),
            path: event.path().clone().into_py(py),
            delta: PyList::new_bound(
                py,
                event.delta(txn).into_iter().map(|d| d.into_py(py)),
            )
            .into(),
            keys: {
                let dict = PyDict::new_bound(py);
                for (key, value) in event.keys(txn).iter() {
                    dict.set_item(&**key, EntryChangeWrapper(value).into_py(py))
                        .unwrap();
                }
                dict.into()
            },
        }
    }

    pub unsafe fn from_xml_text_event(event: &_XmlTextEvent, txn: &TransactionMut, py: Python<'_>) -> Self {
        Self {
            txn: unsafe { std::mem::transmute::<&TransactionMut, &TransactionMut<'static>>(txn) },
            transaction: None,
            target: XmlOut::Text(event.target().clone()).into_py(py),
            path: event.path().clone().into_py(py),
            delta: PyList::new_bound(
                py,
                event.delta(txn).into_iter().map(|d| d.clone().into_py(py)),
            )
            .into(),
            keys: {
                let dict = PyDict::new_bound(py);
                for (key, value) in event.keys(txn).iter() {
                    dict.set_item(&**key, EntryChangeWrapper(value).into_py(py))
                        .unwrap();
                }
                dict.into()
            },
            children_changed: py.None(),
        }
    }
}

#[pymethods]
impl XmlEvent {
    #[getter]
    fn transaction(&mut self, py: Python<'_>) -> PyObject {
        self.transaction
            .get_or_insert_with(|| Transaction::from(unsafe { &*self.txn }).into_py(py))
            .clone_ref(py)
    }

    fn __repr__(&mut self) -> String {
        format!(
            "XmlEvent(children_changed={}, target={}, path={}, delta={}, keys={})",
            self.children_changed, self.target, self.path, self.delta, self.keys,
        )
    }
}
