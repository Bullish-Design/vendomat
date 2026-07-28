# vendomat

**Build your personal native (Rust/maturin/PyO3) libraries once; share the wheels across
every repo via the Nix store.**

Libraries like [pyjutsu](../pyjutsu) and [tyo3](../tyo3) compile a Rust extension with
maturin. When a consumer (e.g. [gitman](../gitman)) depends on one via an editable
`path:` source, **every `uv sync` in every repo recompiles it from scratch** — a multi-GB
`target/` and minutes of cargo per clone.

vendomat moves that single compile **up into Nix**: each lib is built once into a
content-addressed wheel in the `/nix/store`, and consumers install the prebuilt wheel
instead of building. The Nix store *is* the shared, build-once cache — no `~/.cache`
wheelhouse to manage by hand.

## How it works

```
  Pyjutsu (git+file source)
        │  mkMaturinWheel  (cargo + maturin, ONCE, in the Nix sandbox)
        ▼
  /nix/store/…-pyjutsu-0.10.1/pyjutsu-0.10.1-cp313-abi3-linux_x86_64.whl
        │  symlinkJoin
        ▼
  packages.wheelhouse  ──► env.UV_FIND_LINKS in every consumer
        ├──────────────┬──────────────┐
        ▼              ▼              ▼
     gitman          repo B          repo C
   uv sync finds the wheel by tag (cp313-abi3) and installs it. Zero cargo.
```

Because the wheel is a content-addressed derivation, the *first* repo that needs it builds
it; every other repo with the same input revision gets the identical store path for free.
Editing a lib (its source is a `git+file` input) triggers exactly one rebuild, then it's
shared again.

## Layout

```
flake.nix              inputs (nixpkgs + each native lib) and outputs:
                         lib.mkMaturinWheel · packages.<lib>-wheel · packages.wheelhouse
                         · devenvModules.default
lib/mkMaturinWheel.nix  source crate → wheel derivation (importCargoLock + maturin build)
modules/devenv.nix      the devenv module consumers import
```

## Producing wheels

```sh
nix build .#wheelhouse        # build every vendored lib's wheel (cached after first time)
nix build .#pyjutsu-wheel     # just one
ls result/                    # the .whl(s)
```

Add a new native lib: add it as a `flake = false` input (use `git+file://` so the lib's
untracked `target/` is *not* copied into the store), then one `mkWheel { … }` + a line in
the `wheelhouse` `symlinkJoin`.

## Consuming wheels (any devenv repo)

`devenv.yaml`:

```yaml
inputs:
  vendomat:
    url: path:/home/andrew/Documents/Projects/vendomat   # a real flake input
imports:
  - vendomat/modules     # devenv loads modules/devenv.nix from the flake source
```

`devenv.nix`:

```nix
vendor = {
  enable = true;
  libs   = [ "pyjutsu" ];   # install-only; never compiled here
  # self = "pyjutsu";       # set in a lib's OWN repo so it isn't vendored over its editable build
  # sharedCargo = false;    # default true: sccache + shared CARGO_TARGET_DIR for repos that DO compile Rust
};
```

With RepoMan, use `source = "wheel:pyjutsu>=0.8"` for the `git-pyjutsu` pseudo-entry and
set `repoman.nativeBuild = false`. RepoMan resolves the source to the bare requirement passed
to uv. In a direct consumer `pyproject.toml`, drop any `[tool.uv.sources]` path entry for the
lib and depend on it by version (`pyjutsu>=0.8`). The module sets:

- `UV_FIND_LINKS` → the store wheelhouse, so `uv sync` resolves the prebuilt wheel;
- `UV_NO_BUILD_PACKAGE` → the vendored libs, so a missing/mismatched wheel **fails loudly**
  instead of silently falling back to a from-source compile.

## Local vendoring and GitHub publishing

For ordinary Python dependencies, a consumer can keep its editable local sources while it is
being developed, then let Vendomat publish a GitHub-source-only version of every outgoing commit.
Add a `vendomat.toml` at the consumer repo root:

```toml
[[replacement]]
files = ["repoman.lock"]
local = "path:vendor/pyjutsu"
github = "git+https://github.com/Bullish-Design/pyjutsu.git@v0.10.1"
```

Each mapping is an exact, explicit text replacement, and only the listed repo-relative files may
be changed. This works for `repoman.lock`, `pyproject.toml`, or any other text manifest without
forcing Vendomat to reformat it. The GitHub spelling must be pinned to a tag or commit.

When a repo imports Vendomat's devenv module (`vendor.publish.enable` defaults to `true`), Vendomat
installs a non-clobbering `pre-push` hook on shell entry when `vendomat.toml` is present.
For each branch push, it creates a disposable worktree, rewrites every commit being pushed to the
GitHub spellings, pushes those rewritten commits, then aborts the original push so local-path
commits cannot follow. Your current branch and working tree remain in their local-vendor form.
Git prints a nonzero status after the hook deliberately aborts the outer push; the preceding
`published GitHub-source commit(s)` message confirms the inner, clean push succeeded. Repositories
with an existing pre-push hook are left untouched and must compose that hook explicitly.

For Python projects, the hook runs `uv lock` in the disposable worktree after replacing sources.
`uv.lock` must already be committed. Vendomat rejects the push if regeneration adds, removes, or
changes a resolved package version; review that graph change separately. Preview the exact public
manifest and lock diff with `vendomat publish --dry-run`.

See [`examples/publish-demo`](examples/publish-demo) for a self-contained Python/uv consumer and
an offline proof script.

## Constraints

- **abi3 / interpreter tag.** Wheels are built against `python313` (pyjutsu is
  `abi3-py313` → `cp313-abi3`). A consumer on a different Python must still satisfy the tag,
  or uv reports "no compatible wheel" (and `UV_NO_BUILD_PACKAGE` turns that into a hard error
  rather than a silent rebuild). Keep consumers on the matching interpreter floor.
- **Git deps in `Cargo.lock`.** `importCargoLock` needs `outputHashes` for any git
  dependency. pyjutsu and tyo3 are crates.io-only today, so this is a non-issue for now.
- **Per-machine paths.** Inputs point at local checkouts under `~/Documents/Projects`
  (the repoman `repoman_dev_root` convention). Override on another machine with
  `--override-input pyjutsu git+file:///path/to/Pyjutsu`.

## Status

M0–M4 are complete. Vendomat now has two working faces:

- **Artifacts:** `mkArtifact` builds the CPython-3.13 abi3 Pyjutsu wheel; RepoMan's `wheel:`
  resolver installs it from Vendomat's wheelhouse with `repoman.nativeBuild = false`.
- **Knowledge:** `vendomat sync`, `vendomat add`, and `vendomat doctor` install usage-gated
  dependency skills, track their source pins, and warn when a consumer's resolved dependency
  version needs review. `vendor/constraints.txt` is the shared exact-pin source.

The full RepoMan consumer fixture has been verified end to end: its devenv evaluation exports
`UV_FIND_LINKS` and `UV_NO_BUILD_PACKAGE=pyjutsu`; `repoman-sync` installs
`pyjutsu-0.10.1-cp313-abi3-linux_x86_64.whl`; the consumer imports Pyjutsu; and neither Cargo
nor maturin is contributed by the consumer shell. Remaining work is operational: keep the
cross-repository proof repeatable, curate additional dependency skills only where useful, and
defer extra builders or vendored source until real usage justifies them.
