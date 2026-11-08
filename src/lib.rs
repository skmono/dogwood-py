//! Python bindings for the `dogwood` CLI. Each function mirrors one CLI
//! command: file-path arguments become source strings, flags become
//! keyword-only arguments, and the text the CLI would print to stdout is
//! returned. A fatal error (CLI exit code 2) raises `DogwoodError` whose
//! message is the error rendered in the requested `format`.

use std::ffi::CString;

use pyo3::{
    create_exception,
    exceptions::{PyException, PyUserWarning, PyValueError},
    prelude::*,
};

mod error;
mod ops;
mod render;

use error::OpError;
use ops::SchemaInputs;

create_exception!(pydogwood, DogwoodError, PyException);

/// Output format shared by every command (`"human"` or `"json"`).
#[derive(Copy, Clone, PartialEq, Eq)]
enum Format {
    Human,
    Json,
}

impl Format {
    fn parse(s: &str) -> PyResult<Self> {
        match s {
            "human" => Ok(Format::Human),
            "json" => Ok(Format::Json),
            other => Err(PyValueError::new_err(format!(
                "invalid format `{other}`; expected \"human\" or \"json\""
            ))),
        }
    }
}

/// What `lower` should emit.
#[derive(Copy, Clone, PartialEq, Eq)]
enum Emit {
    CedarPolicies,
    CedarSchema,
    CedarJson,
    Both,
}

impl Emit {
    fn parse(s: &str) -> PyResult<Self> {
        match s {
            "cedar-policies" => Ok(Emit::CedarPolicies),
            "cedar-schema" => Ok(Emit::CedarSchema),
            "cedar-json" => Ok(Emit::CedarJson),
            "both" => Ok(Emit::Both),
            other => Err(PyValueError::new_err(format!(
                "invalid emit `{other}`; expected \"cedar-policies\", \"cedar-schema\", \
                 \"cedar-json\", or \"both\""
            ))),
        }
    }
}

/// Render a fatal operation error in the requested format and raise it.
fn op_err(format: Format) -> impl FnOnce(OpError) -> PyErr {
    move |error| DogwoodError::new_err(render::error(&error, format))
}

fn inputs<'a>(
    event_schema: Option<&'a str>,
    providers: Option<&'a str>,
    macros: Option<&'a str>,
) -> SchemaInputs<'a> {
    SchemaInputs {
        event_schema,
        providers,
        macros,
    }
}

/// Pretty-print a .dw policy set.
#[pyfunction(name = "format")]
fn py_format(policies: &str) -> String {
    let mut formatted = dogwood_formatter::format_policies(policies);
    if !formatted.is_empty() && !formatted.ends_with('\n') {
        formatted.push('\n');
    }
    formatted
}

/// Parse a .dw policy set; report syntax and macro errors only.
#[pyfunction]
#[pyo3(signature = (policies, *, event_schema=None, providers=None, macros=None, format="human"))]
fn check_parse(
    policies: &str,
    event_schema: Option<&str>,
    providers: Option<&str>,
    macros: Option<&str>,
    format: &str,
) -> PyResult<String> {
    let format = Format::parse(format)?;
    let report = ops::check_parse(policies, &inputs(event_schema, providers, macros))
        .map_err(op_err(format))?;
    Ok(render::check_parse(&report, format))
}

/// Parse, lower, and type-check policies against the schema. A failing
/// validation (CLI exit 2) raises `DogwoodError` carrying the rendered report.
#[pyfunction]
#[pyo3(signature = (policies, *, policy_schema, event_schema=None, providers=None, macros=None, format="human"))]
fn validate(
    policies: &str,
    policy_schema: &str,
    event_schema: Option<&str>,
    providers: Option<&str>,
    macros: Option<&str>,
    format: &str,
) -> PyResult<String> {
    let format = Format::parse(format)?;
    let report =
        ops::validate_policies(policies, &inputs(event_schema, providers, macros), policy_schema)
            .map_err(op_err(format))?;
    let out = render::validate(&report, format);
    if report.passed {
        Ok(out)
    } else {
        Err(DogwoodError::new_err(out))
    }
}

