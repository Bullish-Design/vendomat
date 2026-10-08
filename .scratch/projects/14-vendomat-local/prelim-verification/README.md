# V5 preliminary verification

**State:** Planned. No spike in this directory has passed. No V5 implementation step has run.

This directory prepares the checks that must precede the V5 implementation. It is a work plan,
not an amendment to the V5 specification. The parent directory remains the authority until
evidence supports a documented change.

## Read order

1. Read [`../CONCEPT-V5.md`](../CONCEPT-V5.md) for the intended shape.
2. Read [`../SPEC-V5.md`](../SPEC-V5.md) for the active requirement IDs.
3. Read [`../GUIDE-V5.md`](../GUIDE-V5.md) for the proposed commands.
4. Read [`../REFINEMENT-2026-10-08.md`](../REFINEMENT-2026-10-08.md) for paths and drive identity.
5. Read [`SPIKES.md`](SPIKES.md) for the questions, fixtures, and pass conditions.
6. Read [`EVIDENCE.md`](EVIDENCE.md) before recording a result.
7. Use [`KICKOFF.md`](KICKOFF.md) to start the verification session.

`../KICKOFF-V5.md` starts implementation. Do not use it for preliminary verification.

## Boundaries

- Run disposable Nix fixtures and read-only checks now. Keep physical disk writes for a later,
  reviewed install procedure.
- Do not run `nixos-rebuild switch`, `nixos-install`, `parted`, `mkfs`, or production cache
  retention changes during this work.
- A virtual machine or disposable disk image may receive writes. Identify the image explicitly.
- Keep raw logs under `~/.local/state/vendomat/v5/prelim-verification/<date>/`.
- Use Gitman for every version-control action. Use Testee for repository verification.
- Keep observations, inferences, and proposed changes separate.

## Outcome

The work is ready for implementation when every P0 spike has a result, every blocker has an
owner or a resolution, and the concept, specification, guide, and kickoff agree. A result can
pass, fail, or remain blocked. A documented upstream fact cannot count as a passed fixture.

The final report must name the exact limits of the concept. It must state which guarantees were
weakened, which mechanisms changed, and which requirements were superseded. Preserve all existing
requirement IDs.
