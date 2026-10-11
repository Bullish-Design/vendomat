# Project 19 decisions

**Date:** 2026-10-11. Concept: [CONCEPT.md](CONCEPT.md).

## Decided by the owner, 2026-10-11

| # | Decision | Reason |
| --- | --- | --- |
| 1 | Basix is the minimal devenv configuration that defines a whole system. Vendomat is its source, store, and cache layer | The owner's definition |
| 2 | No off-host or off-disk copy of the cache. The cache is disposable | It is derived data; source rebuilds it |
| 3 | No push from other hosts. One host per installation serves its own store | Removes push routes, credentials, and a second copy |
| 4 | Harmonia is the one supported store server; the requirement says "a signed, read-only binary cache" | Tested here; sandboxed module; keeps signatures |
| 5 | Cache wiring is derived from the inventory; the key is made at setup; the public key is committed | One fact, stated once |
| 6 | Each built release tag gets a GC root; keep every tag by default; GC only under disk pressure on the building host | More reuse; tags are immutable |
| 7 | SecretSpec is required configuration from the first setup | Native to devenv; reaches a fresh install through `install.secrets` |

## Configuration with defaults, decided later

These do not change the design. Planning picks a default for each.

| Item | Proposed default |
| --- | --- |
| Network that harmonia listens on | Loopback plus one named interface; the firewall stays closed elsewhere |
| HTTP or TLS | HTTP on a trusted network; TLS optional |
| `min-free` / `max-free` | A fraction of the disk, so it suits any size |
| Release-root limit | Keep all; later "newest N per input" |
| Where a no-Nix user sets the cache-server mark | The inventory first; a `vendomat.toml` value when the machine values interface exists |
| Scheduled GC on non-building hosts | Unchanged native default |
| Evaluation-time builds (the four derivations in `DVN-006`) | Not rooted; a cold host builds them |
| Removal of `vendomat push` | In the next release, with a release note |
| Spec rows | Written in planning as successors; old IDs marked superseded, never reused |

## Open for planning

1. **First secret delivery to an adopted host.** `install.secrets` runs only on a fresh install.
   Options: a documented one-time copy over SSH; a fork patch that adds the same payload to `apply`;
   or SecretSpec resolved on the host by a first-boot unit.
2. **Which code moves to Basix.** The machine inventory, the install wrapper, and the disk guards
   define the system, so they may belong to Basix rather than Vendomat. The workspace bridge
   (`[imports]`, `[settings]`) may also be Basix's user interface. Planning decides the split; this
   concept places only source, store, and cache firmly in Vendomat.
3. **`nix-systems` becomes a Basix installation:** Basix plus the owner's own modules.
4. **Project 18** records stay as evidence. Its candidate B recommendation is superseded by this
   concept.
