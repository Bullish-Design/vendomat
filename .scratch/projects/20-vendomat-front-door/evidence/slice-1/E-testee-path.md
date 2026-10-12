# Slice 1, lane E: Testee's devenv path

Date: 2026-10-12. This research changed no source file.

Testee 0.6.1 invokes `devenv` by name. It resolves the binary from its inherited `PATH` for
version, evaluation, and check execution. It has no setting for a binary path. A workspace cannot
select the evaluator that reads that workspace.

The host's normal `PATH` selects stock devenv before the profile fork. The slice 1 gates therefore
put the `.4` fork first when they call Testee. Testee then uses that fork for all three calls. A
stock-first call refuses the Vendomat module because stock devenv has no `vendomatFromYAML` primop.

The raw record and its logs are at
`~/.local/state/vendomat/p20/2026-10-12/slice-1/E-testee/RECORD.md`. The record includes the
source inspection, PATH control runs, fork runs, and a Testee patch prototype. The prototype is
research only; this slice does not change Testee or the host profile.
