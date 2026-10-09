# Research fixture package

Imported from the owner's `v6-machine-research.zip` upload on 2026-10-09. The ZIP SHA-256 is
`af66cdcd7fda5246a3fb3f67fae78783c4b754adb0ef44f365fff547b5ec4341`.

These are **not production scripts** and are **not an executed NixOS VM acceptance test**.

- `policy_contract.py` demonstrates the intended decision predicate using Pydantic 2.13.5. `policy-results.json` records an actual run in the research sandbox. It does *not* represent upstream CLI enforcement.
- `capture-guest-state.sh` is a read-only guest evidence collector that refuses execution unless a disposable VM has `/etc/vendomat-vm-adoption-marker` and the operator sets `VENDOMAT_VM_GUEST=1`. It was syntax-checked, not run against a NixOS guest.
- `VM-TEST-PLAN.md` specifies the repeatable live VM scenarios, exact pins, required artifacts and acceptance interpretation. It is a test design, not a successful run.

The research sandbox has no `nix`, `qemu-system-x86_64`, `testee`, or `gitman`. No real disks, boot entries, or machines were changed.
