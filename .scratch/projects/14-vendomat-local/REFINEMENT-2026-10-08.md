# V5 refinement: paths and drive identity

**Date:** 2026-10-08. **Status:** Proposed. This refines [CONCEPT-V5.md](./CONCEPT-V5.md).
No disk or system configuration changed when this note was written.

## One declaration for a path

The host declares a named path once. Inputs refer to its name. Vendomat passes the value to
devenv shells, Home Manager programs, and NixOS services that request it.

```nix
# Proposed Vendomat options in the host's devenv.nix.
vendomat.paths = {
  notes = "/home/andrew/Notes";
  sources = "/home/andrew/vendor";
  attic = "/var/lib/attic";
};
```

An input can use `config.vendomat.paths.notes` during Nix evaluation. Vendomat can expose the
same value as `VENDOMAT_PATH_NOTES` when it starts a shell or an app. A service gets its own
environment setting. It does not inherit the devenv shell's environment.

These values are strings naming mutable locations. They are not Nix source paths. Vendomat must
not copy their contents into the Nix store when it evaluates a configuration.

The first implementation needs only names and absolute paths. Add ownership, creation, and
backup settings when a real input needs them. Use native user and service directories by default.

## One identity for a drive

A Linux kernel device name can change between boots. Vendomat records a stable identity for each
physical drive and uses stable identifiers for its partitions and filesystems.

| Use | Identifier | Reason |
| --- | --- | --- |
| Select a physical drive for partitioning | `/dev/disk/by-id/` with a serial, EUI, or WWN | Identifies the hardware before partitions exist |
| Identify a GPT partition | `/dev/disk/by-partuuid/` | Exists after partitioning, before formatting |
| Mount a filesystem | `/dev/disk/by-uuid/` | Identifies the formatted filesystem |
| Show a human-readable name | Label | A label is useful for display but can be duplicated |

Vendomat keeps a host inventory with logical names such as `system`, `previous-system`,
`shared`, and `backup`. Each entry records the hardware identifier. After formatting, the entry
also records the new partition and filesystem UUIDs. A reformat changes the filesystem UUID, so
Vendomat must update the inventory before generating a new mount configuration.

This is hardware inventory, not a dependency lock. A replaced drive requires an explicit
inventory change. Vendomat must not silently select a different drive with the same role.

### Observed `server` inventory

| Logical name | Observed hardware identifier | Observed filesystem UUID |
| --- | --- | --- |
| New system target, WD Blue SN5100 4 TB | `nvme-eui.e8238fa6bf530001001b448b4fbe837d` | None yet |
| Current system, NX-512 512 GB | `nvme-NX-512_2280_0040141310300` | Root: `e6b180fa-534a-4b71-aff8-f9fe2e6d0834`; EFI: `0086-EC69` |
| Attic source and restic disk, WD Green | `wwn-0x50014ee2adca73d5` | `21488349-01cb-4efe-9d21-a72f74a908e0` |
| Shared TEAM SSD | `ata-TEAM_TM8PS7002T_TPBF2308070030300443` | `C24C954D4C953CDB` |

These values were read on `server` on 2026-10-08. Confirm them on the machine before any disk
operation. PV-02 confirmed the target ID, model, serial, exact size, lack of visible partitions or
mounts in `lsblk`, and that the current system occupies the 512 GB drive. `wipefs --no-act` was
denied, so the target's partition-table and signature state is unknown. Do not call the target
bare. The 512 GB installation remains the boot fallback.

## Bootstrap rule

The new 4 TB drive becomes the unencrypted boot and root drive. It gets its own EFI System
Partition. The existing 512 GB drive and its EFI System Partition stay intact until the new
system has booted and run reliably.

Before a command can partition or format a drive, Vendomat must resolve the declared hardware
identifier and verify the model, serial, size, and absence of mounts and signatures. It must
also verify that the target is not the drive backing the running root or boot filesystem. A
missing identifier or any mismatch stops the operation. The command must use the stable
identifier, never a kernel-assigned device name.

PV-02's disposable checker rejected ten injected unsafe conditions, and its matching fixture
passed. The real target checker failed closed because it could not read partition-table and
signature data. That synthetic result does not unblock Step 0. An authorized read-only scan and a
reviewed checker remain required.

After formatting, Vendomat records the actual UUIDs and generates NixOS `fileSystems` entries
that use `/dev/disk/by-uuid/`. It verifies each UUID resolves to the expected drive before an
install or switch. A data service must require its declared mount so a missing disk cannot
silently redirect writes into the root filesystem.

The Attic service continues to use its old disk during the first boot. Move its data only after
the new root works. Its path then comes from `vendomat.paths.attic`.

PV-09 found that the private `vendomat` cache has retention 0 and is served through a tailnet-only
`/attic` route. The host-local endpoint fetched a closure into an empty alternate Nix store, but the
installer route and pull credential were not proven. Do not move Attic data or claim a cold install
until a disposable installer fixture passes.

## What this changes in the draft

The current V5 guide's Step 0 is withdrawn. It names `/dev/nvme0n1` as the empty 4 TB target. On
2026-10-08, that name belongs to the running 512 GB system. Do not run its partition or format
commands. Replace that step with a new, reviewed install procedure before disk work.

The first small proof should resolve the four observed hardware identifiers, match each one to the
expected filesystem UUIDs, and fail when an identity is absent or mismatched. It does not need to
format a disk. Step 0 remains blocked until the real target's signatures and partition table can be
read without writing to it.
