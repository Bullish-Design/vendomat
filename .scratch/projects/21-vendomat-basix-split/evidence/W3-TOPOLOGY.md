# W3: Basix pin layout on stock devenv — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w3-topology/REPORT.md (Sonnet subagent). Stub repositories, workspaces, and logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w3-topology/. Orchestrator spot-check: `attribute 'vendomat' missing` in logs/10-a1-shell.log and logs/20-n1.log; the q6 lock holds one nixpkgs node (e7439b6) and root inputs nixpkgs and vendomat follow basix; logs/56 and logs/58 show BASIX_REV=b2 VENDOMAT_REV=v2 after the second update; logs/64 shows the patch 0003 failure on basix. -->


Work dir: `~/.local/state/vendomat/p21/2026-10-13/w3-topology/`. Logs: `logs/`. Scripts: `bin/`. Workspaces: `ws/`. Stub repos: `repos/` (working) and `served/` (bare, served by my own git daemon on 127.0.0.1:29418, now stopped). I did not touch the Vendomat repo, a host profile, or the git daemon on port 19418. No GC. No VM.

## Inputs and versions

- devenv: `/nix/store/5sbcspxmvsj6g41dmv20flpvj9v8pzi8-devenv-2.4.0/bin/devenv`. `devenv version` prints `devenv 2.4.0 (x86_64-linux)` (logs/00-version.log). PATH `devenv` is a different store path (`...axhrys71...-devenv-wrapped-2.4.0`); I did not use it.
- nix 2.34.7 (system) used only for `nix flake lock` / `nix flake update` inside the scratch basix repo.
- nixpkgs: `github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (the rev the W2 fixtures use; already in the store). The Vendomat repo locks `devenv-nixpkgs/rolling` instead; I did not reuse that rev (inference: the test result does not depend on the rev).
- Stub `vendomat` (`vendomat-<tag>.git`): `modules/catalog.nix` sets `VENDOMAT_STUB=1`, `VENDOMAT_REV=vN`, `VENDOMAT_NAME` (parsed from the workspace `vendomat.yaml` with `builtins.match`), and adds `pkgs.hello`. The flake variant adds a `flake.nix` with one input `nixpkgs`.
- Stub `basix` (`basix-<tag>.git`): `devenv.nix` imports `inputs.vendomat + "/modules/catalog.nix"` and sets `BASIX_STUB=1`, `BASIX_REV=bN`. Two variants:
  - non-flake: `devenv.yaml` with inputs `nixpkgs`, `vendomat` (`flake: false`).
  - flake: `flake.nix` with inputs `nixpkgs`, `vendomat` (`vendomat.inputs.nixpkgs.follows = "nixpkgs"`), later also `devenv` (W2 module-only fork, `path:` URL), `nixpkgs-python` (rev 4d2bd16c, the Vendomat pin), `rust-overlay`; `outputs = _: {}`. `alt.nix` is a second entry file that reads `inputs.basix.inputs.vendomat`.
- Command wrapper: `bin/run.sh WS LOG devenv-args...` runs the stock binary with `env -u UV_PROJECT_ENVIRONMENT` in `ws/WS` and strips colour codes. Every log starts with `$ cd ws/X && devenv ...` and ends with `rc=N`.
- btrfs before builds: unallocated 27.87 GiB, metadata 87.75 % (then 86.04 %, 82.34 %, 82.46 %; unallocated up to 33.87 GiB). Readings in `logs/btrfs-readings.log`. Never stopped.

## Side findings that shaped the method

- S1 (observed). `git+file://` URLs lock with only `ref`, no `rev` and no `narHash` (devenv.lock, with a working repo and with a bare repo). The shell then follows the branch head with no pin, so a `file://` stub cannot test `devenv update`. A `git+git://` URL from my own daemon locks `rev`, `narHash`, `revCount`. All results below use `git+git://127.0.0.1:29418/...`. The git-file result is in the first stub run (`ws-file-variant/`).
- S2 (observed). The Nix fetcher caches `ref -> rev` (tarball-ttl). A fresh workspace got a stale basix rev (`logs/51-q6-fresh.log`: basix 77c3f78 while the remote head was 64c5a37). `NIX_CONFIG="tarball-ttl = 0"` removed the staleness (`logs/52`). `devenv update` refreshes the ref (`logs/53`). Re-using the same URL for a recreated repo gave `upload-pack: not our ref`, so each scenario used a new repo name.
- S3 (observed). An empty `devenv.nix` is a syntax error (`unexpected end of file`). Fixtures use `{ ... }: { }`.

