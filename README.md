# vendomat

**Build your personal native (Rust/maturin/PyO3) libraries once; share the wheels across
every repo via the Nix store.**

Libraries like [pyjutsu](../Pyjutsu) and [tyo3](../tyo3) compile a Rust extension with
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
  /nix/store/…-pyjutsu-0.8.0/pyjutsu-0.8.0-cp313-abi3-linux_x86_64.whl
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

`pyproject.toml`: drop any `[tool.uv.sources]` path entry for the lib and depend on it by
version (`pyjutsu>=0.8`). The module sets:

- `UV_FIND_LINKS` → the store wheelhouse, so `uv sync` resolves the prebuilt wheel;
- `UV_NO_BUILD_PACKAGE` → the vendored libs, so a missing/mismatched wheel **fails loudly**
  instead of silently falling back to a from-source compile.

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

Proven end to end on the `pyjutsu → gitman` pair: vendomat builds the pyjutsu wheel once
(~6 min), gitman's `uv sync` installs it with zero compilation, and gitman's full suite
(60 tests) passes. Rebuilding the wheelhouse is a ~5s cache hit.
