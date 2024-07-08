use pyo3::prelude::*;
use pyo3::types::{IntoPyDict, PyAny, PyBool, PyByteArray, PyDict, PyFloat, PyList, PyLong, PyString, PyBytes};
use yrs::types::{Attrs, Change, EntryChange, Delta, Events, Path, PathSegment};
use yrs::{Any, Out, TransactionMut};
use std::ops::Deref;
use std::collections::{VecDeque, HashMap};
use crate::text::{Text, TextEvent};
use crate::array::{Array, ArrayEvent};
use crate::map::{Map, MapEvent};
use crate::doc::Doc;
use crate::undo::StackItem;

pub trait ToPython {
    fn into_py(self, py: Python) -> PyObject;
}

impl<T: ToPython> ToPython for Vec<T> {
    fn into_py(self, py: Python) -> PyObject {
        let elements = self.into_iter().map(|v| v.into_py(py));
        let arr: PyObject = PyList::new_bound(py, elements).into();
        return arr;
    }
}

impl<T: ToPython> ToPython for VecDeque<T> {
    fn into_py(self, py: Python) -> PyObject {
        let elements = self.into_iter().map(|v| v.into_py(py));
        let arr: PyObject = PyList::new_bound(py, elements).into();
        return arr;
    }
}

impl ToPyObject for StackItem {
    fn to_object(&self, py: Python) -> PyObject {
        let obj: PyObject = Py::new(py, self.clone()).unwrap().into_py(py);
        obj
    }
}

//impl<K, V> ToPython for HashMap<K, V>
//where
//    K: ToPyObject,
//    V: ToPython,
//{
//    fn into_py(self, py: Python) -> PyObject {
//        let py_dict = PyDict::new_bound(py);
//        for (k, v) in self.into_iter() {
//            py_dict.set_item(k, v.into_py(py)).unwrap();
//        }
//        py_dict.into_py(py)
//    }
//}

impl ToPython for Path {
    fn into_py(self, py: Python) -> PyObject {
        let result = PyList::empty_bound(py);
        for segment in self {
            match segment {
                PathSegment::Key(key) => {
                    result.append(key.as_ref()).unwrap();
                }
                PathSegment::Index(idx) => {
                    result.append(idx).unwrap();
                }
            }
        }
        result.into()
    }
}

impl ToPython for Delta {
    fn into_py(self, py: Python) -> PyObject {
        let result = PyDict::new_bound(py);
        match self {
            Delta::Inserted(value, attrs) => {
                let value = value.clone().into_py(py);
                result.set_item("insert", value).unwrap();

                if let Some(attrs) = attrs {
                    let attrs = attrs_into_py(attrs.deref());
                    result.set_item("attributes", attrs).unwrap();
                }
            }
            Delta::Retain(len, attrs) => {
                result.set_item("retain", len).unwrap();

                if let Some(attrs) = attrs {
                    let attrs = attrs_into_py(attrs.deref());
                    result.set_item("attributes", attrs).unwrap();
                }
            }
            Delta::Deleted(len) => {
                result.set_item("delete", len).unwrap();
            }
        }
        result.into()
    }
}

impl ToPython for Out{
    fn into_py(self, py: Python) -> pyo3::PyObject {
        match self {
            Out::Any(v) => v.into_py(py),
            Out::YText(v) => Text::from(v).into_py(py),
            Out::YArray(v) => Array::from(v).into_py(py),
            Out::YMap(v) => Map::from(v).into_py(py),
            Out::YDoc(v) => Doc::from(v).into_py(py),
            _ => pyo3::IntoPy::into_py(py.None(), py),
            //Out::YXmlElement(v) => YXmlElement::from(v).into_py(py),
            //Out::YXmlText(v) => YXmlText::from(v).into_py(py),
        }
    }
}

fn attrs_into_py(attrs: &Attrs) -> PyObject {
    Python::with_gil(|py| {
        let o = PyDict::new_bound(py);
        for (key, value) in attrs.iter() {
            let key = key.as_ref();
            let value = Out::Any(value.clone()).into_py(py);
            o.set_item(key, value).unwrap();
        }
        o.into()
    })
}

impl ToPython for &Change {
    fn into_py(self, py: Python) -> PyObject {
        let result = PyDict::new_bound(py);
        match self {
            Change::Added(values) => {
                let values: Vec<PyObject> =
                    values.into_iter().map(|v| v.clone().into_py(py)).collect();
                result.set_item("insert", values).unwrap();
            }
            Change::Removed(len) => {
                result.set_item("delete", len).unwrap();
            }
            Change::Retain(len) => {
                result.set_item("retain", len).unwrap();
            }
        }
        result.into()
    }
}

