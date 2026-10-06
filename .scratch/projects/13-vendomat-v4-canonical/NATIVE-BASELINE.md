# Native baseline record

**Date:** 2026-10-06. **Status:** Canonical record. **Not a gate.**

These 24 facts assert the behaviour of Nix, devenv, NixOS, Home Manager, or Attic. Vendomat cannot
make them true or false. Observe each one once on the pinned versions and record the result here.
They keep their original ID strings so earlier references stay resolvable. None of them gates a V4
phase.

A documented upstream fact is evidence about the upstream tool. It is not a passed gate. Record the
observing command, its exit status, and the tool version beside each row when the pin is set.

## Pinned versions

Recorded in [docs/V4_PIN_RECORD.md](../../../docs/V4_PIN_RECORD.md). Raw logs are in
`/home/andrew/.local/state/vendomat/v4-proof/2026-10-06/baseline/`.

| Tool | Pinned version | Observed on |
| --- | --- | --- |
| Nix | `2.34.7` | `server`, `nix --version` (`versions-nix.txt`) |
| devenv executable | `2.4.0+b904dcb` | `server`, `devenv --version` (`versions-devenv.txt`) |
| devenv module revision | `cachix/devenv` `src/modules` `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4` | Repository `devenv.lock` (`repo-devenv-lock.log`) |
| Nixpkgs | `cachix/devenv-nixpkgs` `256551e45f6303e142ab4a98be1bf243feb77dc0` | Repository `devenv.lock` (`repo-devenv-lock.log`) |
| Home Manager | `fae6e9e42c3b762ab47635cddcfaf6f52374a61b` (P0 fixture lock only) | `fixture-locks.log`. Host version not observed |
| Attic server | `attic-0-unstable-2026-06-26` | `server`, `systemctl show atticd.service -p ExecStart` (`attic-server-unit-and-root.log`) |
| Attic client | Not installed | Pending P5. `attic-client.log` |

## The 24 facts

| ID | Native fact | Owner | How to observe |
| --- | --- | --- | --- |
| `V4-OWN-005` | Reading a store path changes no lock and no installed output. The store is immutable. | Nix | Record file hashes and selected paths. Read a retained path. Compare. |
| `V4-OWN-006` | Evaluating a devenv module starts no process and activates no user or system configuration. | devenv, Nix | Evaluate a module. Observe no service start and no activation. |
| `V4-MOD-003` | Typed Nix options reject an invalid type at evaluation. | Nix module system | Evaluate a valid and an invalid option value. The invalid value fails natively. |
| `V4-MOD-006` | Incompatible declared options produce a native merge conflict or assertion failure, with no silent choice. | Nix module system | Compose conflicting declared values. Inspect the native diagnostic. |
| `V4-MOD-007` | Requesting an absent target export fails and names the missing attribute. | Nix | Import a target absent from the fixture module. Inspect the native failure. |
| `V4-MOD-013` | devenv merges an imported `devenv.yaml` only for local relative or absolute paths inside the git root. Remote inputs are not merged. `--from` for a non-path source does not merge the remote `devenv.yaml`. | devenv | Add an input to a remote author's `devenv.yaml`. Confirm the consumer does not receive it. Documented at devenv.sh/composing-using-imports. |
| `V4-SRC-005` | A NAR hash is recorded in Subresource Integrity format, which names its algorithm. `nix path-info` reports the hashed representation, and `--json-format` selects string or structured form. | Nix | `nix path-info --json --json-format 2` on a retained path. |
| `V4-SRC-010` | A fixed-output derivation's content address is verified after the build. A mismatch fails the build. Failing bytes register as a valid store object but not as the derivation's output. | Nix | Supply wrong fixed-output source bytes. Observe the native validation failure. |
| `V4-SRC-012` | A store path cannot be mutated through normal access. | Nix | Attempt a write to a retained store path. Confirm the denial. |
| `V4-SRC-016` | Project evaluation needs no mounted remote tree, because retained source is a store path. | Nix | Evaluate the accepted project with no network path to the cache. |
| `V4-SRC-017` | Application startup needs no mounted remote tree, for the same reason. | Nix | Start the accepted application with no network path to the cache. |
| `V4-CACHE-004` | `attic push` pushes the closure by default. `--no-closure` disables it. The client-side upstream filter drops paths signed by a key in the cache's upstream key list, whose default is the single entry `cache.nixos.org-1`. `--ignore-upstream-cache-filter` disables the filter, and `attic cache configure --upstream-cache-key-name` sets the list. | Attic | `attic cache info` lists the upstream cache keys. Push a public-cache-signed path with and without the flag. |
| `V4-CACHE-007` | An upload failure leaves the local realized output usable. | Nix | Deny the upload. Run the local output afterwards. |
| `V4-CACHE-010` | Substituter order and public-cache fallback follow `substituters`, per-cache `priority`, and `fallback`. Attic's documented default priority is 41; the public NixOS cache uses 40. | Nix, NixOS | `nix show-config`. Trace with Attic present, absent, and missing one path. |
| `V4-CACHE-011` | Build fallback for an unavailable cache follows the `fallback` setting. | Nix, NixOS | Block Attic and the public cache. Observe the configured behaviour. |
| `V4-CACHE-012` | Nix accepts a non-content-addressed path from a cache only when a trusted key signed it, or `require-sigs` is false, or the store is marked trusted. Attic signs at read time with its per-cache server key, so regenerating that key invalidates every consumer's trust setting. | Nix, Attic | Offer a correctly signed and a wrong-key path. Inspect acceptance. |
| `V4-REC-012` | Mutable application state written at runtime leaves an immutable output path and its NAR hash unchanged. | Nix | Write application data. Re-query the output path and hash. |
| `V4-MACH-003` | `devenv machines plan` writes `plan.json` with a `plan-` identifier and one garbage-collection root per output. The identifier is random, not content-addressed. | devenv Machines | `devenv machines plan <name> --json`. Compare the plan paths with native Nix outputs. |
| `V4-MACH-005` | `apply` uses the saved plan outputs without rebuilding. | devenv Machines | Save a plan, block the build facility, apply, and observe the exact output use. |
| `V4-MACH-006` | `apply` rejects a stale plan for the NixOS role when target generations or SSH access facts changed. It does **not** check staleness against the lock or a re-evaluation. The nix-darwin and Home Manager roles have no staleness check. | devenv Machines | Change the target generation. Apply the old plan. Inspect the native rejection message. |
| `V4-MACH-008` | Transfer during `apply` is a direct `nix copy --to ssh://<target>`. It never substitutes through Attic. Substituters are used only with `--use-machines-as-builders`. | devenv Machines | Trace target traffic during apply. Only one outcome is possible. |
| `V4-MACH-010` | Native status reports an unknown or pending NixOS activation. | devenv Machines | Interrupt the controller confirmation. Query `devenv machines status`. |
| `V4-MACH-012` | A whole-system candidate is tested through native activation or a virtual machine. A sandbox cannot substitute for it. | NixOS | Build and activate a native generation, or run a VM fixture. |
| `V4-MACH-014` | A persistent native service reaches its declared health result after apply. The NixOS watchdog default deadline is 300 seconds, bounded to 30–600. | NixOS, devenv Machines | Apply the plan. Inspect the systemd service and the declared health check on the target. |

