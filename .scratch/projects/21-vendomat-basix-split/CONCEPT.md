# Project 21: Vendomat and Basix, separated

**Final design, 2026-10-13.** The owner asked on 2026-10-12 for a clean-slate review of the project
20 design and for Basix in its own repository. The input was the owner's proposal
([INPUT](evidence/INPUT-separated-concepts-proposal.md)). The owner's rulings R1 to R34 are in
[DECISIONS.md](DECISIONS.md). The [requirement ledger](REQUIREMENTS.md) holds the requirements, and
the [plan](PLAN.md) holds the spikes (W1 to W10) and the implementation slices (S1 to S7). Fixtures
back the parser and the machine facts at prototype level only. No production code, consumer, or
machine changed. Where this document and project 20
disagree, this document states the future design. Project 20 stays the record of what slice 1
built. Each new option name, command, and file format here stays proposed until a fixture proves it
on the pinned tools.

## Goal

One person owns a few computers and many projects. They say in plain words what each one should
have, and they get exactly that. They can undo a change, share builds between their machines, and
learn what a computer does. Nix is the engine. It stays out of sight until the user wants it.

## Two products

| | Vendomat | Basix |
| --- | --- | --- |
| What | The tool: a front door to pinned devenv, Nix, and NixOS | A distribution built with Vendomat |
| User sees | The `vendomat` command and `vendomat.yaml` | The Basix ISO, profiles, capabilities, and lessons |
| Repository | `vendomat` | `basix` (`../basix`, since 2026-10-13) |
| Owns | The YAML reader, the catalog, workspace and machine operations, store sharing | The minimal core, the ISO, the install flow, profiles, capabilities, the curriculum |

The dependency goes one way: Basix depends on Vendomat. Vendomat has no Basix import, condition,
or test. Two names stay (owner ruling). A Basix lesson can teach the layering itself: a distribution
is built with a management tool. The Basix design moved to the Basix repository on 2026-10-13; its
concept is `../basix/.scratch/projects/001-initial-concept/CONCEPT.md`. This document keeps what Vendomat owns and what Vendomat must honour for Basix.

**Ruled (R28):** a Basix workspace gets `vendomat` and `nixpkgs` through the `basix`
input. One update then moves a pair that Basix tested, and no compatibility matrix is needed. W3
([W3-TOPOLOGY](evidence/W3-TOPOLOGY.md)) proved this with stub repositories on stock devenv, with
one change. Stock devenv ignores the `devenv.yaml` inside an imported input, so naming only `basix`
fails. Basix is therefore a flake that lists its inputs and commits its `flake.lock`, and the
template writes one `follows` line per input it takes from Basix. `vendomat update` keeps the lines
current (R25):

```yaml
inputs:
  basix:
    url: git+<basix-url>
  vendomat:
    follows: basix/vendomat
  nixpkgs:
    follows: basix/nixpkgs
imports:
  - basix
```

The `devenv` module input and the language inputs follow the same way. The user does not edit these
lines. Vendomat gets no built-in input and does not ride inside the `devenv` input. **Ruled (R33):**
a workspace that builds with `vendomat.yaml` pins Vendomat in its own `devenv.lock`, and the
personal tools of project 22 never enter a workspace lock.

## The user file

`vendomat.yaml` is the primary interface. The user edits it for routine work.

### Grammar

The file holds maps, lists, and text (R2). Lists may hold maps and other lists (R8). Every value is text;
the catalog's option types give each value its meaning. `true`, `3.10`, `no`, `null`, and `~` stay
text, so the file has no null.

Indentation may use spaces or tabs (R9). The parser compares indentation as text, with no tab width:

- A child line's indentation starts with its parent's indentation and is longer.
- Sibling lines have identical indentation.
- A dedent returns to an open level.
- After a compact item (`- key: value` or `- - x`), the next line fixes the item's form: the item
  indentation plus two spaces, or the item indentation plus one tab. Later lines of the item use the
  same form.
- A mix fails with `inconsistent tabs and spaces` at the line and column.
- `key: - x` is rejected (R10).

A file with tab indentation is not standard YAML. Other YAML tools may reject it.

These YAML features are not allowed:

