# Shared RepoMan Toolchain: Vendomat Concept

**Status:** proposal  
**Date:** 2026-07-16  
**Scope:** make the RepoMan CLI family a shared, immutable Nix toolchain for devenv consumers while retaining editable development for each tool's own repository.

## 1. Problem and desired outcome

Today, a RepoMan-enabled consumer runs `repoman-sync`. That script translates each `path:`
entry in `repoman.lock` into `uv pip install --editable=...` and installs the selected manager
CLIs into that consumer's devenv virtual environment. The result is a separate installation of
`repoman`, `copyroom`, `gitman`, `testee`, `docman`, `zelligate`, `mypi-agent`, and `alliman`
for every consumer repository. RepoMan's tasks then explicitly invoke
`<devenv-state>/venv/bin/<tool>`.

Vendomat already eliminates the equivalent native-build duplication for `pyjutsu`: a wheel is
built once in the Nix store and each consumer resolves it from Vendomat's wheelhouse. The same
model should apply to the RepoMan command family itself.

The target user experience is:

```nix
# consumer devenv.nix
repoman = {
  enable = true;
  managers = [ "copy" "git" "test" "doc" ];
  toolchain.enable = true;
};
```

Entering any such devenv exposes the selected commands on `PATH`, but their executable code and
Python dependency closures come from the same content-addressed `/nix/store` outputs. `gitman`,
`copyroom`, and friends are not installed into that project's venv. A consumer keeps a venv only
for its *own* application dependencies and development tools.

"Single instance" here means one immutable Nix derivation per exact source revision, Python
version, platform, and dependency graph. Shells may each have their own PATH entries, but they
point at the same store paths. This is safer and more reproducible than one mutable global Python
environment. A Home Manager/system-profile installation may additionally expose the tools outside
devenv, but it must not become the source of truth for a project-specific toolchain.

## 2. Goals and non-goals

### Goals

- Build each supported RepoMan CLI once and share it across all consumers with the same Vendomat
  input lock.
- Make the ordinary consumer path independent of `uv pip install` for RepoMan and manager CLIs.
- Preserve the current manager roster and the existing `repoman.lock` ownership of source/version
  selection during the transition.
- Preserve a first-class editable mode for the repository that owns a tool, so changing `gitman`
  still runs the checkout's code rather than an old store build.
- Keep native dependency sharing (`pyjutsu` wheelhouse) working while migrating pure-Python CLIs.
- Provide explicit version provenance and a way to diagnose whether a command came from the shared
  toolchain or a project venv.

### Non-goals

- Do not turn Vendomat into a general Python package registry or require publishing packages to
  PyPI.
- Do not replace RepoMan's manager registry, manager selection, skills model, or per-project
  configuration.
- Do not force all projects onto one floating globally installed version.
- Do not remove a consumer's own Python venv; application dependencies remain project-local.
- Do not include `siteman` until it becomes a defined RepoMan manager with a CLI/package contract.

## 3. Recommended architecture

Vendomat gains a third face in addition to **artifacts** (native wheels) and **knowledge**:

> **Toolchains:** build and compose the RepoMan command family as Nix packages, then deliver a
> selected, version-pinned command closure to devenv consumers.

### 3.1 Source authority and reproducibility

Vendomat owns a declared input for each supported tool source. For local development these may be
`git+file://` inputs; for fleet/CI use they should be Git inputs pinned by `flake.lock`. The
Vendomat lock—not a mutable checkout path discovered at shell entry—determines the exact shared
toolchain revision.

This makes two modes explicit:

| Mode | Who uses it | Command source | Purpose |
| --- | --- | --- | --- |
| `store` | normal consumers | Vendomat package output | shared, pinned, immutable toolchain |
| `editable` | a tool's own repository or intentional integration work | consumer venv/local checkout | live source edits |

`store` is the desired default once migration is complete. `editable` must be opt-in per tool or
per consumer; it is not an error condition.

### 3.2 Package outputs

For each supported tool, Vendomat builds a Python application derivation with its runtime Python
dependencies and its console script:

```text
packages.<system>.
  repoman
  copyroom
  gitman
  testee
  docman
  zelligate
  mypi-agent
  alliman
  repoman-toolchain-<roster>
```

`repoman-toolchain-<roster>` is a `symlinkJoin` (or equivalent wrapper closure) containing the
selected command packages. It must fail evaluation on duplicate executable names rather than
silently shadow one. Each command package is independently content-addressed, so changing
`testee` rebuilds only `testee` and affected closure links—not every manager.

Vendomat should expose a canonical all-supported-tools closure for inspection, plus a library
function that creates a roster-specific closure. The devenv module uses the roster-specific
closure, avoiding irrelevant packages and tool collisions.

