<!-- Raw final report of Agent J (patched devenv build, sonnet), 2026-10-09. Extracted unedited from the agent transcript (longest hand-back). Raw logs: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/. -->

# Agent J report: patched devenv 2.4.0 (P1 + P2 + version fix + release flag)

Raw logs and the full patch series: `~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-j/` (`series.patch` = `git format-patch --stdout`, 235 lines; `scripts/` = my test scripts; `22-dist-flake.nix` = the Q7 flake).
Temp dir `/tmp/tmp.4izP9JzxPM` is removed. My `git daemon` is stopped.
Store paths I built, not deleted but no longer rooted (the `result-*` links were in the removed temp dir, so `nix-collect-garbage` can reclaim them):
- `/nix/store/g85vmkr0g8pc0rqggibgffngrv38khzm-devenv-wrapped-2.4.0` (3 patches, dev build)
- `/nix/store/f7b8wg0xpnsjkmmjj43hxffvp20syns6-devenv-wrapped-2.4.0` (final, release build; drv `bzy62dzvkm6wrdswc333p1ahm2dklgfy-devenv-wrapped-2.4.0.drv`)
- Fetched dependency paths: 1652 paths, 1.7 GiB download.

## Q1 Patch series
ANSWER: The series is 4 commits on `v2.4.0`. The final rev is `fe687140e0db8a0ada57021543521fdbd5422bac`, tag `v2.4.0-vendomat.1`.
```
fe687140 vendomat: build the devenv CLI as a release (DEVENV_IS_RELEASE=true)
2db2969c fix(bootstrap): reuse locked inputs already in the store      (PR #3244, 86b798f1)
c579260e Update latest devenv version                                  (a5c34429)
79604b34 fix(machines): allow Nix SSH connection handshake (#3255)     (a5fd551a)
 CHANGELOG.md                                  |  5 +++
 devenv-nix-backend/bootstrap/resolve-lock.nix | 44 ++++++++++++++++++++++++++-
 devenv/src/devenv/machines.rs                 | 41 +++++++++++++++++++++----
 flake.nix                                     |  2 ++
 src/modules/latest-version                    |  2 +-
 5 files changed, 86 insertions(+), 8 deletions(-)
```
- `a5c34429` is a separate commit that changes only `src/modules/latest-version` from `2.3.1` to `2.4.0`. It cherry-picked cleanly.
- PR #3244 has exactly one own commit, `86b798f1`. The branch is based on a newer `main`, so I cherry-picked only that commit.
- The only conflict was `CHANGELOG.md`, for both `a5fd551a` and `86b798f1`. Both add lines under `## 2.4.1 (unreleased)`, which v2.4.0 does not have. I kept only each patch's own changelog line. The code files merged cleanly.
- The tag was made by me in a local copy. `v2.4.0..origin/main` has 24 commits, so no upstream tag matches.
EVIDENCE: `02-cherry-pick.log`, `03-log-final.txt`, `06-numstat.txt`, `series.patch`. The patch headers are:
```
From 79604b34... Subject: [PATCH 1/3] fix(machines): allow Nix SSH connection handshake (#3255)   (Author Domen Kožar, 2 files, +39/-6)
From c579260e... Subject: [PATCH 2/3] Update latest devenv version   (1 file, +1/-1)
From 2db2969c... Subject: [PATCH 3/3] fix(bootstrap): reuse locked inputs already in the store   (Author Allsimon, 2 files, +44/-1)
```
STATUS: PROVEN.

## Q2 Build
ANSWER:
- `flake.nix` exposes `packages.<system>.devenv` through `workspace.crates.devenv` (`flake.nix:249`, `nix/workspace.nix`). It is a crate2nix per-crate build.
- Command: `nix build "git+file://$PWD?ref=vendomat/v2.4.0-patched#devenv" --accept-flake-config --max-jobs 4`. `--accept-flake-config` is needed so the flake's `devenv.cachix.org` substituter applies.
- Wall time with the cache cold for the 1652 paths: 6m10s for the 3-patch build. The release rebuild took 5m17s and reused everything except the `devenv` and `xtask` crates and the wrapper. I ran fixtures during the second build, so treat its timing as approximate.
- Substituted: 1652 paths. 1623 came from `devenv.cachix.org` and 29 from `cache.nixos.org`.
- Built locally: only the workspace crates, plus the wrapper and `rust-default-1.98.0`.
  - Dry-run: `these 6 derivations will be built: rust-default, rust_devenv-nix-backend, rust_devenv, rust_devenv-run-tests, rust_xtask, devenv-wrapped`.
  - All third-party Rust crates are substituted from `devenv.cachix.org`.
  - Your Attic therefore needs the 4 workspace crates and the wrapper. It can reuse the rest from `devenv.cachix.org`, or you can mirror them.
