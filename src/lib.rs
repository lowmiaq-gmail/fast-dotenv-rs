mod parser;

use std::collections::HashMap;

use pyo3::prelude::*;

type BindingRecord = (Option<String>, Option<String>, String, usize, bool);
type VariableAtomRecord = (String, String, Option<String>);
type ResolvedRecord = (Vec<(String, Option<String>)>, Vec<usize>);

#[pyfunction]
fn parse_text(
    text: &str,
    interpolate: bool,
    environment: HashMap<String, String>,
) -> Vec<(String, Option<String>)> {
    parser::parse_and_resolve(text, interpolate, &environment)
}

/// Resolve a complete text input in one Python/Rust boundary crossing. The
/// result is `(ordered_pairs, invalid_binding_start_lines)`.
#[pyfunction]
fn parse_resolved(
    text: &str,
    interpolate: bool,
    override_environment: bool,
    environment: HashMap<String, String>,
) -> ResolvedRecord {
    parser::parse_and_resolve_with_options(text, interpolate, override_environment, &environment)
}

/// Return the lossless parser records used by the Python compatibility layer.
/// The tuple order mirrors `Binding(key, value, original.string,
/// original.line, error)` and is intentionally a low-level/test-facing API.
#[pyfunction]
fn parse_bindings(text: &str) -> Vec<BindingRecord> {
    parser::parse_bindings(text)
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

/// Return Rust-tokenized variable atoms. Records are
/// `(kind, value_or_name, default)`, where `kind` is `literal` or `variable`.
/// This is consumed by the Python compatibility wrapper in `dotenv.variables`.
#[pyfunction]
fn parse_variable_atoms(text: &str) -> Vec<VariableAtomRecord> {
    parser::parse_variables(text)
        .into_iter()
        .map(|atom| match atom {
            parser::VariableAtom::Literal(value) => ("literal".into(), value, None),
            parser::VariableAtom::Variable { name, default } => ("variable".into(), name, default),
        })
        .collect()
}

#[pymodule]
fn _core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(parse_text, module)?)?;
    module.add_function(wrap_pyfunction!(parse_resolved, module)?)?;
    module.add_function(wrap_pyfunction!(parse_bindings, module)?)?;
    module.add_function(wrap_pyfunction!(parse_variable_atoms, module)?)?;
    Ok(())
}