## Q1. Workspace names only `basix`: does the shell see both variables?

Workspace `devenv.yaml`:
```
inputs:
  basix: { url: git+git://127.0.0.1:29418/basix-nf1.git, flake: false }
imports: [ basix ]
```
Command: `devenv shell -- env` (logs/20-n1.log). Expected: both variables. Actual: rc=1, `error: attribute 'vendomat' missing` at basix `devenv.nix:2`. Same for `imports: - basix/devenv.nix` (logs/21-n2).
Same with a flake-style basix (logs/30-g1.log): `error: attribute 'vendomat' missing`.
Observation: stock 2.4.0 reads `inputs` from the workspace `devenv.yaml` only. The `devenv.yaml` of the imported input is ignored. The workspace lock holds `basix`, `devenv`, `nixpkgs`, `nixpkgs-src` and no `vendomat` (ws/a1). This confirms that patch 0007 has no stock equivalent for a non-flake input.
Verdict Q1: NO for a non-flake basix named alone. YES with the forms in Q4 (flake basix).

## Q2. Does `nixpkgs` follow `basix/nixpkgs`?

- Non-flake basix: NO. `nixpkgs: follows: basix/nixpkgs` fails with `Failed to lock inputs: error: input 'nixpkgs' follows a non-existent input 'basix/nixpkgs'` (logs/22-n3.log; also f2 with `vendomat` follows).
- Flake basix (`flake.nix` with `inputs.nixpkgs`): YES. `ws/g2` and `ws/q6` locks: root `nixpkgs` is `["basix","nixpkgs"]`. One nixpkgs node: `NixOS/nixpkgs` rev `e7439b6b` (the basix rev). `vendomat.inputs.nixpkgs` is also `["basix","nixpkgs"]`. `nixpkgs-python` and `rust-overlay` follow it too (ws/h1, ws/q6).
- Without the `nixpkgs: follows` line the workspace gets its own default `devenv-nixpkgs/rolling` (rev 760b8522) as the second nixpkgs node (`nixpkgs_2` in logs of g1; ws/n5 lock). So the line is required.
Verdict Q2: YES, only when basix is a flake. The workspace must still write the 2-line `nixpkgs` follow.

## Q3. One lock file, which nodes?

