# vendomat

Vendomat composes one owner's machines and projects from native Nix, devenv, and NixOS
configuration. It writes a flake from a flat list of inputs. It keeps source clones. It does not
choose revisions: Nix resolves the graph and owns `flake.lock`.

## What it does

Vendomat tracks two things.

| | Source | Build outputs |
| --- | --- | --- |
| Held in | The source collection on `server`, at `/home/andrew/vendor/<repo>` | Attic |
| Filled by | The owner's CI, which pushes release tags | The builder, through `attic watch-store` |

A project lists its direct inputs in `vendomat.toml`. Every input names a tag.

```toml
[forge]
url = "git://server"

[inputs]
loci-nvim = { repo = "loci.nvim", ref = "refs/tags/v1.2.0" }
nvim-core = { ref = "refs/tags/v0.3.0" }

[passthrough]
nixpkgs = { url = "github:cachix/devenv-nixpkgs/rolling" }

[follows]
loci-nvim = ["nixpkgs"]
nvim-core = ["nixpkgs"]
```

`vendomat sync` writes `flake.nix` from this file. The generated flake hands the resolved inputs
to `flake-outputs.nix`, a file the project owns. A project that uses Vendomat needs no Vendomat
input: delete the command and the project still evaluates and builds.

## Commands

| Command | Does |
| --- | --- |
| `vendomat sync` | Write `flake.nix`. Clone and fetch `keep` entries. With `--collection` (on `server`), also copy `mirror` entries and check out each collection repository's newest tag. `--dry-run` changes nothing |
| `vendomat path <name>` | Print the store path of the locked source of a direct input. `--json` prints JSON |

Host settings (`set`, `get`, `unset`, `diff`, `apply`, `rollback`), `add`, `remove`, `status`,
`query`, and `explore` are specified and not built yet.

## Install

A host delta installs the command as `packages.<system>.vendomat`. The flake has no `default`
package and one input, `nixpkgs`. A project never declares Vendomat as an input.

## Source collection

`hooks/collection-post-receive` keeps the working tree of a collection repository at its newest
release tag. `scripts/collection-add` in `nix-meta` installs it with the tag-only `pre-receive`
rule.

## Authority

The specification, the concept, and the guide are in
[`.scratch/projects/14-vendomat-local/`](.scratch/projects/14-vendomat-local/). Start with
[`.scratch/CURRENT.md`](.scratch/CURRENT.md).

## Verify

```bash
devenv shell -- testee verify --mode quick
VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick   # also builds real consumers with Nix
```
