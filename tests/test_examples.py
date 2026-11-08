"""The example corpus checks from dogwood v1.1's `dogwood-docs/tests/examples.rs`,
run through the bindings: every bundle validates, `explain` matches
`explain.out`, and `replay` matches `expected.out` (trailing whitespace trimmed,
as upstream does).

Bundles marked `requires-experimental-arithmetic` are skipped, as upstream does
without that feature; `test_cli_parity.py` covers how they are rejected.
"""

import pytest

import pydogwood
from conftest import bundle_params

supported = bundle_params(lambda b: not b.needs_arithmetic)


@pytest.mark.parametrize("bundle", supported)
def test_validates(bundle):
    pydogwood.validate(bundle.policy, policy_schema=bundle.schema, **bundle.schema_kwargs())


@pytest.mark.parametrize("bundle", supported)
def test_explain_matches_explain_out(bundle):
    out = pydogwood.explain(bundle.policy, policy_schema=bundle.schema, **bundle.schema_kwargs())
    assert out.rstrip() == bundle.read("explain.out").rstrip()


@pytest.mark.parametrize("bundle", bundle_params(lambda b: not b.needs_arithmetic and b.has("trace.log")))
def test_replay_matches_expected_out(bundle):
    out = pydogwood.replay(
        bundle.policy,
        policy_schema=bundle.schema,
        trace=bundle.read("trace.log"),
        **bundle.schema_kwargs(),
    )
