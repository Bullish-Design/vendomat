# Project 20: Vendomat and Basix

**Accepted design, 2026-10-12.** The owner chose Vendomat as the user entry point on
2026-10-11 and accepted this simplified design on 2026-10-12 ([decisions](DECISIONS.md) R1 to R4).
It is not yet the runtime, and no gate has passed. Fixtures on the pinned tools back each
mechanism below. The
[second review](evidence/SIMPLIFY-REVIEW-2026-10-12-PASS2.md) holds the evidence, the lost
capability, and the open owner questions.

## The mental model

1. You describe a workspace or a machine in one file, `vendomat.yaml`; Vendomat owns every other file.
2. `vendomat` opens the shell, and any other command runs in the pinned devenv.
3. `vendomat update` moves to the newest Vendomat release; version control or the boot menu takes you back.
4. You install a machine from the Basix USB stick, then `vendomat apply` switches it to your file.
5. One machine can serve what it builds; the others name it and copy its public key line.

## Workspaces

`vendomat new` makes a workspace with four files. The user edits only `vendomat.yaml`. The
template owns `devenv.yaml` (the Vendomat input on its `release` branch, `nixpkgs` following
Vendomat's `nixpkgs`, and one import), `devenv.nix` (`{ }`), and `devenv.lock`. No generated
file exists.

`vendomat.yaml` holds a bounded catalog: programs, languages, services, and environment values.
It uses a strict subset of YAML: maps, lists, and string scalars only. A fixed Nix module in the
Vendomat release reads the file with `builtins.readFile` and parses the text with
`vendomatFromYAML`, a function that the pinned devenv fork adds. The module parses the file once
into typed values and lists every bad field, with the file name, before any command does work.
Every mapping to a native option reads only the parsed values. A command therefore cannot run
with a bad value. A syntax error names the file, line, and column. A type error names the file
and the field.

The fixed Nix module is the **catalog module**. It does three things, in order. It reads and
parses `vendomat.yaml`; a missing file is an empty catalog. It declares the catalog entries as
typed options, so the types give the strings their meaning: `"3.10"` stays a version, and `no`
fails in a true-or-false field. It maps the typed values to native devenv or NixOS options; for
example, `programs: [ripgrep]` becomes `packages = [ pkgs.ripgrep ]`. A short example:

```yaml
programs:
  - ripgrep
languages:
  python:
    version: "3.12"
services:
  postgres:
    enable: true
env:
  GREETING: hello
```

A value outside the catalog goes in `devenv.nix` or `devenv.yaml`. That is the advanced door.
Native Nix merge rules apply there.

## Commands

Vendomat has three verbs: `new`, `apply`, and `install` (on the Basix ISO only). `vendomat` with
no argument enters the shell. Every other argument passes to the pinned devenv fork that the
host release carries. `vendomat test` runs `devenv test`. `vendomat update` runs `devenv update`,
which moves the lock to the newest release commit. Restoring `devenv.lock` from version control
restores the earlier release.

## Machines

A Basix machine is a workspace whose `vendomat.yaml` also has a machine table. The learner boots
the Basix ISO on the machine and runs `vendomat install`. The installer lists blank disks by
`/dev/disk/by-id/`, excludes the boot medium, and refuses a disk with partitions or signatures.
The learner types the full by-id name to confirm. The installer partitions, installs, writes the
machine workspace, and sets a console password. The core boots with no key and no secret.

After boot, the learner edits `vendomat.yaml` and runs `vendomat apply`. It builds the machine
and switches to it. It reports the native switch status and any failed unit. The boot menu
gives the earlier generation back.

Remote install, remote deploy, adoption of an existing NixOS system, and custom disk layouts use
native devenv Machines through the advanced door.

## Sharing

A machine table may set `serve = true`. That machine makes its own signing key on first start,
then serves its Nix store to the local network with Harmonia. Another machine names the serving
machine and pastes its public key line. Vendomat derives the cache URL, the trust, fallback to a
local build, and a short connect timeout. A missing path or a down cache never stops a build.

## Not in the first release

Source mirrors and keep clones, a collection builder, key backup and rotation, several cache
hosts, secret providers, and per-workspace Vendomat releases. The current Attic route stays until
a real two-machine Harmonia check passes. A real disk write needs the owner's separate
authorization.
