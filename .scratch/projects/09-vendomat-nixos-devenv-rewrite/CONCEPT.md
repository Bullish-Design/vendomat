# Project 09: Vendomat development system concept

**Status:** Proposed architecture for a greenfield rewrite.
**Decision:** [Vendomat architecture](../../../docs/CONCEPT.md).
**Scope:** Personal NixOS machines connected through the owner's tailnet.

## 1. Purpose

Vendomat helps one person build software in a repository and use it from another NixOS machine.
It also offers a path to shared development actions across the terminal, Atuin, and Neovim.

The foundation is a complete package path:

```text
source repository
    → pinned Nix package recipe
    → checked store output
    → tailnet binary cache
    → consumer's pinned flake input
    → another NixOS machine
```

The action path uses that foundation when it needs packaged tools:

```text
Neovim / Atuin / CLI
    → one action command
    → runtime context providers
    → one structured result
```

The package path works without an action system. The action path does not choose package versions.
This separation lets Vendomat serve its main purpose before it grows a richer interaction layer.

## 2. Design decisions

1. NixOS owns machine services, Nix settings, and durable service state.
2. A producer repository owns its package recipe and source history.
3. A consumer pins each producer as a flake input. The cache supplies bytes, not versions.
4. devenv owns repository tools, tasks, checks, and local services.
5. Vendomat supplies reusable NixOS and devenv modules, Nix helpers, and small commands.
6. Attic serves signed Nix outputs over the tailnet.
7. Publication is explicit. It runs required checks and reports the exact store path.
8. Runtime context stays outside the Nix store and records its source snapshot.
9. A general capability manifest or generator waits for evidence from working actions.

The rewrite does not preserve the old library's interfaces. It should keep native interfaces
usable directly, so a repository can build with Nix even when Vendomat tasks are unavailable.

## 3. Ownership and configuration

| Owner | Declares | Executes or stores |
| --- | --- | --- |
| NixOS machine configuration | Cache endpoint, trusted key, Attic service, installed tools, service credentials | Nix daemon, cache server, durable service state |
| Producer flake | Source inputs, package outputs, checks, optional NixOS modules | Nix builds and store outputs |
| Producer devenv files | Development tools, task imports, selected package output and cache target | Local tasks and services |
| Consumer flake | Producer revision and selected output | Package installation or further builds |
| Vendomat modules | Shared task and machine settings | Thin commands that call Nix and Attic |
| Runtime tools | Context requests and results | Working files, history, notes, and derived context |

One declaration owns each fact. The consumer's `flake.lock` pins a producer revision.
The producer's `flake.lock` pins its build inputs. Its `devenv.lock` pins development inputs.
Vendomat does not repeat those pins in a catalog or manifest.

The development lock may use a different tool revision from the package lock.
The package build must use the producer flake's inputs, so the task and direct Nix build agree.

## 4. Repository shape

A shareable repository may contain:

```text
project/
├── flake.nix          # public Nix outputs
├── flake.lock         # build input pins
├── devenv.nix         # local tools and task settings
├── devenv.yaml        # devenv inputs and imports
├── devenv.lock        # development input pins
├── nix/               # package recipes when needed
├── src/
└── notes/             # durable, human-authored context
```

Vendomat exposes reusable modules and commands from its own repository.
The producer imports the small Vendomat devenv module it needs.
That import must not merge Vendomat's own development environment into the producer.

A Nix package is an output that Nix can build and a consumer can select.
The name `Package` does not mean a generic action, script, or context provider.
Vendomat may offer recipe functions for recurring languages, but each producer owns its final output.

## 5. Package lifecycle

### Build locally

The producer declares a package output such as `packages.x86_64-linux.default`.
The direct interface is `nix build .#default`. A Vendomat task calls that same output.

```text
package:build
    → select the declared flake output
    → run the Nix build
    → report the store path and source identity
```

Local development may build source that differs from the published revision.
That output remains a local experiment.
Vendomat must not describe it as a shareable release.

### Check and publish

The producer publishes a source revision to the configured Git remote.
The cache task requires source content that matches the revision consumers can fetch.

```text
cache:push
    → resolve source revision and selected output
    → run required checks
    → build the output
    → upload its store path to Attic
    → report revision, system, store path, and cache destination
```

A check or upload failure returns failure. The task does not advance any consumer pin.
The cache may hold an output before a consumer selects it. That does not update the consumer.

### Consume elsewhere