## Observation record, 2026-10-06

Status values: **observed** means the row ran in full on this pin. **Observed in part** means the
Nix layer ran and the Attic or NixOS layer is pending. **Pending** means no run yet. The phase
column names what unblocks a pending row. Raw logs are in
`/home/andrew/.local/state/vendomat/v4-proof/2026-10-06/baseline/`. Each file below sits there.
Observed facts are evidence, not gates.

| ID | Status | Result on this pin | Evidence file or unblocking phase |
| --- | --- | --- | --- |
| `V4-OWN-005` | observed | Reading a store file left the store file and the repository `flake.lock` hashes unchanged | `V4-OWN-005.log` |
| `V4-OWN-006` | observed | `devenv build` of a project with one process started no process and wrote no marker | `V4-OWN-006.log` |
| `V4-MOD-003` | observed | Int option accepts `1`. Rejects `"x"` with "not of type `signed integer'" | `V4-MOD-003.log` |
| `V4-MOD-006` | observed | Two different values for a `str` option fail with "conflicting definition values". No silent choice | `V4-MOD-006.log` |
| `V4-MOD-007` | observed | Absent flake output fails and names the missing attribute | `V4-MOD-007.log` |
| `V4-MOD-013` | pending | Needs a plain consumer and a git root. Raw git is barred for this task. Owner route needed | P2 (BLK-P2-01) |
| `V4-SRC-005` | observed | `nix path-info --json --json-format 2` reports `narHash` as `sha256-...` (SRI) | `V4-SRC-005.log` |
| `V4-SRC-010` | observed | Wrong fixed-output hash fails with "hash mismatch". The bytes register at a sibling path. The specified output path stays invalid | `V4-SRC-010.log`, `V4-SRC-010-followup.log` |
| `V4-SRC-012` | observed | Append, remove, create, and chmod on a store path all denied | `V4-SRC-012.log` |
| `V4-SRC-016` | pending | Needs an accepted project with retained source and a network-denied evaluation | P3 |
| `V4-SRC-017` | pending | Needs an accepted application with retained source and a network-denied start | P3 |
| `V4-CACHE-004` | pending | Attic client not installed. Flag behaviour needs a cache and a client | P5 |
| `V4-CACHE-007` | observed in part | Denied `nix copy` left the output valid and runnable. Attic upload denial pending | `V4-CACHE-007.log`. Attic side: P5 |
| `V4-CACHE-010` | observed in part | Lower priority value is queried and used first. Run 1 and run 2 swap the winner. Attic trace pending | `V4-CACHE-010.log`. Attic side: P5 |
| `V4-CACHE-011` | observed in part | All substituters unreachable. Build ran under `fallback=false`. Mid-transfer failure pending | `V4-CACHE-011.log`. Mid-transfer side: P5 |
| `V4-CACHE-012` | observed in part | Correct key accepted. Wrong key rejected. `require-sigs=false` accepts. Attic signing pending | `V4-CACHE-012.log`. Attic side: P5 |
| `V4-REC-012` | observed | Output path and NAR hash unchanged after two runs that wrote state outside the store | `V4-REC-012.log` |
| `V4-MACH-003` | observed in part | Home Manager target plan wrote `plan.json` with a random `plan-` id. The id differs from the P0 run. Plan link is a registered GC root. NixOS plan pending | `V4-MACH-003.log`. NixOS side: P7 |
| `V4-MACH-005` | pending | Needs a NixOS target and a blocked build to show saved outputs are used | P7 (BLK-P7-01) |
| `V4-MACH-006` | pending | Needs a NixOS target whose generation changes after plan | P7 (BLK-P7-01) |
| `V4-MACH-008` | pending | Needs an apply to a reachable target and traffic capture | P7 (BLK-P7-01) |
| `V4-MACH-010` | pending | Needs an interrupted NixOS confirmation on a reachable target | P7 (BLK-P7-01) |
| `V4-MACH-012` | pending | Needs a native NixOS generation or VM fixture | P7 (BLK-P7-01) |
| `V4-MACH-014` | pending | Needs a persistent NixOS service on a reachable target | P7 (BLK-P7-01) |

