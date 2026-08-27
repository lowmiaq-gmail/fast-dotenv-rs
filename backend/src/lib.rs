use pyo3::prelude::*;

type BindingRecord = (Option<String>, Option<String>, String, usize, bool);

pub const BACKEND_CONTRACT: &str = "fast-dotenv-rs.backend.binding";
pub const BACKEND_CONTRACT_VERSION: u32 = 1;

/// Return only the lossless records needed by an upstream Binding adapter.
///
/// The tuple order is `(key, value, original.string, original.line, error)`.
#[pyfunction]
fn parse_bindings(text: &str) -> Vec<BindingRecord> {
    fast_dotenv_core::parse_bindings(text)
        .into_iter()
        .map(|binding| {
            (
                binding.key,
                binding.value,
                binding.original.string,
                binding.original.line,
                binding.error,
            )
        })
        .collect()
}

#[pymodule]
fn _core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("BACKEND_CONTRACT", BACKEND_CONTRACT)?;
    module.add("BACKEND_CONTRACT_VERSION", BACKEND_CONTRACT_VERSION)?;
    module.add_function(wrap_pyfunction!(parse_bindings, module)?)?;
    Ok(())
}
