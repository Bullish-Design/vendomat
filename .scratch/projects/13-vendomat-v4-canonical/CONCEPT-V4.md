# Vendomat V4 concept

**Date:** 2026-10-06. **Status:** Canonical. **Authority:** [V4-SPEC.md](./V4-SPEC.md) holds every
rule. This file states goals and the boundary only. It fixes no interface.

## Purpose

One owner composes personal NixOS machines, development projects, and reusable applications from
native devenv, NixOS, and Home Manager modules. Nix and devenv already make that composition work.
They leave no trail. Vendomat leaves the trail.

Vendomat adds exactly two things no native tool provides:

1. A durable record that binds declared checks to exact output bytes, and records that the cache
   held every closure path at a stated time.
2. Retained source for the inputs a selection chose, with an honest correspondence label.

## Authority

Native declarations and locks are the only selection authority. Nix owns evaluation, derivations,
store identity, and substitution. devenv owns composition, tasks, outputs, and machine operations.
NixOS and Home Manager own activation. Attic owns cached objects and signing. Version control owns
history.

Vendomat owns no selection, no plan, no lock, no resolver, no runtime, and no daemon.

## The two operations

- **`retain`** runs `nix flake archive`, adds a garbage-collection root for each archived path,
  pushes those paths to Attic, and records each input's locked revision and NAR hash.
- **`publish`** freezes one immutable selection, runs the declared required check set, realizes the
  requested output, pushes the output with its runtime closure to Attic, queries every closure path
  back from Attic, and writes one receipt.

## Invariants

1. **Purity.** A publishable selection evaluates with no access to undeclared host state. Nix is
   then the drift detector.
2. **Identity.** An input-addressed store path follows its derivation. Its NAR hash identifies its
   bytes. The receipt records both.
3. **Separate facts.** These never imply one another: source retained; source correspondence
   established; rebuild from source proved; declared checks passed; output available in Attic now;
   dependency change accepted; configuration activated.
4. **Local independence.** Ordinary project entry, editor startup, and accepted output execution
   need no Vendomat process, no mounted tree, and no Attic.
5. **One authority per fact.** Vendomat may cache an evaluated fact for speed. No cached fact
   selects a dependency or overrides a native lock.

## Scope of the source claim

V4 retains the source of every locked native input. That source is exact, and it travels through
Attic as ordinary store paths.

V4 does **not** map a built package back to its upstream source. A package's source status is
`unresolved`, stated plainly. `pkgs.srcOnly` is the native mechanism for that later capability. It
needs its own evidence. See [FUTURE-WORK.md](./FUTURE-WORK.md).

## Publication and distribution form

Develop with the devenv command-line interface. Publish through a flake output attribute, because
`nix build --json`, `nix flake metadata --json`, and `nix flake archive` all need a flake
reference. One lock format serves both.

Source and binaries share one cache. They therefore share one loss domain. Record that.

## First proof

One Neovim review application: one shared command with a documented result format, one plugin
contribution for the normal editor, and one dedicated configured editor. The editor reaches the
command by absolute store path, never by `PATH` lookup.

P1–P6 prove the application, inspection, publication, and recovery path. P7 separately proves any
machine claim.

## Machine claim

devenv Machines copies plan outputs to the target with `nix copy --to ssh://…`. It does not
substitute through Attic. Vendomat therefore makes no machine transfer claim and no machine-cache
claim. It records the native plan identifier beside the receipt and nothing more.

## Boundaries

Vendomat does not provide a package manager, dependency resolver, second lock, build identity,
source protocol, daemon, application runtime, agent framework, context server, action registry,
user-interface schema, deployment planner, rollback implementation, release engine, retention
engine, secret manager, cache protocol, source index, or recursive `devenv.yaml` resolver.

It does not claim complete machine source coverage or offline reconstruction.

## Why the design is small

Native tools alone reach all eight owner goals. The gaps Vendomat closes are record-keeping gaps:
no native tool writes a durable structured record of a check run, and `attic push` emits no
machine-readable output. New Vendomat mechanism must close a demonstrated gap of that kind.