Observed: `find ws/q6 -name '*.lock'` (outside `.devenv/`) lists only `ws/q6/devenv.lock`. Basix's own `flake.lock` stays in the basix source (store). Nodes in `ws/q6/devenv.lock` (final state):
`basix` (git, rev 56711659), `vendomat` (git, rev 4ba829d7, inputs.nixpkgs = basix/nixpkgs), `nixpkgs` (e7439b6b), `nixpkgs-python` (4d2bd16c), `rust-overlay` (3100cf6f), `flake-compat`, `devenv` (the fork path, basix's), `devenv_2` (github cachix/devenv 1049c535, the workspace root `devenv`), `root`.
Verdict Q3: YES, one lock. Nested inputs sit in it as nodes owned by `basix`.

## Q4. Does Basix's import of Vendomat resolve without the workspace naming `vendomat`?

Failing forms (exact errors):
1. Non-flake basix, `imports: - basix`: `attribute 'vendomat' missing` (logs/20-n1).
2. Non-flake basix, `imports: - basix/devenv.nix`: same (logs/21-n2).
3. Non-flake basix, `vendomat: follows: basix/vendomat`: `Failed to lock inputs: error: input 'vendomat' follows a non-existent input 'basix/vendomat'` (logs/23-n4, 12-f3).
4. Flake basix, `imports: - basix` with only `basix` named: `attribute 'vendomat' missing` (logs/30-g1).

Working forms (all rc=0, shell shows `BASIX_STUB=1`, `VENDOMAT_STUB=1`, `VENDOMAT_NAME=alice`):
- W-A (flake basix; this is A1 as written plus the nixpkgs line) (logs/31-g2.log):
```
inputs:
  basix: { url: git+git://127.0.0.1:29418/basix-fl2.git }
  vendomat: { follows: basix/vendomat }
  nixpkgs: { follows: basix/nixpkgs }
imports: [ basix ]
```
- W-B (flake basix; the workspace does not name `vendomat`) (logs/33-g4.log): same but no `vendomat` line, and `imports: - basix/alt.nix`, where `alt.nix` reads `inputs.basix.inputs.vendomat`. Observation: `inputs.<name>.inputs.<sub>` is reachable in a module for a flake input. This makes the entry module depend on the workspace input being named `basix`.
- W-C (non-flake basix): the workspace names `vendomat` by URL (see Q8) (logs/24-n5.log).
Verdict Q4: NO in the form "workspace names only basix". Minimal working form: basix is a flake (`flake.nix` that only lists inputs), and the workspace adds `vendomat: follows: basix/vendomat` (W-A) or imports an entry file that reads `inputs.basix.inputs.vendomat` (W-B).

## Q5. Can `devenv` and language inputs follow through basix?

Workspace (ws/h1, logs/40-h1.log), flake basix with `devenv`, `nixpkgs-python`, `rust-overlay` inputs:
```
inputs:
  basix: { url: git+git://127.0.0.1:29418/basix-fl3.git }
  nixpkgs: { follows: basix/nixpkgs }
  devenv: { follows: basix/devenv }
  nixpkgs-python: { follows: basix/nixpkgs-python }
  rust-overlay: { follows: basix/rust-overlay }
imports: [ basix/alt.nix ]
```
Result: rc=0. Workspace `devenv.nix` printed `WS_DEVENV=/home/andrew/.local/state/vendomat/p21/2026-10-13/w2-machines/src/devenv-patched/src/modules` (the fork), `WS_NPY` and `WS_RO` store paths. Lock root: `devenv: [basix, devenv]`, `nixpkgs-python: [basix, nixpkgs-python]`, `rust-overlay: [basix, rust-overlay]`; `nixpkgs-python.inputs.nixpkgs` and `rust-overlay.inputs.nixpkgs` are `[basix, nixpkgs]`.
Not tested: that the fork's `deferredModule` change takes effect through the follow (W2 proved the fork itself; here only the input path and its use as `inputs.devenv` were proved). A `devenv` follow replaces the default module input; the CLI/module version pairing still applies.
Verdict Q5: YES for `devenv`, `nixpkgs-python`, `rust-overlay`, with a flake basix. Each costs 2 lines in the workspace file.

## Q6. Update behaviour (flake basix, ws/q6)

Workspace = W-A. Basix has a committed `flake.lock` pinning vendomat v1 (rev b2f56cc3).
Commands and results:
1. First `devenv shell -- env` (logs/50): `BASIX_REV=b1`, `VENDOMAT_REV=v1`.
2. Remote vendomat head moves to v2 (4ba829d). Basix not changed. A new workspace with `tarball-ttl = 0` (logs/52) locks basix 64c5a375 and vendomat b2f56cc3 (v1). Observation: the workspace honours basix's `flake.lock` for the nested input; vendomat head does not leak in.
3. `devenv update` with basix unchanged except a lock commit (logs/53, 54): basix moves to the new head, vendomat stays b2f56cc3, shell shows v1.
4. Bump basix: `nix flake update vendomat` in basix, commit as b2, push. `devenv update` in the workspace (logs/55, 56): basix 56711659, vendomat 4ba829d7. Shell: `BASIX_REV=b2`, `VENDOMAT_REV=v2`. One command moved the pair.
5. Push vendomat v3 (head 2dc8d7c), no basix change. `devenv update` (logs/57, 58): rev lines unchanged, shell still `BASIX_REV=b2`, `VENDOMAT_REV=v2`.
Inference: this works because basix ships a `flake.lock`. Without one, the nested input has no basix pin, and the workspace would take the vendomat head at the first lock or at update. I did not run that case.
Verdict Q6: YES (needs a committed `flake.lock` in basix).

## Q7. Offline

Setup: ws/q6 locked; daemon stopped (`ss -ltn | grep 29418` empty), so the stub remotes are unreachable.
- (a) same workspace, default fetcher cache: rc=0, `BASIX_REV=b2` (logs/60).
- (b) same workspace, `XDG_CACHE_HOME` = empty dir: rc=0 (logs/61). Caveat: `.devenv/` of the workspace existed. Inference: a cached eval skipped the fetch.
- (c) non-flake pair (ws/n5), default and empty cache: rc=0 (logs/62, 63), same caveat.
- (d) copies without `.devenv/` (ws/q6off, ws/n5off), empty `XDG_CACHE_HOME`: FAIL, rc=1:
  `fatal: unable to connect to 127.0.0.1:` and `Failed to get attribute 'config.cachix.enable': error: Failed to fetch git repository 'git://127.0.0.1:29418/basix-fl3.git'` (logs/64, 65). This is the patch-0003 failure. It hits `basix` itself, which is the top-level input.
- (e) copy without `.devenv/`, default fetcher cache (ws/q6off2): rc=0 (logs/66).
- (f) copy without `.devenv/`, default cache, inside `unshare -rn` (no network at all; curl fails; only `lo`, down): rc=0, `BASIX_REV=b2`, `VENDOMAT_REV=v2` (logs/67). The github inputs (nixpkgs, devenv, rust-overlay) also came from the store.
Verdict Q7: Offline works while the fetcher cache or `.devenv/` holds the inputs. It fails with an empty fetcher cache and no `.devenv/` (the patch-0003 case). The topology does not change this; a flat workspace fails the same way (n5off). The failure matters for the Basix ISO, where the cache is empty.

## Q8. Simplest topology on stock 2.4.0 and its cost

A1 as written does not work for a non-flake basix. It works for a flake basix. Costs:
- T1 (recommended; A1 with change). Basix ships a `flake.nix` that lists inputs (`nixpkgs`, `vendomat`, `devenv`, language inputs, each with `inputs.nixpkgs.follows = "nixpkgs"`) and a committed `flake.lock`. The user file: `basix` url, then 2 lines per followed input (`nixpkgs`, `vendomat`, plus `devenv` or a language input if used), then `imports: [ basix ]`. For nixpkgs + vendomat: 7 lines under `inputs:`, one `imports:` line. The template can write it.
- T2 (fewer lines). Same Basix repo; the workspace names `basix` and `nixpkgs` only (5 lines), and the entry module reads `inputs.basix.inputs.vendomat`. The workspace input must be named `basix`. Observed (W-B).
- T3 (non-flake basix; fallback). The workspace names `basix` and `vendomat` by URL with `flake: false` and a `nixpkgs` URL. No pairing: the user file carries a separate vendomat URL (and rev if pinned), so basix can drift from the vendomat it tested. This is the compatibility matrix A1 wants to avoid. `nixpkgs` cannot follow.

## Verdicts

| Q | Verdict |
| --- | --- |
| Q1 | NO if basix is a non-flake input named alone (`attribute 'vendomat' missing`). YES with a flake basix plus the follow lines or `alt.nix`. |
| Q2 | YES for a flake basix (one nixpkgs node, rev e7439b6b). NO (non-existent input) for a non-flake basix. |
| Q3 | YES. One `devenv.lock`; nested nodes under `basix`. |
| Q4 | NO as "name only basix". Minimal: flake basix plus `vendomat: follows: basix/vendomat`. |
| Q5 | YES for `devenv`, `nixpkgs-python`, `rust-overlay` through a flake basix. |
| Q6 | YES. One `devenv update` moves basix and vendomat together; a second update keeps vendomat. Needs basix `flake.lock`. |
| Q7 | Works with `.devenv/` or a fetcher cache present, and with no network at all. Fails with an empty cache and no `.devenv/` (patch-0003 case); same for any topology. |
| Q8 | T1: flake basix, committed `flake.lock`, workspace follows. |

**A1: Backed with change.** Basix must be a flake (a `flake.nix` that lists inputs) with a committed `flake.lock`. The workspace still writes `nixpkgs` and `vendomat` follow lines; it cannot name only `basix`. A non-flake Basix disproves A1. Patch 0007 has no stock equivalent for non-flake inputs. The nested-input access `inputs.basix.inputs.<name>` is the stock substitute.

## Minimal working workspace `devenv.yaml` (flake basix)

```
inputs:
  basix:
    url: git+<basix-url>
  vendomat:
    follows: basix/vendomat
  nixpkgs:
    follows: basix/nixpkgs
imports:
  - basix
```
Add `devenv: { follows: basix/devenv }` to use the module fork Basix pins. Copies: `logs/min-working-devenv.yaml`, `ws/q6/devenv.yaml`.

## Not tested

- Basix without a `flake.lock` (inference only).
- `devenv update basix` for one input.
- `deferredModule` effect through the `devenv` follow.
- A real URL scheme such as `github:` or `git+https:` for basix and vendomat (the stub used a loopback git daemon).
- Pinning by a `?rev=` or tag in the basix `flake.nix` instead of `flake.lock`.
