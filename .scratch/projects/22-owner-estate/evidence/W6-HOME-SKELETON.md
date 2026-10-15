# W6: a nix-meta skeleton with `homeConfigurations."andrew@server"` — 2026-10-15

<!-- Provenance: a subagent built and ran the skeleton on 2026-10-15. The scratch flake is
/tmp/p22-proofs/w6/home/ (12 tracked files). A tarball of it and every log are in
~/.local/state/vendomat/p22/w6/ (skeleton.tar.gz, flake-check.log, checks-1.log, lock-report-*.json,
neg-parity.log, build-activation*.log, generation-bins.txt, home-packages.json). The orchestrator did
not rerun the commands. -->

This record backs A2, A8, R9 and `OI-04`. It is a scratch flake. nix-meta did not change, and
nothing was switched.

## Question

Can a flake that holds only homes evaluate and build `homeConfigurations."andrew@server"` from the
modules that nix-meta has today? Can a flake check hold the rule "one lock node for each family
tool"? Can the atuin parity check read pytuin's package instead of a NixOS configuration?

## Inputs

- Nix 2.34.7. nix-meta `main` `ee768f74` (read only). Its `flake.lock` was the starting lock for the
  skeleton, so every shared input kept its revision.
- The skeleton is a plain flake (OI-04 option a) with this layout, as in the concept:

  ```
  flake.nix                  inputs, mkHome, outputs only
  lib/inventory.nix          user, uid 1000, tailnet name, machines, mnemonix ports
  homes/andrew/{default,server}.nix
  modules/home/{base,terminal,tools,agent,mnemonix}.nix
  checks/{default,lock-nodes}.nix
  ```

- It has no `nixosConfigurations`, no `vendomat`, `vendomat-host`, `devenv`, `repoman`, or
  `nixos-core` input. 15 inputs remain (list in `flake.nix`).
- Each module is a plain function of `{ inputs, inv }`. No module reads `specialArgs`, `osConfig`,
  or `config.users.users`. The atuin socket path uses `inv.uid`, as the concept's rule 4 asks.
- The modules come from nix-meta `profiles/terminal.nix`, `developer.nix`, `agent.nix`, and the
  home block of `mnemonix.nix`. The agent module keeps the three CLIs, zellij, and Pi, and drops
  the long Pi model list.

## Method and results

| # | Command | Result |
| --- | --- | --- |
| 1 | `nix flake lock` (lock copied from nix-meta) | the `vendomat` and `vendomat-host` subtrees removed; the other nodes reused |
| 2 | `nix eval --raw '.#homeConfigurations."andrew@server".activationPackage.drvPath'` | evaluates at the first attempt, 34 s cold |
| 3 | `nix flake check -L` | `all checks passed!`, 30 s |
| 4 | `nix build '.#homeConfigurations."andrew@server".activationPackage'` | builds, after two fixes (see Findings 2 and 3) |
| 5 | Inspect the generation | all of `devman devman-link gitman jj linkman copyroom testee atuin atuout pytuin claude codex zellij pi` are in `home-path/bin` (`generation-bins.txt`) |
| 6 | The report of the lock check against nix-meta's own `flake.lock` (negative control) | fails on the current repository, see below |
| 7 | The atuin parity check with `programs.atuin.package = pkgs.atuin` (negative control) | `error: home atuin ...atuin-18.16.1 differs from pytuin atuin ...atuin-18.23.0` |

The generation has 57 entries in `home.packages`, `atuin-daemon.{service,socket}` with
`ExecStart=<pytuin atuin>/bin/atuin daemon start`, `socket_path = "/run/user/1000/atuin.sock"`, and
`sync_address = "https://server.tail770f47.ts.net/atuin"`.

### The checks

- `lock-one-node-per-tool` reads `flake.lock`. It names a node by its `original` repository
  (`repo`, or the last part of `url` or `path`, lower case, `_v2` removed). It fails on more than
  one node for a family tool, on any node of a retired tool (`repoman`, `vendomat`, `docman`), and
  on a tool the home installs with a node count other than one.
- `atuin-parity` asserts at evaluation time that the home's `programs.atuin.package.outPath` equals
  `inputs.pytuin.packages.x86_64-linux.atuin.outPath`. It then runs both binaries in a sandbox.
