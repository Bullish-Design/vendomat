# V5 library rewrite kickoff prompt

> **Stale as of 2026-10-08. Do not paste or follow this prompt.** It is not in the reading order of
> `.scratch/CURRENT.md`. It describes an inline generated `outputs` block, a generated devenv shell,
> and `GEN-001` to `GEN-014`, which the project-output decision supersedes. It also cites 141
> requirement IDs; the specification now holds 171. Use `SPEC-V5.md`, `GUIDE-V5.md` Step 8, and
> `prelim-verification/DECISIONS.md`. The text below stays as provenance.

Paste everything below the line into a clean session.

This covers the **library**: the Nix functions and the Python command line. It needs no disk work,
no root, and no activation, so it can run before, after, or alongside the system bootstrap, which
has its own prompt in `KICKOFF-V5.md`.

---

Rewrite the Vendomat library. Work in `/home/andrew/Documents/Projects/vendomat`.

## Read these first, in this order

All in `.scratch/projects/14-vendomat-local/`:

1. `CONCEPT-V5.md` — the shape and the worked examples.
2. `SPEC-V5.md` — normative. 141 requirement IDs, each with a Verify column.
3. `GUIDE-V5.md` — steps 4, 8, and 9 are yours. Read §4.1 to §4.5, §8, and §9.

## Authority

`AGENTS.md` holds durable rules and points at `.scratch/CURRENT.md`, which names this project as
active. The documents above are the only authority. Treat anything in `docs/` or another
`.scratch/projects/` directory as history unless one of those documents cites it.

## What you are building

Vendomat makes the owner's projects resolvable by local path and already built.

You declare direct inputs in `vendomat.toml`. Vendomat generates a self-contained `flake.nix`
naming only those inputs, with the `follows` lines and an inline `outputs` block. **Nix** resolves
the transitive graph and owns `flake.lock`. Machine settings live in dotted-path TOML converted to
real NixOS options.

Vendomat selects no revision, walks no graph, and writes no lock. There is no resolver — that was
tried and withdrawn. If you find yourself writing a version solver, a topological sort, or a cycle
check, stop: Nix already does it.

## Scope: steps 4, 8, and 9

About 105 lines of Nix and 310 lines of Python. Work in this order; step 8 inlines a template from
step 4.

### Step 4 — the Nix functions

| File | Role | Lines | IDs |
| --- | --- | --- | --- |
| `lib/mkModules.nix` | one declaration to three module faces | 30 | `MOD-001` to `MOD-009` |
| `lib/fromToml.nix` | dotted-path TOML to NixOS options | 10 | `SYS-001` to `SYS-007` |
| `lib/paths.nix` | the `vendomat.paths` option and its environment export | 25 | `PATH-001` to `PATH-004` |
| the consumer `outputs` template | **not** a library function. `generate.py` inlines it in step 8 | 15 | `GEN-004`, `GEN-009` to `GEN-012` |

`GUIDE-V5.md` §4.1 to §4.3 gives all four bodies in full. Use them as written; they are the
reviewed versions.

Three fixture assertions decide whether this step is correct:

- **`MOD-007`** — `extra.nixos` setting something under `environment` must not clobber
  `environment.systemPackages`. The merge is `lib.recursiveUpdate`, not `//`. A shallow merge
  silently drops the installed packages.
- **`SYS-005`** — an option defined in both the host TOML and a Nix module must be an evaluation
  error. That is why the converter uses `lib.mkMerge`.
- **`PATH-003`** — `vendomat.paths` is `attrsOf str`, never `path`. A `path` type copies directory
  contents into the store on evaluation. Verify by appending to a file under a declared path and
  confirming `nix path-info` output is byte-identical before and after.

### Step 8 — the registry and the generator

| File | Role | Lines | IDs |
| --- | --- | --- | --- |
| `registry.py` | pydantic models for `[inputs]` and `[passthrough]`; `add`, `remove`, `read`, `write` | 60 | `REG-001` to `REG-009` |
| `store.py` | clone and fetch under `~/vendor`; refuse a dirty tree | 30 | `STORE-001` to `STORE-005` |
| `generate.py` | registry to `flake.nix`: header, digest, `follows` lines, inline `outputs` | 40 | `GEN-001` to `GEN-012` |
| `cache.py` | `nix path-info --store` presence per input | 50 | `CACHE-005` |
| `cli.py` | `add`, `remove`, `sync`, `status`, `query`, `path`, `explore` | 100 | `CLI-001` to `CLI-008`, `CLI-014` |

A registry entry is a table. An empty table means the clone at `~/vendor/<name>` at its default
ref. Keys `url`, `ref`, `rev`, and `flake` pass through to the generated flake input verbatim.
There are no version constraints (`REG-004` is withdrawn).

