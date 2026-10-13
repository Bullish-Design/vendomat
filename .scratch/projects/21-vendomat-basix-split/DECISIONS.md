# Project 21 decisions

**Date:** 2026-10-12. The owner opened a clean-slate review: "Ignore all previous
requirements/specs/decisions. Our only goal is to have the best, cleanest, most elegant concept
and architecture possible." The rulings below come from that session. They change concept only.
No production code, consumer, or machine changed.

## Owner rulings

| # | Ruling | Owner words (2026-10-12) | Effect |
| --- | --- | --- | --- |
| R1 | Basix moves to its own repository. Vendomat does not depend on Basix. | "I want to split out the Basix concept into its own separate repo." | Replaces project 20 S34. |
| R2 | YAML stays the user format. | "I like yaml for this. It'll be cleaner and easier for newcomers to grasp." | The parser moves into Nix (R7). |
| R3 | Two names: Vendomat is the tool, Basix the distribution. | "Two names" | `vendomat` and `vendomat.yaml` stay in Basix workspaces. |
| R4 | Machines use devenv Machines on a pinned devenv. | "I want devenv machines." "We'll pin a devenv version." | Plain NixOS flakes are not the machine path. |
| R5 | No `eject` command until a clear need appears. | "Agreed on dropping eject until we have a clear need." | A read-only `explain` is the preferred window into Nix. |
| R6 | `vendomat.yaml` is the primary interface. Routine use needs no Nix file. | "The whole point of vendomat is that the user doesn't need to interact with .nix files." | The catalog must cover routine needs. |
| R7 | The YAML parser is written in Nix; the fork's primop is not needed. | Approved the spike ("Do a more thorough spike"), then the grammar work. | Fork patch 0009 can go. |
| R8 | Lists of maps in the normal `- key: value` form, and nested lists, are allowed. | "Allow them." | Supersedes the "lists of maps rejected" rule of `DOOR-075`. |
| R9 | Tabs are allowed for indentation. | "Tabs for indentation need to be allowed." | The file is no longer strict YAML. |
| R10 | A compact item may continue with one tab; `key: - x` is rejected. | "Yes, agreed for both." | Parser v3. |
| R11 | Languages use standard devenv language management. uv is the Python default. | "We should utilize standard devenv language management when possible, with UV the standard/default for Python." | The template lists `nixpkgs-python` and `rust-overlay`; fork patch 0007 is not needed. |
| R12 | Native devenv files stay as an escape hatch for advanced settings. | Asked how to enable "a devenv.nix or devenv.local.nix escape hatch for any advanced or not-provided configuration". | Refines R6: YAML is primary; Nix files are optional and visible. |
| R13 | Basix owns `install` and the disk guard; Vendomat owns `apply` (A2). | "B" (confirm the fixture-backed leanings), 2026-10-13 | `DOOR-072` successor moves to Basix. |
| R14 | The module-only `devenv` fork carries `nixos` as `deferredModule`, offered upstream (A3). | as R13 | — |
| R15 | Local `apply` runs the two activation commands; the deployer watchdog comes later (A4). | as R13 | — |
| R16 | The Basix disk layout carries the blank-disk guard as a disko `preCreateHook` with `destroy = false`; patch 0005 stays in the same binary as 0003 (A5). | "Lets go with option 1 for A5", 2026-10-13 | Replaces 0006. |
| R17 | Path D: any machine builds an ISO of itself; distribution policy goes in `machines.NAME.iso.modules`; upstream in two patches (A6). | "Agreed. Path D it is.", 2026-10-13 | W7, W8. |
| R18 | The Basix ISO carries the prebuilt core closure (A7). | as R13 | — |
| R19 | Hatch use shows on shell entry and in `explain`; errors name `vendomat.yaml`; a personal setting (not a `vendomat.yaml` key) hides the shell line (A8, decision 3c). | as R13; "Agreed with all recommendations" | — |
| R20 | Python keys mirror native names: `uv` and `uv.sync` with `auto`, `true`, or `false`; `auto` turns sync on when `pyproject.toml` exists (A9, decision 3a). | as R19 | — |
| R21 | The catalog sets `networking.hostName` to the machine name (A10). | as R13 | — |
| R22 | Hosts and the ISO install `pkgs.devenv` from Vendomat's pinned nixpkgs, with the patches that R16 and A13 keep; the workspace `devenv` input is the module-only fork; the template omits `require_version` (A12). | as R13 | — |
| R23 | Catalog: an explicit `virtual: "true"` machine key; postgres and redis return as typed keys; catalog defaults use `mkDefault` (decisions 3b, 3d, 3e). | "Agreed with all recommendations" | — |
| R24 | Requirement IDs use one prefix per product: `VMT-` for Vendomat, `BSX-` for Basix (decision 3f). | as R23 | The `SPLIT-` draft is renamed before any ruling. |
| R25 | `vendomat update` adds missing template lines to `devenv.yaml`; its error text names the exact missing line. A spike checks whether devenv fetches unused inputs (decision 4). | "Agreed with recommendation" | — |
| R26 | Basix uses a soft lock: hatch files work, and the shell line and `explain` point to the Nix lesson (decision 5). | as R25 | Basix decision. |
| R27 | `vendomat explain` prints the user's YAML keys, each with its native option and source, plus a section for options set only in Nix, and `--json` (decision 6). | as R25 | — |