- Output: `/nix/store/g85vm…-devenv-wrapped-2.4.0` (3-patch build) and `/nix/store/f7b8w…-devenv-wrapped-2.4.0` (release build).
- Closure: `nix path-info -S -h` gives 391.5 MiB (410539312 bytes). The installed upstream 2.4.0 closure is 410538672 bytes.
- Version prints `devenv 2.4.0+2db2969 (x86_64-linux)` for the 3-patch build and `devenv 2.4.0+fe68714` for the final build. The rev comes from `self.shortRev` (`flake.nix:202`), so you must build from a git ref. A `path:` source gives no rev. `check_version` uses `crate_version!()`, which is plain `2.4.0` without `+rev` (`devenv/src/main.rs:540`).
- `DEVENV_IS_RELEASE`:
  - `nix/workspace.nix:33` defaults `isRelease ? false`, and `flake.nix` never passes it. Nix sets `DEVENV_IS_RELEASE=""` (`nix/crate-config.nix:210`).
  - `devenv/build.rs` then tries `git describe --tags --exact-match`. That finds no `.git` in the sandbox, so the result is `false`.
  - `is_development_version()` (`devenv/src/lib.rs:46`) is therefore true, even for the upstream v2.4.0 flake build. It is true for the installed binary too, which I inferred from the same build path. I did not test the installed binary directly.
  - Fix: commit `fe687140` adds `isRelease = true;` to the `workspace = pkgs.callPackage ./nix/workspace.nix {…}` call, a 2-line change.
- Does a release build enforce `require_version: true`? Yes, proven in Q3.
EVIDENCE: `04-dry-run.log`, `05-build.log`, `05-build-start.txt` (14:56:39 to 15:02:49), `09-build-release.log`, `08-release-commit.txt`.
STATUS: PROVEN. The wall time depends on network speed.

## Q3 require_version and module pin
Setup: `devenv.yaml` has `inputs.devenv.url: git+git://127.0.0.1:29418/devenv?ref=<branch>&dir=src/modules`, served by my local `git daemon`. A tag ref needs the full form `ref=refs/tags/v2.4.0`. The short form `ref=v2.4.0` fails with `couldn't find remote ref refs/heads/v2.4.0`.
Results below are from `13-*.log`, `20-release-matrix.log` and `21-q3-release-cli.log`.

| CLI | modules pin | require_version | result |
|---|---|---|---|
| dev (3-patch) | patched branch (latest-version 2.4.0) | `"2.4.0"` | exit 0, no warning |
| dev | patched | `true` | exit 0, no warning |
| dev | patched | `">=2.4.0, <2.5.0"` | exit 0 |
| dev | patched | `"~2.4.0"` | exit 1: `Failed to parse version constraint '~2.4.0'… unexpected character '~'` |
| dev | patched | `"2.4.1"` | exit 1: `devenv version 2.4.0 does not satisfy the constraint '2.4.1'` |
| dev | stock `refs/tags/v2.4.0` (latest-version 2.3.1) | `true` | exit 0, silent, so NOT enforced |
| release (final) | patched | `"2.4.0"` and `true` | exit 0, no warning |
| release | stock v2.4.0 modules | `true` | exit 1: `devenv CLI version 2.4.0 does not match the modules version 2.3.1. require_version: true is set…` |
| release | stock v2.4.0 modules | `"2.4.0"` | exit 0, but prints `✨ devenv 2.4.0 is newer than devenv input (2.3.1) in devenv.lock. Run 'devenv update' to sync.` |

- The `latest-version` change is needed for `require_version: true`. Without it, the release build refuses the stock v2.4.0 modules.
- The assertion at `src/modules/update-check.nix:75-78` passes when `cfg.cli.isDevelopment` is true. So `require_version: true` enforces nothing on a non-release build. Use the final build (`fe687140`) if you want enforcement.
- For a string constraint, Rust checks the CLI crate version only (`devenv-core/src/config.rs:929`). That check works on any build.
STATUS: PROVEN.

## Q4 Offline test (P2)
Setup: a local `git daemon` serves a `lib-a` tag `refs/tags/v1` and the patched modules. Steps: `devenv update` and `devenv shell` online, then kill the daemon, remove `.devenv`, point `XDG_CACHE_HOME` at an empty dir, and run `devenv shell -- true`.

