# R65: cache-key trust between two machines, proved in VMs

**Date:** 2026-10-16. **Ruling:** R65 (a part of R61, the two-machine check). **Owner words (verbatim):** "Great, agreed and approved. Permission granted for all changes. Kick off parallel background sonnet subagents to implement this."
**Rows:** `VMT-290` to `VMT-294`. **Check:** `opt:machines-trust` (`tests/test_machines_trust.py`, `tests/trust_vm.py`, `tests/fixtures/machines-trust/`).
**Run:** Testee run `20261016T155146Z-2c1a2073fb8c`, PASS, 8 passed, 0 failed, 0 skipped, 266.5 s. Tree `6be471a3d6` (the same tree as `testee verify` GREEN, run `20261016T155104Z-b86a85781247`, 4 of 4). An earlier run on the same test code before three lint fixes, `20261016T154201Z-1dc8edde5b84`, also passed 8 of 8; the values in the table below come from it. Raw logs: `~/.local/state/vendomat/p21/2026-10-16/s7/machines-trust/run-155146Z/` (the earlier run: `run-154202Z/`) (`results.log`, `commands.log`, `alpha-serial.log`, `beta-serial.log`).

## How trust works (observation from the code and the run)

1. Each machine that serves makes its own signing key at first boot (unit `vendomat-cache-key`). The public key is `/var/lib/vendomat/cache-key.pub`, named `HOSTNAME:BASE64`.
2. `vendomat apply` on the machine copies that file to `.machines/NAME/cache-key.pub` in the workspace and commits it (`VMT-282`).
3. The catalog (`devenv/devenv.nix`, `peersOf`) reads `.machines/PEER/cache-key.pub` of every other machine that serves. It reads the file when it evaluates the workspace. A machine whose file is missing gets no peer entry.
4. For each peer the catalog sets `vendomat.sharing.peers`: the URL `http://HOST:5000` and the public key. `devenv/sharing.nix` writes them to `nix.conf` as `extra-substituters` and `extra-trusted-public-keys`, with `fallback = true` and `connect-timeout = 5`.
5. So the public key of machine A must be in the workspace of machine B, as a committed file, before B evaluates and applies. The key changes the system of B (`nix.conf` is in `/etc`), so B must run `vendomat apply` after it holds the file. No other path carries trust. The key is not copied from the network.
6. B learns the address of A from the machine name, or from the `host:` key without its `user@` prefix (`peerHost`). The module writes no address. The name must resolve on B (DNS, a tailnet name, or `/etc/hosts`). The fixture uses `/etc/hosts`.
7. A answers on TCP port 5000 only on the interfaces in `trustedInterfaces` (`VMT-169`, `VMT-173`). The fixture lists `lan0`.

Inference: the workspace repository is the only channel for the key, so a user needs the commit of A in the workspace of B. How the commit travels (a shared remote, a pull) is outside Vendomat. The design expects one repository for the workspace.

## Design of the check

| Part | Choice |
| --- | --- |
| Machines | `alpha` and `beta`, both made by the real catalog (`imports: - vendomat/devenv`, a source copy as input `vendomat`) and devenv Machines. `virtual: "true"` and `trustedInterfaces: [lan0]` in `vendomat.yaml`. |
| Link | A second virtio card in each QEMU process. QEMU `dgram` netdev on UDP loopback ports of the host. A udev rule names the card `lan0` by MAC address. Addresses `10.77.0.1` and `10.77.0.2`. No host bridge, no host interface, no host block device. |
| Files | Images, cache, and state under `/mnt/shared/vendomat-p21/trust/run-STAMP`; the harness deletes them at the end. |
| Outside network | None. The harness cache on the user-mode network serves what the machines cannot build. QEMU runs in a transient user unit that answers ENOSYS to `io_uring_setup` (as `opt:machines-vm`). |
| Workspace repository | Born on alpha (commit C0). Beta gets a clone of C0. After alpha applies (commit C1), the harness carries C1 to beta as a Git bundle and beta runs `git pull --ff-only`. The harness plays the shared remote. The user types no other version-control command; `vendomat apply` on each machine commits the key itself. |
| New system of beta | The VMs cannot build offline. After C1 the harness builds the beta system of the same tree on the host and offers its six new store paths through the harness cache. The machine evaluates the same tree and must reach the same system path; the test asserts that. |
| A path only alpha has | Alpha builds a derivation with a random name (`nix-build -E`). Two such paths: one for the success, one for the controls. The test checks that beta does not hold them and the harness cache does not list them. |
| Memory | 3072 MB for each machine. No QEMU resource fault occurred (the S3 fault did not return). |

