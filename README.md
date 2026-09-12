# vendomat

**Vendor native artifacts, dependency knowledge, and the shared `*man` command toolchain
across every repo through Nix.**

Libraries like [pyjutsu](../pyjutsu) and [tyo3](../tyo3) compile a Rust extension with
maturin. When a consumer (e.g. [gitman](../gitman)) depends on one via an editable
`path:` source, **every `uv sync` in every repo recompiles it from scratch** — a multi-GB
`target/` and minutes of cargo per clone.

vendomat moves that single compile **up into Nix**: each lib is built once into a
content-addressed wheel in the `/nix/store`, and consumers install the prebuilt wheel
instead of building. The Nix store *is* the shared, build-once cache — no `~/.cache`
wheelhouse to manage by hand.

That wheel is the **published** artifact, not a second opinion about it. `mkMaturinWheel`
stamps a manylinux platform tag and strips the store `RUNPATH`, and `vendomat publish <lib>`
uploads that exact store file to the library's GitHub release. One build, one artifact, two
indexes — the store and the release URL — which therefore cannot disagree.

## What the wheelhouse is for

**Read this before enabling Face A.** The wheelhouse (`vendor.enable`) is an *accelerator*,
not a distribution channel:

- **A native library with no published release yet.** Nothing to point a URL at.
- **Local iteration ahead of a release.** Edit the lib, one `nix build`, every Nix consumer
  sees it without cutting a tag. This is the one thing a release URL cannot do, and it is
  why the store index earns its keep.

For every other case the consumer declares the release URL in `[tool.uv.sources]` and needs
no Nix, no vendomat, and no flake input. gitman project 35 settled that: a published,
hashed wheel referenced by URL is what makes a tool adoptable in a repo that has never heard
of Nix, and this repo does not replace it. **A repo that enables no face must not import the
module at all** — it pays a flake input's evaluation and an `install-hook` probe per shell
entry for no output.

One rule keeps the two indexes honest: **an iteration build gets its own version**
(`0.21.0.dev0+<rev>`), never the same version as a published release. One version, one
artifact. `vendomat publish` enforces both halves — it refuses to upload an iteration wheel,
and it refuses to give a published version a second set of bytes.

## How it works

```
  Pyjutsu (published git tag)
        │  mkMaturinWheel  (cargo + maturin, ONCE, in the Nix sandbox)
        ▼
  /nix/store/…-pyjutsu-0.20.0/pyjutsu-0.20.0-cp313-abi3-manylinux_2_39_x86_64.whl
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

Add a new native lib as a `flake = false` input with a published `git+https://` tag. The git
input copies tracked files only, so the lib's untracked `target/` is not copied into the store.
Then add one `mkArtifact { … }` entry and a line in the `wheelhouse` `symlinkJoin`.

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
  # noBuild = true;         # default false: let uv fall back to the declared release URL
  # sharedCargo = false;    # default true: sccache + shared CARGO_TARGET_DIR for repos that DO compile Rust
};
```

With RepoMan, use `source = "wheel:pyjutsu>=0.8"` for the `git-pyjutsu` pseudo-entry and
set `repoman.nativeBuild = false`. RepoMan resolves the source to the bare requirement passed
to uv. In a direct consumer `pyproject.toml`, drop any `[tool.uv.sources]` path entry for the
lib and depend on it by version (`pyjutsu>=0.8`). The module sets:

- `UV_FIND_LINKS` → the store wheelhouse, so `uv sync` resolves the prebuilt wheel. Because
  the store wheel and the release wheel are the same bytes, one `uv.lock` hash is valid
  through either route, and a store miss costs a download rather than a failure.
- `UV_NO_BUILD_PACKAGE` → **off by default** (`vendor.noBuild = true` to opt in). The store
  must not be able to fail a resolution the declared release URL can satisfy. Setting it by
  default is what took down loci-core's devenv shell (gitman project 32, G3). Falling back to
  the URL is not a silent fallback — the URL is the declaration.

## Publishing a wheel

```sh
vendomat publish pyjutsu --dry-run   # build .#pyjutsu-wheel, report the upload
vendomat publish pyjutsu             # upload that exact store file to the release
```

The release tag is derived from the wheel's own version (`v0.20.0`), so the tag and the wheel
name cannot disagree. The command refuses a wheel with a bare `linux_x86_64` tag, refuses an
iteration version, and refuses to attach different bytes to a version that is already
published.

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

Each successful publication records the published local commit in
`refs/vendomat/published/<remote>/<branch>`. The next push replays only the commits after that
marker onto the published history, so publishing is repeatable. If the branch is rewritten or
reset below the marker, Vendomat refuses the push and names the commit to rebase onto.

A push that cannot fire a Git hook (for example `gitman push`, which pushes with `--no-verify`)
can reach the same publisher through a pyjutsu hook. Add `<repo>/.pyjutsu-hooks.toml`:

```toml
[hooks.pre-push]
python = ["vendomat.publish:on_pre_push"]
```

The entry point resolves both commits from the repository itself, because pyjutsu hooks get no
standard input. A successful publication aborts the outer push, so the caller reports the push as
blocked; the `published GitHub-source commit(s)` message confirms the inner push succeeded.

For Python projects, the hook runs `uv lock` in the disposable worktree after replacing sources.
`uv.lock` must already be committed. Vendomat rejects the push if regeneration adds, removes, or
changes a resolved package version; review that graph change separately. Preview the exact public
manifest and lock diff with `vendomat publish --dry-run`.

See [`examples/publish-demo`](examples/publish-demo) for a self-contained Python/uv consumer and
an offline proof script.

## Sharing the RepoMan command toolchain

Face D builds the first-party command line tools once from their own `uv.lock` files. The
`repoman-toolchain-core` closure currently provides `repoman`, `copyroom`, `docman`, `gitman`,
and `templateer`. `testee` remains a consumer-local development dependency because it must test
the consumer's own Python environment.

Importing Vendomat enables the store toolchain by default:

```nix
vendor.toolchain = {
  enable = true;
  mode = "store";   # use "editable" in a tool's own repository
  roster = "core";
};
```

Store mode puts the selected commands on `PATH`, exports `REPOMAN_TOOLCHAIN_BIN`, and writes a
machine-readable provenance manifest. The Vendomat `flake.lock` is the toolchain source of
truth. Editable mode delivers no store package and tells RepoMan to use the working tree's
virtual environment. The module invokes selected commands through their absolute store paths,
so an unrelated executable in a consumer virtual environment cannot shadow them.

## Machine Devman plane

Vendomat also owns the machine-level Devman generation lifecycle. Devman owns
the manifest contract, policy resolution, and renderer. RepoMan owns migration
of one repository. Vendomat owns staging, Dagu validation, activation, retained
generations, and rollback.

Each participating repository carries `.devman/project.toml`:

```toml
schema = 1
project = "devman"
groups = ["base", "format", "release"]
policy = "stable"
```

The plane commands use the public Devman renderer. They do not run a
repository task or edit a tracked repository file:

```sh
vendomat plane plan devman --to v0.6.0
vendomat plane update devman --to v0.6.0
vendomat plane show devman
vendomat plane recover devman
vendomat plane rollback --to 1
```

For a first canary, pass the repositories explicitly. Repeat `--project-root`;
the command reads each repository's manifest and builds one generation for the
whole set:

```sh
vendomat plane update devman --to v0.6.0 \
  --project-root /path/to/devman \
  --project-root /path/to/repoman \
  --project-root /path/to/vendomat \
  --policy-root /path/to/devman