ANSWER:
1. Unpatched installed `devenv 2.4.0+b904dcb`, exit 1 (`14-q4-unpatched.log`):
```
fatal: unable to connect to 127.0.0.1: … Connection refused
… at …/.devenv/bootstrap/resolve-lock.nix:89:29:
 89|  fetchedSource = builtins.fetchTree (node.info or { } // removeAttrs resolvedLocked [ "dir" ]);
 … while fetching the input 'git://127.0.0.1:29418/devenv?ref=vendomat/v2.4.0-patched&rev=2db2969c…&shallow=1'
 error: Failed to fetch git repository 'git://127.0.0.1:29418/devenv'
```
This reproduces the failure at `resolve-lock.nix:89`. Here the first unreachable node was the `devenv` input; `lib-a` was unreachable too.
2. Patched `devenv 2.4.0+2db2969`, exit 0 (`15-q4-patched.log`):
   - `devenv shell -- true` returned exit 0.
   - `devenv shell -- printenv LIBA` returned exit 0 and printed `/nix/store/jjr9xqvyrw49ji5p50gf87i70gj22077-source`, the same path as the online run.
3. Network-blocked variant: I set `https_proxy`/`http_proxy` to `http://127.0.0.1:9`, so GitHub and cachix are unreachable too. I used plain `github:NixOS/nixpkgs/c7def046…` as `nixpkgs`.
   - Patched: exit 0 for `shell -- true` and for `shell -- printenv LIBA` (`17-…log`). It printed a cache-info warning for `devenv.cachix.org` only.
   - Unpatched: exit 1 with the same `resolve-lock.nix` failure (`18-…log`).

Caveat found: with the default `github:cachix/devenv-nixpkgs/rolling` as `nixpkgs` and the network blocked, the patched CLI still fails.
- The error is `unable to download 'https://github.com/NixOS/nixpkgs/archive/c7def046….tar.gz'` (`16-…log`, `fix4pp/shell2.out`).
- The cause is `default.nix` in `devenv-nixpkgs`. It calls `builtins.fetchTree` with `rev` and `narHash` for `nixpkgs-src`, outside devenv's `resolve-lock.nix`. P2 does not cover that.
- So a fully offline cold-cache shell works with plain nixpkgs inputs, not with `devenv-nixpkgs`.
- I did not test the same offline case with `devenv-nixpkgs` and a warm fetcher cache.

`devenv update` exit status on fetch failure (`19-update-exit.log`):
- With the lock existing and `lib-a` unreachable, `devenv update`, `devenv update lib-a` and `devenv update nixpkgs` all exit 0 on both the patched and unpatched CLI.
  - `devenv update` and `devenv update lib-a` print `✖ error: Failed to fetch git repository 'git://127.0.0.1:29418/lib-a'`.
  - `devenv update nixpkgs` prints no error.
  - `devenv.lock` is unchanged (md5 `651213f1…`).
  - So it is still 0 on the patched CLI. Scripts must not trust the exit code of `devenv update`.
- When the unreachable input was the `devenv` module input in the offline fixture, `devenv update` exited 1 (`Failed to lock inputs`). This was on both CLIs, with the lock unchanged.
STATUS: PROVEN for the above. The `devenv-nixpkgs` offline failure is proven for the proxy-blocked case.

## Q5 P1 check
ANSWER: `SENSITIVE_INSTALL_SSH_OPTS` (`devenv/src/devenv/machines.rs:50-60`) still contains `PermitLocalCommand=no` (line 60), on purpose. P1 changes `nix_ssh_opts_env` (line 1124 onward) instead:
```
["-o","PermitLocalCommand=yes","-o","LocalCommand=echo started"] … .chain(ssh_opts_argv(user_opts))
```
- It prepends the two options ahead of the install policy, because OpenSSH uses the first value. Only the `NIX_SSHOPTS` used by `nix copy` gets them.
- Direct SSH commands keep `PermitLocalCommand=no`.
- The patch adds the unit test `nix_ssh_handshake_overrides_sensitive_install_policy_and_custom_local_command`.
- `strings` on `.devenv-wrapped` of the final build finds `LocalCommand=echo started` (2 matches) and `PermitLocalCommand=yes`.
STATUS: Source read and string presence PROVEN. A full `devenv machines install` run on a QEMU VM was not done, and the unit tests were not run. The hang fix at runtime is UNPROVEN. I skipped both because of time.

