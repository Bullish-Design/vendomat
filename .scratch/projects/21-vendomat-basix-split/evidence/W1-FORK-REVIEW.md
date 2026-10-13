# W1: can Vendomat run on stock devenv? — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w1-fork/logs/REPORT.txt (Sonnet subagent). Scripts, workspaces, and logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w1-fork/. Orchestrator spot-check: logs/D1 shows `Cannot merge definitions of machines.box.nixos` on the unpatched input; logs/A3 shows stock `Failed to fetch git repository ... Connection refused`. -->

W1 REPORT: can Vendomat run on stock pinned devenv (no fork)? 2026-10-13
Work dir: ~/.local/state/vendomat/p21/2026-10-13/w1-fork (logs/, bin/ scripts, exp/ workspaces, src03/ = v2.4.0 + 0003 only, result-0003 = its build)

VERDICTS
0002 latest-version: drop at next release (upstream a5c3442 on main; main rev 72e18a7 holds 2.4.0). Or avoid: see Q3.
0003 resolve-lock reuse: keep until upstream merges (PR #3244 OPEN since 2026-10-01, no reviews; no release after v2.4.0). Needed only when a store holds a locked source but the Nix fetcher cache does not.
0004 DEVENV_IS_RELEASE: drop now. The nixpkgs devenv 2.4.0 is a release build (package.nix sets DEVENV_IS_RELEASE=true).
0008 lazy-mount copy: not reproduced. Keep only if 0003 stays; unproved either way.
Q4 deferredModule: no binary fork needed; fork only the module input.

OBSERVATIONS
Q1 0002 changes only src/modules/latest-version (2.3.1 -> 2.4.0). Release tags lag: v2.2.2=2.2.1, v2.3=2.2.2, v2.3.1=2.2.2, v2.4.0=2.3.1. The file comes from nixpkgs-unstable devenv.version by an hourly workflow, so a tag always lags.
 Effect with a release CLI 2.4.0 and devenv input = tag v2.4.0: no require_version -> shell prints "devenv 2.4.0 is newer than devenv input (2.3.1) in devenv.lock" (logs/C2.log). With require_version: true -> hard failure "devenv CLI version 2.4.0 does not match the modules version 2.3.1" (logs/C1). devenv.warnOnNewVersion=false silences the warning (logs/C3). Stock upstream flake binary (dev build) shows neither.
 Input rev 72e18a7 (main, latest-version 2.4.0) + require_version: true passes on stock, fork, nixpkgs binaries (C2.log).
Q2 resolve-lock.nix is EMBEDDED in the binary (include_dir! of devenv-nix-backend/bootstrap in backend.rs:1523; extracted to .devenv/bootstrap each run and overwritten). The devenv input supplies only src/modules. So 0003 cannot ship without rebuilding the binary.
 Repro 0003 (workspace exp/wsA, input git+git://127.0.0.1:19518/extra.git, git daemon stopped, source in store):
  - default Nix cache: stock SUCCEEDS offline (fetcher cache answers). (logs/A2)
  - XDG_CACHE_HOME=empty dir: stock FAILS: "fatal: unable to connect to 127.0.0.1: Connection refused ... at .devenv/bootstrap/resolve-lock.nix:89:29 ... error: Failed to fetch git repository 'git://127.0.0.1:19518/extra.git'". Fork SUCCEEDS. (logs/A3)
  So the defect is: locked source in store + no fetcher cache (new user, ISO, cleared cache) + remote down.
 0008: built v2.4.0+0003 only (result-0003). First entry (no lock), with store path deleted by nix-store --delete, with and without empty fetcher cache, with lock present, flake and non-flake inputs, dir=, tag ref, imports: ALL SUCCEED on stock, 0003-only and fork (logs/F1-F6). Project 16 evidence (fork-3-inheritance.md) records the failure on the real collection; I could not reproduce it on a loopback git daemon.
 Fork-free options tested: input `path:/nix/store/<hash>-source` (flake: false) works on stock with empty cache (logs/E1); lock then has no narHash/origin, so it drops provenance. Not tested: nix --offline (cannot help: the cache is empty), a substituter (fetchTree does not consult one for git types; unproved).
Q3 nixpkgs at flake.lock rev e7439b6: devenv 2.4.0, release build, substitutable from cache.nixos.org (30 paths, 88 MiB). `devenv version` prints "2.4.0" (stock upstream: 2.4.0+b904dcb, a dev build). require_version: stock upstream flake binary = never enforced; fork and nixpkgs = enforced (C1). Vendomat needs require_version only to catch CLI/module drift; a host release that pins both makes it redundant. Not needed if the nixpkgs devenv is the pin.
Q4 YES. Stock 2.4.0 binary + devenv input path:<copy of v2.4.0 src/modules, machines.nix nullOr deferredModule>?dir=src/modules, with machines.box.nixos defined twice (function + attrset): `devenv eval machines.box.build.nixos` succeeds, built system has both (etc/w1 and hello) (logs/D2). Same workspace with github v2.4.0 input fails: "Cannot merge definitions of `machines.box.nixos'" (logs/D1).
 From the input (no rebuild): everything under src/modules (top-level.nix, machines.nix, machines/*, update-check.nix, latest-version, languages, services).
 Embedded in the binary: bootstrap/{default,bootstrapLib,resolve-lock}.nix, all Rust, init templates, shell hooks, direnvrc. Caveat: CLI machines code reads module attributes, so keep module and CLI in the same release.
Q5 Facts: nixpkgs devenv 2.4.0 = release, cached; it lacks 0001 (PR #3255 merged 2026-10-08, after v2.4.0), so the machines install SSH hang (#3254) remains. Upstream flake package = dev build, needs devenv.cachix.org. Recommendation: install devenv from the Vendomat flake nixpkgs pin (pkgs.devenv) on host and ISO, so both carry the same binary. Pin the devenv INPUT in devenv.lock to a small module-only fork (tag + machines.nix deferredModule + latest-version), no Rust build. Set devenv.warnOnNewVersion=false or omit require_version. When upstream releases 0001 and 0002, bump nixpkgs and drop the module fork if deferredModule is merged upstream (offer it).

OVERALL: "no fork of the binary" is reachable for 0002, 0004, 0005-0009 and for deferredModule (module-input fork). Blocker: 0003 (and 0008 if real) until PR #3244 merges AND a release carries it, and only for the empty-fetcher-cache cold-store case. 0001 (SSH hang) is also unreleased.
UNPROVED: 0008 failure; truly offline github inputs on stock; substituter-based fix; main modules with 2.4.0 CLI beyond a trivial shell; the SSH-hang workaround; upstream flake package cache hit.
