# S5: front-door routing, digest guard, bypass, direnv, launcher (2026-10-11)

**Scope.** Project 20 spike S5. Requirements in scope: `DOOR-009`, `DOOR-010`, `DOOR-011`, and the
section 2 and section 4 contract of [CONCEPT.md](../CONCEPT.md). No repository file outside this record
and `fixtures/s5-front-door/` changed. Everything below is observation on pinned tools unless it says
"inference".

## 0. Inputs

| Item | Value |
| --- | --- |
| Host | `server`, x86_64-linux, 8 cores. Load average 8 to 26 during the runs (other agents ran). All timings are noisy; read the min and median. |
| Fork CLI (used for every guard run) | `devenv 2.4.0+fb5d382`, `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv` |
| Stock CLI (Q3 only) | `devenv 2.4.0+b904dcb`, `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0/bin/devenv` |
| Nix | 2.34.7 (one `nix` on the logs showed "Nix 2.35.2" in the `repl` banner; the devenv-bundled Nix) |
| nixpkgs | `github:cachix/devenv-nixpkgs/256551e45f6303e142ab4a98be1bf243feb77dc0` (the rev in the Vendomat `devenv.lock`) |
| direnv | 2.37.1, with `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` in a temp dir. The real allow list is untouched. |
| Python | 3.13.14 |
| Environment | Every run used `cleanenv.sh`, which unsets `DEVENV_*`, `DIRENV_*`, `IN_NIX_SHELL`, `VIRTUAL_ENV`, `NIX_PYTHONPATH`, `PYTHONPATH`. The session carries a leaked devenv shell. |
| Raw logs | `~/.local/state/vendomat/p20/2026-10-11/S5/` (`logs/`, `fx/`, `fxm/`, `ws/`, `q3b/`, `dr/`, `launcher/`) |
| Fixtures | [fixtures/s5-front-door/](fixtures/s5-front-door/) (each file has a NON-PRODUCTION header) |

### Incidents (read first)

1. **`devenv gc` ran twice before I read its code. It may have run a Nix store GC.** The first run was
   in the baseline matrix; the second was an `strace` probe. Both hung with no output and I killed
   them (185 s and 20 s). The nix-daemon journal shows `unexpected Nix daemon error: error: interrupted by the user`
   at 22:18:11 and 22:22:14, which match the two kills. `strace -f -e trace=execve` showed only `git`
   ran, so the work happens in-process through the daemon. No `nix-store`, `nix-collect-garbage`, or
   `nix store gc` child ran. A Nix GC deletes unrooted paths only. The interrupted runs deleted at most a little.
   Free space rose 0.8 GiB between the two readings, which I cannot tie to these runs. I did not run
   `gc` again, so the `gc` row of the matrix is **not tested**. Owner: decide if this needs a check.
2. The fake host release in my launcher fixture wrote `/tmp/devenv.lock` once. I confirmed it was mine and removed it.
3. In this shell, bare `ls` is `eza --icons` and hangs. It cost two command timeouts and nothing else.

## 1. Questions and hypotheses

| # | Question | Hypothesis before the run |
| --- | --- | --- |
| Q1 | Which devenv commands evaluate each guard form? | An assertion stops shell, test, up, and the `shell` attribute only (S1 of project 16). Build and machines skip it. |
| Q2 | Does devenv's eval cache stay warm when Vendomat rewrites identical bytes? | Unknown. Possibly keyed on mtime. |
| Q3 | Commit or ignore `.vendomat/`? | Committed is safer for Testee, because Testee drops ignored files. |
| Q4 | What does the launcher do today in four cases, and which protocol does it need? | It already handles (a) and (b). (c) falls back to the host release. There is no (d). |
| Q5 | Does a pass-through keep exit codes, signals, stdin, tty? | `os.execvp` does, `subprocess` needs care. |
| Q6 | Can `use vendomat` wrap `use devenv`? | Yes, at small cost. |
| Q7 | Can one exit code table hold on the prototype? | Yes, with a reserved range. |

## 2. Q1: guard coverage matrix

### Inputs

Fixture [guard-fixture/devenv.nix](fixtures/s5-front-door/guard-fixture/devenv.nix). Each form fires
only when its own marker file `stale-<form>` exists. One run per (form, command). The runtime forms
print `GUARD-X-FIRED`, built from a variable, so the script text in `print-dev-env` output cannot match.

