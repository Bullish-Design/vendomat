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

## R60 follow-up: the demo settings in `vendomat.yaml` (2026-10-15)

Open item 3 is answered by R60 (`VMT-183`, [R60-SETTINGS](R60-SETTINGS.md)). The demo change was prepared and
waited for a release. It is **landed** (below), because `v0.10.0` carries the `settings` key.

- Workspace: `/home/andrew/Documents/Projects/vendomat-demo/.gitman/workspaces/move-settings-to-yaml`
  (change "Move module settings to vendomat.yaml (needs a Vendomat release with R60)", parent demo `main`
  `01e6d409`). It moves both settings to `vendomat.yaml`, empties `devenv.nix`, and edits `scripts/smoke`.
- The proof used an untracked `devenv.local.yaml` that sets the `vendomat` input to
  `git+file:///home/andrew/Documents/Projects/vendomat?ref=main&rev=aa5919517e2bd638af29dd4728df17287fe79132`
  (Vendomat `main` after R60). The tracked `devenv.lock` is unchanged. The local file is in the demo
  repository's `.git/info/exclude`.
- `scripts/smoke`: exit 0, `PASS`, log `~/.local/state/vendomat-demo/runs/20261015T151615Z/smoke.log`.
  `vendomat explain` in the smoke copy lists both keys with their options and "Set only in Nix: (none)".
- With the released `v0.9.0` the same files fail: `vendomat.yaml:22:1: settings: unknown key (known: env,
  languages, machines, programs, services)`.
- To land it: after the owner releases a Vendomat with R60, run `devenv update vendomat` in the workspace,
  delete `devenv.local.yaml`, run `scripts/smoke`, and land the change.

## S8 step 1 done: nix-systems moved (2026-10-15, later)

