<!-- Raw final report of Agent K (Vendomat devenv module prototype, sonnet), 2026-10-09. Extracted unedited from the agent transcript (longest hand-back). Raw logs: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/. -->

AGENT K REPORT: devenv 2.4.0+b904dcb (rev b904dcb5), nix 2.34.7. All 8 questions have a fixture result. Source = /nix/store/n1zz8rrfw0sx39dizqj4a6468lxga71q-source (the v2.4.0 rev; path from `nix flake metadata github:cachix/devenv/b904dcb5…`).
Raw log dir: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-k/ (cmds.log = every command with exact output, env.sh, final-regression.log, q1-timing.txt, q1-dup-tail*.txt, fake-attic*.log, paths.json, prototype-module-final.nix = final module verbatim).
Setup: own `git daemon` on 127.0.0.1:39418, repos tagged, fake `attic` on PATH. Daemon stopped and the temp dir removed. No sudo, no disks touched, `server` unchanged.
Caveat: my own shell was inside a devenv shell. I unset DEVENV_* and IN_NIX_SHELL from Q5 on. Earlier runs got the right DEVENV_ROOT from the inner devenv.
The module went through tags v1 to v14. Q1 timing ran on v1.1. Q7 ran on v12. The final regression ran on v14.

HEADLINE FINDINGS
1. A failing task with `before=["devenv:enterShell"]` does NOT block `devenv shell` in 2.4.0. An `assertions` entry does block it.
2. devenv checks `assertions` only when `config.shell` is evaluated (top-level.nix:466). That covers `devenv shell`, `devenv test` and `devenv up`. `devenv build <attr>`, bare `devenv build` and `devenv eval` do NOT check them.
3. A flake input or a plain string under `outputs` breaks bare `devenv build`. A derivation works.
4. Nothing in `devenv build` runs a task.
5. Assigning `machines.<h>.nixos` from two places breaks or silently drops modules. See Q7.

Q1 AUTO-IMPORT
ANSWER: Yes. It evaluates with no recursion, and `lib` from the module args is enough.
- The naive filter fails. `inputs.vendomat` also has `devenvModules.default`, so the module imports itself: `error: stack overflow; max-call-depth exceeded`.
- Fix: exclude by `(i.outPath or null) != self.outPath`. `self` comes from `devenvModules.default = import ./module.nix self`.
- Nothing enabled: `devenv build shell` gives the identical store path with and without the import: `/nix/store/fqq4jfhpshvir35p7f8wpdibx8r2af5s-devenv-shell`. Shell shows `LIB_A=unset LIB_B=unset`.
- `lib-a.enable=true`: `LIB_A=on`, and `lib-a-tool` is on PATH.
- `inputs` attribute names: `data-fl,devenv,lib-a,lib-b,lib-other,nixpkgs,self,vendomat`. `hasDevenvModules` is false for data-fl (flake=false), devenv, nixpkgs and self. They are skipped.
- A flake with `devenvModules.other` only is skipped (`lib-other`, `LIB_OTHER` unset).
- A non-flake git input without `flake: false` fails before module evaluation: `Lock validation failed … /flake.nix does not exist`.
- Duplicate option name. The raw error shows the importing file twice: `The option 'lib-a.enable' in '…/devenv.nix' is already declared in '…/devenv.nix'`. Wrapping each face in `lib.setDefaultModuleLocation "inputs.<n>.devenvModules.default"` fixes the names: `The option 'lib-a.enable' in 'inputs.lib-a.devenvModules.default' is already declared in 'inputs.lib-d.devenvModules.default'.`
- Importing a face both through auto-import and by hand gives the same duplicate error.
- Eval time with `--no-eval-cache`, `eval shell.name`, median of 9: baseline (no import) 1174 ms, 0 faces 1114, 2 faces 1055, 10 faces 1126. `build shell`: 1505, 1421, 1531, 1625 ms. The differences are noise. Cached eval takes about 106 ms.
STATUS: PROVEN.

Q2 SHELL-ENTRY CHECK
ANSWER: Both the task and the assertion work as checks, but only the assertion blocks shell entry.
- Task, tags only: `✓ Running vendomat:check`, shell entered.
- Task with a branch ref (`?ref=main`):
  - The task prints "refusing to enter the shell … lib-a … ref=main" and fails.
  - `devenv:enterShell` shows `(dependency failed)`.
  - `devenv shell -- echo inside-shell` STILL prints `inside-shell` and exits 0.
  - An interactive PTY shell (`script`) also ran `echo PTY-INSIDE-SHELL`.