| Form | Code |
| --- | --- |
| a | `assertions = [{ assertion = !stale; message = ...; }]` |
| b1 | `env.S5_B1 = if stale then throw "..." else "ok"` (lazy throw in one value) |
| b2 | `config = lib.mkIf (if stale then throw "..." else true) { ... }` (throw in the module condition: any read of any option of the module fires it) |
| c | `enterShell` script that exits 1 |
| d | task with `before = [ "devenv:enterShell" ]` that exits 1 |
| e | check in `enterTest` that exits 1 |

Commands: [scripts/matrix.sh](fixtures/s5-front-door/scripts/matrix.sh) (a no-machine fixture) and
[scripts/matrix-machines.sh](fixtures/s5-front-door/scripts/matrix-machines.sh) (adds one preview
machine, `build.nixos` forced to a cheap derivation, so nothing activates or installs). Each command
ran with `</dev/null`, a 180 s timeout, and the stale marker present.

### Expected

Forms a, b1, c, d, e fire on `shell` and `test`. Only b2 fires on `build` and machine commands.

### Actual

`F` = guard fired and the command failed (exit 1). `W` = guard message printed but exit 0.
`-` = not fired. Blank = not applicable. Raw: `logs/forms/summary.txt`, `logs/machines/summary.txt`.