R13 to R27 come from the 2026-10-13 review of A2 to A14 and the follow-up decisions. A1, A11, A13,
A14, the live-ISO service rule, and the VM image cleanup stay open.

R6 and R12 together: routine use needs only `vendomat.yaml`. Native files remain for settings the
catalog does not cover.

## Recommendations awaiting a ruling

| # | Recommendation | Basis |
| --- | --- | --- |
| A1 | A Basix workspace names only `basix`; `vendomat` and `nixpkgs` follow through it. | Removes the compatibility matrix. Unproved. |
| A2 | Basix owns `install` and the disk guard; Vendomat owns `apply`. | `install` has one consumer, the Basix ISO. |
| A3 | Add a devenv patch that types `machines.NAME.nixos` as `deferredModule`, and offer it upstream. | [NIXOS-MERGE](evidence/NIXOS-MERGE.md) |
| A4 | Local `vendomat apply` runs the two activation commands of devenv's deploy worker. The deployer with its watchdog comes later. | [MACHINES-RESEARCH](evidence/MACHINES-RESEARCH.md) |
| A5 | Drop fork patches 0005 and 0006. Remote install becomes the native door. | They guard only the remote path. |
| A6 | Expose ISO and VM builds through `machines.NAME._nixosEval`. | `machines.nix:684`. Unproved. |
| A7 | The Basix ISO carries the core closure for an offline install. | Inference. |
| A8 | Show hatch use on shell entry and in `vendomat explain`; name `vendomat.yaml` in conflict errors through `_file`. | Concept, escape hatch section. |
| A9 | The catalog enables `uv.sync` only when `pyproject.toml` exists. | devenv warns on every shell entry otherwise (`python/default.nix:253-255`). |

### Fixture status of the recommendations, 2026-10-13

W1 and W2 ran on stock devenv 2.4.0 ([W1](evidence/W1-FORK-REVIEW.md),
[W2](evidence/W2-MACHINES.md)). A fixture pass backs a recommendation; it does not rule on it.