### 3.3 Python dependency strategy

Each command must be packaged as a Nix Python application, not copied into a shared virtualenv.
The package builder needs a deterministic mapping for project metadata and Python dependencies:

- use native Nix Python packages where available;
- package missing third-party dependencies as locked Nix derivations, with hashes committed in
  Vendomat's lock/materialization data;
- do not permit a Nix build to download unpinned packages at runtime;
- build `gitman` against Vendomat's vended `pyjutsu` package/wheel strategy rather than letting
  its build substitute an editable sibling checkout.

This is the principal implementation cost. It must be solved tool-by-tool, starting with the
small pure-Python CLIs, rather than assuming every `pyproject.toml` automatically builds in Nix.

### 3.4 Devenv delivery contract

Vendomat's module adds the closure to `packages` and exports an unambiguous command directory:

```nix
repoman.toolchain = {
  enable = true;
  mode = "store";            # "editable" retains current behavior
  include = [ ];              # extra tools beyond repoman.managers, normally empty
};

# Defined by the Vendomat module in store mode:
env.REPOMAN_TOOLCHAIN_BIN = "${toolchain}/bin";
```

The manager roster determines the default command set:

| manager key | package | executable |
| --- | --- | --- |
| core | `repoman` | `repoman` |
| `copy` | `copyroom` | `copyroom` |
| `git` | `gitman` | `gitman` |
| `test` | `testee` | `testee` |
| `doc` | `docman` | `docman` |
| `session` | `zelligate` | `zelligate` |
| `agent` | `mypi-agent` | `mypi` |
| `spec` | `alliman` | `alliman` |

Vendomat must validate that every selected manager is packageable before enabling store mode and
report the exact unsupported manager. It must not silently fall back to a venv installation.

## 4. Required RepoMan changes

RepoMan owns the interface that currently assumes a venv, so this cannot be completed inside
Vendomat alone.

### 4.1 Command resolution abstraction

Replace direct references to `${config.devenv.state}/venv/bin/<tool>` in RepoMan manager modules
with one command-resolution contract. In store mode, task scripts invoke
`$REPOMAN_TOOLCHAIN_BIN/<command>`; in editable mode they retain the venv path. The resolver must
use an absolute known path, not merely `command -v`, so a project's unrelated venv cannot shadow
a selected shared tool.

Add a RepoMan option such as:

```nix
repoman.cliProvider = "venv"; # "venv" | "vendomat"
```

Vendomat's module sets this to `vendomat` only when `repoman.toolchain.enable = true`. RepoMan
validates that `REPOMAN_TOOLCHAIN_BIN` is present for that provider. This preserves backwards
compatibility for consumers that do not yet import Vendomat.

### 4.2 Replace `repoman-sync` in store mode

`repoman-sync` has two separable responsibilities today:

1. install the CLI family into the active venv;
2. run `repoman install-skills` after the commands exist.

In Vendomat provider mode it must not execute `uv pip install` for `repoman` or manager entries.
It becomes a post-provisioning operation (or is replaced by `repoman-provision`) that verifies the
shared command closure, installs/refreshes generated skills, and reports provenance. Venv mode
keeps the existing lock-driven install behavior unchanged.

The command should still read `repoman.lock` during migration to compare requested sources with
the Vendomat toolchain manifest and fail on a mismatch. Once the shared-package manifest is
authoritative, `repoman.lock` needs an additive source kind such as `toolchain:<name>@<revision>`
or a declared `toolchain` block. Do not overload `wheel:`: wheels are Python dependency artifacts;
toolchain entries select executable closures.

### 4.3 Task and subprocess behavior

Every RepoMan task, doctor, status aggregation, and internal subprocess call must use the same
provider resolver. This includes `testee`, `docman`, `zelligate`, `mypi`, and `alliman`, not only
the obvious `repoman` command. Add tests that deliberately put an incompatible command in the
consumer venv and prove the store-provider tasks still invoke the shared executable.

## 5. Required Vendomat changes

1. Add source inputs and package recipes for the core/manager CLI repositories.
2. Add a reusable `mkPythonCli`/package-materialization mechanism, with a documented policy for
   dependency overrides and generated lock data.
3. Define the manager-key → package → executable mapping in one place. RepoMan's existing roster
   remains the business authority; Vendomat consumes or validates a compact exported mapping to
   avoid duplication drift.
4. Add `packages.repoman-toolchain-*` and expose a library function for roster closures.
5. Add `repoman.toolchain` (or a clearly namespaced Vendomat equivalent) module options and
   evaluate-time validation.