## Commands, expectations, and results (values from run `20261016T154201Z-1dc8edde5b84`; the final run repeats every step with new keys)

| Step | Command (in the machine) | Expected | Observed |
| --- | --- | --- | --- |
| 1 | read `/var/lib/vendomat/cache-key.pub`; `curl http://alpha:5000/nix-cache-info` on beta | both keys exist and differ; beta reaches alpha on `lan0`; the firewall of alpha names `lan0` and port 5000; beta `nix.conf` has no peer | pass. Keys `alpha:V3C50aaU...NwDk=` and `beta:p7eozFML...OQqQU=` |
| 2 | `vendomat apply` on alpha | `wrote .machines/alpha/cache-key.pub and put it in the commit`; clean tree; commit holds only the key; system unchanged | pass. Commit `ece3696e5a12` holds the key, equal to the machine file |
| 3 | `nix-build -E ...` on alpha; `test -e PATH` on beta | two paths on alpha only | pass |
| 4 | control 0: `nix-store -r PATH1` on beta | refused | rc 1: `path ... is required, but there is no substituter that can build it` |
| 5 | control 0b: same with `--option extra-substituters http://alpha:5000` | refused, because no trusted key | rc 1: `ignoring substitute ... from 'http://alpha:5000', as it's not signed by any of the keys in 'trusted-public-keys'` |
| 6 | `git pull --ff-only` on beta; `vendomat apply` on beta | the beta system equals the host build; no failed unit; beta commits its own key | pass. System `g7aigfi848nf...-nixos-system-beta`; failed units none |
| 7 | `cat /etc/nix/nix.conf`; `nix show-config` on beta | `extra-substituters = http://alpha:5000`; `extra-trusted-public-keys` is the committed key of alpha; the key is not in `trusted-public-keys` | pass |
| 8 | `nix-store -r PATH1 -v` on beta; `nix path-info --sigs`; `nix store verify --sigs-needed 1` | substituted from alpha, not from the harness cache; signature by `alpha:` key; verify passes | pass. `copying path ... from 'http://alpha:5000'...`; harness NAR downloads unchanged; signature `alpha:TDBb2pwM...`; verify ok |
| 9 | negative control 1: `nix-store -r PATH2 --option trusted-public-keys 'HARNESS-KEY alpha:WRONG'` | refused | rc 1: `not signed by any of the keys in 'trusted-public-keys'`; PATH2 absent |
| 10 | negative control 2: the same with `trusted-public-keys` = the harness key only | refused | rc 1, same text; PATH2 absent |
| 11 | control 3: `nix-store -r PATH2 -v` with the module settings | substituted from alpha | pass |
| 12 | end state | no failed unit, `running` on both | pass |

## Limits (observation and inference kept apart)

- Observation: the controls change `trusted-public-keys` on the command line. `--option extra-trusted-public-keys` only adds to the file value (first attempt, run `20261016T153706Z-5ca3d7383a23`: the wrong-key control passed the substitution, because the real key stayed in the list). This is a fault of the first test, not of the module.
- The wrong key and the missing key are command-line overrides on beta, not a committed wrong key. Inference: a committed wrong key gives the same settings text, so the same refusal.
- The harness, not a real remote, carries the commit. The host builds the next beta system, because the VMs have no network.
- Both machines are QEMU machines with generated hardware, not `framework` and `server`. The real-machine part of R61 stays open and needs the owner's yes.
- The name `alpha` resolves through `/etc/hosts`. A real network needs DNS or a tailnet name.
- The first run attempt `20261016T153010Z-8f1803d261f2` failed in the test code (it read a build log line as a store path). Nothing else failed.
