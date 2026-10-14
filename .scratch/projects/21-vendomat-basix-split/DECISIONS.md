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
| R28 | Basix is a flake that lists its inputs and commits its `flake.lock`. A Basix workspace names `basix` and takes `vendomat`, `nixpkgs`, the `devenv` input, and the language inputs through `follows` lines that the template writes and `vendomat update` keeps current. This is devenv's own pattern for every module set except its two built-in inputs; Vendomat gets no built-in input and does not ride inside the `devenv` input (A1). | "A1. go with your recommendation", 2026-10-13 | W3. |
| R29 | On a live ISO, Basix turns off harmful services with a deny list (`liveOff [ names ]` in `iso.modules`). A live marker that service modules check may come later. | "Live iso - agreed", 2026-10-13 | W8. |
| R30 | A lasting rollback restores `vendomat.yaml`, `devenv.lock`, and the hatch files from an earlier commit and ends in a new commit, then applies. Each machine keeps a small record that maps each system path to the workspace commit it came from; `system.configurationRevision` is not used. `vendomat rollback` reads that record. The boot menu and the profile rollback stay recovery tools (A11). | "Agreed with your recommendation for A11", 2026-10-13 | W9. The record format is unproved. |
| R31 | The host and ISO binary keeps patch 0003 until PR #3244 ships in a release; recheck at each nixpkgs bump. Patch 0005 splits into a binary half and a module half, and the catalog sets `machines.NAME.vendomat.mode`. Patch 0008 is dropped (A13). | "Agreed on A13", 2026-10-13 | W6. |
| R32 | Test VMs use a committed QEMU hardware report per VM shape, written through the filter `del(.hardware.cpu[].tlb_size)`. A VM shape pins `-machine`, the disk bus, the NIC model, and a named `-cpu`. `install` applies the same filter to real reports (A14). | "Agreed on ... A14", 2026-10-13 | W10. |
| R33 | Project 22's pin-layout proposal is accepted: a workspace that builds with `vendomat.yaml` pins Vendomat in its own `devenv.lock` (R28), and the personal tools never enter a workspace lock. | "Agreed on pin layout", 2026-10-13 | Answers project 22 A7, part 1. |
| R34 | Vendomat never opens upstream pull requests for its devenv patches. The patches are evaluated through personal patched use; the owner may revisit this after months of use. This supersedes "offered upstream" in R14 and "upstream in two patches" in R17; the rest of R14 and R17 stands. | "we will never open upstream PRs for this. We'll evaluate thoroughly in our personal patched usage, and can check back in after months of usage.", 2026-10-13 | The module-only fork and the patched binary are long-lived. Watching upstream (PR #3244, releases) stays allowed. |
| R35 | Homes stay outside Vendomat. The owner's home is standalone Home Manager (project 22), switched with `home-manager switch`. The catalog maps no home key; devenv's native `machines.NAME.home-manager` stays reachable only through the escape hatch. A two-command alias may later make a home switch look native in Vendomat or Basix. | "For home manager target, just keep homes outside vendomat - option 1. We can always add a two command alias if we want things to appear \"native\" for vendomat/basix", 2026-10-13 | Answers project 22 A7, part 2. |
| R36 | Vendomat ships no host-side module. Everything a workspace needs comes through its own lock (R28, R33). The project 14 NixOS module's `share/vendomat/consumer-module.nix` and `machine.json` are removed when the project 14 code is replaced. Run-time host facts come from `/etc/devenv/machine-facts.json`. | "Go with option 1 for host side modules.", 2026-10-13 | Answers project 22 A7, part 3. Project 22's pointer file stays a project 22 idea. |
| R37 | Basix publishes releases like Vendomat: immutable tags plus a fast-forward `release` branch. The collection hook allows `release` for any repository, not only `vendomat` (D3, option a, with the hook rule widened). The release contract names no transport; where a learner's machine fetches updates stays open. | "D3: agreed", 2026-10-13 | The hook change is the Vendomat side of S5. |
| R38 | Basix keys live in a second file, `basix.yaml`, read with the parser from the Vendomat source (D5, option c). The recommendation was option a. The owner chose c knowing it breaks "one file" for the user (R6). Vendomat builds no catalog extension point for Basix keys. | "D5: I like c", 2026-10-13 | Supersedes the D5 extension-point plan in S3 and S5. `BSX-124` replaces `BSX-065`. How the Basix hatch hint reaches the shell line stays open. |
| R39 | The new system configures no Attic. Harmonia is part of the initial install: every installed machine runs Harmonia from first boot and signs with a key it makes at first boot. `serve` is a Vendomat machine key in `vendomat.yaml`; it defaults to on, and `serve: false` turns it off. Vendomat owns the sharing module (Harmonia, and the substituter and key for clients) and proves it with two VMs in S3. Basix keeps the default on in its core (S5). The real two-machine check stays in S7. Build outputs stay in the building machine's store under a GC root. The Attic on today's `server` belongs to the current estate and stays untouched. | "I do *not* want to configure Attic from the beginning, lets make sure harmonia is a part of the initial install though."; "Agreed with your recommendation on harmonia" (every installed machine serves by default), 2026-10-13 | Supersedes `VMT-105` (by `VMT-126`) and `VMT-120` (by `VMT-127`). Adds `VMT-128` and Basix `BSX-129`. S2 drops the Attic push. Guide Section 2.3 is history. Settles the Basix `serve` key, which Basix deferred. |
| R40 | D1, option a: the project 14 and V6 verbs and the `vendomat.toml` flow keep working until nix-systems and vendomat-demo move to `vendomat.yaml`; S8 then removes them all, `push` included. `machine install` moves to Basix (R13). S3 must not break the old flow. | "Agreed with all recommendations", 2026-10-13 | R39 removes the old reason to keep `push` (Attic); it goes in S8 with the rest. |
| R41 | D2, option a: the module fork tag is Vendomat's second flake input, `devenv` (`dir=src/modules`). The template writes `devenv: follows: vendomat/devenv`. | as R40 | Changes the "one flake input" shape rule: `tests/test_repo_shape.py` and `AGENTS.md` change in S1 step 9. `VMT-073`, `VMT-111`. |
| R42 | D4, option a: a committed `.machines/NAME/facter.json` marks a machine installed, and the catalog sets `vendomat.mode = "adopt-existing"`. The YAML key `mode: fresh-install` overrides it for a deliberate reinstall. | as R40 | S3 records the remote `facter` phase case (the file exists before a remote install) in a fixture. `VMT-099`. |
| R43 | D6, option a: each machine keeps an append-only `/var/lib/vendomat/generations.jsonl`, one line per apply (generation, toplevel, commit, dirty flag, time). `apply` refuses uncommitted changes to `vendomat.yaml`, `devenv.lock`, and the hatch files unless `--dirty`; `rollback` uses clean entries only. | as R40 | `VMT-098`, `VMT-110`. Superseded in part by R49 / `VMT-166` (apply only): apply now commits watched changes after the build instead of refusing them; the record and the clean-rollback rule stay. |
| R44 | D7, option a: the module fork's tags are `v2.4.0-vendomat-modules.N`. | as R40 | `VMT-082`. |
| R45 | D8, option a: the environment variable `VENDOMAT_HIDE_ADVANCED=1` hides the shell `advanced:` line. | as R40 | `VMT-093`. |
| R46 | An exit status 4 of `switch-to-configuration` is a warning. `apply` and `rollback` write the record line and print the warning. | "1. confirmed" (2026-10-14, answer to the project 24 report) | `VMT-162` is ruled. |
| R47 | The owner commits each machine's public cache key as `.machines/NAME/cache-key.pub`. A bare `apply` writes the file and asks for a commit. | "2. Confirmed" (2026-10-14) | `VMT-157` and `VMT-161` are ruled. |
| R48 | Switch the host to the S2 binary. | "4. Confirmed, let me know if theres something I need to do" (2026-10-14) | nix-meta `main` `cf8ef3cc` installs it. The owner runs the switch (it needs a password). |
| R49 | A successful `vendomat apply` builds first, commits only the allowlisted watched workspace configuration, then activates and records it. A present ignored watched file must be force-added or removed. `--dirty` skips the config commit and records the current HEAD as dirty. A failed build makes no config commit, activation, or record. | Option selected, 2026-10-14: “Use proposed policy (Recommended).” (an option label; the owner did not see the details in the effect column) | Supersedes R43 in part, for apply only (apply commits watched changes after the build); the record and clean-rollback rules of R43 remain. `VMT-166`. The details below are implementer choices that the owner was not asked about: an ignored watched file blocks even with `--dirty`; the config commit stays if activation fails; the path-scoped rollback commit and the meaning of `--exact`. |
| R50 | The sharing module exposes `trustedInterfaces` (default empty), opens TCP 5000 only on those interfaces while `serve = true`, and leaves unmarked interfaces closed. `serve = false` disables the service and all openings. | Option selected, 2026-10-14: “Explicit trusted interfaces; unmarked closed (Recommended).” (an option label; the owner did not see the details in the effect column) | `VMT-169`; the passing VR7 scratch fixture remains proposal evidence only. The details below are implementer choices that the owner was not asked about: the module opens no global port 5000; `serve = false` disables the key unit. The catalog has no YAML key for `trustedInterfaces`; no ruling covers it (`VMT-172`). |
| R51 | A machine entry with no value (`machines:` then `laptop:`) is an empty map, so the machine takes every default. Every other key with no value still fails with `no value`. The parser stays strict by default; the catalog names the one path (`machines.NAME`) where no value is an empty map. A list item never takes the exception. | "Great, lets go for option 2" (2026-10-14, after the options for `VMT-160`) | `VMT-170` supersedes `VMT-012` in part and closes the gap `VMT-160`. Basix imports the same parser (R38) and names its own paths. R49 and R50 are left to the `p21-contracts` session. |

R13 to R32 come from the 2026-10-13 review of A1 to A14 and the follow-up decisions. Every
recommendation A1 to A14 now has a ruling. The VM images were deleted on 2026-10-13.

R6 and R12 together: routine use needs only `vendomat.yaml`. Native files remain for settings the
catalog does not cover.

**2026-10-13 (later):** The owner ruled on D3 (R37) and D5 (R38).

**2026-10-13:** The Basix design, the 13 `BSX-` ledger rows, and the Basix plan moved to the Basix
repository (`../basix`, `../basix/.scratch/projects/001-initial-concept/CONCEPT.md`). No ruling changed. Decisions D3 and D5 stay here and are copied there.

## Recommendations awaiting a ruling

**Status, 2026-10-13:** every recommendation A1 to A14 now has a ruling: R13 to R32 (A1 in R28, A2 in
R13, A3 in R14, A4 in R15, A5 in R16, A6 in R17, A7 in R18, A8 in R19, A9 in R20, A10 in R21, A11 in
R30, A12 in R22, A13 in R31, A14 in R32). R33 and R34 came later. The tables below, the fixture
status table, and the leaning table are kept as history. They show what stood before each ruling.

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
| A11 | Restore and apply now; a `vendomat rollback` command that does both later. | W9 ([W9](evidence/W9-ROLLBACK.md)) confirms it with changes: the restore must end in a commit (a bare working-copy restore is lost and the next apply silently rolls forward); rebuilding from restored files gives the identical earlier store path and copies nothing. Open choice: record each generation's commit in `system.configurationRevision` (provenance, but every commit gives a new generation; set it through a `VENDOMAT_REV` variable, because the eval cache ignores git HEAD) or in a sidecar record on the target (stable paths, untested). |
| A12 | `pkgs.devenv` from the pinned nixpkgs, module-only fork input, no `require_version`. | With A13, the host binary is `pkgs.devenv` with patch 0003 applied (and 0005, 0006 if A5 needs them), not a separate fork repository. |
| A13 | Keep a binary with patch 0003 until PR #3244 ships. | W6 ([W6](evidence/W6-HOST-BINARY.md)) backs it: stock fails offline with an empty fetcher cache and the patched binary enters; warming the cache works only if the machine was online once, so it does not cover a fresh machine or ISO; PR #3244 is open and unreviewed, and v2.4.0 is the latest release. Recheck at each nixpkgs bump. |
| A14 | Commit a hardware report from a QEMU guest for test VMs. | W10 ([W10](evidence/W10-FACTER.md)) backs it. The only run-to-run change is `.hardware.cpu[].tlb_size`, an uninitialised value from a hwinfo bug; `del(.hardware.cpu[].tlb_size)` makes repeated reports byte identical. RAM size, CPU count, MAC, and disk count change the report but not the toplevel. The CPU model (`vmx`) and the QEMU machine type change the toplevel, so a test-VM shape pins `-machine`, the disk bus, the NIC model, and a named `-cpu`. `install` should apply the same drop filter to real reports. |

## Implementation decisions awaiting a ruling (D1 to D8)

**Recorded 2026-10-13, after the design freeze.** The design rulings R1 to R36 leave these
implementation choices open. Two read-only inventories of the repository and the host found them
while the [implementation guide](IMPLEMENTATION-GUIDE.md) was written. Each entry gives the
question, the facts, the options, and a recommendation. None is a ruling. Ask the owner before the
slice that needs each one, and record the answer as a ruling (R37 onward). The guide's Section 4
repeats the short form.

### D1: the project 14 verbs and the `vendomat.toml` flow

**Ruled (R40), 2026-10-13: option a.**

**Needed by:** S3 (launcher dispatch), S8. **Ledger:** none yet.

Facts: the repository still ships the project 14 and V6 verbs `sync`, `path`, `check`, `push`,
`bump`, and `machine install`, and the code behind them (`registry.py`, `generate.py`,
`devenvgen.py`, `store.py`, `locate.py`, `lockpath.py`, `bump.py`, `machine.py`, the V6 module
under `nix/devenv-module/`, `preflight/`, `direnv/vendomat.sh`, two templates, and their tests).
The live consumers nix-systems and vendomat-demo use `vendomat.toml` and `.vendomat/`; none uses
`vendomat.yaml`. Project 22's concept moves them "when project 21's catalog ships". Project 21
rules on none of these verbs. R13 moves `install` to Basix. `VMT-120` kept Attic until a
two-machine Harmonia check passes; R39 supersedes that.

| Option | Pros | Cons |
| --- | --- | --- |
| a. Keep the old verbs working until the two consumers move; then remove them in a new slice S8. `machine install` moves to Basix; `push` stays until `VMT-120` passes. | No consumer breaks. The removal is one clean change after the migration. | The repository holds two flows for a while; S3 must not break the old one. |
| b. Remove the old flow in S3. | The repository becomes project 21 only, at once. | nix-systems and vendomat-demo stop working until they move; their move then blocks S3. |
| c. Freeze the old flow in a separate legacy package. | Consumers keep a pinned tool. | A second package to build and pin; more surface, not less. |

**Recommendation:** a.

### D2: how a plain Vendomat workspace pins the module-only `devenv` input

**Ruled (R41), 2026-10-13: option a.**

**Needed by:** S1 (step 9), S3 (template). **Ledger:** `VMT-073`, `VMT-111`.

Facts: Basix workspaces take `devenv` through `basix/devenv` (R28; W3 Q5 proved a `devenv`
follow). A workspace without Basix has no such path today. Vendomat's flake has one input,
`nixpkgs`, and `tests/test_repo_shape.py` plus `AGENTS.md` forbid a second one; that rule was a
guard against V4 code coming back.

| Option | Pros | Cons |
| --- | --- | --- |
| a. Add the module fork tag as Vendomat's second flake input `devenv`; the template writes `devenv: follows: vendomat/devenv`. | One `vendomat update` moves Vendomat and its tested modules together, as R28 does for Basix. No version pair to keep in step by hand. | Changes a durable shape rule (`test_repo_shape.py`, `AGENTS.md`). Needs a check that a `dir=src/modules` input works as a flake input of Vendomat. |
| b. The template pins the tag directly; `vendomat update` rewrites the tag to the one the Vendomat release names. | The flake shape rule stays. | Two places hold the version; `update` must edit `devenv.yaml` beyond adding missing lines. |
| c. The template pins the tag directly; the user moves it by hand. | Simplest code. | Vendomat and its modules can drift apart; contradicts the "tested pair" reason of R28. |

**Recommendation:** a.

### D3: how Basix publishes releases

**Ruled (R37), 2026-10-13: option a,** with the hook rule widened to any repository.

**Needed by:** S5. **Ledger:** `BSX-070`.

Facts: the collection's `hooks/collection-pre-receive` accepts only new tags, and a fast-forward
of `refs/heads/release` only for the repository named `vendomat`. Vendomat workspaces read
`git://server/vendomat?ref=release`.

| Option | Pros | Cons |
| --- | --- | --- |
| a. Same as Vendomat: immutable tags plus a fast-forward `release` branch; extend the hook to allow `release` for `basix`. | One update model for both products; `vendomat update` moves both along `release`. | A small hook change and test in the Vendomat repository. |
| b. Tags only; workspaces pin a tag. | No hook change. | An update must rewrite the tag in every workspace. |

**Recommendation:** a.

### D4: how the catalog knows a machine is installed

**Ruled (R42), 2026-10-13: option a.**

**Needed by:** S3. **Ledger:** `VMT-099`.

Facts: patch 0005 refuses `devenv machines install` for a machine whose
`machines.NAME.vendomat.mode` is `adopt-existing` (W6 B5). A module without the option fails open;
the catalog must set it. The Basix install writes `.machines/NAME/facter.json` and copies the
workspace into the new system (R13, R32).

| Option | Pros | Cons |
| --- | --- | --- |
| a. A committed `.machines/NAME/facter.json` means installed (`adopt-existing`); a YAML key `mode: fresh-install` overrides it for a deliberate reinstall. | Automatic; the install already writes the file. Safe by default after an install. | The devenv remote `facter` phase also writes the file before an install; a committed file from that phase would block the install until the user sets the override. |
| b. An explicit YAML key `installed: "true"` on every installed machine. | Plain and visible. | A user who forgets the key leaves a running machine unguarded. |
| c. Both: the file sets the default, the key overrides it either way. | Safe default and full control. | One more rule to explain. |

**Recommendation:** a (it is c with one override direction); S3 records the facter-phase case in a
fixture.

### D5: how Basix adds its keys to Vendomat's catalog

**Ruled (R38), 2026-10-13: option c,** a second file, `basix.yaml`. The recommendation below was a. The
Basix key types are ruled in the Basix repository (`../basix/.scratch/projects/001-initial-concept/DECISIONS.md`, Basix R1).

**Needed by:** S3 (the extension point), S5. **Ledger:** `BSX-059`, `BSX-065`.

Facts: Basix needs YAML keys `profile`, `capabilities`, `serve`, and `disk` in the machine table,
and a lesson hint in the shell line and `explain` (R26). The catalog rejects unknown keys and lists
the known ones (`VMT-032`). Vendomat must not import, test, or name Basix (R1).

| Option | Pros | Cons |
| --- | --- | --- |
| a. A typed extension point in the catalog, for example `vendomat.catalog.extraMachineKeys.<name> = { type; apply; }` and `vendomat.hatch.hint`; the unknown-key check consults it. | Basix registers keys without Vendomat naming Basix; errors stay in one list. | A public interface to keep stable. |
| b. Basix reads its own section of `vendomat.yaml` with its own copy of the parser. | No Vendomat interface. | Two parsers and two error lists; the catalog still rejects the Basix keys unless it skips them. |
| c. Basix keys live in a second file, for example `basix.yaml`. | Clean separation. | Breaks "one file" for the user (R6). |

**Recommendation:** a.

### D6: where each machine keeps the rollback record

**Ruled (R43), 2026-10-13: option a.**

**Needed by:** S4. **Ledger:** `VMT-098`, `VMT-110`.

Facts: R30 asks for a per-machine record from system path to workspace commit and rules out
`system.configurationRevision`. W9 found that a dirty work tree reads as `<HEAD>-dirty`, and that
two different dirty edits share that string.

| Option | Pros | Cons |
| --- | --- | --- |
| a. An append-only JSON Lines file `/var/lib/vendomat/generations.jsonl`, one line per apply (generation, toplevel, commit, dirty flag, time); `apply` refuses uncommitted changes to `vendomat.yaml`, `devenv.lock`, and hatch files unless `--dirty`; `rollback` uses clean entries only. | Simple to read and append; survives reboots; history is never rewritten. | A new file to back up with the machine; root writes it. |
| b. A file inside each generation's directory. | Tied to the generation it describes. | Generation directories are store links; writing beside them is fragile. |
| c. The record lives in the workspace repository (a commit per apply). | Version control holds the history. | The record then depends on the workspace being present and pushed; links to the recorded idea "a commit per apply" but adds noise. |

**Recommendation:** a.

### D7: the module fork's tag name

**Ruled (R44), 2026-10-13: option a.**

**Needed by:** S1. **Ledger:** `VMT-082`.

Facts: the collection already holds `v2.4.0-vendomat.2`, `.3`, and `.4` for the old binary fork.
Tags never move or disappear.

| Option | Pros | Cons |
| --- | --- | --- |
| a. `v2.4.0-vendomat-modules.N` | Names the upstream base and the kind of fork; cannot collide with the old tags. | Long. |
| b. `v2.4.0-vendomat.5` onward | Continues the old line. | Mixes a module-only tag with full binary forks under one name. |

**Recommendation:** a.

### D8: the personal setting that hides the `advanced:` line

**Ruled (R45), 2026-10-13: option a.**

**Needed by:** S3. **Ledger:** `VMT-093`.

Facts: R19 asks for a personal setting outside `vendomat.yaml`. The shell line counts settings in
`devenv.nix` and `devenv.local.nix`.

| Option | Pros | Cons |
| --- | --- | --- |
| a. An environment variable, `VENDOMAT_HIDE_ADVANCED=1`, in the user's shell profile. | Personal, needs no file in the workspace, applies to every workspace. | Invisible in the workspace itself. |
| b. An option in `devenv.local.nix`. | Lives with the checkout. | The setting would itself count as hatch use and appear in the line it hides. |
| c. A user config file, for example `~/.config/vendomat/config`. | Discoverable; room for later settings. | A new file format to define and prove. |

**Recommendation:** a.

### D9: configuration commits during apply

**Ruled (R49), 2026-10-14: option selected, "the proposed policy".** The owner chose the option label. The details below went beyond the question. They are implementer choices: an ignored file blocks even with `--dirty`; the config commit stays if activation fails; a watched-file rollback commits only its restored paths; `rollback --exact` keeps whole-tree meaning. R49 supersedes R43 in part, for apply only.

**Ledger:** `VMT-166`.

After `devenv build machines.NAME.build.nixos` succeeds, `vendomat apply` commits the current
contents of the four watched paths (`vendomat.yaml`, `devenv.lock`, `devenv.nix`, and
`devenv.local.nix`) before activation. The path-scoped commit leaves unrelated staged work in the
index. A present ignored watched file blocks apply until it is force-added or removed, including
with `--dirty`. `--dirty` skips the config commit and records the existing HEAD with `dirty: true`.
A build failure leaves the config uncommitted and does not activate or append a record line. A
successful config commit remains if activation later fails, so a retry builds the same committed
configuration. A watched-file rollback commits only its restored watched paths and preserves other
staged work; `rollback --exact` retains its whole-tree semantics.

### D10: the sharing module's network boundary

**Ruled (R50), 2026-10-14: option selected, "explicit trusted interfaces; unmarked closed".** The owner chose the option label. That the module opens no global port and that `serve = false` disables the key unit are implementer choices that the question did not state.

**Ledger:** `VMT-169`, gap `VMT-172`.

The NixOS module option is `vendomat.sharing.trustedInterfaces`, a list of interface names whose
incoming TCP 5000 traffic may reach Harmonia. It defaults to `[]`. The module opens no global
TCP 5000 port. `serve = false` disables the key unit, Harmonia, and the interface openings even if
the list is nonempty. The tests prove these parts:

- `opt:sharing-vm` (production module, three VMs): loopback and the trusted `eth1` answer on port
  5000; the untrusted `eth2` of `alpha` does not; `gamma` (serving, no trusted interface) does not
  answer on `eth1`; `beta` (`serve = false`) has no Harmonia unit, no key unit, and no listener.
- `test_serve_false_keeps_port_closed_even_with_a_trust_marker` (evaluation level only): with
  `serve = false` and a nonempty list, the module opens no port and enables no Harmonia. No VM boots
  that case.
- `test_a_serving_machine_with_the_firewall_off_gets_a_warning` (evaluation level): with
  `networking.firewall.enable = false`, port 5000 is open on every interface and the list has no
  effect, so the module warns.

The catalog has no YAML key for `trustedInterfaces` (gap `VMT-172`, no ruling).

## Ideas recorded, not pursued now

Catalog keys as an allow list of native option paths with one generic type converter; a JSON
Schema for editor completion; a commit per `apply`; machines that pull their own branch; one estate
repository whose machine keys define cache trust; capability directories with a module, a lesson,
and a check; an assistant that edits only the intent file.
