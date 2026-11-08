"""The Python-side contract the CLI parity tests cannot see: argument
validation, keyword-only flags, and exception/warning types."""

import json
import re
import warnings

import pytest

import pydogwood
from conftest import DOGWOOD, EXAMPLES, read_utf8

BUNDLE = EXAMPLES / "access_not_revoked_since_grant"
POLICY = read_utf8(BUNDLE / "policy.dw")
SCHEMA = read_utf8(BUNDLE / "schema.cedarschema")


def test_dogwood_version_matches_reference_workspace():
    # Without building the CLI (the aarch64 job skips that): the submodule's
    # workspace version is what `dogwood --version` reports.
    manifest = read_utf8(DOGWOOD / "Cargo.toml")
    match = re.search(r'^\[workspace\.package\]\n(?:[^\[].*\n)*?version = "([^"]+)"', manifest, re.M)
    assert match, "no [workspace.package] version in the reference Cargo.toml"
    assert pydogwood.DOGWOOD_VERSION == match.group(1)


@pytest.mark.parametrize("fn", [pydogwood.check_parse, pydogwood.schema_action])
def test_unknown_format_is_value_error(fn):
    with pytest.raises(ValueError, match="invalid format `xml`"):
        fn(POLICY, format="xml")


def test_unknown_emit_is_value_error():
    with pytest.raises(ValueError, match="invalid emit `policies`"):
        pydogwood.lower(POLICY, policy_schema=SCHEMA, emit="policies")


@pytest.mark.parametrize(
    ("fn", "args"),
    [
        (pydogwood.validate, (POLICY, SCHEMA)),
        (pydogwood.lower, (POLICY, SCHEMA)),
        (pydogwood.replay, (POLICY, SCHEMA, "")),
        (pydogwood.explain, (POLICY, SCHEMA)),
        (pydogwood.check_parse, (POLICY, None)),
        (pydogwood.schema_action, (SCHEMA, "human")),
    ],
)
def test_flags_are_keyword_only(fn, args):
    with pytest.raises(TypeError):
        fn(*args)


def test_policy_schema_is_required():
    with pytest.raises(TypeError, match="policy_schema"):
        pydogwood.validate(POLICY)


def test_failed_validation_raises_with_report():
    # A clean parse/lower whose type check fails: the CLI's exit-2 report.
    policy = 'permit (principal, action, resource) when { context.no_such_attribute == 1 };'
    with pytest.raises(pydogwood.DogwoodError) as err:
        pydogwood.validate(policy, policy_schema=SCHEMA, format="json")
    report = json.loads(str(err.value))
    assert report["passed"] is False
    assert report["errors"]


def test_json_fatal_error_is_the_serialized_diagnostic():
    with pytest.raises(pydogwood.DogwoodError) as err:
        pydogwood.check_parse("permit (", format="json")
    diagnostic = json.loads(str(err.value))
    assert diagnostic["severity"] == "error"
    assert diagnostic["labels"][0]["start"] == 8


def test_lower_warns_only_when_not_self_contained():
    with pytest.warns(UserWarning, match="NOT self-contained"):
        pydogwood.lower(POLICY, policy_schema=SCHEMA)

    plain = EXAMPLES / "allow_anything"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        pydogwood.lower(
            read_utf8(plain / "policy.dw"),
            policy_schema=read_utf8(plain / "schema.cedarschema"),
        )