6. Export `REPOMAN_TOOLCHAIN_BIN`, `REPOMAN_TOOLCHAIN_REVISION`, and a machine-readable
   provenance manifest in the closure.
7. Extend `vendomat doctor` with package availability, roster compatibility, command origin,
   Python ABI, and `pyjutsu` wheel compatibility checks.
8. Document the distinction between the shared CLI closure and the existing `wheelhouse`; the
   former supplies commands, the latter supplies native Python dependencies to consumer venvs.

## 6. Migration plan

### Phase 0 — inventory and contract tests

Record every manager's Python version, console script, runtime dependencies, external binaries,
and current venv-path call sites. Establish a RepoMan command-provider abstraction with `venv` as
the unchanged default. Add regression tests for current behavior.

### Phase 1 — prove one pure-Python manager

Package `copyroom` and `repoman` in Vendomat. Enable a `vendomat` provider in one fixture with
`managers = [ "copy" ]`. Verify no manager is installed in the consumer venv, `repoman` and
`copyroom` run from `/nix/store`, skills install successfully, and an editable consumer remains
unchanged.

### Phase 2 — package the core roster incrementally

Add `testee`, then `docman`, `zelligate`, `mypi-agent`, and `alliman`, including their external
Nix-provided binaries/modules. Each tool adds a package build test, a command-origin test, and a
consumer integration test. Do not mark a manager supported merely because its package evaluates;
exercise its doctor/task flow.

### Phase 3 — gitman and native integration

Package `gitman` against the vended `pyjutsu` artifact. Prove a `git` consumer has no Rust,
Maturin, Cargo build, or editable `pyjutsu` installation. Keep `repoman.nativeBuild = true` and
editable provider support for Pyjutsu's own development repository.

### Phase 4 — make shared mode the consumer default

After every currently supported manager has passed integration testing, make
`repoman.toolchain.enable` default to true when Vendomat is imported. Keep explicit `mode =
"editable"` for tool development and a documented short-lived `venv` compatibility escape hatch.
Only then deprecate venv CLI installation in ordinary consumer templates.

### Phase 5 — optional profile convenience

Expose the all-tools package through Home Manager/NixOS for ad-hoc terminal use. This is a
convenience layer only; devenv continues to select its toolchain from the project's pinned
Vendomat input so project behavior remains reproducible.

## 7. Acceptance criteria

A completed implementation must demonstrate all of the following:

- Two distinct devenv consumers with identical Vendomat locks resolve `repoman` and selected
  manager executables to the same `/nix/store` paths.
- Their `.devenv` venvs contain neither the manager distributions nor their console-script
  wrappers.
- Manager tasks and `repoman doctor/status` use the shared paths even if a conflicting executable
  exists in the venv or inherited PATH.
- A manager's own repository can opt into editable mode and immediately run local uncommitted
  changes.
- `gitman` continues to use the shared Pyjutsu artifact with zero consumer Cargo/Maturin work.
- A missing, stale, unsupported, or source-mismatched manager produces an actionable failure;
  there is no silent venv fallback.
- Store-mode packages and command provenance are covered by Nix evaluation/build tests and at
  least one end-to-end devenv fixture.

## 8. Risks and decisions to make before implementation

1. **Package materialization:** choose the Nix Python packaging strategy before adding many tools.
   A per-tool ad hoc dependency override approach will become unmaintainable.
2. **Source/version authority:** decide whether Vendomat's flake lock alone is authoritative in
   store mode, or whether `repoman.lock` gains a first-class `toolchain:` reference. The latter is
   clearer for per-repo policy; the former is simpler initially. Either choice needs a mismatch
   check, not implicit precedence.
3. **Python ABI alignment:** today Vendomat targets Python 3.13 while RepoMan's standalone flake
   packages Python 3.12. The shared toolchain must choose and document one interpreter baseline;
   this is especially important for Gitman/Pyjutsu compatibility.
4. **External tool provisioning:** a shared Python CLI does not eliminate per-devenv services or
   external binaries such as Git, Zellij, secretspec, Node, or documentation tooling. RepoMan's
   enable-gated Nix modules continue to provision those capabilities.
5. **Writable project state:** commands can remain shared while their configuration, reports,
   skills, and caches remain per repository. No CLI package may write into `/nix/store`.

## 9. Decision summary

Build a **shared, pinned Nix command closure**, not a shared mutable virtualenv and not merely a
global profile installation. Vendomat owns package construction and delivery; RepoMan owns
manager selection and command invocation through a provider abstraction. Maintain editable mode
for tool authors, migrate one manager at a time, and make unsupported/mismatched states fail
explicitly.
