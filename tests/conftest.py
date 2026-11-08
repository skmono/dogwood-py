"""Shared fixtures for the pydogwood test suite.

The reference is the `third_party/dogwood` git submodule, pinned to dogwood
v1.1: its `dogwood-docs/examples/` bundles are the test corpus, and its
`dogwood-cli` is the binary the bindings are compared against. Initialize it
with `git submodule update --init`.
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

DOGWOOD = Path(__file__).parent.parent / "third_party" / "dogwood"
EXAMPLES = DOGWOOD / "dogwood-docs" / "examples"
MCP_MANIFEST = DOGWOOD / "dogwood-language" / "mcp_tools.json"
DOGWOOD_VERSION = "1.1.0"

if not EXAMPLES.is_dir():
    raise pytest.UsageError(
        f"{DOGWOOD} is not checked out; run `git submodule update --init`"
    )


def read_utf8(path: Path) -> str:
    """Exact file text: UTF-8 on every platform, no newline translation."""
    return path.read_bytes().decode("utf-8")



@dataclass(frozen=True)
class Bundle:
    """One example bundle: a policy, its action schema, and optional extras."""

    dir: Path
    # (CLI flag, Python keyword, file name) for each service-schema override present.
    overrides: tuple = field(default=())

    @property
    def name(self) -> str:
        return self.dir.name

    def read(self, name: str) -> str:
        return read_utf8(self.dir / name)

    def has(self, name: str) -> bool:
        return (self.dir / name).is_file()

    @property
    def policy(self) -> str:
        return self.read("policy.dw")

    @property
    def schema(self) -> str:
        return self.read("schema.cedarschema")

    @property
    def needs_arithmetic(self) -> bool:
        return self.has("requires-experimental-arithmetic")

    def schema_kwargs(self) -> dict:
        return {kw: self.read(name) for _, kw, name in self.overrides}

    def schema_flags(self) -> list:
        return [arg for flag, _, name in self.overrides for arg in (flag, name)]


def _bundle(path: Path) -> Bundle:
    # Same flag mapping as dogwood-docs/tests/examples.rs: `events.dwschema`
    # wins over `event.dwschema`.
    overrides = []
    for name in ("events.dwschema", "event.dwschema"):
        if (path / name).is_file():
            overrides.append(("--event-schema", "event_schema", name))
            break
    if (path / "providers.json").is_file():
        overrides.append(("--providers", "providers", "providers.json"))
    if (path / "macros.dw").is_file():
        overrides.append(("--macros", "macros", "macros.dw"))
    return Bundle(path, tuple(overrides))


BUNDLES = [
    _bundle(p)
    for p in sorted(EXAMPLES.iterdir())
    if (p / "policy.dw").is_file() and (p / "schema.cedarschema").is_file()
]


def bundle_params(predicate=lambda b: True):
    return [pytest.param(b, id=b.name) for b in BUNDLES if predicate(b)]


@pytest.fixture(scope="session")
def dogwood_cli() -> str:
    """The reference `dogwood` binary: `$DOGWOOD_CLI`, else built from the submodule."""
    cli = os.environ.get("DOGWOOD_CLI")
    if not cli:
        manifest = str(DOGWOOD / "Cargo.toml")
        subprocess.run(
            ["cargo", "build", "--release", "-q", "-p", "dogwood-cli", "--manifest-path", manifest],
            check=True,
        )
        metadata = subprocess.run(
            ["cargo", "metadata", "--no-deps", "--format-version", "1", "--manifest-path", manifest],
            capture_output=True, text=True, check=True,
        )
        exe = "dogwood.exe" if sys.platform == "win32" else "dogwood"
        cli = str(Path(json.loads(metadata.stdout)["target_directory"]) / "release" / exe)
    version = subprocess.run([cli, "--version"], capture_output=True, text=True, check=True)
    assert version.stdout.split() == ["dogwood", DOGWOOD_VERSION], (
        f"{cli} is not dogwood {DOGWOOD_VERSION}: {version.stdout!r}"
    )
    return cli
