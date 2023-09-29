use lib0::any::Any;
use pyo3::prelude::*;
use pyo3::types as pytypes;
use yrs::types::{Attrs, Delta, Path, PathSegment, Value};
use std::ops::Deref;
use std::collections::VecDeque;
use crate::text::Text;

pub trait ToPython {
    fn into_py(self, py: Python) -> PyObject;
}

impl<T: ToPython> ToPython for Vec<T> {
    fn into_py(self, py: Python) -> PyObject {
        let elements = self.into_iter().map(|v| v.into_py(py));
        let arr: PyObject = pytypes::PyList::new(py, elements).into();
        return arr;
    }
}

impl<T: ToPython> ToPython for VecDeque<T> {
    fn into_py(self, py: Python) -> PyObject {
        let elements = self.into_iter().map(|v| v.into_py(py));
        let arr: PyObject = pytypes::PyList::new(py, elements).into();
        return arr;
    }
}

impl ToPython for Path {
    fn into_py(self, py: Python) -> PyObject {
        let result = pytypes::PyList::empty(py);
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
        let result = pytypes::PyDict::new(py);
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

impl ToPython for Value {
    fn into_py(self, py: Python) -> pyo3::PyObject {
        match self {
            Value::Any(v) => v.into_py(py),
            Value::YText(v) => Text::from_text(v).into_py(py),
            _ => pyo3::IntoPy::into_py(0, py),
            //Value::YArray(v) => YArray::from(v).into_py(py),
            //Value::YMap(v) => YMap::from(v).into_py(py),
            //Value::YXmlElement(v) => YXmlElement::from(v).into_py(py),
            //Value::YXmlText(v) => YXmlText::from(v).into_py(py),
        }
    }
}

fn attrs_into_py(attrs: &Attrs) -> PyObject {
    Python::with_gil(|py| {
        let o = pytypes::PyDict::new(py);
        for (key, value) in attrs.iter() {
            let key = key.as_ref();
            let value = Value::Any(value.clone()).into_py(py);
            o.set_item(key, value).unwrap();
        }
        o.into()
    })
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
                let byte_array = pytypes::PyByteArray::new(py, v.as_ref());
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
            _ => pyo3::IntoPy::into_py(0, py),
            //Any::Map(v) => {
            //    let mut m = HashMap::new();
            //    for (k, v) in v.iter() {
            //        let value = v.to_owned();
            //        m.insert(k, value);
            //    }
            //    m.into_py(py)
            //}
        }
    }
}
