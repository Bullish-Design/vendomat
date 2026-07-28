# Loci-Core integration development snapshot

This filtered flake input exposes Vendomat's uncommitted Project 04 implementation to Loci-Core
without staging or committing user work and without copying Vendomat's ignored `.devenv`, `.git`,
cache, or evidence directories into the Nix store.

It contains only the root flake/package metadata plus `lib/`, `modules/`, `src/`, and `vendor/` from
the Vendomat working tree. Replace Loci-Core's path input with the canonical Vendomat Git URL once
Project 04 has an authorized checkpoint commit.