## Q6 Maintenance cost
- P1 (`79604b34`): 35 added and 6 removed lines in `machines.rs`, plus 4 changelog lines. Rust.
- `latest-version` (`c579260e`): 1 line. Upstream main already has it.
- P2 (`2db2969c`): 43 added and 1 removed in `devenv-nix-backend/bootstrap/resolve-lock.nix`, plus 1 changelog line. Nix only, no Rust. It is still OPEN, last updated 2026-10-01 (`gh pr view 3244`).
- Release commit (`fe687140`): 2 lines in `flake.nix`. This is fork-only. Upstream will not take it, so it stays on every bump.
- A dry `git rebase --onto origin/main v2.4.0` onto `a73c5b84` (24 commits ahead):
  - Only `CHANGELOG.md` conflicts again, for P1 and P2.
  - The code of both patches applies cleanly. `resolve-lock.nix` has had no upstream change since v2.4.0.
  - P1 and `a5c34429` are already in main, so git drops them.
  - Fork-only commits left after a bump to a main that has P1: P2 (until merged) and the release flag. Drop the changelog hunks when you rebase.
- Re-check on each upstream bump:
  1. `git log <old>..<new> -- devenv-nix-backend/bootstrap/ devenv/src/devenv/machines.rs src/modules/latest-version`.
  2. `src/modules/latest-version` equals the CLI crate version.
  3. `gh pr view 3244`: if merged, drop P2.
  4. `flake.nix` still has the `workspace = pkgs.callPackage ./nix/workspace.nix {` call. Check that `isRelease` still takes effect (`nix/crate-config.nix:210`).
  5. `nix build --dry-run` still shows only the workspace crates as local builds.
  6. Rerun the Q3 matrix, the Q4 offline test, and the version output `2.4.0+<rev>`.
STATUS: PROVEN (rebase dry run, `07-rebase.log`).

## Q7 Distribution sketch
Verbatim flake (also at `22-dist-flake.nix`):
```nix
{
  description = "Vendomat core: pinned, patched devenv CLI";

  # Fork = cachix/devenv v2.4.0 + a5fd551a (machines install) + latest-version 2.4.0
  #        + PR 3244 (reuse locked inputs) + isRelease = true.
  # Production URL: git://server/devenv?ref=refs/tags/v2.4.0-vendomat.1
  inputs.devenv-fork.url = "git+git://127.0.0.1:29418/devenv?ref=refs/tags/v2.4.0-vendomat.1";

  # Do NOT add `follows` for nixpkgs or nix: the fork's own flake.lock pins
  # the toolchain, and Attic holds the build for exactly that lock.

  outputs = { self, devenv-fork }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAll = f: builtins.listToAttrs (map (s: { name = s; value = f s; }) systems);
    in
    {
      packages = forAll (system: {
        devenv = devenv-fork.packages.${system}.devenv;
        default = devenv-fork.packages.${system}.devenv;
      });

      overlays.default = final: prev: {
        devenv = devenv-fork.packages.${final.stdenv.hostPlatform.system}.devenv;
      };

      nixosModules.default = { pkgs, ... }: {
        environment.systemPackages = [ devenv-fork.packages.${pkgs.stdenv.hostPlatform.system}.devenv ];
        # Let the builder pull the fork's closure from the owner's Attic.
        # nix.settings.extra-substituters = [ "https://attic.example/vendomat" ];
      };
    };
}
```
Evaluation (`22-dist-eval.log`):
- `nix eval --raw .#packages.x86_64-linux.devenv.drvPath` gives `/nix/store/bzy62dzvkm6wrdswc333p1ahm2dklgfy-devenv-wrapped-2.4.0.drv`. This equals `nix path-info --derivation` of the directly built release output.
- The overlay's `devenv.drvPath` gives the same drv.
- A minimal `nixosSystem` using `nixosModules.default` has `environment.systemPackages` containing that same `.drv`.
- The lock pins the fork rev `fe687140…`.
Notes:
- Replace the URL with `git://server/devenv?ref=refs/tags/v2.4.0-vendomat.1`. The flake needs the fork to carry its `flake.lock`, which it does.
- Evaluation fetches the fork's GitHub inputs: cachix, crate2nix, nix, nixd, rust-overlay, ghostty and devenv-nixpkgs.
- The consuming NixOS system must not set `follows` on the nixpkgs input, or the derivation changes and the cache misses.
- Attic must cache the built `devenv-wrapped` plus the 4 local crates. I did not push to an Attic.
STATUS: PROVEN for evaluation. Building through this wrapper flake and installing via NixOS are UNPROVEN. The drv equality shows the build would be the same.

## Other unproven items
- A real `devenv machines install` run (Q5).
- Offline behaviour with `devenv-nixpkgs` and a warm fetcher cache.
- aarch64 builds.
- The `server` host and Attic push, which I did not touch.
- Whether the upstream release process differs from the upstream flake default for `isRelease`. I only read the flake and `build.rs`.