A consumer pins the producer's source revision in its `flake.lock` and selects an output.
Nix computes the requested store path. It downloads the signed output if Attic holds it.
Otherwise, Nix may build it locally when source and dependencies are available.

Outputs for different system architectures have different identities and may need separate builds.
A signed cache response proves which cache supplied bytes. It does not prove an independent rebuild
would produce identical bytes. Package checks and reproducible recipes remain important.

Attic is a Nix binary cache. It does not serve source revisions or Python wheels to `uv`.
Projects that require another artifact format declare a separate distribution path for it.

## 6. Tailnet cache

One NixOS machine hosts Attic. NixOS declares its storage, service, tailnet endpoint, and backup policy.
Client machines declare the endpoint and trusted public key through Nix settings.
Only the cache host holds its signing key. Upload credentials remain outside the Nix store.

Tailnet access restricts network reachability. Signed outputs give Nix a separate authenticity check.
Write authorization stays separate from read access. Cache retention and local Nix garbage collection
have separate settings and tests.

The first version uses an explicit push task. Automation can call that task later.
The cache needs no global package registry because consumer locks already choose revisions.

## 7. Vendomat interface

The first Vendomat devenv module has a small task surface:

| Task | Contract |
| --- | --- |
| `package:build` | Build one selected flake output and report its store path. |
| `package:check` | Run declared Nix checks and return their status. |
| `cache:push` | Check, build, upload, and report one output. |
| `cache:status` | Report cache configuration and availability for one output. |

Repository settings select the output and cache target in `devenv.nix`.
There is no separate `vendomat.yaml` for the foundation.

Each task defines its working directory, inputs, output fields, and exit status.
Task code must not depend on implicit shell entry. A person or automation can invoke it directly.
Use a small script when a task needs shared parsing, validation, or error handling.
Keep package builds in Nix and cache storage in Attic.

## 8. Capability layer

The optional layer gives a stable identity to a human action across interfaces.
It uses these terms:

| Term | Meaning |
| --- | --- |
| Capability component | A command, context provider, or interface adapter. |
| Workflow | A human-facing composition, such as Review. |
| Action | One named operation with typed input and output, such as `code.review`. |
| Context bundle | Typed runtime data with source identity and freshness. |
| Surface | A CLI, Atuin skill, Neovim command, or another caller. |

The first proof is one `code.review` command. It accepts a defined target and returns
structured findings. An Atuin skill and Neovim command call the same executable.
They translate input and display results; they do not implement review logic.

Context providers read current source, diffs, history, and notes when the action runs.
They record which revision or working tree snapshot they read. Generated summaries also record
the facts that support them. Nix packages can supply provider tools, but current context is runtime data.

Start with hand-written adapters for this one action. If several working actions repeat the same
contracts and adapters, consider a small declaration and native configuration generator.
Do not create a general parser, resolver, or cross-surface registry to support the first action.

## 9. State and failure boundaries

Nix store outputs are immutable. Attic stores copies for distribution.
NixOS services keep their state in declared writable directories.
Repositories keep generated context in ignored local directories or identified user state paths.
Human-authored notes remain in Git.

A cache outage does not change source pins. A consumer builds locally if it has the needed inputs.
If it cannot build, it fails and reports the missing cache or source dependency.
A context provider failure does not corrupt the last complete context snapshot.
An interface adapter failure must not change the action's result format.

The initial system does not require automatic watchers, a central daemon, a context server,
an action registry, model prediction, or generated editor configuration.

## 10. Acceptance proof

The package foundation is proven when one real producer passes these checks:

1. Direct Nix build and Vendomat task select the same package output.
2. Required checks gate cache publication.
3. A second NixOS machine downloads the exact output from the tailnet cache.
4. The consumer's lock selects the source revision, independently of the cache.
5. Cache absence has an observed local-build or clear-failure result.

The capability layer is proven separately when two surfaces call one `code.review` command
and receive the same structured result for the same source snapshot.

## References

- [Nix flakes](https://nix.dev/concepts/flakes.html)
- [devenv tasks](https://devenv.sh/tasks/) and [polyrepo composition](https://devenv.sh/guides/polyrepo/)
- [Attic cache use](https://docs.attic.rs/user-guide/) and [Attic deployment on NixOS](https://docs.attic.rs/admin-guide/deployment/nixos.html)
- [Nix garbage collection](https://nix.dev/manual/nix/2.35/command-ref/nix-store/gc.html)
