# Upstream facts, 2026-10-11

These facts come from upstream source and documentation. They are evidence about the upstream tools,
not passed gates. Full report with file paths and line numbers:
`~/.local/state/vendomat/v6/single-disk-cache/upstream/report.md`. Sources: nixpkgs
`e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`; Nix source 2.34.8 (the pin's `nix_2_34`; the host runs
2.34.7); harmonia 3.3.0; nix-serve-ng 1.1.0-unstable-2026-03-26; Garage 1.3.1; Tailscale 1.102.5
documentation; Attic config template at the pinned revision.

## Nix `file://` binary cache

| Fact | Source |
| --- | --- |
| Each file is written to `<file>.tmp.<pid>.<n>`, then renamed | `local-binary-cache-store.cc:73-85` |
| The NAR is written before the narinfo; the narinfo is signed and written last | `binary-cache-store.cc:270-286` |
| `nix copy` skips a path when its `<hash>.narinfo` exists; validity is the narinfo file alone | `store-api.cc:928,1026`; `binary-cache-store.cc:386-392` |
| Parameters: `compression` (default `xz`), `compression-level`, `parallel-compression`, `secret-key`, `secret-keys`, `write-nar-listing`, `index-debug-info`, `priority`, `want-mass-query` | `binary-cache-store.hh`, `store-api.hh:219-233` |
| No garbage collection and no delete for a binary cache store (`require<GcStore>` fails) | `store-delete.cc:37`, `store-gc.cc`, `store-cast.hh:15-23` |
| `secret-key` adds the cache signature to the source signatures | `binary-cache-store.cc:30-39,283` |

Inference: a killed push leaves no narinfo without a NAR. It can leave a `*.tmp.*` file and a complete
orphan NAR.

## `ssh-ng://`

| Fact | Source |
| --- | --- |
| Substitution from an untrusted store needs a signature by a key in `trusted-public-keys` (or `?trusted=1`) | `substitution-goal.cc:116,228`; `local-store.cc:975-978` |
| The client runs `nix-daemon --stdio` as the SSH login user | `ssh-store.cc:201-215` |
| A non-trusted receiving user cannot skip signature checks; an unsigned path is refused | `daemon.cc:504-508,909-910`; `local-store.cc:986-988` |
| `nix.sshServe`: `enable`, `write` (only for protocol `ssh`), `trusted`, `keys`, `protocol` (default `ssh`). It makes user `nix-ssh` with `ForceCommand` and no forwarding or TTY | `nixos/modules/services/misc/nix-ssh-serve.nix` |

## harmonia 3.3.0

- Reads the Nix SQLite database read-only and the store files directly. It does not use the daemon.
- Signs each narinfo on the fly with `sign_key_paths` and keeps the stored signatures.
- No authentication on reads. No upload. No allow-list: every valid path is served, file contents too.
- NixOS module `services.harmonia`: socket-activated, `DynamicUser`, `ProtectSystem=strict`, an empty
  capability set, and a system call filter. Its `gc.*` options collect the **local** store.
- Configuration keys include `bind`, `workers`, `priority` (module default 50), `sign_key_paths`,
  `enable_compression`.

## nix-serve-ng 1.1.0 (pinned)

Built against Lix in the pin. One signing key (`NIX_SECRET_KEY_FILE`); with a key, the narinfo
carries only the cache signature. No authentication, no upload, no allow-list. Module
`services.nix-serve` with `package = pkgs.nix-serve-ng`, little systemd hardening.

## Tailscale Serve

`tailscale serve --https=443 --set-path=/x <absolute dir>` serves a directory of static files
(https://tailscale.com/kb/1242/tailscale-serve; `ipn/ipnlocal/serve.go:1219-1260`, Go
`http.FileServer`). It adds no authentication. Tailnet membership and the tailnet policy are the only
gate.

## S3-compatible services

- Garage 1.3.1: a daemon with LMDB metadata by default (SQLite optional), `rpc_secret`, a layout
  assign and apply, a bucket, and an S3 key, even on one node.
- MinIO: the community repository is archived and says it is no longer maintained (`gh api`:
  `archived: true`, last push 2026-04-24). nixpkgs still carries `2025-10-15`.

## Attic 0.1.0 retention

`[garbage-collection] interval` (default 12 h; 0 disables) and `default-retention-period` (default 0,
which disables time-based deletion). `attic cache configure --retention-period` sets one cache's
period. Source: `server/src/config-template.toml:117-132`.
