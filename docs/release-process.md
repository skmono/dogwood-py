# Release Process

Releasing a new `pydogwood` version is tag-driven. Pushing a `v*` tag triggers the `release` job in
`.github/workflows/CI.yml`. That job waits for wheels from every platform plus the sdist, generates build-provenance
attestations, publishes to PyPI through [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, so
no long-lived tokens), and creates the GitHub Release with the distributions attached.

## Prerequisites (one-time)

- A PyPI trusted publisher for `pydogwood`. Before the first release, add it as a *pending* publisher at
  https://pypi.org/manage/account/publishing/. Afterwards it lives at
  https://pypi.org/manage/project/pydogwood/settings/publishing/. Configure it with:
    - Owner `skmono`, repository `pydogwood`, workflow `CI.yml`, environment `pypi-release`
- A GitHub environment `pypi-release`, created in the repo under Settings → Environments, with:
    - Deployment tags restricted to the pattern `v*`
    - A required reviewer (a maintainer), which adds a manual approval step to every release

## Release steps

### 1. Bump the version

On a release branch, update:

- `Cargo.toml`: the `version` field. maturin reads the package version from here.
- `Cargo.lock`: regenerate it by running `cargo build`.

If the release moves to a new Dogwood version, also update:

- the `dogwood-language` / `dogwood-formatter` requirements in `Cargo.toml`;
- `src/ops.rs` and `src/error.rs`, copied from that version's `dogwood-cli`;
- `src/render.rs`, adapted from the same crate;
- the `third_party/dogwood` submodule, checked out at the matching tag;
- `DOGWOOD_VERSION` in `src/lib.rs` (the test suite checks it against the submodule's CLI).

Open a PR and wait for CI to pass on every platform, then merge.

### 2. Tag and push

From the updated `main`:

```bash
git checkout main && git pull
git tag -a vX.Y.Z -m "pydogwood vX.Y.Z"
git push origin vX.Y.Z
```

Pushing the tag starts a full CI run plus the `release` job.

### 3. Approve the deployment

The `release` job pauses at the `pypi-release` environment until a reviewer approves it. Open the CI run for the tag
in the Actions tab and click **Review deployments** → `pypi-release` → **Approve and deploy**.

The job then downloads every wheel and the sdist, attests them, and uploads them with `pypa/gh-action-pypi-publish`,
which also publishes a PEP 740 attestation for each file. It then creates the GitHub Release for the tag, with notes
generated from the merged PRs and every distribution attached. Re-running the job is safe: files already on PyPI
are skipped, and an existing GitHub Release is reused with its attachments replaced.

### 4. Verify

At https://pypi.org/project/pydogwood/X.Y.Z/, check that the sdist and wheels for every platform are present:

- **Linux:** x86_64 and aarch64 (manylinux)
- **macOS:** x86_64 and arm64
- **Windows:** x64

Each platform should have four wheels: one `cp39-abi3` wheel covering CPython 3.9+, plus version-specific wheels for
the free-threaded 3.14t and 3.15t and for PyPy 3.11.