- Source: `run_enter_shell_tasks` (devenv/src/devenv/mod.rs:2239-2252): "Task failures are logged as warnings but don't prevent shell entry." Its comment at ~2252 reads "Shell entry proceeds even if some tasks fail". It discards the status as `_status`. Callers: main.rs:1152 (PTY) and main.rs:1369 (non-PTY).
- Assertion: it reads `${config.devenv.root}/devenv.lock` with `builtins.readFile`, at eval time. `inputs.self` is the workspace path and reads it too. Result: `error: Failed assertions: - vendomat: these git inputs are not pinned to a tag: input node lib-a: git://127.0.0.1:39418/lib-a ref=main`. The command did not run.
- `vendomat.check.enable = false` drops both the task (`devenv tasks list` shows no `vendomat:check`) and the assertion. The shell enters on a branch ref.
- Under `devenv test`: the task runs, because `enterTest` is `after` `enterShell`, and it fails. `devenv test` ends with `× enterTest tasks failed`, exit 1, and the test body did not run (source: mod.rs ~2510 `if status.has_failures() { bail!("enterTest tasks failed") }`). Under tags it passes.
- `devenv tasks run vendomat:check` exits 1 on a branch ref.
- Assertion scope: with a branch ref in the lock, `devenv build outputs.hello`, bare `devenv build` and `devenv eval` all SUCCEED (final-regression.log). Only shell/test/up evaluate `config.shell`.
- Check scope: github-type inputs are not checked. Only `original.type == "git"` is (the devenv-nixpkgs input has ref `rolling`). The check also covers transitive git nodes.
- One more way to block: `enterShell = ''… >&2; exit 7''` aborts with `Shell environment capture failed: <stderr text>`. The message shows only if written to stderr.
STATUS: PROVEN (CLI paths). The enterShell-exit route in a PTY shell is UNPROVEN.

Q3 CACHE PUSH
ANSWER: Yes. `devenv tasks run vendomat:push` calls `attic push demo --stdin` with the paths from `devenv build`.
- `devenv build` bare prints JSON of attr to store path for every option of type `output`/`outputOf`, such as `outputs.*` (bootstrapLib.nix:488-583). It does NOT build `shell`.
- The script runs `devenv build | jq -r '.[]' | attic push "$cache" --stdin`.
- Fake attic log: `argv: push demo --stdin`, stdin = `/nix/store/s4hlz…-cowsay-3.8.4` and `/nix/store/xl1h9…-hello-2.12.3`. These match `devenv build`. Nested `devenv build` inside a task works if `devenv` is on PATH. `attic push` itself pushes the closures.
- Auto-run after `devenv build`: NO.
  - `Commands::Build` (main.rs:1431) only calls `devenv.build()` (mod.rs:2585-2660). That function runs no task.
  - The only task roots are `devenv:enterShell`, `devenv:enterTest`, `tasks run`, and process starts.
  - I found no `devenv:build` task and no post-build hook (grep of the whole tree: only Nix log-bridge enum names).
  - Fixture: after `devenv build`, the fake attic call count stayed unchanged.
- `wantedBy` (tasks.nix:181-195) means "tasks that select this task when they run". Setting `wantedBy=["devenv:enterShell"]` plus `before` makes the push run on `devenv shell`, not on `devenv build` (call count went 1 to 2 on shell entry).
- Not proven: the Nix `post-build-hook` setting. It is outside devenv and I did not test it.
STATUS: PROVEN.

Q4 INPUT STORE PATHS
ANSWER: Use an attrsOf-str option for `devenv eval`. For `devenv build`, put a derivation under `outputs`.
- `devenv eval vendomat.inputPaths` prints the path of each input: data-fl, lib-a, nixpkgs, vendomat, devenv. `self` is excluded because it is the workspace directory, not a store path.
- `inputs.devenv.outPath` is `<store>-source/src/modules`. Use `i.sourceInfo.outPath` for the top-level path.
- Plain strings under `outputs`: bare `devenv build` fails with `Failed to check for outPath in attribute: devenv.config.outputs.vendomat.inputPathsStr.data-fl: expected an attrset, but got a String`.
- The flake input attrset itself fails: `Failed to convert build to JSON: Cannot convert function to JSON`.
- A derivation works: `outputs.vendomat.inputPaths = pkgs.writeText "vendomat-input-paths.json" (builtins.toJSON cfg.inputPaths)`. `devenv build outputs.vendomat.inputPaths` gives `/nix/store/g7vm2irq…-vendomat-input-paths.json`. `nix-store -qR` shows the 5 input sources in its closure. Pushing that root therefore caches the input sources too.
- `outputs` type: `outputOf attrs`. Lists are skipped by `build` (mod.rs:2589-2610).
STATUS: PROVEN.

Q5 HOST PATHS
ANSWER: Works with no `--impure`.
- The default `vendomat.paths` is `builtins.fromJSON (builtins.readFile pathsFile)`, with a file under `$HOME` as stand-in. Shell: `VENDOMAT_PATH_ATTIC=/var/lib/attic`, `VENDOMAT_PATH_PROJECTS=/home/andrew/Documents/Projects`, `VENDOMAT_PATH_SOURCE_STORE=/srv/source`. The name is upper-cased and `-` becomes `_`.
- It also works with `--no-impure`. Control: `builtins.getEnv "HOME"`, `builtins.currentSystem` and `readFile "/etc/hostname"` all work with and without `--no-impure`.
- backend.rs:1715 sets `pure-eval=true` when not impure, yet the fixture shows impure builtins work. Why: UNPROVEN.
- Editing the host file changes the next `devenv eval` result and the shell env. The eval cache tracks the read.
- A missing file gives `{}`. I did not test the real `/etc/vendomat/paths.json`.
STATUS: PROVEN for a file under `$HOME`.