- `family-packages` evaluates every derivation path of `home.packages` (no build).

| Lock | Family nodes | Result |
| --- | --- | --- |
| Skeleton `flake.lock` | `devman gitman linkman copyroom testee mancore pytuin atuout mnemonix nix-terminal` once each; `templateer`, `pyjutsu` once each (inside copyroom) | pass |
| nix-meta `flake.lock` today | `gitman` twice (`gitman`, `gitman_2` at v0.9.1 through `vendomat`); `vendomat` twice (`vendomat`, `vendomat-host`); retired `repoman`, `docman`, `vendomat` present | **fail**, as the concept predicts |

## Findings

1. **pytuin's atuin package is untagged.** pytuin `v0.3.0` ships atuin 18.18.1. The 18.23.0 package
   (a prebuilt release binary) came 34 commits later, and nix-meta locks `947caac5`, which
   predates it. The skeleton pins pytuin by `rev` (`b6be6d2`). Rule 3 (tags only) needs a pytuin
   release first.
2. **pytuin and atuout must move together.** pytuin `b6be6d2` builds its own atuout from the source
   the `atuout` input names. With atuout at nix-meta's rev `db7edbcd`, the build fails: "grpcio not
   installed", "protobuf not installed" (`build-activation.log`). atuout `57b2cb7` (the rev in
   pytuin's lock) builds. The skeleton pins that rev. A tag pair, or a single owner, avoids the
   clash.
3. **devman and devman-link collide in a Home Manager profile.** Both ship
   `lib/python3.13/site-packages/devman_contract/`. NixOS links only `/bin` and `/share/devman`, so
   no clash arises there. `home-manager-path` links every subpath and fails
   (`build-activation-2.log`). The skeleton installs both through one `buildEnv` with
   `pathsToLink = [ "/bin" "/share/devman" ]`. The devman Home Manager translator (W3) needs the
   same restriction.
4. **The parity check changes meaning.** nix-meta's check compares a source build
   (`atuin 18.23.0 (NO_GIT)`) with the server build. pytuin's binary prints
   `atuin 18.23.0 (78366dca...)`. The skeleton check accepts the prefix `atuin 18.23.0` and the
   server string `atuin-server 18.23.0`. nix-meta's current check string would fail.
5. **`agentman` has no flake output.** `~/Documents/Projects/agentman` has no `flake.nix`. Today
   Vendomat's `repoman-toolchain-core` closure delivers it. The skeleton drops that closure and
   therefore carries no agentman. The agentman daemon in the home needs a package source first.
6. **copyroom and testee keep their own nixpkgs.** copyroom pins nixpkgs `e7439b6`. testee follows
   `devenv/nixpkgs` in nix-meta; the skeleton has no devenv input (R13), so testee gets a nested
   nixpkgs node. These nodes are not family tools, so the check does not count them.
7. **The `programs.pi-coding-agent` module and `nix-terminal` evaluate unchanged** under standalone
   Home Manager (`useGlobalPkgs` is gone; the skeleton builds its own `pkgs` with
   `allowUnfree`). A warning `'system' has been renamed to 'stdenv.hostPlatform.system'` comes from
   an input and is not fixed here.

## Verdict

**Holds.** A flake that holds only homes evaluates, passes its flake checks, and builds
`homeConfigurations."andrew@server"` with every family tool on `PATH`. The one-node check fails on
nix-meta's current lock and passes on the skeleton's. The atuin parity check works from pytuin's
package, and it fails when the home uses another atuin.

The skeleton is not a migration. Several input forms break rule 3: `git+file` for nix-terminal, atuout, pytuin and
mnemonix; a raw `rev` for pytuin and atuout; `main` for nix-terminal and the agent CLIs. Agentman
is missing.

## Unproved

- A switch (that is W2). The build proves the generation exists, not that it activates.
- `home-manager switch` over the tailnet inputs (`git://server`), since the tag rule needs
  releases that do not exist yet.
- The Pi model list, the `/run/secrets` reads, and the `nixbuild` module. The skeleton leaves
  them out.
- A comparison of the skeleton's closure with the machine's Home Manager closure today.