| Command | a assertion | b1 lazy throw | b2 module throw | c enterShell | d task before | e enterTest |
| --- | --- | --- | --- | --- | --- | --- |
| `shell -- true` (also `shell`, `shell -- cmd`) | F | F | F | F | **W** (shell starts) | - |
| `test` (`ci`) | F | F | F | F | F | F |
| `build` (no attribute) | - | - | F | - | - | - |
| `build shell` | F | F | F | - | - | - |
| `eval env` | - | F | F | - | - | - |
| `tasks run <t>` | F | F | F | F (env capture runs `enterShell`) | - (not in the task's chain) | - |
| `tasks list` | - | - | F | - | - | - |
| `info` | - | F | F | - | - | - |
| `up` and `processes up` | F | F | F | F | **W** (processes start) | - |
| `print-dev-env` | F | F | F | - | - | - |
| `direnv-export` (`use devenv`) | F | F | F | - | **W** | - |
| `direnvrc` (prints text) | - | - | - | - | - | - |
| `update` | - | - | - | - | - | - |
| `search` | - | - | - | - | - | - |
| `repl` (`:q` at once) | - | - | - | - | - | - |
| `container build <x>` | not tested: the fixture defines no container; the run failed with "attribute not found" in every case, guard or not | | | | | |
| `machines info` (machine fixture) | - | - | F | - | | |
| `build machines.server.build.nixos` | - | - | F | - | | |
| `machines plan`, `check`, `status` | - (reached SSH, failed on `preview.invalid` as in the clean run) | - | F | - | | |
| `gc` | **not tested** (incident 1) | | | | | |

Notes on the matrix:

- Exit codes: F is exit 1. A killed `up` shows 124 (my `timeout -s INT 25`) when the process manager runs on.
- `machines info` in the no-machine fixture printed "No machines defined" and did not fire b2. With a
  machine defined it fired. Treat a no-machine workspace as unguarded for that command.
- `up -d`, `processes list`, `down` worked on the fork: `s5-sleep ready`, then no process left.
- A guard failure at eval time prints 500 to 1,100 lines of trace (`evaluating file ...`). The message
  is the last line. The `enterShell` guard (c) prints 3 clean lines.
- Under b1 and b2 the same eval-time error also appears for `eval`, `info`, `tasks list`. Form a never
  fires there, because assertions are collected only by the `shell` derivation.
- Escape hatch proved: b2 with `builtins.getEnv "VENDOMAT_ALLOW_STALE" != "1"` in the condition
  passed with the variable set and failed without it, alternating over four runs. The eval cache tracks
  the variable.
- Timings (warm, loaded host, median of runs where nothing failed): `build` 0.13 s, `eval env` 0.18 s,
  `tasks list` 0.16 s, `info` 0.19 s, `tasks run` 0.21 s, `print-dev-env` 0.10 s, `direnv-export` 0.45 s,
  `shell -- true` 0.36 s, `build shell` 1.5 s, `update` 0.74 s, `machines info` 0.17 s, `direnvrc` 0.07 s.
  A failing eval takes 1.4 to 3.2 s. `search` takes 68 to 172 s every time (no cache). `build machines.server.build.nixos`
  cold took 13.4 s.

### Which commands need protection from the Vendomat command path

With the assertion form alone (today's `.vendomat/devenv.nix`), these commands read a stale
workspace without a stop: `build`, `eval` of any non-`shell` attribute, `tasks list`, `info`,
`machines info/plan/check/status`, `build machines.*`, `container`. The two that matter most are the
machine commands and `build`, because `DOOR-009` leaves them to Vendomat. With form b2 added, all of
them stop, except `update`, `search`, `direnvrc`, and `repl` until the user reads an option.
`update` is safe unguarded, because it only resolves inputs. A runtime-only guard (c, d, e) never
protects `build`, `eval`, `info`, machines, `print-dev-env`, or direnv. Form d is not a guard: shell,
`up`, and direnv continue after it fails.

## 3. Q2: generated-file stability and cost

### Inputs

Workspace [workspace/](fixtures/s5-front-door/workspace/): `vendomat.yaml`, a template `devenv.yaml`
with `imports: [./.vendomat]`, a template `devenv.nix` stub. [prep.py](fixtures/s5-front-door/prep.py)
is a throwaway prep step. It parses `vendomat.yaml` with the repo's `yamlsubset`, renders
`.vendomat/{devenv.yaml,devenv.nix,config.json,digest}`, and writes a file only when its bytes change.
The generated module holds the two digest assertions. Command: [scripts/timing.sh](fixtures/s5-front-door/scripts/timing.sh),
`N=7`, each run `devenv shell -- true` on the fork, all exit 0. Raw: `logs/timing-*.txt`.

### Actual

| Variant | min | median | max |
| --- | --- | --- | --- |
| V0 warm, nothing changed | 0.184 s | 0.210 s | 0.240 s |
| V2 prep, skips every write | 0.179 | 0.233 | 0.362 |
| V1 prep rewrites identical bytes (new mtimes) | 0.179 | 0.235 | 0.287 |
| V3 `touch` on every generated file and `vendomat.yaml` | 0.170 | 0.199 | 0.299 |
| V5 `touch` on `.vendomat/devenv.yaml` only | 0.166 | 0.178 | 0.350 |
| V4 content change (one env value), prep, then shell | 2.809 | 3.016 | 3.475 |
| V6 `--no-eval-cache` (3 runs) | 1.615 | 1.792 | 1.806 |

Prep overhead (10 runs each, `logs/startup.txt`):

| Step | min | median |
| --- | --- | --- |
| `python3 -I -c pass` | 25.0 ms | 30.9 ms |
| `prep.py` with Python start, no write | 35.5 ms | 46.4 ms |
| `prep.py` with Python start, forced rewrite | 38.4 ms | 47.8 ms |
| Prep body only (import, parse, render, compare) | | about 6 ms |
| `import vendomat.cli` (Typer, in the repo venv) | 119 ms | 141 ms |
| `vendomat --version` (installed V5 CLI) | 133 ms | 161 ms |
| `devenv version` (fork) | 15.9 ms | 25.1 ms |

**Observed.** devenv's eval cache keys on file content. A rewrite of identical bytes and an
mtime-only `touch` leave the warm time at 0.2 s. A real content change costs about 3 s once.
Skipping the write is still right, because a changed byte invalidates the cache and the Testee run
sees no diff. A front door written as a small prep script adds about 45 ms. A front door that loads
the full Typer CLI adds about 140 to 160 ms. Both are below the 0.2 s warm evaluation.
`direnv exec` warm: `use devenv` 0.358 s median, `use vendomat` 0.440 s median (7 runs each, two
alternations), so the prep adds about 0.08 s.

## 4. Q3: commit or ignore `.vendomat/`

### Inputs and method

Testee's own code (`/nix/store/4swsksq6fqqkp5hmyr9ww9by1w4a5730-source`, Testee 0.6.1) runs
`devenv eval testee.manifestJson shell.drvPath` in its fresh workspace **before** `testee.prepare` runs
(`src/testee/runner/plan.py:90`). I cloned the workspace commit five ways and ran
`devenv eval shell.drvPath env.S5_TOOLS_MOD` on the fork and on stock
([scripts/q3run.sh](fixtures/s5-front-door/scripts/q3run.sh); raw: `q3b/*.log`).

### Actual

| Clone | Fork | Stock | Error text |
| --- | --- | --- | --- |
| B: `.vendomat/` committed | exit 0, module loaded | exit 0, module loaded | none |
| A: `.vendomat/` absent (ignored) | exit 1 | exit 1 | `Failed to get attribute 'config.cachix.enable'` ... `error: ./.vendomat/devenv.nix file does not exist` |
| C: empty `.vendomat/` | exit 1 | exit 1 | same as A |
| D: only `devenv.nix` (digest missing) | exit 1 | exit 1 | `error: path '.../.vendomat/digest' does not exist` |
| E: only `devenv.yaml` | exit 1 | exit 1 | same as A |

Stale committed copy ([scripts/q3stale.sh](fixtures/s5-front-door/scripts/q3stale.sh)), clone B with a
hand-edited `vendomat.yaml`: `eval shell.drvPath`, `shell -- true`, `build shell`, `test`, and
`tasks run devenv:enterShell` all exit 1 with `vendomat: vendomat.yaml changed since the last prepare. Run: vendomat shell`.
A hand edit of `.vendomat/devenv.yaml` gives `vendomat: .vendomat/devenv.yaml was edited by hand. Run: vendomat shell`.
With the lock deleted, stock devenv rebuilt a lock that held the generated `tools` input from a
**local** `./.vendomat` import. Stock handles a local import's `devenv.yaml` inputs; the fork patch
matters only for inputs inherited from imported sources.

**Observed.** An ignored `.vendomat/` makes the `imports: [./.vendomat]` line fail in the devenv
bootstrap, before any Vendomat step can run. The error names the missing file and gives no Vendomat
hint. Testee would stop at `eval_failed`, so no Testee check can run on a fresh checkout unless Testee
keeps the ignored directory. A committed `.vendomat/` evaluates on stock and fork. A stale committed
copy fails the same eval with the Vendomat command in the message, which gives Testee a red result
and not a silent pass.

**Recommendation.** Commit `.vendomat/`. Keep generation deterministic and write on change only, so
`testee.prepare = [["vendomat", "prepare"]]` is a no-op and never trips `workspace_dirty`. Add
`vendomat prepare --check` (proposed) that writes nothing and exits 67 when a file would change. Run
it as a Testee check and in CI. Do not ignore `.vendomat/` and patch Testee with `testee.keep`: that
hides the stale case and fails in any other fresh clone.

## 5. Q4: host launcher bootstrap

### Inputs

Real [launcher/vendomat](../../../../launcher/vendomat) with `VENDOMAT_HOST_RELEASE` set to a fake
([launcher/host-release](fixtures/s5-front-door/launcher/host-release)), and `VENDOMAT_LAUNCHER_CACHE`
in a temp dir. For (b) I built a real fake pinned source: a flake whose package is `bin/vendomat`
([launcher/pinned-source-flake.nix](fixtures/s5-front-door/launcher/pinned-source-flake.nix)), added to the
store as `nix store add --name source` (`/nix/store/wl1cmqi2vyx8wj6c6s4rslzjcs3x7m7m-source`, NAR hash
`sha256-2y7q9sVoebLWsSNbaDEgPYFtZUevwL1PvYUv2aav54Y=`), and wrote that hash into `devenv.lock`.
Raw: `logs/launcher-real.log`, `logs/launcher-c.log`. The launcher still looks for `vendomat.toml`; the
fixture dirs carry one.

### Actual: the V5 launcher

| Case | Command | Result | Time |
| --- | --- | --- | --- |
| (a) no lock | `sync` | stderr: "has no devenv.lock; using the host release to bootstrap it"; the host release wrote the first lock; exit 0 | 0.03 s |
| (a) no lock | `shell` | "'shell' runs in the workspace shell ..."; **exit 3**. The launcher serves only `sync` and help. | 0.02 s |
| (b) valid pin, store path present, cache empty | `sync` | `nix build --offline` of `path:<store>#packages.x86_64-linux.vendomat` built the pinned build; the pinned build ran; exit 0 | 1.35 s |
| (b) same, cache filled | `sync` | pinned build ran at once | 0.03 s |
| (c) pin absent from the store | `sync`, `--version` | "the Vendomat pinned by ... is not in the store and cannot be fetched" then "using the host release to repair the workspace"; the **host release ran; exit 0** | 0.13 s |
| (c) and no host release | `sync` | the same two lines, then "no host release at /nonexistent"; exit 2 | |
| `VENDOMAT_USE_HOST=1` | `sync` | "using the host release"; host ran | |
| (d) protocol mismatch | | **no such case exists**: there is no handshake | |

**Defects found.**

1. `od -An -tx1` prints `*` for a repeated line. A NAR hash with 16 identical bytes (for example all
   zeros) yields a broken hex string and `nix-store` fails with "wrong length". Real hashes will not
   do this. `od -v` fixes it. (Observed with a fake all-zero hash.)
2. Case (c) runs the **host release** against a workspace that pins another build, and exits 0.
   That is correct for repairing a lock. It is wrong for a command such as `build` or `machines apply`,
   because the host release can differ from the pin. Under the new concept, which routes every command
   through the launcher, this silent fallback must become an error for every command except a named repair.
3. The launcher keys on `vendomat.toml` and serves only `sync`. Both change with `DOOR-010`.

### Proposed protocol (prototype)

[launcher-proto.sh](fixtures/s5-front-door/launcher-proto.sh) and
[run-launcher-proto.sh](fixtures/s5-front-door/run-launcher-proto.sh); raw: `logs/launcher-proto.log`, `logs/exitcodes.log`.

- The launcher serves **every** command in a workspace.
- The launcher exports `VENDOMAT_LAUNCHER_PROTOCOL=<n>`, `VENDOMAT_LAUNCHED_BY=launcher`,
  `VENDOMAT_RELEASE_KIND=pinned|host`, and (pinned) `VENDOMAT_PINNED_BUILD=<out>`.
- A Vendomat build declares the launcher protocols it accepts in `share/vendomat/launcher-protocol`
  (`"MIN MAX"`). The launcher reads the file **before** it runs the build. A build without the file counts as `0 0`.
- No lock or no `vendomat` node: host release, with a message (as today).
- Pin present and build unavailable: **error, exit 69**, with the repair command. No fallback.
  `VENDOMAT_USE_HOST=1` is the explicit, announced route.

| Case | Prototype result |
| --- | --- |
| (a) no lock | host release ran, exit 0, message names why |
| (b) pin, build accepts protocol 1 | `PINNED-outP1 ran: shell kind=pinned proto=1 by=launcher`; an arbitrary command `tasks run foo` ran the same way |
| (c) pin absent | exit 69: "the Vendomat build pinned by ... is not in the store, and offline entry cannot build it" and "reconnect, then run: VENDOMAT_USE_HOST=1 vendomat sync" |
| (d) pinned build needs 2..3, launcher speaks 1 | exit 70: "the pinned Vendomat accepts launcher protocol 2..3; this host launcher speaks 1" and "update the host release, or run the pinned build directly" |
| (d) launcher speaks 2 | the build ran, `proto=2` |
| (d') pre-protocol build (file absent) | exit 70, "accepts launcher protocol 0..0" |
| (c') pin absent, `VENDOMAT_USE_HOST=1` | host release ran |
| unreadable `devenv.lock` | exit 72 |
| no host release | exit 71 |

### Does the pinned Vendomat run without the launcher?

Yes, after entry. A shell fixture with `packages = [ <vendomat> ]` placed it first on `PATH`: outside the
shell `vendomat build` ran the host stub; inside `devenv shell` it ran the pinned build, with no
`VENDOMAT_LAUNCHED_BY` set ([scripts/inshell.sh](fixtures/s5-front-door/scripts/inshell.sh)). The pinned
build must therefore treat the launcher variables as optional. Only the first entry needs the launcher
or the host release. This matches `VMOD-020`.

## 6. Q5: pass-through

### Inputs

Throwaway wrappers: [passthrough-exec.py](fixtures/s5-front-door/passthrough-exec.py) (`os.execvp`),
[passthrough-subprocess.py](fixtures/s5-front-door/passthrough-subprocess.py) (`subprocess.run`),
[passthrough-forward.py](fixtures/s5-front-door/passthrough-forward.py) (`Popen` plus signal forwarding).
Harness [run-passthrough.py](fixtures/s5-front-door/run-passthrough.py) against
[fake-devenv](fixtures/s5-front-door/fake-devenv); then the real fork through
[scripts/real-pass.py](fixtures/s5-front-door/scripts/real-pass.py). Raw: `logs/passthrough.log`, `logs/real-pass.log`.

### Actual (fake devenv)

| Case | exec | subprocess.run | Popen + forward |
| --- | --- | --- | --- |
| exit 0, 1, 3, 77 | same | same | same |
| child dies of SIGSEGV | -11 (the parent sees the signal) | 245 (wrong: 256-11) | 139 (shell convention) |
| stdin pipe | passes | passes | passes |
| args with spaces, `--`, empty string | exact | exact | exact |
| pty: stdin and stdout are ttys | yes | yes | yes |
| SIGINT to the process group (Ctrl-C) | child gets one SIGINT, exit 42 | child gets it and the wrapper also gets `KeyboardInterrupt`; exit 130 | **racy**: child can get SIGINT twice; three runs gave 1, 42, 130 |
| SIGINT to the wrapper pid only | child exits 42 | wrapper exits 130; `run()` kills the child | child exits 42 |
| SIGTERM to the wrapper pid only | child exits 43 | wrapper dies (-15); **child left running** | child exits 43 |

### Actual (real fork CLI, exec and forward wrappers)

`shell -- sh -c 'exit 7'` gives 7. `shell -- true` gives 0. `tasks run no:such` gives 1. An unknown
subcommand gives 2 (clap usage). SIGINT to the group during `up --no-tui` gives exit 0 for both
wrappers, with no process left in the session. `up -d`, `processes list`, `down` ran clean.

**Observed.** `os.execvp` is exact for exit codes, signals, stdin, and tty, because the wrapper leaves
the process table. A wrapper that stays as parent must forward only signals that the terminal does not
already send to the group, and must map death-by-signal to 128+n. **Recommendation.** Do all prep, then
`os.execvp` the pinned `devenv`. Use a parent process only for a command that needs a step after
devenv exits.

## 7. Q6: direnv

### Inputs

Isolated direnv config. [direnv/direnvrc](fixtures/s5-front-door/direnv/direnvrc) evals the fork's
`devenv direnvrc` and adds `use_vendomat`: it watches the files, runs the prep step, then calls
`use devenv`. Scripts `run-direnv.sh`, `run-direnv2.sh`, `run-direnv3.sh`. Raw: `logs/direnv*.log`.

The fork's `use_devenv` runs `devenv direnv-export` with `_DEVENV_CALLER=direnv`, and watches
`.envrc`, `devenv.nix`, `devenv.lock`, `devenv.yaml`, `devenv.local.*`, and `$DEVENV_DOTFILE/input-paths.txt`.
Those paths include `.vendomat/*` files after the first load, because devenv records them.

### Actual

| Scenario | Result |
| --- | --- |
| `use vendomat`, first load (cold, fresh clone, first eval) | 19.1 s, env loaded |
| `use vendomat`, warm `direnv exec` | 0.40 s (median of 7: 0.440 s; `use devenv` 0.358 s) |
| edit `vendomat.yaml`, then `use vendomat` | prep rewrote files, `GREETING=v2` loaded, 3.2 s |
| edit `vendomat.yaml`, then `use devenv` (bypass) | `Failed assertions: - vendomat: vendomat.yaml changed since the last prepare. Run: vendomat shell`, then `direnv: failed to build the devenv environment`. **`direnv exec` exits 0 and runs the command with no devenv environment** (`GREETING=` empty). |
| lint fault, `use vendomat` with `return 1` | prep error printed; `direnv exec` exits **0** and runs the command |
| lint fault, `use vendomat` with `exit 1` | `direnv: error exit status 1`; **`direnv exec` exits 1; the command does not run**; `direnv export json` exits 1 |
| fix the file, `use vendomat` | env loaded again, 2.9 s |

**Observed.** The stock `use devenv` ends with `exit 0` after a devenv failure, so a stale or failing
workspace gives a loud message and a silent exit 0 in `direnv exec`. `use vendomat` can fail properly
with `exit 1`. The watch list for `use vendomat` needs `vendomat.yaml` (the one file devenv does not
know about before the first load), `devenv.lock`, `devenv.yaml`, `devenv.nix`, and `.vendomat/digest`. devenv's
own list covers the rest. Prep must run before `use devenv` on every direnv reload.

## 8. Q7: exit codes

Prototype: [vendomat-proto.py](fixtures/s5-front-door/vendomat-proto.py) (prep, then `execvp` devenv),
[prep.py](fixtures/s5-front-door/prep.py), [launcher-proto.sh](fixtures/s5-front-door/launcher-proto.sh),
driver [run-exitcodes.sh](fixtures/s5-front-door/run-exitcodes.sh); raw: `logs/exitcodes.log`.

Observed on the prototype:

| Case | Exit | First stderr line |
| --- | --- | --- |
| `shell -- true` | 0 | `vendomat: release=direct` |
| `shell -- sh -c 'exit 7'` | 7 | passthrough |
| `tasks run no:such` | 1 | devenv's |
| `frobnicate` | 2 | devenv's (clap) |
| no command | 64 | `vendomat: usage: ...` |
| tab in `vendomat.yaml` | 65 | `vendomat: lint fault: vendomat.yaml:2: tab indentation is not supported` |
| `packages: "hello"` | 66 | `vendomat: schema fault: vendomat.yaml: key 'packages': expected a list of strings` |
| `prep --check`, stale | 67 | `vendomat: generated files are stale: [...]. Run: vendomat prepare` |
| launcher: pinned build missing | 69 | |
| launcher: protocol mismatch | 70 | |
| launcher: no host release | 71 | |
| launcher: lock unreadable | 72 | |

Proposed table:

| Exit | Meaning |
| --- | --- |
| 0 | success |
| 1, 2, other | the devenv command or the user command, unchanged |
| 64 | Vendomat usage fault |
| 65 | lint fault in `vendomat.yaml` |
| 66 | schema or value fault |
| 67 | generated files are stale (`prepare --check`) |
| 68 | schema unavailable for the locked pins, offline (not exercised; no schema exists yet) |
| 69 | pinned Vendomat build unavailable |
| 70 | launcher protocol mismatch |
| 71 | no host release |
| 72 | lock unreadable |
| 128+n | the child died of signal n |

Caveat: `shell -- cmd` and `test` return the user command's code, so 64 to 72 can collide. Every
Vendomat fault line starts with `vendomat:`. The V5 CLI codes (1 decision needed, 2 infrastructure
or configuration, 3 invalid usage) and the V5 launcher's exit 3 change at cutover.

## 9. Proves, inference, unproved

**Proves (pinned tools, fixtures above).**

- The coverage matrix in section 2, including that machine commands skip a config assertion, an
  `env` throw, and every runtime guard, and that only a module-wide throw reaches them.
- devenv's eval cache is content-keyed: identical rewrite and mtime-only touch keep 0.2 s warm.
- An ignored `.vendomat/` breaks `devenv eval` in a fresh checkout with
  `./.vendomat/devenv.nix file does not exist`; a committed one evaluates on stock and fork.
- Testee runs `devenv eval ... shell.drvPath` before prepare (code read, plus the same eval run by hand).
- The V5 launcher falls back to the host release when the pinned build is missing; the prototype
  protocol works for cases (a) to (d).
- `os.execvp` passes exit codes, stdin, tty, and signals exactly; direnv's `use devenv` hides failure behind exit 0.

**Inference.**

- A module-wide throw is a better single guard than an assertion. It also stops `machines rollback`
  while the workspace is stale; the `VENDOMAT_ALLOW_STALE` escape covers that. I did not test
  `machines apply` and `rollback` on a real plan.
- Prep calls to `devenv eval` (schema export, S3) must set the escape variable, because the guard
  would stop them while the digest is stale. Not tested with a real schema export.
- The pinned build should carry the devenv CLI it needs (wrapper `VENDOMAT_DEVENV`), so the pin selects both.
  Not tested; today the host PATH has stock devenv.

**Unproved.**

- Real `testee verify` on a workspace with a committed `.vendomat/` (I ran the same eval by hand).
- `container`, `mcp`, `lsp`, `hook`, `allow`, `gc` under a guard.
- A network fetch of a pinned build from a real tag (only the offline store path and the missing case).
- direnv with `devenv hook`/`allow` (devenv's own auto-activation) as a bypass route.
- Behavior with a real schema, a real transitive input, and a real Basix workspace.

## 10. Recommendations

**Guard placement.** Generate a module-wide stale check (form b2) in `.vendomat/devenv.nix`, plus the
current assertions (form a) for a clean `Failed assertions:` message. Gate the check on
`builtins.getEnv "VENDOMAT_ALLOW_STALE" != "1"`. Prep sets the variable for its own devenv calls.
Document it for emergency `machines rollback`. Do not use forms c, d, or e as guards. Keep one enterShell
echo (form c) only as a courtesy message. Never rely on a guard for `update`, `search`, `direnvrc`.

**Committed or ignored.** Commit `.vendomat/`. Add `vendomat prepare --check` as a Testee check
and a CI step. Generation is deterministic and writes on change only.

**Launcher protocol.** The launcher serves every workspace command. It reads `vendomat.yaml`. It hands
off to the pinned build only after reading `share/vendomat/launcher-protocol`. Missing pinned build is
exit 69, not a fallback. The host release acts only when there is no lock, no `vendomat` node, or
`VENDOMAT_USE_HOST=1`. Fix `od -v`. The pinned build treats the launcher variables as optional.

**direnv and CI.** Ship `use_vendomat` in a Vendomat-provided direnvrc (`vendomat direnvrc`). It
runs prep, then `use devenv`, and ends with `exit 1` on a prep fault. Watch `vendomat.yaml` and
`.vendomat/digest`. CI does not use `direnv exec`, because stock `use devenv` exits 0 on failure. CI
runs `vendomat prepare --check`, then `vendomat <command>`, or the pinned `devenv` on the committed tree.

**Front door.** Prep, then `os.execvp` devenv. No parent process for pass-through.

**Exit codes.** The table in section 8.

## 11. NEW claims (no ID allocated)

- `NEW:` A failing assertion in the `assertions` option stops `shell`, `test`, `up`, `print-dev-env`,
  `direnv-export`, `tasks run` (through its environment capture), and `build shell`. It does not stop
  `build`, `eval` of other attributes, `tasks list`, `info`, or any `machines` command.
- `NEW:` A throw in the condition of a module-wide `lib.mkIf` stops every command that reads the
  config, including `build`, `tasks list`, `info`, and all machine commands. It does not stop `update`,
  `search`, or `direnvrc`.
- `NEW:` `devenv tasks run <task>` captures the shell environment, so it runs `enterShell` and fails
  when `enterShell` fails.
- `NEW:` A task with `before = ["devenv:enterShell"]` that fails does not stop `shell`, `up`, or
  `direnv-export`; it stops `test`.
- `NEW:` devenv's eval cache keys on file content, not mtime.
- `NEW:` The `getEnv` escape on a guard is honored by the eval cache.
- `NEW:` `imports: [./.vendomat]` with the directory missing or without `devenv.nix` fails
  devenv's bootstrap with `./.vendomat/devenv.nix file does not exist`, on stock and fork.
- `NEW:` Testee 0.6.1 evaluates the workspace before `testee.prepare`.
- `NEW:` Stock `devenv` locks the inputs of a **local** import's `devenv.yaml`.
- `NEW:` Stock `use devenv` (direnv) exits 0 after a devenv failure; `direnv exec` then runs the command with no environment.
- `NEW:` `devenv gc` blocks for minutes through the Nix daemon with no output (cause unknown; see incident 1).
- `NEW:` The V5 launcher falls back to the host release when the pinned build is missing, and `od` without `-v` breaks on repeated bytes.
- `NEW:` Launcher protocol 1 (`VENDOMAT_LAUNCHER_PROTOCOL`, `share/vendomat/launcher-protocol`).
- `NEW:` `vendomat prepare --check`, exit code 67.
- `NEW:` Exit codes 64 to 72 reserved for Vendomat faults.
- `NEW:` `VENDOMAT_ALLOW_STALE=1` escape.
- `NEW:` `use_vendomat` direnv function and `vendomat direnvrc`.

## 12. Concept changes

1. `CONCEPT.md` section 4: replace "A digest guard stops supported shell and test entries" with the
   module-wide stale check. Build and machine commands are then guarded, not only routed. Keep Vendomat
   as the supported route, because the guard output is long and only repairs by running Vendomat.
2. Section 2: state that `.vendomat/` is committed, and add `vendomat prepare --check`.
3. Section 2: "the host launcher finds the Vendomat build pinned by the workspace lock" needs the
   protocol file and the no-fallback rule for a pinned workspace.
4. `DOOR-009`: extend from "plain `devenv shell`" to "any devenv command that evaluates config".
   `DOOR-010`: add that a missing pinned build is an error, not a fallback.
5. Say that `use devenv` is not a safe CI route and that Vendomat ships its direnv function.

## 13. Log paths

All under `~/.local/state/vendomat/p20/2026-10-11/S5/`: `logs/baseline/`, `logs/forms/`,
`logs/machines/`, `logs/timing-*.txt`, `logs/timing-summary.txt`, `logs/startup.txt`,
`logs/passthrough.log`, `logs/real-pass.log`, `logs/real-up-*.log`, `logs/launcher-real.log`,
`logs/launcher-c.log`, `logs/launcher-proto.log`, `logs/direnv.log`, `logs/direnv2.log`,
`logs/direnv3.log`, `logs/exitcodes.log`, `logs/q3-stale-summary.txt`, `logs/gc-strace.txt`;
Q3 clones in `q3b/` (`*-fork.log`, `*-stock.log`).