| Not allowed | Example | Write this instead |
| --- | --- | --- |
| Anchors, aliases, merge keys | `&base`, `*base`, `<<: *base` | repeat the value |
| Tags | `!!int 5` | nothing; the catalog types the value |
| Flow style | `[a, b]`, `{a: 1}` | block lists and maps |
| Block scalars and multi-line plain text | `\|`, `>` | one quoted line with `\n` |
| Document markers, several documents | `---`, `...` | one document per file |
| Empty values (except a machine entry, R51) | `key:` | `key: ""` |
| Duplicate keys | `a:` twice in one map | one key |
| A colon-space in plain text | `note: a: b` | `note: "a: b"` |
| A list on the key's line | `programs: - ripgrep` | start the list on the next line |
| Special first characters | a value that starts with `@` or `` ` `` | quote it |
| Escapes other than `\"` `\\` `\n` `\t` | `"A"` | the character itself |
| Plain keys that start with a digit or hold a space | `3d: x` | quote the key |
| A byte order mark | | UTF-8 without a BOM |

One empty value is allowed: a machine entry with no value (`laptop:`) is an empty map, so the machine
takes every default (R51, `VMT-170`). Every other key with no value fails.

Errors read `vendomat.yaml:LINE:COL: reason`. Two gaps remain: a file nested about 800 levels deep
fails with a Nix error that does not name the file (`VMT-013`), and a fault of a schema-checked
field names the key path but has no line (`VMT-035`).

### Reader

A parser written in plain Nix (builtins only) lives in the Vendomat source (R7). The catalog module reads
the file with `builtins.readFile` and parses it with that function. The workspace lock pins the
parser, so any devenv of the pinned version reads the workspace. No devenv primop and no unsafe Nix
setting is needed. Evidence: [YAML-SPIKE-1](evidence/YAML-SPIKE-1.md) and
[YAML-SPIKE-2](evidence/YAML-SPIKE-2.md).

### Catalog

The catalog module parses the file once, checks every field, and maps the typed values to native
options. Routine use needs no Nix file (R6). It reports every bad field in one error before any command does work (carried from project
20). Where a native option exists, the catalog uses the native name. The catalog adds checks and
Vendomat defaults, and nothing else. Defaults use `lib.mkDefault`; YAML values stay plain
definitions (R23). Typed keys include `services.postgres` and `services.redis` (R23).

**Languages** use devenv's standard language modules (R11). The YAML `languages` section mirrors
devenv's `languages.*` options. Python uses uv by default:

```yaml
languages:
  python:
    version: "3.12"
```

maps to `languages.python.enable`, `languages.python.version`, `languages.python.uv.enable`, and,
when `pyproject.toml` exists, `languages.python.uv.sync.enable`. The keys `uv` and `uv.sync` mirror
the native names. `uv.sync` takes `auto` (the default), `true`, or `false`, and `auto` turns sync on
only when `pyproject.toml` exists (R20). devenv then keeps the virtual
environment in `.devenv/state/venv` and stops uv from downloading its own Python. devenv's
language modules look up inputs such as `nixpkgs-python` and `rust-overlay` in the workspace. The
template therefore lists those inputs, each following `nixpkgs`. This is how standard devenv
expects them, and it removes the need for fork patch 0007.

## The escape hatch

Native devenv files stay available for settings that YAML cannot express:

| File | Purpose | Committed |
| --- | --- | --- |
| `vendomat.yaml` | Routine settings, the primary interface | yes |
| `devenv.nix` | Advanced settings for everyone who uses the workspace | yes |
| `devenv.local.nix` | Personal settings for this checkout | no |
| `devenv.yaml` | Extra inputs and imports; Vendomat checks its own lines | yes |
| `devenv.local.yaml` | Local input overrides | no |

Rules:

- **One value, one place.** YAML values are plain definitions. Lists and maps merge with Nix
  definitions. A scalar set in both places stops with a conflict error that names both files.
  `lib.mkForce` in Nix overrides on purpose. YAML values never get a lower priority, because Nix
  would then win silently.
- **Errors name the YAML file.** The catalog puts its mappings in an inner module with
  `_file = "vendomat.yaml"` (R19).
- **The hatch stays visible.** Shell entry prints one line when a hatch file has content, for
  example `advanced: devenv.nix sets 4 options; devenv.local.nix active (this checkout only)`.
  `vendomat explain` shows each option's value and the file that set it. A personal setting (not a
