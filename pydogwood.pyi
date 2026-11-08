"""Python bindings for the Dogwood policy CLI.

Each function mirrors one ``dogwood`` command: file paths become source
strings, flags become keyword-only arguments, and the text the CLI prints to
stdout is returned.
"""

from typing import Final, Literal, Optional

__all__ = [
    "DOGWOOD_VERSION",
    "DogwoodError",
    "check_parse",
    "explain",
    "format",
    "lower",
    "replay",
    "schema_action",
    "schema_event",
    "schema_mcp",
    "schema_providers",
    "validate",
]

_Format = Literal["human", "json"]
_Emit = Literal["cedar-policies", "cedar-schema", "cedar-json", "both"]

DOGWOOD_VERSION: Final[str]
"""The Dogwood CLI version these bindings mirror, e.g. ``"1.1.0"``."""

class DogwoodError(Exception):
    """A fatal operation error (CLI exit code 2), rendered in the requested format.

    A failed ``validate`` also raises it, with the validation report as message.
    """

def format(policies: str) -> str:
    """``dogwood format``: pretty-print a ``.dw`` policy set."""

def check_parse(
    policies: str,
    *,
    event_schema: Optional[str] = None,
    providers: Optional[str] = None,
    macros: Optional[str] = None,
    format: _Format = "human",
) -> str:
    """``dogwood check-parse``: parse a policy set; report syntax and macro errors only."""

def validate(
    policies: str,
    *,
    policy_schema: str,
    event_schema: Optional[str] = None,
    providers: Optional[str] = None,
    macros: Optional[str] = None,
    format: _Format = "human",
) -> str:
    """``dogwood validate``: parse, lower, and type-check policies against the schema.

    Raises ``DogwoodError`` with the report when validation fails.
    """

def lower(
    policies: str,
    *,
    policy_schema: str,
    event_schema: Optional[str] = None,
    providers: Optional[str] = None,
    macros: Optional[str] = None,
    emit: _Emit = "both",
    format: _Format = "human",
) -> str:
    """``dogwood lower``: lower a policy set to Cedar policies and the augmented schema.

    Emits a ``UserWarning`` when the Cedar output is not self-contained.
    """

def replay(
    policies: str,
    *,
    policy_schema: str,
    trace: str,
    event_schema: Optional[str] = None,
    providers: Optional[str] = None,
    macros: Optional[str] = None,
    format: _Format = "human",
) -> str:
    """``dogwood replay``: replay a ``.log`` event trace; return per-timepoint verdicts."""

def explain(
    policies: str,
    *,
    policy_schema: Optional[str] = None,
    event_schema: Optional[str] = None,
    providers: Optional[str] = None,
    macros: Optional[str] = None,
    format: _Format = "human",
) -> str:
    """``dogwood explain``: explain a policy set in deterministic semi-English, rule by rule."""

def schema_action(schema: str, *, format: _Format = "human") -> str:
    """``dogwood schema action``: check a Cedar action schema (``.cedarschema``)."""

def schema_event(schema: str, *, format: _Format = "human") -> str:
    """``dogwood schema event``: check an event-schema DSL file (``.dwschema``)."""

def schema_providers(providers: str, *, format: _Format = "human") -> str:
    """``dogwood schema providers``: check a provider declarations file (``providers.json``)."""

def schema_mcp(manifest: str) -> str:
    """``dogwood schema mcp``: generate a Cedar action schema from an MCP ``tools/list`` manifest."""