The owner approved rulings R53 to R61 and option (c) (no `testee` pin in nix-systems). The agent landed
the move with Gitman. Raw logs, drvPath lists, and closure comparisons:
`~/.local/state/vendomat/p21/2026-10-15/s8/move/`. Tools: devenv 2.4.0 (host binary), Vendomat `release`
`9b8885e3` (v0.9.0), devenv modules `061c2184`. Run VMs with disposable files under
`/mnt/shared/nix-systems/s8/` (deleted afterward). No install, `apply`, `nixos-rebuild`, or activation ran. The
`secrets/` directory was never read (the repository's own harness encrypts a test file at test time).

| Step | Result |
| --- | --- |
| N1 (R53) | `f6de84c91ec1` was already on nix-systems `main` as `58bc8867` when this work began (landed by someone else; its check was not run or seen by this agent). The workspace was gone. |
| Baseline (R56) | nix-systems `e8a55e0f`: `server.nix` installs docman as a package. `server` did not evaluate before (option `vendomat` missing). |
| Move | nix-systems `9419924d` on `main`, pushed. |

**drvPath** (`devenv eval machines.NAME.build.nixos.drvPath`, no build):

| Machine | Baseline `e8a55e0f` | Move `9419924d` |
| --- | --- | --- |
| framework | `s29rq0ml5zrgnjd85scv0azbwv1px16a` | `iq83gnj3bxjpb6429jq18gfpfl1dx1b6` |
| server | `dk83lsxfw6f6g1i6rn61ys44csy7yj7i` | `ap0g9dfv0zfrigr08l61kffj796n65m3` |

**Named differences (BOOT-010).** `framework`: Harmonia only (51 new and 8 changed derivations: harmonia-3.3.0 with
its crates, `harmonia.toml`, the Harmonia and key units, the `/var/lib/vendomat` tmpfiles rules, and the assembly
derivations). With `serve: "false"` the framework value equals the baseline. `server`: the same set, the firewall scripts
(TCP 5000 on `tailscale0`, R52), the host tools (fork `devenv-wrapped-2.4.0` becomes nixpkgs `devenv-2.4.0` from the
Vendomat release; `vendomat` and the launcher `0.7.0-rc.1` become `0.9.0`), and the removal of the `testee` package
(option c). `system-path` differs only in those entries. nixpkgs (`e7439b6b`), home-manager, disko, sops-nix, and the
other personal tool tags did not change. `devenv-cli` is gone from the lock. The lock lost only the `testee` node in the
last step.

**Checks.** `tests/run` (lock-and-build with the CACHE-010 settings comparison, `core-vm`, `vm-flow` 31 steps with the
framework tripwire): all passed. `tests/services/services-vm` (the production `server.nix` with the test overlay): 62 PASS,
1 OBSERVED (Tailscale Serve start without a tailnet), 0 failed, including the new check 9 (Harmonia answers with a key
named `server`; TCP 5000 opens on `tailscale0` only). Changes to the checks: no loopback collection, no `vendomat sync`
or `check`, no library face, no closure build of a real machine; `tests/disk` is deleted (it tested patch 0006; R54); the
tripwire now relies on the missing `target.host` because the refusal by mode (patch 0005) is retired.

**Facts that bite.**
- The integrate gate (`testee_integrate_gate.py`) treats any `Bullish-Design/testee` text in `devenv.yaml` or `devenv.nix` as
  a Testee repository, and Testee 0.8 rejects a `devenv.yaml` with a `testee` input (`module_not_supported`). nix-systems
  defines no Testee tasks, so `testee verify` gives NO VERDICT (`not defined: check:lint, check:format, check:types,
  test:full`). With the `testee` input gone the gate does not apply and the push passes. Its check stays `tests/run`.
- Host condition, not fixed: about 120 leaked `hindsight-coding-agents` node processes use up the user's 8 MiB
  `RLIMIT_MEMLOCK`, and qemu 11.1.1 stops with `Failed to initialize io_uring: Cannot allocate memory`. The VM runs used
  `systemd-run --user -p SystemCallFilter=~io_uring_setup -p SystemCallErrorNumber=ENOSYS` (script in the log directory).
- Origin of nix-systems still has the stale branch `v6-services-rerun` and the bookmarks `v6-server-role`, `v6-step6-vm`,
  `v6-step7-disk`, `v6-step7-disk-evidence`, `v6-step8-services`. Left alone by owner instruction.

**Open items after the move.**
1. S8 step 3 (remove the TOML flow here) is unblocked: no consumer uses `vendomat.toml` now.
2. S8 step 2 (nix-meta module import) waits for project 22 and the V4 backlog.
3. Later, separate nix-systems changes: remove Attic (R39), Home Manager (project 22 R8), and the other personal tools
   from the server role (R57); commit `.machines/NAME/cache-key.pub` after the first `apply` (needs the owner's yes, R61);
   commit `facter.json` after the real install (blocked until Basix B7, R54).
4. Run `devenv eval` on both machines before and after every `vendomat update` (R59).

### Landed on v0.10.0 (2026-10-15)

Vendomat v0.10.0 carries R60 ([RELEASE-0.10.0](RELEASE-0.10.0.md)). The demo change landed as `bb6bad05bf63` on
the demo `main` and `origin`. The demo now uses the catalog `settings` key on `v0.10.0`.

- `devenv.local.yaml` is deleted, and its line left the demo repository's `.git/info/exclude`.
- `devenv update vendomat` moved only the `vendomat` node, from `9b8885e3` (v0.9.0) to `c6b36c1e2010` (v0.10.0).
- `scripts/smoke`: exit 0, `PASS`. `devenv shell -- true`: exit 0. `vendomat explain` maps `settings.greeting.text`
  and `settings.marker.label` to their options, from `vendomat.yaml`, and prints "Set only in Nix: (none)".
- The first smoke run failed: the store lacked the `greeting` input path. `nix flake prefetch` restored it.
- Raw logs: `~/.local/state/vendomat/p21/2026-10-15/release-0-10-0/` (`demo-*`). The demo record is in its `EVALUATION.md`.