Q6 PROFILES
ANSWER: Yes. The module sets `profiles.hostname.server.module` and `profiles.user.andrew.module` with `lib.mkDefault` values.
- Shell shows `HOST=server USER=andrew`.
- Profiles `hostname.laptop` and `user.nobody-else` did not activate.
- A workspace override with a plain value wins: `HOST=server-override EXTRA=from-workspace`. The module values need `mkDefault`, or two plain values conflict.
- Source: bootstrapLib.nix:260-276 (order is hostname, then user, then manual).
STATUS: PROVEN.

Q7 MACHINES GUARD
ANSWER: A devenv module can add into `machines.<n>.nixos`, but only in a narrow case. The safe pattern is to wrap.
- Fixture: nixpkgs `e7439b6b` and disko v1.13.0 `de570873`, `hardware.facter = null`.
- Machine option type is `nullOr unspecified`, which merges with `mergeDefaultOption`:
  - Two function definitions fail: `module … does not look like a module` (reproduced in plain `lib.evalModules`). The devenv error is garbled.
  - Two attrset definitions merge shallowly, and a same-key collision silently drops one side. With a user `imports` key, the user's bad layout was silently ignored and the system built.
  - Mixed function and attrset definitions are an error.
- Wrapper pattern: the user writes `vendomat.inventory.<h>.nixos` (type `deferredModule`). The module sets `machines.<h>.nixos = { key = "vendomat-guard:<h>"; imports = [ guard userModule ]; }`.
- It rejects any other definition of `machines.<h>.nixos`, via `options.machines.definitionsWithLocations`. That is a NixOS-level assertion (fires on `devenv build machines.<h>.build.nixos`) plus a devenv-level one (fires on `devenv shell`).
- Failures on `devenv build machines.test.build.nixos` (all exit 1):
  - disko device `/dev/nvme0n1`: `vendomat guard (test): disko disk device is not a by-id path listed with role "install-target" … disko.devices.disk.main.device = /dev/nvme0n1 / allowed: /dev/disk/by-id/nvme-FAKE_TARGET_0001`.
  - by-id path with role `keep`: same message naming the keep disk.
  - disko default mounts: `fileSystems device uses by-partlabel or a kernel name … fileSystems."/".device = /dev/disk/by-partlabel/disk-main-root` (and `/boot`).
  - `/dev/sda1` mount: `fileSystems."/boot".device = /dev/sda1`.
  - Direct definition of `machines.test.nixos`: `vendomat guard (test): machines.test.nixos is also defined outside vendomat.inventory.test.nixos`.
- Good layout (by-id install-target, `mkForce` by-uuid mounts) builds: `/nix/store/zdx3i89904czc91s27wc2d1p8ibq8528-nixos-system-test-26.11.20261008.e7439b6`. About 17 s.
- Disko generates by-partlabel mounts by default, so every disko layout must override `fileSystems.*.device` to by-uuid to pass the guard.
STATUS: PROVEN. No install, no disks touched.

Q8 VERSION PINNING
ANSWER: Yes. The lock holds `original: {type: git, url: git://127.0.0.1:39418/vendomat, ref: refs/tags/v12}` and `locked.rev c2b336ab…`.
- Publishing tag v13 does not move the workspace. `devenv update vendomat` with the yaml still on v12 changed nothing (`MODULE_TAG=unset`).
- Bumping the yaml to `refs/tags/v13` then `devenv update vendomat` gives lock rev `5d086902…` and the new module (`MODULE_TAG=v13`).
- Moving the v13 tag in the repo: the shell stays on the old rev until `devenv update vendomat`. The update then picks rev `d6cdd7b3…` (`v13-moved`). A tag can move, so the lock rev is the real pin. The shell-entry check passes either way.
- Observation: new workspaces lock the `devenv` input (`github:cachix/devenv?dir=src/modules`) to rev `a73c5b84…`, not necessarily the CLI's rev. `Cargo.toml` in that tree says 2.4.1. Lock-pinning this input is advisable.
STATUS: PROVEN.

PROTOTYPE MODULE
flake.nix: `outputs = { self }: { devenvModules.default = import ./module.nix self; };`
module.nix, verbatim, is in the file below. It is the Q1 to Q7 module, final tag v14, about 230 lines.
Path: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-k/prototype-module-final.nix

Design points to carry into the spec:
(a) Exclude self by outPath. Wrap each face with `setDefaultModuleLocation`.
(b) Put hard pre-shell checks in `assertions`. Keep tasks as extra checks that only warn at shell entry and fail under `devenv test`.
(c) Under `outputs`, only derivations. Plain strings or flake inputs break `devenv build`.
(d) Do not define `machines.<h>.nixos` from two places. Use the wrapper.
(e) No post-build hook. A push must be an explicit `vendomat-push` or task call, or hang off shell entry through `wantedBy`.
