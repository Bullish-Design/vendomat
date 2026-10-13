# W1: devenv import of a symlinked user-path module — 2026-10-13

<!-- Written by a subagent from its own spike. Raw logs: /home/andrew/.local/state/vendomat/p22/spike-devlayer-path/LOG.md. The orchestrator has not spot-checked it. -->

Scratch fixtures only. No change to any repository, to `~/.config`, or to the host profile. No switch, no rebuild.

## Inputs

- `devenv version`: `devenv 2.4.0+b904dcb (x86_64-linux)`. `nix --version`: `nix (Nix) 2.34.7`.
- Spike directory: `~/.local/state/vendomat/p22/spike-devlayer-path/`.
- `project/` is its own git repo. `devenv.nix` sets `env.SPIKE_BASE = "1"`. `devenv.yaml` has one input, `nixpkgs` at `github:cachix/devenv-nixpkgs/rolling`. `devenv.lock` came from the devman checkout, so nixpkgs was already in the store.
- `project/devenv.local.nix` is a symlink to `central/devenv.local.nix`. The file is untracked and listed in `.git/info/exclude`. This matches production.
- `central/devenv.local.nix` is `{ ... }: { imports = [ <abs path>/share/modules/mod.nix ]; }`.
- `share/` sits outside the git repo.
- Store files A, B, C came from `builtins.toFile`. They set `SPIKE_VAR` to `A`, `B`, and `C-longer-content`.
- Store trees hm1 and hm2 came from `nix-store --add`. Each holds `.local/share/layer/modules/mod.nix`. They set `SPIKE_VAR` to `D1` and `D2`. They stand in for a Home Manager files tree.
- Production pattern, read only: `~/.config/devman/projects/devman/devenv.local.nix` has `imports = [ /run/current-system/sw/share/devman/link-module.nix ];`.
- `readlink ~/Documents/Projects/devman/devenv.local.nix` gives `/home/andrew/.config/devman/projects/devman/devenv.local.nix`.
- `/run/current-system/sw/share/devman/link-module.nix` is a symlink to `/nix/store/b9rrdnmy6gbqixyvs4rz76x7qkcr76yv-devman-link-0.6.0/share/devman/link-module.nix`.

## Fixtures

| F | Claim | Result |
| --- | --- | --- |
| F1 (Q1) | `devenv.local.nix` imports a regular file at an absolute path outside the repo, and it evaluates. | PASS. `devenv shell -- printenv SPIKE_BASE SPIKE_VAR` printed `1` and `plain`. The central symlinked `devenv.local.nix` was untracked. |
| F2 (Q2) | The import still evaluates when `mod.nix` is a symlink to a store file. | PASS. `mod.nix -> /nix/store/akybvcf6...-spike-mod-a.nix`. `printenv SPIKE_VAR` printed `A`. |
| F3 (Q3) | Repointing the leaf symlink to another store file is picked up without `--refresh-eval-cache`. | FAIL (stale). After `ln -sfn $B mod.nix`, `printenv SPIKE_VAR` printed `A` twice. `devenv print-dev-env \| grep SPIKE_VAR` printed `SPIKE_VAR='A'`. A repoint to the larger file C also printed `A`. |
| F3b (Q3 refresh) | `--refresh-eval-cache` picks up the new leaf target. | PASS. `devenv --refresh-eval-cache shell -- printenv SPIKE_VAR` printed `B`. The next run without the flag also printed `B`. |
| F4 (Q4) | Repointing an intermediate directory symlink is picked up without `--refresh-eval-cache`. | PASS. `share/layer -> <hm1>/.local/share/layer` printed `D1`. After repoint to hm2 with no flag, it printed `D2`. The sequence hm1, hm2, hm1, hm2 printed `D1`, `D2`, `D1`, `D2`. |
| F5 (HM per-file repeat) | A per-file link `share/pf/modules/mod.nix`, repointed from the hm1 leaf to the hm2 leaf, is picked up without the flag. | FAIL (stale). After the repoint, `printenv SPIKE_VAR` printed `D1`. After a repoint back to hm1, it printed `D1`. |

## Observations

- Every case evaluated on first entry. An absolute import outside the repo works for a regular file, a leaf symlink, and a path under a directory symlink.
- A leaf symlink repoint stayed unseen until `--refresh-eval-cache`. File size did not matter (F3, file C).
- A directory symlink repoint was seen on the next run, with no flag. It reproduced over four repoints.
- In F4 the leaf file also differed per tree. Only the directory symlink moved.
- The cache is `.devenv/nix-eval-cache.db`. It is a SQLite file. The table `file_input` holds `path`, `content_hash`, and `modified_at`.
- The leaf-symlink path had one row. Its `modified_at` was the symlink creation time at first evaluation. The row did not change after the repoint.
- The row for the directory-symlink path had `modified_at = 1`.
- `stat -L` gives mtime 1 for every store file.
- The `content_hash` values did not match `sha256sum` of the file. The hash scheme is unknown.
- `.devenv/input-paths.txt` listed `central/devenv.local.nix` but not `share/modules/mod.nix`.
- Two fixtures ran in parallel once by mistake. I discarded that run and repeated Q3 and Q4 in sequence. The results above come from the sequential runs.

## Inference

- Devenv may revalidate tracked files by mtime, following symlinks. Store mtimes are constant. A leaf repoint then looks unchanged. This fits F3 and F5. Observation did not prove it.
- The mechanism for F4 is unknown. A directory symlink repoint invalidated the cache. I did not find out why.
- The production path `/run/current-system/sw/...` has both a directory symlink and a leaf symlink. Its behavior may follow F4 or F3. The spike did not decide this.

## Verdicts

- The design may rely on this: a `devenv.local.nix` import of an absolute path outside the repo evaluates on devenv 2.4.0+b904dcb. It evaluates when the path is a symlink into `/nix/store`.
- The design may rely on this: a layout where the module sits under a directory symlink picks up a repoint with no flag (F4).
- The design must not rely on a per-file leaf symlink. It stays stale until `--refresh-eval-cache` (F3, F3b, F5). After `home-manager switch`, each repo would keep the old module. The run would report success with old content.
- The design needs one of three things: a directory-symlink layout, a forced refresh of every repo cache after a switch, or a `devman doctor` check that compares the cached module path to the live one.

## Unproved

- The real Home Manager layout. The spike simulated it with `nix-store --add` trees. It did not use a real `home.file` or `home.activation`.
- The behavior of the production path `/run/current-system/sw/share/devman/link-module.nix` across a `nixos-rebuild`.
- The mechanism behind F3 and F4: mtime revalidation, or another rule.
- Whether a mixed layout (directory symlink above, per-file symlink below) is stale or fresh.
- Behavior with a project that has a populated lock for all inputs, and with `direnv` reloads. The spike used `devenv shell` only.
