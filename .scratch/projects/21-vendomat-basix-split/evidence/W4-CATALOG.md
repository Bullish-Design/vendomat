# W4: the catalog on stock devenv — 2026-10-13

<!-- Written by the orchestrator from the Sonnet subagent's final report; the subagent's own write of REPORT.md was refused by its tool. Raw evidence: /home/andrew/.local/state/vendomat/p21/2026-10-13/w4-catalog/logs/F*.log (command, output, rc). Catalog, template, harness, and scripts stay in that work dir. Orchestrator spot-check: F3b lists six faults in one error; F6 names vendomat.yaml in both conflicts; F11 prints the advanced line; F13 fails a mix at vendomat.yaml:3:3; F4.log shows the six-step pyproject.toml cycle with no stale result. -->

## Inputs

- devenv 2.4.0 (stock nixpkgs build), Nix 2.34.7.
- `devenv` input: the module-only `deferredModule` fork from W2 (`w2-machines/src/devenv-patched/src/modules`).
- nixpkgs: `cachix/devenv-nixpkgs` at `256551e`, the rev in the Vendomat lock. The template adds
  `nixpkgs-python` and `rust-overlay`.
- Parser: `parse.nix` v3, a byte copy (sha256 in `logs/inputs.sha`).
- Catalog: `catalog/catalog.nix`, 240 lines, imported as a `path:` input. A `devenv.yaml` import
  cannot leave the project directory.
- Disk: unallocated 33.87 GiB, metadata 82.5 % at the last reading (`logs/btrfs.log`). The first
  start stopped at metadata 94.28 %; btrfs then allocated a new metadata chunk and use fell to 79 %.
- The Vendomat repository was not changed. `import vendomat` still works in its venv.

## Fixtures

Each fixture ran in its own workspace `ws-fN`. The commands are in the logs.

| F | Claim | Result |
| --- | --- | --- |
| F1 | The parser corpus passes inside the catalog | Pass. 600/600 valid trees, 131/131 hand cases, 162/163 edge cases. `deep_1000` overflows in the catalog and in the bare parser. Rust reference 25/27: the two misses are tab cases that v3 accepts on purpose. |
| F2 | A minimal file enters a shell | Pass, for a one-key file, no file, and an empty file. |
| F3 | Three bad fields give one error | Pass. One error with three lines. F3b gives six lines, including an unknown program. |
| F4 | Python with and without `pyproject.toml` | Pass. Without the file: uv on, sync off, no warning. With it: the uv task runs. F4c control: sync forced on with no file prints "No pyproject.toml found" and the task fails. |
| F4b | The eval cache follows `pyproject.toml` | Pass. Six steps (absent, absent, created, created, deleted, deleted). Create and delete each re-evaluated and changed `uv.sync.enable`. Repeat steps came fully from cache (8 cached lines, 0 uncached). |
| F5 | Rust with the template input | Pass. No version gives nixpkgs `rustc 1.97.1`. `version: "1.81.0"` gives `rustc 1.81.0` through `rust-overlay`. |
| F6 | A scalar conflict names both files | Pass, on `languages.python.version` and on `env.GREETING`. |
| F7 | `mkForce` in `devenv.nix` wins | Pass. |
| F8 | Lists and maps merge | Pass. |
| F9 | `machines.NAME.nixos` merges | Pass, from the YAML, a `devenv.nix` attribute set, and an imported function. |
| F10 | `networking.hostName` is the machine name | Pass. A different value fails with both files named; `mkForce` wins. |
| F11 | The hatch line on shell entry | Pass. `advanced: devenv.nix sets 4 settings; devenv.local.nix sets 1 setting (this checkout only)`. Stubs and empty files print nothing. |
| F12 | `explain` prints value and source | Pass. `vendomat-explain PATH` prints the value and the file. |
| F13 | A tab-indented file end to end | Pass. A mix fails with `vendomat.yaml:3:3: inconsistent tabs and spaces`. |
| F14 | A14 control | Pass. Without `virtual` a machine fails on a missing `facter.json`; with `virtual: "true"` it evaluates. |

## Verdicts

- **A8:** backed, with one change. The line counts "settings", not "options".
  `definitionsWithLocations` cannot count what one file wrote: it forces other definitions, and one
  devenv option throws an uncatchable type error (`config.task.package` is null). The working count
  calls the hatch file as a module and counts the leaves of its attribute tree. It does not follow
  imports outside the workspace.
- **A9:** backed (F4, F4b, F4c). The cache tracks `builtins.pathExists` in both directions. This is
  an inference from behaviour; the devenv source was not read. `builtins.readDir` is the fallback if
  a later devenv regresses.
- **A10:** backed (F9, F10). It is a plain definition, so a different name needs `mkForce`.
- **A14:** backed at evaluation level (F14). The YAML key `virtual` is a proposal.

## Facts that surprised

1. The catalog's `config` must stay a literal attribute set. `config = guard mapping` gave infinite
   recursion, so each value carries its own `guard`.
2. Any read of `config` forces `_module.check = guard true`. A test harness cannot use
   `evalModules`, so F1 calls the module as a function.
3. devenv prints about 300 lines of Nix trace before the message. Vendomat's wrapper must print the
   text after the last `error:`.
4. Inside map options the priority sits on the key, so `explain` reads the key's priority to name
   the right file.
5. `devenv eval X` reads `config.X`, so `explain` is a lazy option tree with no environment
   variable.
6. Every shell entry prints `devenv 2.4.0 is newer than devenv input (2.3.1)`.
   `devenv.warnOnNewVersion = false` silences it.
7. A shell with Python 3.12 builds CPython. The agent stopped that build and used versions already
   in the store.
8. A schema fault has a key path but no line number, because the parser returns no line for a
   value (`SPLIT-035`).

## Catalog choices for the owner

- Catalog defaults use `mkDefault`. YAML values are plain definitions.
- The YAML keys `uv.enable` and `virtual` are proposals.
- `services` (postgres, redis) from slice 1 is not in this catalog.

## Not proved

An ISO or VM build through the catalog; `vendomat apply`; the A1 topology together with the catalog
(W3 proved it with stubs); deleting `vendomat.yaml`; a Python version missing from
`nixpkgs-python` (the code path exists, with no fixture).

## Ledger

The draft is [REQUIREMENTS-DRAFT.md](../REQUIREMENTS-DRAFT.md). It uses the prefix `SPLIT-`.
