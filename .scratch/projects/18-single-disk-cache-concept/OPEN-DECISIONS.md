# Project 18 open decisions

**Date:** 2026-10-11. Each item needs the owner. Each gives the options and one recommendation.
Evidence: [CONCEPT.md](CONCEPT.md) and [evidence/](evidence/README.md).

## 1. Which cache design

1. **B, static directory** (`nix copy --to file://`, SSH-forced publish, read-only file route).
2. A, harmonia over the server store (no copy, no publish on `server`; serves the whole store).
3. E, Attic on the root disk (carry `CACHE-013`; move the database and storage to `/`).
4. No change before the cutover; decide after `server` runs on the new disk.

**Recommendation: 1.** It removes the daemon, the database, and the patch, and it keeps the publish
boundary. Its mechanism passed on this host; its production route is unproved.

## 2. Pull access on the tailnet (closes PV-09 by decision)

1. **Tailnet-only reads, no pull secret.** Any device that can reach `server` over the tailnet can read
   build outputs. The tailnet policy can narrow that set. This equals the collection's `git://` rule.
2. Keep a pull secret: Caddy with basic authentication in front of the directory, and a netrc on each
   client. PV-09 stays open.

**Recommendation: 1.** The installer then needs only tailnet membership and the public key.

## 3. How the read route is served

1. **Tailscale Serve file route** (`tailscale serve --https=443 --set-path=/cache <dir>`): no new
   service. Documented; not tested here.
2. Caddy on loopback behind Tailscale Serve: one more service; tested here as the stand-in.

**Recommendation: 1**, with a VM or a live check first. Fall back to 2 if the file route fails a check.

## 4. What happens to the 69 GB of Attic data

1. **Start empty.** Publish the new system closure, the fork, and Vendomat after the first boot. The
   builder republishes from release tags. The old Attic stays readable on the old system.
2. Copy selected roots from the old Attic into the new cache with `nix copy` before retiring it.

**Recommendation: 1.** The data holds many test objects. Every wanted output can be rebuilt from tags.

## 5. Retention

1. **None for now.** Every published path stays. Watch the bytes used. This equals today (Attic has
   no retention period).
2. A NixOS timer in `nix-systems` that deletes by an owner rule, then unnamed NARs, then old temp files.

**Recommendation: 1.** Revisit when the cache passes an owner-set size.

## 6. Scope of "one disk"

1. **The cache and the new role only.** The restic repository on `/mnt/wd_green1` and the data on
   `/mnt/shared` are separate decisions; the new role does not mount either.
2. Every service and every byte of `server` moves to the 4 TB disk, including the restic repository.

**Recommendation: 1.** A backup on the disk it protects gives no protection. That choice belongs to
the backup project, not to the cache.

## 7. The cache signing key

1. **A new key** (`nix key generate-secret`), stored with sops-nix like `attic-signing-key` today. The
   core trusts the new key.
2. Reuse the Attic `vendomat` key pair, so `trusted-public-keys` does not change. Untested: it needs
   the key read from the Attic database.

**Recommendation: 1.** The new system starts clean, and the old key stays valid for the old cache.

## 8. Cutover step 8 (the `/mnt` refusal)

1. **Keep step 8:** stop `atticd`, unmount both data disks for the install, remount after.
2. First move the old system's mount points out of `/mnt` with a `nix-meta` change.

**Recommendation: 1.** It is already written and reviewed. One disk does not remove it.
