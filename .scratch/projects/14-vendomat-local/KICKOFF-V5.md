# V5 implementation kickoff prompt

Paste everything below the line into a clean session.

---

Start the Vendomat V5 implementation. Work in `/home/andrew/Documents/Projects/vendomat`.

## Read these first, in this order

All in `.scratch/projects/14-vendomat-local/`:

1. `CONCEPT-V5.md` — the shape and the worked examples.
2. `SPEC-V5.md` — normative. 141 requirement IDs, each with a Verify column.
3. `GUIDE-V5.md` — the commands. Steps 0 to 10.
4. `REFINEMENT-2026-10-08.md` — named paths and drive identity.

## Authority

`AGENTS.md` holds durable rules and points at `.scratch/CURRENT.md`, which names this project as
active. The four documents listed above are the only authority for this work. Treat anything in
`docs/` or in another `.scratch/projects/` directory as history unless one of those four cites it.

## What V5 is, in four sentences

Vendomat makes the owner's projects resolvable by local path and already built. You declare inputs
one level deep in `vendomat.toml`; Vendomat generates a `flake.nix` naming only those direct inputs,
and Nix resolves the transitive graph into `flake.lock`. Machine settings
live in dotted-path TOML converted to real NixOS options. One Attic cache over Tailscale means
nothing builds twice.

Vendomat owns no durable state. Native tools do the merging, conflict detection, substitution, and
activation.

## Ground truth as of 2026-10-08

**Safety — read before any disk command.**

- `/dev/nvme0n1` is the **running 512 GB system**: `/boot`, swap, and `/` (`nvme0n1p3[/@]`).
  On 2026-10-07 that same name was the empty 4 TB drive. **Never partition or format by kernel
  device name.** Use `/dev/disk/by-id/`.
- The 4 TB target is `nvme-eui.e8238fa6bf530001001b448b4fbe837d` (today `/dev/nvme1n1`), bare: no
  partition table, no filesystem, no mount.
- `sudo` is at `/run/wrappers/bin/sudo`. The copy first on `PATH` is not setuid and fails with a
  misleading message. This is not a broken system.

**Fleet.** `server` (Dell Precision 5820, headless, `x86_64-linux`) is the only live host and runs
`atticd` and the builder. The laptop `framework` (`x86_64-linux`) is installed last, in step 10, and
has been unreachable since 2026-10-07. **No step before 10 may depend on it** (`BOOT-018`,
`BOOT-020`). `nix-meta/flake.nix:289` records that the earlier `wsl` and `desktop` hosts were
retired; `nixosConfigurations` holds only `server`.

**Drive inventory.** All four identifiers and all four filesystem UUIDs resolved on 2026-10-08.

| Logical name | Hardware identifier | Filesystem UUID |
| --- | --- | --- |
| `new-system`, WD Blue SN5100 4 TB | `nvme-eui.e8238fa6bf530001001b448b4fbe837d` | none yet |
| `previous-system`, NX-512 512 GB | `nvme-NX-512_2280_0040141310300` | root `e6b180fa-534a-4b71-aff8-f9fe2e6d0834`, EFI `0086-EC69` |
| `backup`, WD Green (Attic + restic) | `wwn-0x50014ee2adca73d5` | `21488349-01cb-4efe-9d21-a72f74a908e0` |
| `shared`, TEAM SSD | `ata-TEAM_TM8PS7002T_TPBF2308070030300443` | `C24C954D4C953CDB` |

**Pins and cache.**

| Item | Value |
| --- | --- |
| Nix | 2.34.7 |
| devenv | 2.4.0+b904dcb |
| Attic | server and client `attic-0-unstable-2026-06-26` |
| Cache | `vendomat`, private, priority 20, retention 0 |
| Cache key | `vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA=` |
| Attic listen | `127.0.0.1:8089`, Tailscale Serve at `/attic` |
| Canary path | `/nix/store/l6imh86vz9ic4cmyikisxszrrfvs7ab8-nvim-review-editor` — already in the cache. Use it to test whether the cache answers |