`vendomat.yaml` key) hides the shell line, and `explain` still shows every source (R19). `explain`
prints the user's YAML keys, each with its native option, value, and source file, then a section for
options set only in Nix; `--json` prints the same data (R27). The output format is unproved.
- **Promotion.** A pattern that many users write in Nix becomes a catalog key or a Basix capability.

No `eject` command exists until a clear need appears (R5). A read-only `explain` is the window into
Nix.

**Ruled (R26):** Basix uses a soft lock on the hatch. It is a Basix decision. Vendomat supplies the
shell line and `explain`. How the Basix hint reaches that line is open (decision D5 chose a second
file, R38). See `../basix/.scratch/projects/001-initial-concept/CONCEPT.md`.

## Machines

Machines use devenv Machines on a pinned devenv (R4). Evidence:
[MACHINES-RESEARCH](evidence/MACHINES-RESEARCH.md) and, for the fixtures below,
[W2-MACHINES](evidence/W2-MACHINES.md). On 2026-10-13 all four W2 fixtures passed in VMs on stock
devenv 2.4.0: the `deferredModule` merge, local apply with a boot-menu rollback, ISO and VM builds
through `_nixosEval`, and the local install from the ISO. No real disk was used.

W2 findings that shape the design:

- The facts file names `networking.hostName`, not the devenv machine name. The catalog sets
  `networking.hostName` to the machine name, so a bare `vendomat apply` can find itself (R21).
- A boot-menu rollback boots the earlier generation once. The `system` profile still points at the
  newer generation, so the next normal boot returns to it. A lasting rollback is: restore
  `vendomat.yaml` and `devenv.lock` from version control, then `vendomat apply`. **Ruled (R30):**
  `vendomat rollback` restores `vendomat.yaml`, `devenv.lock`, and the hatch files from an earlier
  commit, ends in a new commit, refuses uncommitted changes, and then applies. Each machine keeps a
  small record from each system path to the workspace commit it came from.
  `system.configurationRevision` is not used ([W9-ROLLBACK](evidence/W9-ROLLBACK.md)). The record
  format is unproved. The boot menu and the profile rollback stay recovery tools.
- devenv's hardware module needs `.machines/NAME/facter.json`. The ISO and test VMs set
  `hardware.facter = null`; an installed machine uses its real report. The catalog reads an explicit
  `virtual: "true"` machine key for this (R23). The test-VM hardware reports and the `install`
  filter (R32; [W10-FACTER](evidence/W10-FACTER.md)) belong to Basix: see `../basix/.scratch/projects/001-initial-concept/CONCEPT.md`.
- The prebuilt install (the ISO carries the toplevel and disk script) worked with no network in a
  4 GB guest and needs no devenv at install time. Building on the ISO needed network,
  `NIX_REMOTE=daemon`, and about 8 GB of RAM. The prebuilt install is the release path (R18). A distribution ISO carries the prebuilt closure; the Basix ISO is described in the Basix concept.

devenv builds a machine locally with no target: `devenv build machines.NAME.build.nixos`. Every
activation step (install, deploy, rollback) runs over root SSH, and `localhost` still means SSH.
Vendomat adds the local path.

- **`vendomat apply`.** A bare `vendomat apply` reads the machine name from
  `/etc/devenv/machine-facts.json`, which devenv writes on every machine. It builds the toplevel,
  then runs `nix-env --profile /nix/var/nix/profiles/system --set TOP` and
  `TOP/bin/switch-to-configuration switch`, as devenv's own deploy worker does (R13, R15). `vendomat apply NAME`
  for another machine passes through to `devenv machines deploy NAME`. Later, running devenv's
  deployer locally can add its watchdog and automatic rollback.
- **Install from the Basix ISO.** Basix owns `install` and the disk guard (R13). It runs the six local
  steps that devenv runs over SSH, from the ISO's prebuilt toplevel and disk script, so the install
  needs no network and no devenv. The steps, the guard, and the W2 results are in `../basix/.scratch/projects/001-initial-concept/CONCEPT.md`.
