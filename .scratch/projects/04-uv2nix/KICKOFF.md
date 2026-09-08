# Kickoff — uv2nix for the roster closure (step 1: templateer)

## The goal

Move every roster CLI in vendomat from nixpkgs-resolved dependencies to
uv2nix-resolved dependencies, so each tool is built against the exact versions its
own `uv.lock` pins. Start with templateer as a proving run.

**This session's scope is step 1 only: prove uv2nix builds templateer.** Do not
migrate the other four. Do not delete anything. The end state is all five on
uv2nix, but the decision to proceed comes after this prototype reports back.

## Why — the measured evidence

Today each CLI resolves its dependencies against nixpkgs through a hand-maintained
name → package table in `lib/mkPythonCli.nix`. That table ignores what the tool's
own lockfile says. The two already disagree:

| package | repoman's `uv.lock` | nixpkgs (what is actually on PATH) |
|---|---|---|
| **typer** | 0.21.1 | **0.24.0** |
| **rich** | 14.2.0 | **14.3.3** |
| pydantic | 2.12.5 | 2.12.5 |
| click | 8.3.1 | 8.3.1 |
| jinja2 | 3.1.6 | 3.1.6 |

The `repoman` in the shared closure is built against typer 0.24.0, three minor
versions ahead of the 0.21.1 its test suite ran against. Nobody chose that; it is
whatever nixpkgs carried on build day. So "repoman works" is currently **inferred**
from a test run against a different dependency tree than the one shipped. CONCEPT 03
§7 requires proving directly rather than inferring.

The second driver: when nixpkgs and a tool disagree by a major version, the current
design forces hand-pinning. That already happened. templateer needs
`pydantic-ai-slim>=2,<3`; this nixpkgs carries pydantic-ai 1.107.0. The result is
`pkgs/templateer-deps.nix` — 9 wheel pins with hand-transcribed filenames and
sha256s, derived one build error at a time. uv2nix would generate that from
`uv.lock` instead.

## Repo and current state

Primary repo: `/home/andrew/Documents/Projects/vendomat` (version 0.3.6, trunk
`main`, clean and in sync with origin).

```
flake.nix                    # inputs: nixpkgs + 6 first-party source inputs (flake = false)
lib/mkArtifact.nix
lib/mkMaturinWheel.nix
lib/mkPypiWheel.nix          # installs ONE published PyPI wheel; the hand-pin builder
lib/mkPythonCli.nix          # builds a CLI; holds the nixpkgs dep table
lib/mkToolchain.nix          # joins CLIs into one closure; fails on duplicate command names
pkgs/templateer-deps.nix     # the 9 hand pins, as a python package-set OVERLAY
modules/devenv.nix
tests/test_toolchain_nix.py  # grep-level + real `nix` guards on the above
```

The roster is five commands: `repoman` 0.7.5, `copyroom` 0.7.4, `docman` 0.2.0,
`gitman` 0.6.1, `templateer` 0.4.0. They compose into
`repoman-toolchain-core`, currently
`/nix/store/g497xl6ac4lwhiln0b0h6bqsmxkyxg4i-repoman-toolchain-core`.

`nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling"`. Python is 3.13 throughout.

### How templateer is built today

templateer cannot share `pkgs.python313`, so `flake.nix` gives it its own interpreter:

```nix
pythonTemplateer = pkgs.python313.override {
  self = pythonTemplateer;
  packageOverrides = import ./pkgs/templateer-deps.nix { ... };
};
mkTemplateerCli = import ./lib/mkPythonCli.nix { inherit pkgs; python = pythonTemplateer; };
```

This isolation is why templateer is the right prototype target: swapping how that one
interpreter's closure is produced touches no other tool. Verified — adding templateer
rebuilt nothing else.

## The blocker, and how small it actually is

uv2nix needs a `uv.lock` in the source it builds. Only repoman ships one in its
published tag. **But all four others have a `uv.lock` on disk — it is gitignored**,
at `.gitignore:12` in templateer_v2/copyroom/docman and `.gitignore:16` in gitman.

So unblocking templateer is: un-ignore `uv.lock`, commit it, cut a tag, bump the
vendomat input.