| # | Status |
| --- | --- |
| A3 | Backed: the patched `devenv` input merged an attrset, a function, and a per-machine default; the stock input failed or lost settings. Needs no binary fork. |
| A4 | Backed: the two commands made generation 2 live with zero failed units; `bootctl set-oneshot` booted generation 1. |
| A5 | Backed by W1: the guards cover only remote install. W5 ([W5](evidence/W5-DISK-GUARD.md)): a disko `preCreateHook` guard replaces 0006 on the local and the remote path when the disk sets `destroy = false`; it cannot replace 0005, because stock `machines install` kexecs the target before disko runs. |
| A6 | Backed: `devenv build outputs.iso` and `outputs.vm` built and booted, with `hardware.facter = null`. |
| A7 | Backed: the prebuilt ISO installed offline in a 4 GB guest; an in-ISO build needed network and about 8 GB. |
| A1 | Backed with a change by W3 ([W3](evidence/W3-TOPOLOGY.md)): Basix must be a flake that lists its inputs and commits its `flake.lock`, and the workspace writes `follows` lines for `vendomat`, `nixpkgs`, and any other input it takes from Basix. Naming only `basix` fails: stock devenv ignores an imported input's own `devenv.yaml`. One `devenv update` moved the Basix and Vendomat pair. |
| A8 | Backed by W4 F6, F11, F12 ([W4](evidence/W4-CATALOG.md)). The line counts "settings" (leaves of the hatch file's attribute tree), not "options". |
| A9 | Backed by W4 F4, F4b, F4c. devenv's eval cache follows a created or deleted `pyproject.toml`. |
| A10 | Backed by W4 F9, F10. |
| A14 | Backed at evaluation level by W4 F14, with a proposed YAML key `virtual`. |
| A2 | Not yet tested as a command; W2 T3 proved the steps. |

### New recommendations from W1 and W2

| # | Recommendation | Basis |
| --- | --- | --- |
| A10 | The catalog sets `networking.hostName` to the machine name. | The facts file holds the host name, not the machine name (W2 T4). |
| A11 | A lasting rollback is "restore `vendomat.yaml` and `devenv.lock`, then apply". The boot menu is for recovery only. | After a boot-menu rollback the profile still points at the newer generation (W2 T1). |
| A12 | Hosts and the ISO install `pkgs.devenv` from Vendomat's pinned nixpkgs; the workspace's `devenv` input is a module-only fork; the template omits `require_version`. | W1 Q3 to Q5. |
| A13 | Keep a binary with patch 0003 until PR #3244 ships, or accept that a fresh machine cannot enter a workspace while the remote is down. | W1 Q2. |
| A14 | The ISO and test VMs set `hardware.facter = null`; the install writes the real report. | W2 T2, T3. |

## Owner leanings, 2026-10-13 (provisional)

The owner gave first views on A2 to A14 and asked that none be taken as final. Later the same day
the owner confirmed the fixture-backed ones as R13 to R22; A11, A13, and A14 stay provisional. They will be revisited
with the spike results. These are not rulings.

| # | Leaning | Open point |
| --- | --- | --- |
| A1 | Not given. | W3 backs a flake Basix with template `follows` lines. |
| A2 | Basix owns `install`. | — |
| A3 | Module-only fork with `deferredModule`, offered upstream. | — |
| A4 | The two activation commands now; the deployer watchdog later. | — |
| A5 | Option 3 with option 1 for 0005 (owner, 2026-10-13): the Basix disk layout carries the guard as a disko `preCreateHook` with `destroy = false` (replaces 0006); patch 0005 stays in the same binary as 0003. | Open gaps from W5: a build-time check that guarded disks keep `destroy = false`; no guard on a custom disk in `devenv.nix`; one guard over all disks in a multi-disk layout. |
| A6 | Option 2, Path D (owner, 2026-10-13): any machine builds an ISO of itself; distribution policy goes in `machines.NAME.iso.modules`; upstream in two patches. | W8 ([W8](evidence/W8-ISO-POLICY.md)) backs it: six overrides are required (timeout override, EFI and USB bootable, ISO file systems, no swap, no LUKS devices); `enableAllHardware` is policy; two W7 overrides are not needed. Patch 1 +21, patch 2 +46 -4. devenv's overrides use priority 60, so policy needs `mkForce` to change them. Live-ISO services: W8 tested a Basix deny list (`liveOff`); a live marker is untested. |
| A7 | The prebuilt core closure only, to start. | — |
| A8 | Shell line, `explain`, and `_file`, plus a flag that hides the line. | Proposed: a `vendomat.yaml` key hides only the shell line; `explain` still shows all. |
| A9 | An explicit YAML key whose default is "auto". | The "auto" default uses the W4 F4b detection. |
| A10 | The catalog sets `networking.hostName`. | — |
| A11 | Restore and apply now; a `vendomat rollback` command that does both later. | — |
| A12 | `pkgs.devenv` from the pinned nixpkgs, module-only fork input, no `require_version`. | With A13, the host binary is `pkgs.devenv` with patch 0003 applied (and 0005, 0006 if A5 needs them), not a separate fork repository. |
| A13 | Keep a binary with patch 0003 until PR #3244 ships. | See A12. |
| A14 | Commit a hardware report from a QEMU guest for test VMs. | Two `nixos-facter` runs differed (W2); the fixture must show the report is stable or strip changing fields. |

## Ideas recorded, not pursued now

Catalog keys as an allow list of native option paths with one generic type converter; a JSON
Schema for editor completion; a commit per `apply`; machines that pull their own branch; one estate
repository whose machine keys define cache trust; capability directories with a module, a lesson,
and a check; an assistant that edits only the intent file.
