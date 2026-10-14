# Basix-request contract spikes — 2026-10-14

These are disposable fixture results, not S3, S4, S5, or Basix acceptance gates. The complete
inputs, scripts, command lines, stdout, stderr, source hashes, and a longer observation/inference
split are outside the repository at
`/home/andrew/.local/state/vendomat/p21/2026-10-14/contract-spikes/REPORT.md`.

## Inputs and boundary

- Nix 2.34.7, devenv 2.4.0+b904dcb, Git 2.54.0; Nixpkgs was selected from the Vendomat
  `flake.lock`. Vendomat local and `origin/main` were both `ccd419d` at the final inspection.
- The inspected S3 catalog tree was detached at `80aa775` with unlanded S3 changes. The parser
  hash was `3df1e9af58c198748f18bab7ca1bbab8df613936892f13d2a64a755fb6339b33`;
  the hashes of the other inspected files are in the external report. Fixtures ran from an
  external scratch directory. Neither product repository was changed by the fixtures.
- The stub catalog fixture was `tests/nix/catalog.nix` on the pinned Nixpkgs. The parser
  fixture called `devenv/parse.nix` directly. Python fixtures ran through
  `devenv shell --from path:<S3 workspace> -- uv run --no-project python contract_fixture.py`.
  No real Basix consumer or published S1 input was involved.

## Observations

| Request | Command and expected result | Actual result |
| --- | --- | --- |
| VR1 parser | `nix-instantiate --eval --strict --json --expr` imported `devenv/parse.nix` as `file: text:` with `basix.yaml` and read `at [ "machines" "learner" "profile" ]`; expected parsed value and position. | Exit 0; `profile = "console"`, key `3:5`, value `3:14`. A copy of the stub catalog fixture exposing `config.vendomat.parsed` returned the names `learner` and `spare` (exit 0). |
| VR2 template | The external `contract_fixture.py` passed a Basix-style imported template explicitly to `update.plan`; expected the missing `follows` and import lines, preserving authored lines. | Exit 0; added `vendomat`, `nixpkgs`, `devenv`, and `basix/devenv`; authored `mytool`, `./local.nix`, and a comment remained. `update.template_dir()` did not select that imported template. The launcher still selects its bundled template for `new`. |
| VR6 programs | `nix-instantiate --eval --strict --json tests/nix/catalog.nix` read a scratch `vendomat.yaml` with a `machines.learner.programs` block list containing `ripgrep`; expected the requested machine-package mapping. | Exit 1: `vendomat.yaml:4:5: machines.learner.programs: unknown key (known: host, mode, serve, virtual)`. |
| VR4 errors | Python `errortrim.trim` and the launcher's Bash `trim_error` read a scratch trace containing `basix.yaml:3:14: invalid profile`; expected that line first under VR4. | Both returned only `configuration failed`, dropping the `basix.yaml` line from the short error. The full trace stayed in the fixture. |
| VR3 commit | `vr3-fixture.sh` used `git commit --only -- vendomat.yaml devenv.lock devenv.nix` in an isolated scratch Git repository; expected only configuration files committed. | Exit 0; `vendomat.yaml` and `devenv.lock` committed, unrelated staged `notes.md` remained. A simulated failed build left the configuration commit but no generation record. An untracked template file needed `git add -N` before `commit --only`; normal status hid an ignored `devenv.local.nix`. |

The exact commands, pinned revision, file contents, exit codes, and raw outputs for each row are
in the external report and its adjacent files. These direct results prove only the small
interfaces exercised there. They do not close `VMT-117`, `VMT-121`, or any slice.

## Inferences and next proofs

- **VR1:** The current parser and parsed option have the shape Basix needs. Vendomat still must
  promise a stable path/interface, publish it, and prove a real Basix consumer against the
  published module input.
- **VR2:** The merge algorithm can preserve Basix's `follows` lines when supplied with its
  template. Vendomat must decide a tracked workspace source and a `new` source interface,
  resolve an imported input through the lock, and run a real one-update consumer fixture.
- **VR6:** The schema, package-name check, NixOS package mapping, and error/explain fixtures
  remain. Validate real `machines.NAME.nixos.environment.systemPackages` merging.
- **VR4:** Both trimmers need a generic workspace-root YAML rule and the same fixture. Then a
  real Basix failed evaluation must show the `basix.yaml` fault before the trace summary.
- **VR3:** Owner ruling is needed on two viable failure behaviors: commit before build and retain
  a failed-attempt commit with no generation record, or build before commit and verify that
  the committed inputs produce the same toplevel before activation. New and ignored files,
  managed-file scope, and the meaning of `dirty` need explicit treatment. The Git prototype
  did not run `vendomat apply`, `rollback`, or a VM.

## VR7 trusted-network fixture: unrun

The unlanded S3 sharing module currently sets
`networking.firewall.allowedTCPPorts = [ 5000 ]`. The proposed proof uses a server VM with
trusted and untrusted virtual interfaces and a probe VM connected to both isolated networks.
It checks LAN access to `/nix-cache-info`, refusal on the untrusted interface, an unmarked
default, `serve: false`, signed substitution on the trusted path, and fallback with the peer
down. Exact NICs, addresses, commands, and expected observations are in the external report.

This VM fixture was **not run**: the existing S3 sharing VM check still had active QEMU and
Testee processes when the evidence workspace opened. On the host at that time,
`btrfs filesystem usage /` showed 30.87 GiB unallocated and metadata use 74.50%; disk space
was above the project's stop thresholds. No VR7 network-boundary result is claimed. The
owner still needs to select a trust marker and the default for an unmarked network.