There is no `update` command. `nix flake update <input>` already does it (`CLI-006` withdrawn).

### Step 9 — system configuration

| File | Role | Lines | IDs |
| --- | --- | --- | --- |
| `systemcfg.py` | `set`, `get`, `unset` over `<host>.toml`; `diff`; `apply`; `rollback` | 120 | `SYS-007` to `SYS-011`, `CLI-009` to `CLI-013` |

Build `diff` carefully. It evaluates `nixosConfigurations.<host>.config.<path>` before and after and
compares the JSON. Reporting what a change does before activation is the whole advantage over
editing Nix by hand.

## The three verifications that matter most

Run these before you call any step done.

**`GEN-002` — one nixpkgs.** The generator exists to write `follows` lines, because `follows` is
flake metadata read before evaluation and no Nix function can produce it. Without it, two inputs
locked a week apart split the closure.

```sh
nix flake metadata --json \
  | jq -r '[.locks.nodes | to_entries[] | select(.key|test("nixpkgs"))] | length'
```

Expect `1`. More than one means a `follows` line is missing.

**`GEN-009` — a consumer needs no Vendomat.** This justifies inlining the `outputs` block rather
than shipping `mkProject` as a library function.

```sh
rg -c vendomat flake.nix                                   # expect 0
env PATH=$(echo "$PATH" | tr ':' '\n' | grep -v vendomat | paste -sd:) \
  nix develop -c true
nix build .#devShells.x86_64-linux.default --no-link
```

**`GEN-003` — direct inputs only.** Add one input whose repo needs two others. `flake.nix` gains
exactly one entry; `flake.lock` gains three.

And `GEN-008`: record `sha256sum flake.lock`, run every Vendomat command, confirm the sum is
unchanged, then confirm `nix flake update <input>` still works. Vendomat must never read or write
that file.

## The existing source tree

`src/vendomat/` holds 3,926 lines serving version 0.4.4. It is **provenance, not a base.** Do not
extend it, and do not read it for design. V5 starts from a bare source tree; the git history stays.

Eleven central overlays, ten local-checkout overlays, and one flake-input consumer use the current
paths. Every machine is being reconfigured, so those paths are replaced rather than preserved. One
obligation survives as `BOOT-010`: **record what the old command line exposed that the new one does
not.** Replacement is permitted; silent loss is not.

Work in one Gitman lane per step so the replacement is revertable.

## Rules

- Open one Gitman lane per step. Never run raw `git` or `jj`.
- Verify with `devenv shell -- testee verify --mode quick`. Do not call pytest, ruff, or ty
  directly.
- A requirement is satisfied when its Verify column runs and passes. A document never satisfies a
  requirement. There are no phases and no gates — each step has one **Stop if** condition.
- Write every fixture before the implementation it checks. State the expected pass, fail, and gap
  results first.
- Preserve every requirement ID. Never reuse or renumber one. Mark a changed requirement
  *Superseded by* a new ID; do not edit it in place. When you supersede one, grep for duplicates of
  the same claim — two requirements once carried the same rule and only one was caught.
- If a fixture disproves the specification, update the specification, the guide, and the concept
  together. Do not leave the three disagreeing.
- Simplified Technical English for every comment, docstring, command-line help string, and error
  message. One idea per sentence, active voice, no filler.
- Every error message names the input, the file, or the option path it concerns. `SPEC-V5.md` §10
  is the error table; match it.

## Do not

- Write a resolver, a version solver, a topological sort, or a cycle check. Nix owns the graph.
- Read or write `flake.lock`.
- Make a consumer depend on Vendomat, as a flake input or otherwise.
- Add an `update` command.
- Touch any disk, run `nixos-rebuild`, or need root. This session is code and fixtures only.
- Re-open settled decisions: publication is ambient with no receipt; the command line is
  system-installed while `mkModules` is a flake input for repositories that author modules; the
  `outputs` block is inlined; cores export a function rather than a package.

## Open questions — ask, do not invent

| Question | Blocks |
| --- | --- |
| Is `~/vendor` still the source root, or does it move under a `vendomat.paths` name? | `store.py` |
| Which fixed inputs does every generated flake carry — `nixpkgs` and `devenv` only, or also `systems`? | `generate.py` |
| Should `explore` call the dedicated editor by store path, or by a name the core installs? | `cli.py` |

## First reply

Before you write anything: list the requirement IDs you intend to satisfy, name the files you will
create and in what order, name the fixtures you will write first, and state which of the three key
verifications you will run at each step boundary. Then begin with step 4.
