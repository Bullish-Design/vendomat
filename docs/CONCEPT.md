# Vendomat: a NixOS and devenv development system

> Architecture concept, 2026-10-03. This describes a new system for personal NixOS machines.

## The idea

Vendomat makes a collection of personal repositories work together as one development system.
NixOS configures each machine. Each repository declares its own development environment and build outputs.
Vendomat supplies shared Nix modules, devenv tasks, and small commands that connect those parts.

The main workflow is:

```text
edit a repository
    ↓
devenv provides its tools and tasks
    ↓
Nix builds a package from pinned source
    ↓
Vendomat pushes the store output to a cache on the tailnet
    ↓
another NixOS machine selects that package and downloads the output
```

Vendomat is an orchestration layer, not a required background service or a second package manager.
Its interface is mostly Nix configuration and devenv tasks. Small scripts implement actions that configuration cannot perform alone.
Other applications remain welcome. NixOS or devenv installs, configures, and invokes them.

The system targets one person's NixOS machines. It does not need a public package registry or support for machines without Nix.
This is a new architecture. The existing vendomat implementation does not define its feature set.

## What each part owns

| Part | Responsibility |
| --- | --- |
| NixOS | Machine packages, Nix settings, services, tailnet access, cache client or server, and durable service state. |
| Nix | Package recipes, pinned inputs, build outputs, and store paths. |
| devenv | Repository tools, local services, tasks, checks, and reusable development configuration. |
| Vendomat | Shared modules and commands for common package, cache, and project workflows. |
| Git/Jujutsu | Source code, package revisions, and human-authored project history. |
| Atuin | Command recall, captured interactions, and reusable AI skills. |
| Neovim | Editing and a thin interface to repository commands. |
| Files/SQLite | Mutable local context when a repository needs it. |

NixOS declares what a machine can provide. A repository declares what it needs and what it builds.
Vendomat connects the declarations. A task performs an action only when the user or another caller requests it.

## Three configuration levels

### 1. Machine configuration

The NixOS configuration declares each machine's role. A workstation needs development tools and cache access.
A cache host also runs the cache service. A build host may accept remote Nix builds later.

Vendomat supplies a small NixOS module for common settings. It can configure the cache endpoint,
trusted signing key, required tools, and host role. It can import the cache service's own NixOS module.
It should expose existing NixOS options where possible instead of copying their full interfaces.

Tailnet routing limits access to the cache endpoint. The cache signs outputs, and NixOS trusts its public key.
Write access needs separate credentials. NixOS supplies credentials at runtime, outside the Nix store.
Tailnet policy and private credentials remain explicit inputs to the machine configuration.

### 2. Repository configuration

Every repository owns its source, build recipe, and development environment:

```text
my-library/
├── flake.nix        # package outputs for Nix consumers
├── flake.lock       # package input revisions
├── devenv.nix       # tools, local services, and tasks
├── devenv.yaml      # devenv inputs and shared imports
├── devenv.lock      # development input revisions
├── nix/             # package recipes when they need their own files
└── src/
```

The flake is the stable consumption interface for a shareable package. Its outputs may include
`packages`, `apps`, `checks`, or NixOS modules. A small project can keep its recipe in `flake.nix`.

devenv provides the working environment. A repository imports only the Vendomat features it uses.
It can define its own tasks without asking Vendomat to understand the project's language or layout.

The package recipe has one source of truth. A devenv task calls the Nix build for that recipe.
It does not recreate the recipe in shell code. The development lock can select tools independently
from the package lock. A consumer's `flake.lock` selects the package revision it will use.

### 3. Shared Vendomat configuration

Vendomat itself is a repository that exposes:

- a reusable devenv module with common tasks and tools;
- a NixOS module for cache clients and the cache host;
- small Nix functions for package patterns that recur;
- small scripts for build reports, cache publication, and diagnostics;
- examples that show how a library, application, and consumer use those interfaces.

Vendomat does not keep a second list of every repository or package version.
Each consumer names and pins the packages it uses. Each package repository owns its build recipe.

## Building and sharing a package

### Build

A project exposes a Nix package output. `nix build .#default` is the direct build interface.
The Vendomat task calls that same build and reports the resulting store path.

```text
devenv tasks run package:build
    → nix build the selected flake output
    → report its store path and source revision
```

The task supplies a consistent command name. Nix supplies the build graph and store output.
The task should not hide a second compiler path or write a package into a mutable shared directory.
Local builds may use working tree edits. Shared use also needs a committed source revision that
consumers can fetch. Publish that revision to its source remote before pushing its build output.

Vendomat can provide reusable recipes for recurring cases, such as a Rust program or Python package.
Projects can also use plain Nixpkgs functions or their own recipe. Reuse follows actual duplication.

### Cache

A cache host runs Attic on a NixOS machine and exposes it only through the tailnet.
NixOS configures its service, storage, endpoint, and signing key. Client machines declare the
cache URL and trusted public key through `nix.settings`.

After a successful build, an explicit task uploads the selected store output:

```text
devenv tasks run cache:push
    → reject uncommitted source changes
    → identify the source revision available from the source remote
    → run required checks and build the selected output
    → push that store path to Attic
    → report the package revision, store path, and cache destination
```

The first version uses an explicit push. A later automation may call the same task.
The cache keeps build outputs available to other machines according to its retention policy.
Local Nix garbage collection and cache retention are separate policies.

The cache stores Nix outputs. It is not a source repository, version catalog, Python package index,
or backup of mutable working state. A project that needs another distribution format can add one
without changing the Nix package path.
For example, a Python project that installs through `uv` needs a wheel source that `uv` understands.
An Attic cache alone cannot fill that role. Nix consumers use the Nix package output directly.