**Existing trees.** `src/vendomat/` (3,926 lines) is the current code surface. It is **provenance,
not a base.** V5 starts from a bare source tree in this repository; the git history stays.
`nvim-review` and `nix-nvim` are real repositories in `~/Documents/Projects/` that V5 converts.

## Your scope for this session: steps 0 to 3

Stop at the end of step 3. Those four steps write to **no disk** and activate **nothing**.

**Step 0 — drive identity preflight.** Write and run the read-only preflight from `GUIDE-V5.md`
§0.2. It resolves every declared identifier and UUID, then refuses the target if it backs `/`,
`/boot`, `/nix`, or `/home`, or carries a filesystem, partition table, or mount. Then run the two
deliberate failure tests: point it at the running system's drive and at the WD Green, and confirm
both abort naming the reason. Satisfies `DISK-001` to `DISK-005`.

**Step 1 — the machine core.** Write `core/default.nix`. It holds only what both machines need to
boot and be reachable. `atticd`, the builder, and restic are `server` deltas; Hyprland, power
management, and wifi are laptop deltas. Use `lib.mkDefault` for any value a host may override.
Satisfies `BOOT-001`, `BOOT-003`, `BOOT-016`.

**Step 2 — cache access inside the core.** First confirm the substituter URL; it is unverified.
Then add the substituter, the trusted key, and `netrc-file`. The pull token comes from sops,
root-only, and must never enter a tracked file or a store path. Satisfies `BOOT-002`, `CACHE-001`,
`CACHE-002`.

**Step 3 — prove the core in a virtual machine.** Add a throwaway `vmtest` host,
`nixos-rebuild build-vm`, boot it, and confirm it reaches a login with the substituter configured.
Satisfies `BOOT-006`.

## Rules

- Open one Gitman lane per step. Never run raw `git` or `jj`.
- Verify with `devenv shell -- testee verify --mode quick`. Do not call pytest or ruff directly.
- A requirement is satisfied when its Verify column runs and passes. A document never satisfies a
  requirement. There are no phases and no gates — each step has one **Stop if** condition.
- Do not write any Python this session. Steps 1 to 7 need none, deliberately: the Nix layer must
  stand alone so broken tooling can never stop a machine booting (`BOOT-009`).
- Record each step's date, commands, and result. Keep raw logs in
  `~/.local/state/vendomat/v5/<date>/`.
- Preserve every requirement ID. Never reuse or renumber one. Mark a changed requirement
  *Superseded by* a new ID; do not edit it in place. When you supersede one, grep for duplicates —
  `BOOT-004` and `BOOT-011` both carried the same claim and only one was caught the first time.
- If a fixture disproves the specification, update the specification, the guide, and the concept
  together. Do not leave the three disagreeing.

## Do not

- Partition or format anything this session. Step 0 is read-only.
- Touch the 512 GB drive. It is the fallback and must stay independently bootable (`BOOT-021`).
- Move the Attic data. It stays on the WD Green disk until after the new root boots (step 7.8).
- Re-open settled decisions: publication is ambient with no receipt;
  Vendomat selects no revision and never touches `flake.lock`; the command line is system-installed
  and no consumer declares Vendomat as a flake input; `server` is installed fresh on the 4 TB drive
  rather than converted in place; the laptop comes last.

## Open questions — ask, do not invent

| Question | Blocks |
| --- | --- |
| Is the substituter URL `https://server.tail770f47.ts.net/attic/vendomat`? | Step 2 |
| Confirm 90-day Attic retention and `nix.gc --delete-older-than 30d`? Recorded as decided; apply before step 7.8 | Step 7.8 |
| Does the laptop keep the name `framework`? | Step 10 |

## First reply

Before you write anything: list the requirement IDs you intend to satisfy in this session, name the
files you will create, and state the one thing you will check before each disk-adjacent command.
Then begin with step 0.
