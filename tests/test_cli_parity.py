"""Differential tests: each binding against the dogwood v1.1 CLI on the same inputs.

A CLI exit 0 must be a normal return equal to its stdout, with its stderr note
(from `lower`) raised as `UserWarning`s. A CLI exit 2 must be a `DogwoodError`
whose message is what the CLI printed: on stdout for JSON errors and failed
validations, on stderr (plus its trailing newline) for human-rendered errors.
"""

from __future__ import annotations

import subprocess
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

import dogwoodpy
from conftest import BUNDLES, EXAMPLES, MCP_MANIFEST, read_utf8

FORMATS = ("human", "json")
EMITS = ("cedar-policies", "cedar-schema", "cedar-json", "both")


@dataclass
class Case:
    id: str
    args: list
    fn: Callable
    kwargs: dict
    cwd: Path = EXAMPLES
    stdin: str | None = None
    formats: tuple = FORMATS


def _half(text: str) -> str:
    return text[: len(text) // 2]


def _bundle_cases(b):
    policy, schema, flags, kw = b.policy, b.schema, b.schema_flags(), b.schema_kwargs()
    ps = ["--policy-schema", "schema.cedarschema"]
    lowered = {"policies": policy, "policy_schema": schema, **kw}
    yield Case("format", ["format", "policy.dw"], dogwoodpy.format, {"policies": policy}, formats=(None,))
    yield Case("check-parse", ["check-parse", "policy.dw", *flags], dogwoodpy.check_parse, {"policies": policy, **kw})
    yield Case("validate", ["validate", "policy.dw", *ps, *flags], dogwoodpy.validate, lowered)
    for emit in EMITS:
        yield Case(
            f"lower-{emit}",
            ["lower", "policy.dw", *ps, "--emit", emit, *flags],
            dogwoodpy.lower,
            {**lowered, "emit": emit},
        )
    yield Case("explain", ["explain", "policy.dw", *ps, *flags], dogwoodpy.explain, lowered)
    yield Case("explain-no-schema", ["explain", "policy.dw", *flags], dogwoodpy.explain, {"policies": policy, **kw})
    yield Case("schema-action", ["schema", "action", "schema.cedarschema"], dogwoodpy.schema_action, {"schema": schema})
    for _, key, name in b.overrides:
        if key == "event_schema":
            yield Case("schema-event", ["schema", "event", name], dogwoodpy.schema_event, {"schema": b.read(name)})
        elif key == "providers":
            yield Case("schema-providers", ["schema", "providers", name], dogwoodpy.schema_providers, {"providers": b.read(name)})
    if b.has("trace.log"):
        trace = b.read("trace.log")
        yield Case(
            "replay",
            ["replay", "policy.dw", *ps, "--trace", "trace.log", *flags],
            dogwoodpy.replay,
            {**lowered, "trace": trace},
        )
        # Error path: an unparsable trace line.
        bad_trace = trace + "\ngarbage ((\n"
        yield Case(
            "replay-bad-trace",
            ["replay", "policy.dw", *ps, "--trace", "-", *flags],
            dogwoodpy.replay,
            {**lowered, "trace": bad_trace},
            stdin=bad_trace,
        )
    # Error paths: truncated policy and truncated action schema.
    cut = _half(policy)
    yield Case("check-parse-cut", ["check-parse", "-", *flags], dogwoodpy.check_parse, {"policies": cut, **kw}, stdin=cut)
    yield Case("validate-cut", ["validate", "-", *ps, *flags], dogwoodpy.validate, {**lowered, "policies": cut}, stdin=cut)
    cut_schema = _half(schema)
    yield Case("schema-action-cut", ["schema", "action", "-"], dogwoodpy.schema_action, {"schema": cut_schema}, stdin=cut_schema)


def _cases():
    for b in BUNDLES:
        for case in _bundle_cases(b):
            case.cwd = b.dir
            for fmt in case.formats:
                yield pytest.param(case, fmt, id=f"{b.name}-{case.id}" + (f"-{fmt}" if fmt else ""))
    for name, manifest in [
        ("mcp_tools", read_utf8(MCP_MANIFEST)),
        ("tools-object", '{"tools": []}'),
        ("not-json", "not json"),
    ]:
        case = Case(f"schema-mcp-{name}", ["schema", "mcp", "--manifest", "-"], dogwoodpy.schema_mcp, {"manifest": manifest}, stdin=manifest)
        yield pytest.param(case, None, id=case.id)


@pytest.mark.parametrize(("case", "fmt"), list(_cases()))
def test_matches_cli(dogwood_cli, case, fmt):
    args = case.args + (["--format", fmt] if fmt else [])
    kwargs = case.kwargs | ({"format": fmt} if fmt else {})
    # Bytes, not text mode: no locale encoding or newline translation (Windows).
    stdin = case.stdin.encode("utf-8") if case.stdin is not None else None
    cli = subprocess.run([dogwood_cli, *args], cwd=case.cwd, input=stdin, capture_output=True)
    stdout, stderr = cli.stdout.decode("utf-8"), cli.stderr.decode("utf-8")
    assert cli.returncode in (0, 2), stderr

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if cli.returncode == 0:
            assert case.fn(**kwargs) == stdout
            assert all(w.category is UserWarning for w in caught)
            assert "".join(f"note: {w.message}\n" for w in caught) == stderr
            return
        with pytest.raises(dogwoodpy.DogwoodError) as err:
            case.fn(**kwargs)
    if stdout:
        assert str(err.value) == stdout
        assert stderr == ""
    else:
        assert str(err.value) + "\n" == stderr