- **Remote install and deploy** stay native devenv Machines behaviour, the advanced door. The
  Basix disk layout carries the blank-disk guard as a disko `preCreateHook`, with `destroy = false`,
  so the local and the remote install both run it before any write
  (R16; [W5-DISK-GUARD](evidence/W5-DISK-GUARD.md); layout and gaps in `../basix/.scratch/projects/001-initial-concept/CONCEPT.md`). This replaces fork
  patch 0006. It does not replace
  0005: stock `machines install` kexecs the target before disko, so a mistaken remote install
  stops a running machine, although its disk stays safe.
- **One NixOS value, several writers.** `machines.NAME.nixos` has the type `unspecified`. Two
  definitions merge shallowly and lose settings, or fail
  ([NIXOS-MERGE](evidence/NIXOS-MERGE.md)). With the escape hatch, the YAML, Basix, and the user may
  all write it. The fix is a one-line devenv patch that gives `nixos` (and `home-manager` and
  `nix-darwin`) the type `deferredModule`. W2 proved it on stock devenv through a patched `devenv`
  input. It lives in the module-only fork (R14); no upstream pull request is opened (R34).
- **ISO and VM builds.** `machines.NAME._nixosEval` is a readable internal option with the full
  NixOS evaluation. A module can expose `system.build.isoImage` and `system.build.vm` from it. A
  distribution ISO can then be a machine in the distribution's repository, and every machine gets a test VM. W2
  built and booted both (`outputs.iso` and `outputs.vm`). The module-only fork makes them public
  options, `machines.NAME.build.vm` and `machines.NAME.build.iso`, typed `nullOr package` so a plain
  `devenv build` does not build images ([W7-BUILD-OPTIONS](evidence/W7-BUILD-OPTIONS.md)). Any
  machine can build an ISO of itself (R17): `build.iso` extends the machine's evaluation with the NixOS ISO
  module and six required overrides, and applies the modules in `machines.NAME.iso.modules`. A machine
  that imports its own ISO module keeps its own image. Policy, such as `enableAllHardware` or turning
  off services in the live session, goes in `iso.modules`
  ([W8-ISO-POLICY](evidence/W8-ISO-POLICY.md)). A module that changes an option which `build.iso`
  overrides needs `lib.mkForce`. The Basix live-ISO deny list (R29) is in `../basix/.scratch/projects/001-initial-concept/CONCEPT.md`.
- **The YAML machine table.** Vendomat maps `host` to `target.host`, and `serve` to its sharing module
  (see Sharing below; R39 makes `serve` a Vendomat key, `VMT-128`). The keys `profile`,
  `capabilities`, and `disk` belong to Basix. Basix keeps them in a second file,
  `basix.yaml` (R38; `BSX-124` replaces `BSX-065`), and reads it with this parser (see `../basix/.scratch/projects/001-initial-concept/CONCEPT.md`).
- **Sharing** is Vendomat's NixOS module per machine (R39). Every installed machine runs Harmonia
  from first boot and makes its own signing key then; the machine key `serve: false` turns it off.
  Clients get the substituter, the key, `fallback = true`, and a short timeout (carried from
  project 20). The new system configures no Attic. devenv's `--use-machines-as-builders` gives
  shared builds over SSH.

**Ruled (R13):** Basix owns `install` and the disk guard, and Vendomat owns `apply`.

## The fork

The goal is a stock pinned devenv with no fork. devenv has two parts that ship separately: the
binary (Rust, plus the embedded bootstrap Nix files such as `resolve-lock.nix`), and the module
source under `src/modules`, which comes from the workspace's `devenv` input. A module change
therefore needs no binary rebuild. Evidence: [W1-FORK-REVIEW](evidence/W1-FORK-REVIEW.md).

