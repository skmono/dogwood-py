# dogwoodpy

Python bindings for the [Dogwood](https://github.com/dogwood-policy/dogwood) policy toolchain.

Every `dogwood` CLI command is available as a Python function. You pass file
contents as strings instead of paths, and CLI flags become keyword arguments
with the same names and defaults. Each function returns exactly what the CLI
would print to stdout.

```python
import dogwoodpy

policy = open("policy.dw").read()
schema = open("schema.cedarschema").read()

print(dogwoodpy.validate(policy, policy_schema=schema))
# OK: validation passed with no errors or warnings.

report = dogwoodpy.replay(
    policy,
    policy_schema=schema,
    trace=open("trace.log").read(),
    format="json",
)
```

| Python | CLI |
|---|---|
| `format(policies)` | `dogwood format` |
| `check_parse(policies, *, event_schema=None, providers=None, macros=None, format="human")` | `dogwood check-parse` |
| `validate(policies, *, policy_schema, event_schema=None, providers=None, macros=None, format="human")` | `dogwood validate` |
| `lower(policies, *, policy_schema, event_schema=None, providers=None, macros=None, emit="both", format="human")` | `dogwood lower` |
| `replay(policies, *, policy_schema, trace, event_schema=None, providers=None, macros=None, format="human")` | `dogwood replay` |
| `explain(policies, *, policy_schema=None, event_schema=None, providers=None, macros=None, format="human")` | `dogwood explain` |
| `schema_action(schema, *, format="human")` | `dogwood schema action` |
| `schema_event(schema, *, format="human")` | `dogwood schema event` |
| `schema_providers(providers, *, format="human")` | `dogwood schema providers` |
| `schema_mcp(manifest)` returns the `.cedarschema` text | `dogwood schema mcp` |

- `format` accepts `"human"` or `"json"`. `emit` accepts `"cedar-policies"`,
  `"cedar-schema"`, `"cedar-json"` or `"both"`. Any other value raises `ValueError`.
- When the CLI would exit with code 2, the function raises
  `dogwoodpy.DogwoodError`. The message is the error rendered in the requested
  `format`. A failed `validate` also raises, with the validation report as the
  message.
- When `lower` produces Cedar that is not self-contained, it emits a
  `UserWarning`. The CLI prints this as a note on stderr.
- The package ships type stubs (`py.typed`), so `format` and `emit` values and
  keyword-only flags are checked by mypy, pyright and editors.

See the [Dogwood documentation](https://dogwood-policy.github.io/dogwood/) for
the policy language, schemas and trace format.

## Installation

```sh
pip install dogwoodpy
```

Wheels are published for Linux (x86_64, aarch64), macOS (x86_64, arm64) and
Windows (x64). Each covers CPython 3.9 or newer, free-threaded CPython
3.14t/3.15t, and PyPy 3.11.

## Install from source

You need a Rust toolchain that supports edition 2024 (Rust 1.85 or newer). Get
one from [rustup](https://rustup.rs).

```sh
git clone --recurse-submodules https://github.com/skmono/dogwood-py.git
cd dogwood-py
pip install .
```

For development, create a virtual environment with the pinned dev dependencies,
then build and test:

```sh
make venv-dev
source venv-dev/bin/activate
make quick      # maturin develop, then stub check and pytest
```

`make stubtest` checks that `dogwoodpy.pyi` matches the built module. After
changing the dependencies in `pyproject.toml`, run `make fresh-requirements` to
regenerate `requirements.txt` and `requirements.dev.txt`.

The tests use the `third_party/dogwood` git submodule, which is pinned to
Dogwood v1.1. They check the bindings against its example corpus. They also
run every function against the v1.1 `dogwood` CLI on the same inputs and
require identical output. The first run builds that CLI from the submodule,
which takes a few minutes. To use a binary you already have, set
`DOGWOOD_CLI=/path/to/dogwood`. It must report version `1.1.0`.

If you cloned without `--recurse-submodules`, run
`git submodule update --init`. Building or installing the package does not need
the submodule. Only the tests do.

Releases are published from CI; see
[docs/release-process.md](docs/release-process.md).

## License

Licensed under the [Apache License, Version 2.0](LICENSE).

`src/ops.rs` and `src/error.rs` are copied from `dogwood-cli` in
[Dogwood](https://github.com/dogwood-policy/dogwood). `src/render.rs` is
adapted from the same crate. Dogwood is also licensed under Apache-2.0.
Their attribution is in [NOTICE](NOTICE).
