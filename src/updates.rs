use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyList};
use yrs::{diff_updates_v1, encode_state_vector_from_update_v1, merge_updates_v1};

#[pyclass]
pub struct Update {}

#[pymethods]
impl Update {
    #[staticmethod]
    fn merge_update(updates: &Bound<'_, PyList>) -> PyResult<PyObject> {
        let updates: Vec<Vec<u8>> = updates.extract().unwrap();

        let Ok(update) = merge_updates_v1(&updates) else {
            return Err(PyValueError::new_err("Cannot merge updates"));
        };
        let bytes: PyObject = Python::with_gil(|py| PyBytes::new_bound(py, &update).into());

        Ok(bytes)
    }

    #[staticmethod]
    fn encode_state_vector_from_update(update: &Bound<'_, PyBytes>) -> PyResult<PyObject> {
        let update: &[u8] = update.extract()?;
        let Ok(u) = encode_state_vector_from_update_v1(&update) else {
            return Err(PyValueError::new_err(
                "Cannot encode state vector from update",
            ));
        };
        let bytes: PyObject = Python::with_gil(|py| PyBytes::new_bound(py, &u).into());
        Ok(bytes)
    }

    #[staticmethod]
    fn diff_update(update: &Bound<'_, PyBytes>, state_vector: &Bound<'_, PyBytes>) -> PyResult<PyObject> {
        let update: &[u8] = update.extract()?;
        let state_vector: &[u8] = state_vector.extract()?;
        let Ok(u) = diff_updates_v1(&update, &state_vector) else {
            return Err(PyValueError::new_err("Cannot diff updates"));
        };

        let bytes: PyObject = Python::with_gil(|py| PyBytes::new_bound(py, &u).into());
        Ok(bytes)
    }
}