| Patch | Purpose | Status (W1, 2026-10-13) |
| --- | --- | --- |
| 0001 | SSH handshake fix for Machines | Merged upstream (PR #3255), not released. Affects only remote `machines install`, the advanced door |
| 0002 | Update the latest devenv version file | Drop; a version mismatch only warns (`devenv.warnOnNewVersion = false` silences it) |
| 0003 | Bootstrap reuses locked inputs in the store | **Keep** until PR #3244 merges and ships. Stock fails when the source is in the store, the fetcher cache is empty, and the remote is down |
| 0004 | Build the CLI as a release | Drop; the nixpkgs devenv 2.4.0 is a release build |
| 0005 | Refuse `machines install` of a machine that already runs | Keep, in the same binary as 0003 (R16); it splits into a binary half and a module half (R31). No hook can replace it: stock install kexecs the target before disko (W5 G4b) |
| 0006 | Target preflight before disko | Replaced by a guard in the Basix disk layout's disko `preCreateHook`, with `destroy = false` (W5); runs on the local and the remote path |
| 0007 | Inherit an imported source's inputs | Drop; the template lists the inputs |
| 0008 | Copy a lazily mounted locked source into the store | Not reproduced; dropped (R31) |
| 0009 | `vendomatFromYAML` primop | Drop; the Nix parser replaces it |
| new | `nixos` as `deferredModule` | Needed. Ships in a module-only fork of the `devenv` input; no upstream PR (R34) |
| new | Public `machines.NAME.build.vm` and `build.iso`; `build.iso` for any machine with `iso.modules` | A6 Path D (R17). Same module-only fork; kept as two patches, no upstream PR (R34) (+21, then +46 -4; W7, W8) |

**Shipping (ruled, R22 and R31).** Hosts and the Basix ISO install `pkgs.devenv` from Vendomat's pinned
nixpkgs: a release build from the public cache, the same binary everywhere. The workspace's
`devenv` input points at a module-only fork (the `deferredModule` change, the public `build.vm` and
`build.iso` options, and the version file). The template omits `require_version`. Until PR #3244
ships, the host binary is `pkgs.devenv` with patches 0003 and 0005 applied through an overlay (R16,
R22; [W6-HOST-BINARY](evidence/W6-HOST-BINARY.md)); without 0003, a fresh machine with the remote down
cannot enter a workspace. Patch 0005 reads `machines.NAME.vendomat.mode`: its Rust half is in the
binary, its module half in the module-only fork, and the catalog sets `adopt-existing` for installed
machines. Patch 0008 is not needed.

## Carried from project 20

The bare `vendomat` enters the pinned shell. Other arguments pass through to devenv. `vendomat
update` is `devenv update` on the `release` branch. Restoring `devenv.lock` restores the earlier
release. The new system configures no Attic (R39); a real two-machine Harmonia check stays a gate
(S7). The keyless boot of the Basix core is in the Basix concept. A real disk write needs the owner's separate authorization.

## Changes to project 20

These project 20 items need successor IDs when this concept gets a requirement ledger. Their
original text stays unchanged.

| Project 20 item | Change |
| --- | --- |
| S34 (machine catalog in the Vendomat release) | Basix has its own repository and release |
| `DOOR-074` (fork primop; `devenv.nix` must be `{ }`) | A Nix parser in the Vendomat source; `devenv.nix` is the escape hatch |
| `DOOR-075` (tabs and lists of maps rejected) | Tabs, lists of maps, and nested lists allowed; `key: - x` rejected |
| `DOOR-072` (`vendomat install` on the Basix ISO) | Local install steps on the Basix ISO; Basix owns the command (R13) |
| Concept line "Vendomat owns every other file" | Native files are an optional, visible escape hatch |

## Open questions

The rulings answered the questions of the first draft:

- The pin topology for Basix workspaces: a flake Basix with template `follows` lines (R28, R33).
- Which product owns `install`: Basix (R13).
- How a later release adds a template input for a new language: `vendomat update` adds the missing
  template lines (R25).
- Whether Basix locks the escape hatch for learners: a soft lock (R26), recorded in the Basix concept.
- The output format of `vendomat explain`: ruled in content (R27); the exact format is unproved.

- A standalone Home Manager target (project 22): homes stay outside Vendomat (R35). A two-command
  alias may later make a home switch look native.
- Host-side modules (project 22): Vendomat ships none; a workspace gets everything through its own
  lock (R36).

No design question stays open.

Observed gaps that no ruling covers are rows in the [ledger](REQUIREMENTS.md): parser depth limit
and line numbers (`VMT-013`, `VMT-035`), trace trimming of devenv errors (`VMT-117`), the devenv
version warning (`VMT-118`), and whether devenv fetches unused inputs (`VMT-116`). The two-machine
Harmonia check (`VMT-120`) is an unproved gate. The disk guard gaps (`BSX-114`, `BSX-115`) and the
real-hardware gate (`BSX-119`) are Basix rows, now in the Basix ledger.
