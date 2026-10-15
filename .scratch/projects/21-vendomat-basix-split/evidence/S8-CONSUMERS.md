# S8 step 1: move the consumers to `vendomat.yaml` — 2026-10-15

Slice S8 of the [implementation guide](../IMPLEMENTATION-GUIDE.md), step 1 only. R40 keeps the
old flow working until both consumers move. Steps 2 to 4 stay open (see "Open items").
Raw logs: `~/.local/state/vendomat/p21/2026-10-15/s8/` (`demo-update.log`, `demo-shell.log`,
`demo-smoke.log`). Tools: devenv 2.4.0 (`/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0`),
Vendomat `release` = `e5923a8f5c0f` (v0.8.0), `devenv` input = S1 tag `v2.4.0-vendomat-modules.1`
(`061c2184cfcc`).

| Repository | Result |
| --- | --- |
| vendomat-demo | Landed. `main` = `85e6c725485965724489e571822f4d6c14213736`, pushed to `origin`. |
| nix-systems | Not moved. Stopped before any change: unlanded work, and a design gap. |

## vendomat-demo

**Start state (observed).** One workspace (`default`). Local `main` (`778fb108`, "Pin patched devenv
fork v2.4.0-vendomat.3") was one commit ahead of `origin/main` (`cbd153d5`). That commit was on
`main` and only unpushed, so the push of `main` published it with the change. The repository has
no `AGENTS.md`, no `CLAUDE.md`, no `.envrc`, and no Testee configuration. Its check is
`scripts/smoke`.

**Settings mapping.**

| Old setting (`vendomat.toml`) | New place |
| --- | --- |
| `[forge] url = "git://server"` | URLs in `devenv.yaml` |
| `[targets] devenv = true` | none (the template needs no target) |
| `[inputs] vendomat` (tag `v0.7.0-rc.1`) | `devenv.yaml` input `vendomat` = `git://server/vendomat?ref=release` |
| `[inputs] devenv` (fork `.3`, `dir=src/modules`) | `devenv.yaml` `devenv: follows: vendomat/devenv` |
| `[inputs] greeting, marker, unused` (tag `v0.2.0`, `dir=sources/NAME`) | `devenv.yaml`, same URLs |
| inherited inputs `greeting-defaults`, `marker-defaults` (listed in the old fragment) | `devenv.yaml`, same URLs |
| `[imports] greeting, marker` | `devenv.yaml` `imports`: `greeting/devenv`, `marker/devenv` |
| `[settings.greeting] text`, `[settings.marker] label` | `devenv.nix` (escape hatch) |
| generated `nixpkgs` pin | `nixpkgs: follows: vendomat/nixpkgs` (template) |

**Escape-hatch items (`devenv.nix`).** `vendomat.settings.greeting.text` and
`vendomat.settings.marker.label`. The authored modules define these two options. The catalog has no
key for the settings of an authored module. `vendomat.yaml` therefore holds only the template
text. `vendomat explain` lists both values under "Set only in Nix".

**Design note (inference).** The demo's claim "a workspace user needs no Nix edit" no longer holds
for the two module settings. A catalog key that carries module settings (or a way for an authored
module to read `vendomat.yaml`) would restore it. No ruling covers this. Not decided here.

**Removed.** `vendomat.toml`, `.vendomat/` (`devenv.nix`, `devenv.yaml`, `digest`), the old V6
module import, and the old `devenv.lock` (a new lock replaced it).

**Changed beyond the move.** `scripts/smoke` ran `vendomat sync` and `vendomat check`. It now copies
`vendomat.yaml`, `devenv.nix`, `devenv.yaml`, and `devenv.lock`, enters the shell, removes the
`unused` input and compares `shell.drvPath`, and edits the greeting in `devenv.nix` where it edited
the TOML file. `README.md` and `EVALUATION.md` describe the new flow; `EVALUATION.md` has a new
dated section.

**Lock (`devenv.lock`, observed after `devenv update`).**

| Input | Rev |
| --- | --- |
| `vendomat` | `e5923a8f5c0f0f81f3c0926dc2cf32887f6f6ba3` (equals `release` at landing, checked with `git ls-remote git://server/vendomat release`) |
| `devenv` | `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9` (S1 tag) |
| `greeting`, `greeting-defaults`, `marker`, `marker-defaults` | `487012f1007b199be0b68171be6e927aa0acb883` (tag `v0.2.0`) |

**Checks.**

| Command | Expected | Actual |
| --- | --- | --- |
| `devenv update` | Lock the inputs above | Exit 0 |
| `devenv shell -- sh -c 'printenv DEMO_GREETING DEMO_MARKER'` | Values as before | `Hello from Vendomat`, `demo`; shell prints `advanced: devenv.nix sets 2 settings` |
| `devenv eval env.DEMO_GREETING env.DEMO_MARKER` | Same | Same |
| `vendomat explain` | Lists both Nix-only settings | Listed |
| `scripts/smoke` | PASS | Exit 0, `PASS` (`~/.local/state/vendomat-demo/runs/20261015T140829Z/smoke.log`) |

A first smoke run failed on a bug in the new script (the guard grep matched a comment). Fixed in
the same change; the second run passed.

## nix-systems (stopped)

**Unlanded work (observed).** `jj workspace list` shows five extra workspaces. Four hold nothing
that `trunk()` lacks. The workspace `v6-services-rerun`
(`../gitman-workspaces/v6-services-rerun`) holds commit `f6de84c91ec1`, "test: services VM check
runs the unmodified role only (fork .2, no fixes variants)". It changes `tests/services/devenv.local.nix`,
`tests/services/overlay.nix`, and `tests/services/services-vm`. Bookmark `v6-services-rerun` is on
`origin`, and `main` does not hold it. The task rule says to stop and report. Nothing was changed.
The owner decides whether to land, drop, or keep it.

**Design gap (observed, read-only).** Even with that resolved, the move needs an owner choice. The
repository's `devenv.nix` uses `vendomat.inventory.<host>.nixos`, `mode`, and `disks`, and also
`machines.<host>.target.*`, `install.*`, `deploy.*`, and `hardware.facter`. The catalog module
(`devenv/devenv.nix`) defines no `vendomat.inventory` option. Its machine keys are `host`, `virtual`,
`mode`, `serve`, and `programs`. The `AGENTS.md` rules (module owns `machines.<host>.nixos`;
`vendomat machine install`; `vendomat sync`; `vendomat check`) describe the old flow. Other items
that need a place:

| Old setting | Needs |
| --- | --- |
| `[inputs] repoman, gitman, testee, docman, copyroom, devman` (GitHub tags) | devenv.yaml inputs |
| `[passthrough] sops-nix, disko, nixpkgs, home-manager` (rev pins) | devenv.yaml inputs; `nixpkgs` would stop being its own pin if it follows `vendomat/nixpkgs`, which changes every machine closure |
| `[inputs] devenv-cli` (fork `.2`) | none (the host binary replaces it, S2) |
| `vendomat.inventory.*`, `machines.*.nixos` imports | no catalog key; no defined hatch shape |
| `.machines/NAME/known_hosts`, `sshOpts` | hatch, if kept |

No drvPath baseline was taken (no change was made). When the move runs, take the before and after
`nix eval` of `.drvPath` for `machines.server` and `machines.framework` toplevels, per BOOT-010.
The `secrets/` directory was never read.

## Open items

1. Owner: what to do with `v6-services-rerun` (`f6de84c91ec1`) in nix-systems.
2. Owner: the nix-systems shape in the new flow (where inventory, disks, and per-host NixOS
   imports live, and whether `nixpkgs` follows `vendomat/nixpkgs`). A ledger row may follow once
   the owner chooses.
3. Owner: a catalog key (or another route) for the settings of authored modules, for the demo.
4. S8 step 2 (nix-meta's old module import, project 22) and step 3 (remove the TOML flow here)
   stay open. Step 3 must wait for nix-systems: it still uses `vendomat.toml`.