**Check first whether `.gitignore` is template-managed.** These repos carry the
`my-ai` copyroom layer (`copyroom layer list`). If the template owns `.gitignore`,
edit the template — otherwise the next `copyroom update` reverts all four.

## Do this

1. Confirm whether `.gitignore` is managed by the `my-ai` layer. Fix at the right
   level.
2. In `templateer_v2`: un-ignore `uv.lock`, commit it, cut a tag (0.4.1).
3. In vendomat: add the uv2nix inputs and build templateer's interpreter from
   `uv.lock` instead of `pkgs/templateer-deps.nix`. Put it behind a flag or a
   parallel attribute — **leave the existing pins in place and working** until the
   new path builds and runs.
4. Compare the two builds. Report what uv2nix resolves that the hand pins did not,
   and vice versa.
5. Report back with a recommendation before migrating anything else.

## Constraints and known traps

**The nixpkgs-follows trap.** Recorded in
`.scratch/projects/03-shared-repoman-toolchain/PROGRESS.md`: making the vendomat
input follow the system nixpkgs forked the closure in two — same source, same
version, different build. The whole design is one build shared everywhere. uv2nix
brings three new inputs (`pyproject-nix`, `uv2nix`, `pyproject-build-systems`), each
with `follows` wiring that can fork it the same way. The live test already guards
this: "vendomat's own flake resolves to the same store path".

**One interpreter version across the closure.** `lib/mkToolchain.nix` asserts a
single `pythonVersion` across all tools (CONCEPT 03 §8.3). The uv2nix-built
templateer must stay 3.13.

**Duplicate distributions.** A standalone pin produced two copies of `idna` and
`buildPythonPackage` refused the closure — which is why `pkgs/templateer-deps.nix`
is an overlay rather than a set of derivations. Expect the same class of failure
from a partial uv2nix integration.

**Expected uv2nix friction:** sdists needing build-system fixups that the lockfile
does not describe. This is the main thing the prototype exists to measure. If it is
worse than the 9 hand pins, that is a valid result — say so.

**Do not** delete `pkgs/templateer-deps.nix` or `lib/mkPypiWheel.nix` in this
session. `mkPypiWheel` is a general-purpose builder that may outlive the pins.

## Success criteria

- `nix build .#templateer` (uv2nix path) succeeds.
- `templateer --version` prints 0.4.0 from the built output.
- The resolved dependency versions match `uv.lock` exactly. Prove it by comparing,
  not by assuming.
- `nix build .#repoman-toolchain-core` still yields all five commands.
- Other roster tools do **not** rebuild.
- `tests/test_toolchain_nix.py` passes.

## Verification

Run tests through **testee** (`.claude/skills/testee`), not pytest directly.
Run all version control through **gitman** (`.claude/skills/gitman`), never raw
jj/git — and note this checkout has been found on a **detached HEAD** before, so
trust `gitman status` over `git log` for the true trunk.

The end-to-end check lives in the other repo:

```
cd ~/Documents/Projects/nix-meta && ./scripts/repoman-toolchain-test
```

14 checks against the real evaluated configuration and the real file a login shell
sources. It currently passes. If the closure hash moves, nix-meta's vendomat input
must be bumped and `sudo nixos-rebuild switch --flake .#server` re-run — **the user
runs that command, not the agent.**

## Deferred to later steps (do not do now)

- Migrating repoman, copyroom, docman, gitman.
- Deleting `pkgs/templateer-deps.nix` and the nixpkgs dep table in `mkPythonCli.nix`.
- Adding a test that asserts installed versions match each tool's lockfile — this is
  the check that stops the typer 0.21 vs 0.24 drift from recurring, and it is the
  most valuable long-term item. Design it, do not build it yet.

## Housekeeping

Progress notes go in `.scratch/projects/`. Note: `03-shared-repoman-toolchain/PROGRESS.md`
was once 235,087 lines — the same 53-line document appended 4,435 times by an unknown
writer. It was truncated on 2026-09-08 and the culprit was never found. If a PROGRESS
file grows into the thousands of lines, that bug is back.