#[repr(transparent)]
pub struct EntryChangeWrapper<'a>(pub &'a EntryChange);

impl<'a> IntoPy<PyObject> for EntryChangeWrapper<'a> {
    fn into_py(self, py: Python) -> PyObject {
        let result = PyDict::new_bound(py);
        let action = "action";
        match self.0 {
            EntryChange::Inserted(new) => {
                let new_value = new.clone().into_py(py);
                result.set_item(action, "add").unwrap();
                result.set_item("newValue", new_value).unwrap();
            }
            EntryChange::Updated(old, new) => {
                let old_value = old.clone().into_py(py);
                let new_value = new.clone().into_py(py);
                result.set_item(action, "update").unwrap();
                result.set_item("oldValue", old_value).unwrap();
                result.set_item("newValue", new_value).unwrap();
            }
            EntryChange::Removed(old) => {
                let old_value = old.clone().into_py(py);
                result.set_item(action, "delete").unwrap();
                result.set_item("oldValue", old_value).unwrap();
            }
        }
        result.into()
    }
}

impl ToPython for Any {
    fn into_py(self, py: Python) -> pyo3::PyObject {
        match self {
            Any::Null | Any::Undefined => py.None(),
            Any::Bool(v) => v.into_py(py),
            Any::Number(v) => v.into_py(py),
            Any::BigInt(v) => v.into_py(py),
            Any::String(v) => v.into_py(py),
            Any::Buffer(v) => {
                let byte_array = PyByteArray::new_bound(py, v.as_ref());
                byte_array.into()
            }
            Any::Array(v) => {
                let mut a = Vec::new();
                for value in v.iter() {
                    let value = value.to_owned();
                    a.push(value);
                }
                a.into_py(py)
            }
            Any::Map(v) => {
                let mut a = Vec::<(&str, PyObject)>::new();
                for (k, v) in v.iter() {
                    let value = v.to_owned();
                    a.push((k, value.into_py(py)));
                }
                a.into_py_dict_bound(py).into()
            }
        }
    }
}

pub fn py_to_any(value: &Bound<'_, PyAny>) -> Any {
    if value.is_none() {
        Any::Null
    } else if value.is_instance_of::<PyBytes>() {
        let v: &[u8] = value.extract().unwrap();
        Any::Buffer(v.into())
    } else if value.is_instance_of::<PyString>() {
        let v: &str = value.extract().unwrap();
        Any::String(v.into())
    } else if value.is_instance_of::<PyBool>() {
        let v: bool = value.extract().unwrap();
        Any::Bool(v)
    } else if value.is_instance_of::<PyLong>() {
        const MAX_JS_NUMBER: i64 = 2_i64.pow(53) - 1;
        let v: i64 = value.extract().unwrap();
        if v > MAX_JS_NUMBER {
            Any::BigInt(v)
        } else {
            Any::Number(v as f64)
        }
    } else if value.is_instance_of::<PyFloat>() {
        let v: f64 = value.extract().unwrap();
        Any::Number(v)
    } else if let Ok(v) = value.downcast::<PyList>() {
        let mut items = Vec::new();
        for i in v.iter() {
            let a = py_to_any(&i);
            items.push(a);
        }
        Any::Array(items.into())
    } else if let Ok(val) = value.downcast::<PyDict>() {
        let mut items: HashMap<String, Any> = HashMap::new();
        for (k, v) in val.iter() {
            let k = k.downcast::<PyString>().unwrap().to_str().unwrap().to_string();
            let v = py_to_any(&v);
            items.insert(k, v);
        }
        Any::Map(items.into())
    } else {
        Any::Undefined
    }
}

pub(crate) fn events_into_py(txn: &TransactionMut, events: &Events) -> PyObject {
    Python::with_gil(|py| {
        let py_events = events.iter().map(|event| match event {
            yrs::types::Event::Text(e_txt) => TextEvent::new(e_txt, txn).into_py(py),
            yrs::types::Event::Array(e_arr) => ArrayEvent::new(e_arr, txn).into_py(py),
            yrs::types::Event::Map(e_map) => MapEvent::new(e_map, txn).into_py(py),
            //yrs::types::Event::XmlElement(e_xml) => YXmlEvent::new(e_xml, txn).into_py(py),
            //yrs::types::Event::XmlText(e_xml) => YXmlTextEvent::new(e_xml, txn).into_py(py),
            _ => py.None(),
        });
        PyList::new_bound(py, py_events).into()
    })
}
