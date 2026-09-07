# Face D — progress

## Done

### Sub-phase 0 — the command-provider seam (repoman)

Landed on repoman's `main` as `cli-provider` (not pushed; see below).

The Python half already existed: `checks.cli_provider()`, `checks.toolchain_bin()`,
`manager_binary()`, and their tests. The gap was the nix module.

- `repoman.cliProvider`, an enum of `"venv"` and `"store"`, default `"venv"`.
- `repoman.toolchainBin` resolves through it, so `gitman.nix`, `copyroom.nix` and
  `docman.nix` keep their single interpolation and learn no second path shape.
- Store mode fails a TASK on an unset `REPOMAN_TOOLCHAIN_BIN`, via `:?`. It does not
  expand to `""` and exec `/gitman`.
- Store mode only REPORTS at shell entry. Nothing in the closure sits on the
  shell-entry critical path without a degrade.
- Seven regression tests in `tests/test_modules_nix.py` pin venv mode as unchanged.
- `testee verify --mode ci`: PASSED.

### Sub-phase 1 — package copyroom and repoman (vendomat)

Landed on vendomat's `main` as `toolchain-store-mode`. Not pushed: the sandbox
classifier denied `git push`.

- `lib/mkPythonCli.nix` — the one mapping from `pyproject.toml` to a Nix Python
  application. Metadata is read, never restated. Dependencies resolve through an
  explicit `depMap`; an unmapped one throws by name.
- `lib/mkToolchain.nix` — the roster join. Throws on a duplicate command name and on
  a mixed Python baseline. Writes `share/vendomat/toolchain.json`.
- `packages.repoman`, `packages.copyroom`, `packages.repoman-toolchain-core`.
- `vendor.toolchain.enable` / `.roster` in `modules/devenv.nix`. Exports
  `REPOMAN_TOOLCHAIN_BIN` and `REPOMAN_TOOLCHAIN_MANIFEST`, and sets
  `repoman.cliProvider = "store"` when repoman's option exists.
- Proven by real `nix` runs, not by evaluation alone: both commands build, both run,
  both resolve into `/nix/store`, `demo` is gone, and the collision guard throws.
- `testee verify --mode ci`: PASSED.

### Sub-phases 2 and 3 — docman and gitman (vendomat)

- `docman` needed no new derivation, as the inventory predicted.
- `gitman` builds against `packages.pyjutsu`, a Python package installed from the wheel
  this flake already vends. The wheel stays the artifact of record; the package only
  installs it.
- Proven: gitman's RUNTIME closure contains no cargo, rustc, maturin or mold, and
  `gitman --version` imports pyjutsu from the store.
- All four commands run and their doctors execute — `repoman managers`,
  `copyroom doctor`, `docman doctor`, `gitman status`. Evaluating is not supporting.

## Next, in order

1. **Sub-phase 4 — make store mode the default** when vendomat is imported, keeping
   `mode = "editable"` first-class for tool authors and a documented venv escape hatch.
2. **Sub-phase 5 — Home Manager**, replacing the machine venv on the login shell.
3. **A live devenv fixture.** The store path is proven by unit tests and by hand; an
   end-to-end consumer shell would prove the empty venv directly.

## Decided

**testee is not in the closure** (owner, 2026-09-07). Its tools import the
consumer's code, so it stays a per-repo `pyproject.toml` dev dependency and
RepoMan's `install="uv"` registry entry stands.

**templateer is not in the closure either** (owner, 2026-09-07). It is not a
RepoMan manager — no registry key, no manager module — and it was the only tool
needing new Nix derivations. Same treatment as testee: a per-repo dependency.

Together these close the roster at four commands, and the roster needs no
package materialization work at all. That was CONCEPT §8.1's principal cost.
