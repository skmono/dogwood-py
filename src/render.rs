//! Output rendering for each command, in both human and JSON form — the
//! `dogwood-cli` `render` module, returning `String`s instead of printing.

use std::fmt::Write;

use crate::error::OpError;
use crate::ops::{
    CheckParseReport, ExplainReport, LowerArtifacts, ReplayReport, SchemaCheckReport,
    ValidateReport, Verdict,
};
use crate::{Emit, Format};

/// Serialize any report to pretty JSON (with the CLI's trailing newline).
fn json(value: &impl serde::Serialize) -> String {
    // A report is a plain owned struct of scalars/strings/vecs; serialization
    // cannot fail in practice.
    let mut s = serde_json::to_string_pretty(value).expect("report serializes");
    s.push('\n');
    s
}

/// Render a fatal error. Human mode uses miette's graphical report handler
/// (underlined snippet); JSON mode emits the serializable error.
pub fn error(err: &OpError, format: Format) -> String {
    match format {
        Format::Json => json(err),
        Format::Human => format!("{:?}", miette::Report::new(err.clone())),
    }
}

pub fn check_parse(report: &CheckParseReport, format: Format) -> String {
    if format == Format::Json {
        return json(report);
    }
    let mut out = String::new();
    let _ = writeln!(
        out,
        "OK: parsed {} polic{}.",
        report.policy_count,
        if report.policy_count == 1 { "y" } else { "ies" }
    );
    for (i, p) in report.policies.iter().enumerate() {
        let mut notes = Vec::new();
        if p.uses_temporal {
            notes.push(format!("{} temporal leaf/leaves", p.temporal_count));
        }
        if !p.provider_invocations.is_empty() {
            notes.push(format!("{} provider call(s)", p.provider_invocations.len()));
        }
        if !notes.is_empty() {
            let _ = writeln!(out, "  policy {i}: {}", notes.join(", "));
        }
        for undeclared in &p.undeclared_providers {
            let _ = writeln!(out, "  policy {i}: warning: undeclared provider `{undeclared}`");
        }
    }
    out
}

pub fn validate(report: &ValidateReport, format: Format) -> String {
    if format == Format::Json {
        return json(report);
    }
    let mut out = String::new();
    for e in &report.errors {
        let _ = writeln!(out, "error: {}", e.message);
    }
    for w in &report.warnings {
        let _ = writeln!(out, "warning: {}", w.message);
    }
    if report.passed_without_warnings {
        out.push_str("OK: validation passed with no errors or warnings.\n");
    } else if report.passed {
        let _ = writeln!(
            out,
            "OK: validation passed ({} warning(s)).",
            report.warnings.len()
        );
    } else {
        let _ = writeln!(
            out,
            "FAILED: {} error(s), {} warning(s).",
            report.errors.len(),
            report.warnings.len()
        );
    }
    out
}

/// The emitted text, plus the CLI's stderr note when the Cedar output is not
/// self-contained (the caller surfaces it as a Python warning).
pub fn lower(artifacts: &LowerArtifacts, emit: Emit, format: Format) -> (String, Option<String>) {
    if format == Format::Json {
        return (json(artifacts), None);
    }
    let out = match emit {
        Emit::CedarPolicies => artifacts.cedar_policies.clone(),
        Emit::CedarSchema => artifacts.cedar_schema.clone(),
        Emit::CedarJson => artifacts.cedar_schema_json.clone(),
        Emit::Both => format!(
            "// ─── Cedar policies ───\n{}\n// ─── Augmented schema ───\n{}",
            artifacts.cedar_policies, artifacts.cedar_schema
        ),
    };
    let note = (!artifacts.self_contained).then(|| {
        format!(
            "this Cedar is NOT self-contained — temporal/provider fields were hoisted \
             ({} temporal, {} provider) and need Dogwood at authorize time.",
            artifacts.temporal_fields.len(),
            artifacts.provider_fields.len()
        )
    });
    (out, note)
}

pub fn schema_check(report: &SchemaCheckReport, format: Format) -> String {
    if format == Format::Json {
        return json(report);
    }
    let mut out = String::new();
    for w in &report.warnings {
        let _ = writeln!(out, "warning: {w}");
    }
    if report.warnings.is_empty() {
        let _ = writeln!(out, "OK: {} schema is valid.", report.kind);
    } else {
        let _ = writeln!(
            out,
            "OK: {} schema is valid ({} warning(s)).",
            report.kind,
            report.warnings.len()
        );
    }
    out
}

pub fn replay(report: &ReplayReport, format: Format) -> String {
    if format == Format::Json {
        return json(report);
    }
    let mut out = String::new();
    for v in &report.verdicts {
        let decision = match v.verdict {
            Verdict::Allow => "ALLOW",
            Verdict::Deny => "DENY",
        };
        let _ = write!(out, "@{} (time point {}): {decision}", v.timestamp, v.index);
        if !v.determining_rules.is_empty() {
            let rules: Vec<String> = v.determining_rules.iter().map(|r| r.to_string()).collect();
            let _ = write!(out, "  [rules: {}]", rules.join(", "));
        }
        out.push('\n');
        for e in &v.errors {
            let _ = writeln!(out, "    error: {e}");
        }
    }
    out
}

/// `explain`: the informalization as indented plain text, or the structured
/// report (phrase trees with spans, plus the text) as JSON.
pub fn explain(report: &ExplainReport, format: Format) -> String {
    if format == Format::Json {
        return json(report);
    }
    format!("{}\n", report.text)
}
