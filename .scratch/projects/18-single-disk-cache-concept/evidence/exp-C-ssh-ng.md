# Experiment C: `ssh-ng://` as push and pull route

**Date:** 2026-10-11, 08:23-08:28 EDT. Method, versions, and limits: [README.md](README.md).
Raw: `~/.local/state/vendomat/v6/single-disk-cache/runs/C/`.

## Setup

- The same throwaway `sshd` and forced `nix-daemon --stdio` as A. No HTTP server.
- Push: `nix copy --from local?root=/dev/shm/<src> --to ssh-ng://andrew@127.0.0.1`.
- Probe: `nix path-info --store ssh-ng://andrew@127.0.0.1 <path>` (one SSH connection each).
- The host does not sign locally built paths (`secret-key-files` is empty). The harness signed only its
  own unique paths with `nix store sign --key-file <throwaway key sdc-C-1>`.
- Cold: `nix copy --from ssh-ng://andrew@127.0.0.1 --to local?root=<scratch>/cold-*` with
  `--option substituters ''` and, in turn, (1) the throwaway key only, (2) the throwaway key plus
  `cache.nixos.org-1`.

## Expected

The unique path copies cold. The Vendomat closure fails with only the throwaway key, because no path in
it carries that key. With `cache.nixos.org-1` added, only the unsigned Vendomat package fails.

## Results (three runs)

| Measure | Median (min-max) |
| --- | --- |
| Unique 64 MiB push | 0.729 s (0.719-0.805) |
| `sync -f` on root after that push | 0.338 s (0.330-0.399) |
| NAR hash: source store = host store | equal, 3 of 3 |
| Vendomat closure "push" | 0.253 s (0.241-0.261): already valid on the host |
| Closure probes | 35 of 35 valid |
| Four concurrent 64 MiB pushes | exits 0,0,0,0; wall 1.226 s (1.136-1.284) |
| Probes during concurrent pushes | 3 per run, all valid, max 0.293 s (0.261-0.398) |
| Cold copy of the signed unique path | exit 0, 1.466 s (1.448-1.473); bytes equal |
| Cold copy of the closure, throwaway key only | exit 1: `cannot add path '…-mailcap-2.1.54' because it lacks a signature by a trusted key` (3 of 3) |
| Cold copy of the closure, plus `cache.nixos.org-1` | exit 1: `cannot add path '…-vendomat-0.7.0-rc.1' because it lacks a signature by a trusted key` (3 of 3) |
| Never-existing path | `nix path-info --store` exit 1, `is not valid` |
| Host-only path, never pushed | valid (served), 3 of 3 |
| Kill at 0.22, 0.43, 0.65 s | probe not valid after each kill (0.81-0.93 s per probe); retry exit 0 in 0.792 s (0.756-0.871); probe valid |

`sshd` logged every connection. Each run logged one `srclimit_penalise … deferred penalty of 1.000
seconds` line, caused by the harness's port check that connected without authenticating.

## Observations

- A probe over `ssh-ng` took 0.21-0.40 s. An HTTP narinfo probe took 1-3 ms (A, B) or up to 0.1 s (E).
- Cold substitution over `ssh-ng` needs a signature on every path by a trusted key. The server signs
  nothing it builds today.
- The served set is the whole host store, as in A.

## Inference

- C needs `secret-key-files` on the server, so new builds are signed, and a one-time `nix store sign`
  for older paths that must be served.
- C keeps PV-09 in another form. The daemon on each client (root) needs an SSH private key and a pinned
  host key for the cache. A cold installer needs both before its first substitution.
- OpenSSH `PerSourcePenalties` (`NAT-048`) can delay or refuse many short connections from one source.

## Not shown

The `nix.sshServe` module and its `nix-ssh` user, a non-trusted push, use as a substituter in
`nix.settings` by the root daemon, and connection reuse under a real build.
