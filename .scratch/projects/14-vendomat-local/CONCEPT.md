> **Superseded by [CONCEPT-V5.md](./CONCEPT-V5.md).** This draft put the dependency graph in the consumer file and had no system-configuration tier.

# Vendomat concept — system-local inputs

**Date:** 2026-10-07. **Status:** Proposed. **Supersedes:** the V4 concept and its phase programme.
**Preserves:** `NATIVE-BASELINE.md` as observed fact.

## Purpose

One owner builds many small projects that depend on each other. Vendomat makes those dependencies
**resolvable by local path** and **already built**.

It is the system-local equivalent of a `devenv.yaml` `inputs:` section: the same mechanism, pointed
at this machine instead of a forge.

## The claim

Add Vendomat to a project. Enter the shell. The owner's libraries are present, built, and selected
by the project's own lock. No manual build. No forge round trip.

## Four parts

| Part | What it is | Where it runs |
| --- | --- | --- |
| Cache | One Attic cache, private, over Tailscale | `server`, storage on the 4TB NVMe |
| Source store | Git clones of the owner's and third-party repos | `~/vendor/<name>` |
| Consumer module | A devenv module other projects import | Every project |
| Builder | A timer that builds new revisions | `server` |

## How a consumer uses it

A consumer declares Vendomat the way it declares any input, with a local flake reference:

```yaml
inputs:
  vendomat:
    url: "git+file:///home/andrew/vendor/vendomat?rev=<rev>"
imports:
  - vendomat/modules
```

`git+file://` with `?rev=` locks a real `rev` and `narHash`. Observed on Nix 2.34.7, 2026-10-07.
Pin by `rev`, not by `ref`: these checkouts are jj-colocated, so git `HEAD` is often detached.

The module supplies the cache as a substituter, its trusted public key, and the credential path.
Nothing else is required of the consumer.

## Two derived directories

- `~/vendor/<name>` — the source store. A cache of git remotes. Regenerable by `sync`.
- `<repo>/.vend/<name>` — per-repo out-links, created by `nix build --out-link`.

Both are **derived, never inputs.** `devenv.lock` is the only selection authority. `.vend/` is
gitignored and deletable at any time.

`nix build --out-link` creates an indirect garbage-collection root. So `.vend/` gives a stable path
for tools and retention at the same time, with no Vendomat code. `ls -l .vend/` is the effective
selection report.

## Publication is ambient

There is no `publish` operation and no `retain` operation.

The builder runs `nix build` on new revisions. `attic watch-store` on the builder pushes whatever
appears in the store. Every other machine substitutes on demand. Nothing is pushed by hand.

The build log and its exit status are the durable record of what was checked against which bytes.
CI supplies that for free, so Vendomat writes no receipt.

Every consumer target is `x86_64-linux`, and the builder is `x86_64-linux`. One build serves every
machine. No matrix, no cross-compilation, no remote builders.

The source store is also the build queue. One list, two uses.

## The command line

Four commands. Each one reports; none selects.

| Command | Result |
| --- | --- |
| `sync` | Clone or fetch each repo in the store |
| `query` | Each repo, its revision, and whether its build is in the cache |
| `path <name>` | Resolve a name to a path |
| `explore <name>` | Open the dedicated editor at that repo's root |

`explore` is `cd "$(vendomat path <name>)" && exec nvim-review-editor`. The dedicated editor is an
existing output of `nvim-review`: `wrapNeovimUnstable` with `wrapRc = true`, so it cannot disturb
the owner's normal profile. Its configuration is one Nix string.

## Authority

Native declarations and locks select. devenv composes. Nix builds and substitutes. Attic stores and
signs. NixOS and Home Manager activate. Version control keeps history.

Vendomat maintains clones and out-links, and reports what it finds.

**Vendomat owns no durable state.** The cache belongs to Attic. The store is a cache of remotes.
`.vend/` is derived. The build record belongs to CI. Every class is native-owned or regenerable.

## Boundaries

Vendomat is not a dependency resolver, a second lock, a registry, an index, a daemon, a deployment
engine, a retention engine, a cache protocol, or an audit system. It makes no machine claim.

## Observed facts this design depends on

Each one was observed on the pinned tools. They are the reason the design is shaped this way.

1. `attic push` drops paths that came from an upstream cache unless the upstream filter is cleared.
2. The Nixpkgs and Home Manager Neovim wrappers default to `--suffix PATH`, so a command must be
   reached by absolute store path.
3. devenv merges an imported `devenv.yaml` only for local paths inside the git root. Remote inputs
   are not merged.
4. The flake delivery form evaluates impurely by default.
5. `git+file://…?rev=` locks a real revision and NAR hash.

## Done looks like

From a project that has never used Vendomat: add the input, enter the shell, and use one of the
owner's libraries with no local build. Then run `vendomat explore <name>` and land in the editor at
that repo's root.

That is the whole acceptance test. It runs on one machine in one afternoon.

## Open items

| Item | State |
| --- | --- |
| `sudo` on `server` | Broken: not setuid root. Blocks every root action |
| Attic storage move | Needs `nvme0n1` partitioned and its UUID, then a 5-point edit in `nix-meta/machines/server.nix` |
| Consumer trust | The substituter and `trusted-users` are still unset in the system config (`BLK-P5-06`) |
| Cache growth | Retention is 0 and eager builds accumulate. Decide a garbage-collection policy before the disk fills |
| Editor configuration | `nvim-review`'s baked rc is two lines. An exploring editor needs more in it |

## Naming

`~/vendor/` is the source store. `.vend/` holds derived out-links. These are two different things,
so they keep two names. `~/vendor/` is unchanged from the current default, so no migration is due.