### Consume

A consumer pins a package repository as a Nix flake input and selects one of its outputs.
That consumer can be a NixOS configuration or another development repository.

```text
consumer's flake.lock → exact source revision and package recipe
consumer's package reference → selected output
tailnet cache → built bytes for the resulting store path
```

The flake input identifies *what* to build. The cache supplies *already built bytes* for that result.
The cache does not choose a package version. If the cache lacks an output, Nix can build it from
source when the source and build dependencies are available. If neither path works, the build fails.
Different machine architectures may need different outputs. The cache serves each output by its own store path.

This gives every NixOS machine the same way to consume a personal application or library.
A machine can install a command, run an application, or include a library in another Nix package.
It does not need a sibling checkout of the package repository.

## Repository task interface

Vendomat provides a small default task surface:

| Task | Result |
| --- | --- |
| `package:build` | Build one declared Nix output and report its path. |
| `package:check` | Run the repository's declared Nix checks. |
| `cache:push` | Upload the selected output after a successful build. |
| `cache:status` | Show the selected cache and whether it can serve the output. |
| `context:update` | Refresh local derived context, when enabled. |

A repository can add `test`, `lint`, or language-specific tasks. It can also replace a default task.
The package name and cache target are repository settings in `devenv.nix`, not a separate manifest.

Each shared task has a stated working directory, input, output, and exit status.
Tasks avoid hidden shell-entry requirements so humans, Atuin, Neovim, and agents can call them directly.
Required checks must pass before `cache:push` uploads an output. A failed upload does not change a consumer's pin.

For example, a library can declare its package and enable shared tasks:

```nix
# Illustrative Vendomat module interface, not final option syntax.
vendomat = {
  package = "default";
  cache = "personal";
};
```

The final module should stay small enough that a user can inspect the actual Nix build and cache command.

## Local context and interaction

The development system also helps a person and their agents find project information.
It does not require a context server or graph database.

Human-authored notes live in Markdown under Git. Generated indexes and summaries live in an ignored
project directory or a user state directory. A `context:update` task can combine source search,
Git/Jujutsu history, notes, and small extraction tools. It records which source revision or working
tree snapshot it read, so a caller can detect stale output. It replaces generated files atomically.

Atuin records shell history and supports AI skills and agent sessions when enabled.
Its skills call the same CLI tools and devenv tasks that a person uses. Captured command output is
optional and local, so it is useful context rather than the system's authoritative record.

Neovim stays thin. It starts tasks and shows their results through terminal buffers, quickfix lists,
and small Lua commands. It does not own build, cache, or context logic.

## Mutable state and parallel work

Nix defines programs and immutable build outputs. Runtime state stays in normal writable directories.
NixOS owns service state. A repository owns its ignored local state. Vendomat uses a user state
directory only for data shared across repositories, with a stable repository identifier in each path.

Small state starts as files. SQLite is available when several queries or updates need structured data.
The owner of a state directory defines its permissions, cleanup rule, and backup need.

Parallel agents use separate Jujutsu workspaces. Each agent gets a working directory and its own
project-local state path. Workspaces share repository history, so agents coordinate changes before
publication. Stronger process isolation can use NixOS tools when a concrete workflow needs it.

## Rules that keep the system simple

1. Put machine behavior in NixOS configuration.
2. Put shareable build outputs in Nix package recipes.
3. Put repository tools and actions in devenv.
4. Use Vendomat only for behavior repeated across repositories.
5. Keep a package revision in the consumer's lock file, not in a global registry.
6. Keep mutable state outside the Nix store.
7. Make publication explicit and report exactly what it published.
8. Let every interface call the same task or package output.

These rules allow scripts and other applications. They require NixOS or devenv to provide and
configure those applications. A script earns a place in Vendomat when several repositories need
the same behavior or when one action has failure rules that a task definition cannot express clearly.

## What this concept leaves for later

The first system does not need automatic watchers, a fleet scheduler, a dedicated context service,
a sandbox manager, a graph database, embeddings, or prompt optimization. It also does not need a
public package index. Those features can be added behind the existing package and task interfaces.

## A complete example

Suppose `project-a` is a personal application and `project-b` uses it on another NixOS machine.

1. `project-a` declares `packages.x86_64-linux.default` in its flake.
2. Its devenv configuration imports Vendomat's tasks and selects the `default` package.
3. The developer commits and publishes the source revision to its Git remote.
4. The developer runs `devenv tasks run package:check` and `devenv tasks run cache:push`.
5. The push task builds the flake output and uploads its store path to the tailnet cache.
6. `project-b` pins `project-a` in its flake lock and selects that package output.
7. Nix downloads the signed output from the cache when that exact output is available.

Changing `project-a` does not silently change `project-b`. Updating `project-b`'s flake lock selects
the new revision. A cache hit saves build time but does not change that selection.

This is the intended shape of Vendomat: declarative machines and packages, repository-owned devenv
workflows, and a small shared layer that makes building and sharing personal software routine.

## Technical basis

- [Nix flakes and outputs](https://nix.dev/concepts/flakes.html)
- [devenv tasks](https://devenv.sh/tasks/) and [devenv polyrepo composition](https://devenv.sh/guides/polyrepo/)
- [Attic cache use](https://docs.attic.rs/user-guide/) and [Attic on NixOS](https://docs.attic.rs/admin-guide/deployment/nixos.html)
- [Nix garbage collection](https://nix.dev/manual/nix/2.35/command-ref/nix-store/gc.html)