Fourteen rows are observed or observed in part. Ten rows are pending.

## Seven open experiments the research closed

The earlier contract listed these as experiments needing fixtures. Upstream documentation and source
answer them. Record the answer; run no fixture to decide the design.

| Earlier experiment | Answer | Effect |
| --- | --- | --- |
| `P-ATTIC`, filter half | One flag or one cache setting, as in `V4-CACHE-004`. | The remaining `P-ATTIC` work is the availability proof only. |
| `P-NAR-IDENTITY` | Attic re-hashes every upload and rejects a mismatch. Nix re-hashes every import and rejects a mismatch. | Byte identity is enforced natively at both ends. One end-to-end comparison remains, as `V4-CACHE-015`. |
| `P-MACHINES` | Transfer is always a direct copy, as in `V4-MACH-008`. | Withdrawn. V4 makes no machine transfer claim. |
| `P-DELIVERY`, plain-repository half | Remote `devenv.yaml` is not merged, as in `V4-MOD-013`. | A plain consumer declares the module's inputs itself. |
| `P-EDITOR` | `wrapNeovimUnstable` with `wrapRc = true` sets `VIMINIT` to the generated Lua path through `--set-default`, which isolates configuration. Plugins are ordinary `buildVimPlugin` derivations usable in both forms. `neovimRequireCheckHook` is a native plugin check. | Withdrawn as a design question. It stays a P1 scenario. |
| `P-SOURCE`, locked-input half | `nix flake metadata --json` gives each input's `rev` and `narHash`. `nix flake archive` copies every input's source tree into a store. A `gcroots` symlink pins it. | No Vendomat source format is needed for locked inputs. |
| `P-CAPTURE-LIST` | Not needed. The archive covers every locked input. | Withdrawn with `D-CAPTURE-GRAPH`. |

Two further native facts shape the design and have no requirement of their own:

- **`nix flake archive --to <attic url>` cannot work.** Attic's binary-cache route serves `GET` only
  for `nix-cache-info`, narinfo, and NAR. Uploads use a separate endpoint. Source distribution is
  therefore two steps: archive into the local store, then `attic push` those paths.
- **`attic push` emits no machine-readable output.** Its output is prefixed lines on standard error.
  Its exit status is nonzero if any path failed, while successful uploads remain on the server.
  Verify availability by querying the cache as a store.

## Two traps

Record these so no fixture relies on the wrong mechanism.

1. **A `devenv:enterShell` task failure does not block shell entry.** Upstream source states that
   shell entry proceeds even if some tasks fail. Never use an `enterShell` task as a gate.
2. **`devenv tasks run` exits 0 or 1 only, and prints its JSON output on success only.** A missing
   declared check is therefore indistinguishable from a failed one by exit status. Check existence
   with `devenv tasks list --json` first. This is the mechanism `V4-CHK-011` requires.