/// Lower a .dw policy set to Cedar; emit policies and the augmented schema.
/// Non-self-contained output (the CLI's stderr note) emits a `UserWarning`.
#[pyfunction]
#[pyo3(signature = (policies, *, policy_schema, event_schema=None, providers=None, macros=None, emit="both", format="human"))]
#[allow(clippy::too_many_arguments)]
fn lower(
    py: Python<'_>,
    policies: &str,
    policy_schema: &str,
    event_schema: Option<&str>,
    providers: Option<&str>,
    macros: Option<&str>,
    emit: &str,
    format: &str,
) -> PyResult<String> {
    let emit = Emit::parse(emit)?;
    let format = Format::parse(format)?;
    let artifacts =
        ops::lower_to_cedar(policies, &inputs(event_schema, providers, macros), policy_schema)
            .map_err(op_err(format))?;
    let (out, note) = render::lower(&artifacts, emit, format);
    if let Some(note) = note {
        let msg = CString::new(note).expect("note has no NUL bytes");
        PyErr::warn(py, &py.get_type::<PyUserWarning>(), &msg, 1)?;
    }
    Ok(out)
}

/// Replay a whole .log event trace; return per-timepoint verdicts.
#[pyfunction]
#[pyo3(signature = (policies, *, policy_schema, trace, event_schema=None, providers=None, macros=None, format="human"))]
fn replay(
    policies: &str,
    policy_schema: &str,
    trace: &str,
    event_schema: Option<&str>,
    providers: Option<&str>,
    macros: Option<&str>,
    format: &str,
) -> PyResult<String> {
    let format = Format::parse(format)?;
    let report = ops::replay_trace(
        policies,
        &inputs(event_schema, providers, macros),
        policy_schema,
        trace,
    )
    .map_err(op_err(format))?;
    Ok(render::replay(&report, format))
}

/// Explain a .dw policy set in deterministic semi-English, rule by rule.
#[pyfunction]
#[pyo3(signature = (policies, *, policy_schema=None, event_schema=None, providers=None, macros=None, format="human"))]
fn explain(
    policies: &str,
    policy_schema: Option<&str>,
    event_schema: Option<&str>,
    providers: Option<&str>,
    macros: Option<&str>,
    format: &str,
) -> PyResult<String> {
    let format = Format::parse(format)?;
    let report =
        ops::explain_policies(policies, &inputs(event_schema, providers, macros), policy_schema)
            .map_err(op_err(format))?;
    Ok(render::explain(&report, format))
}

/// `schema action`: check a Cedar action schema (.cedarschema).
#[pyfunction]
#[pyo3(signature = (schema, *, format="human"))]
fn schema_action(schema: &str, format: &str) -> PyResult<String> {
    let format = Format::parse(format)?;
    let report = ops::check_action_schema(schema).map_err(op_err(format))?;
    Ok(render::schema_check(&report, format))
}

/// `schema event`: check an event-schema DSL file (.dwschema).
#[pyfunction]
#[pyo3(signature = (schema, *, format="human"))]
fn schema_event(schema: &str, format: &str) -> PyResult<String> {
    let format = Format::parse(format)?;
    let report = ops::check_event_schema(schema).map_err(op_err(format))?;
    Ok(render::schema_check(&report, format))
}

/// `schema providers`: check a provider declarations file (providers.json).
#[pyfunction]
#[pyo3(signature = (providers, *, format="human"))]
fn schema_providers(providers: &str, format: &str) -> PyResult<String> {
    let format = Format::parse(format)?;
    let report = ops::check_providers(providers).map_err(op_err(format))?;
    Ok(render::schema_check(&report, format))
}

/// `schema mcp`: generate a Cedar action schema from an MCP `tools/list`
/// manifest (JSON). Returns the .cedarschema text.
#[pyfunction]
fn schema_mcp(manifest: &str) -> PyResult<String> {
    ops::generate_mcp_schema(manifest).map_err(op_err(Format::Human))
}

#[pymodule]
fn pydogwood(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("DogwoodError", m.py().get_type::<DogwoodError>())?;
    m.add_function(wrap_pyfunction!(py_format, m)?)?;
    m.add_function(wrap_pyfunction!(check_parse, m)?)?;
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    m.add_function(wrap_pyfunction!(lower, m)?)?;
    m.add_function(wrap_pyfunction!(replay, m)?)?;
    m.add_function(wrap_pyfunction!(explain, m)?)?;
    m.add_function(wrap_pyfunction!(schema_action, m)?)?;
    m.add_function(wrap_pyfunction!(schema_event, m)?)?;
    m.add_function(wrap_pyfunction!(schema_providers, m)?)?;
    m.add_function(wrap_pyfunction!(schema_mcp, m)?)?;
    Ok(())
}
