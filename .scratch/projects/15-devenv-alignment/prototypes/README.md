# Prototypes from the 2026-10-09 fixtures

Each file is a disposable-fixture prototype, not reviewed code. It proves a mechanism on
devenv 2.4.0. The agent report in `../raw/` gives the commands and results.

| File | What it proves | Source |
| --- | --- | --- |
| `vendomat-module.nix` | The Vendomat devenv module: face auto-import, pin assertion, push task, input paths, host paths, profile defaults, Machines disk guard | Agent K, tag v14 |
| `vendomat_sync.py` | The pre-resolver: writes `.vendomat/devenv.yaml`, flattens transitive inputs and `follows`, writes the digest | Agent I |
| `vendomat.direnv.sh` | `use_vendomat`: re-syncs on change, then `use devenv` | Agent I |
| `devenv-v2.4.0-vendomat.1.patch` | The patched devenv series (`git format-patch`) | Agent J |
| `devenv-dist-flake.nix` | Builds and installs the patched devenv from a fork input | Agent J |
| `check_pins.py` | Tag-pin check over `devenv.yaml` and the whole `devenv.lock` | Agent H |
| `lockpath.nix` | Store path of a locked input, offline | Agent H |
| `devenv-pin-check.py` | Fleet scan of devenv module pins and `require_version` | Agent G |
| `vendomat-module-described.nix` | The module with the builder: devenv, NixOS, and Home Manager modules built from each input's `vendomat` description | Agent L |
| `library-description-example.nix` | A library flake with a `vendomat` description and no Vendomat input | Agent L |
| `face-check.sh` | The inertness check: shell, NixOS, and Home Manager derivations with and without a library | Agent L |