```

`plan` validates a candidate without activation. `update` writes one immutable
generation and swaps the `active` pointer only after every generated workflow
passes `dagu validate`. Failed renders keep the old pointer. An update first
inspects project identities. It renders changed projects and copies unchanged
valid projections into the new generation. A later update is a no-op when all
identities match. The `show` command reports the active registry path,
identities, and project records. `recover` preserves abandoned staging or
activation files for inspection. The machine-local state defaults to
`~/.local/state/vendomat/devman`; set `VENDOMAT_DEVMAN_POLICY_ROOT` or use
`~/.config/vendomat/plane.toml` for the central policy checkout.

The active generation is a complete Devman registry root. It contains
`projects/`, `dags/`, and `generation.json` under the stable `active` symlink.
The old compatibility registry remains separate during migration. A canary
machine can point its Dagu service and machine CLI at the active root:

```nix
services.devman-dagu.registryDir = "$HOME/.local/state/vendomat/devman/active";
services.devman-dagu.stateDir = "$HOME/.local/state/vendomat/devman/active";
```

Keep the consumer shell hook on the compatibility registry until the cutover.
The hook still uses `devman project apply`; it must not write into an immutable
active generation.

## Local input iteration

Committed flake inputs use published tags. To build against a sibling checkout, override the
input for that command:

```sh
nix build --override-input pyjutsu git+file:///path/to/pyjutsu .#pyjutsu-wheel
nix build --override-input repoman git+file:///path/to/repoman .#repoman
```

There is no `flake.local.nix`. Repeat the override for each local input that you are editing.
The `git+file:` form still copies tracked files only and keeps untracked build output out of
the store.

For local shellij work, create an ignored `devenv.local.yaml` with the local shellij URL. A
shell taken with that overlay active re-locks `devenv.lock` at the local path. Before committing,
restore the fleet lock with:

```sh
mv devenv.local.yaml /tmp/ && devenv update && mv /tmp/devenv.local.yaml .
```

## Constraints

- **abi3 / interpreter tag.** Wheels are built against `python313` (pyjutsu is
  `abi3-py313` → `cp313-abi3`). A consumer on a different Python must still satisfy the tag,
  or uv reports "no compatible wheel" (and `UV_NO_BUILD_PACKAGE` turns that into a hard error
  rather than a silent rebuild). Keep consumers on the matching interpreter floor.
- **Git deps in `Cargo.lock`.** `importCargoLock` needs `outputHashes` for any git
  dependency. pyjutsu and tyo3 are crates.io-only today, so this is a non-issue for now.
- **Published inputs.** Committed inputs use `git+https://` and `refs/tags/` pins. Use the
  local override above for iteration.

## Status

M0–M4 and Face D are complete. Vendomat now has three working faces:

- **Artifacts:** `mkArtifact` builds the CPython-3.13 abi3 Pyjutsu wheel; RepoMan's `wheel:`
  resolver installs it from Vendomat's wheelhouse with `repoman.nativeBuild = false`.
- **Knowledge:** `vendomat sync`, `vendomat add`, and `vendomat doctor` install usage-gated
  dependency skills, track their source pins, and warn when a consumer's resolved dependency
  version needs review. `vendor/constraints.txt` is the shared exact-pin source.
- **Toolchains:** `mkUv2nixCli` builds the five-command core closure from each tool's `uv.lock`;
  `mkToolchain` rejects command collisions, records provenance, and enforces one Python baseline.

The local consumer fixture passes with `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick`.
The full `nix-meta` server check also passes all 14 checks against the active login shell.
Remaining work is operational: keep those proofs repeatable, curate dependency skills only when
there is a real knowledge need, and defer extra builders, fleet orchestration, and vendored source
until real usage justifies them.
