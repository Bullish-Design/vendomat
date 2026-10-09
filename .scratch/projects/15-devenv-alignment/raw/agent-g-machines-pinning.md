<!-- Raw final report of Agent G (Machines adoption and devenv pinning, sonnet), 2026-10-09. Extracted unedited from the agent transcript (longest hand-back). Model output: an observation here is the agent's claim, backed by the raw logs it names under ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/. -->

Agent G report (re-sent). All runs used devenv 2.4.0+b904dcb, nix 2.34.7, nixpkgs nixos-unstable e7439b6, and disposable loopback QEMU VMs. Temp dirs removed. Raw log dir (48 files, plus fixture/ copies of all three fixtures): `~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-g/`. Log names below are relative to that dir.

Two findings change the plan:
- The 2.4.0 CLI hangs on `machines install` when the machine has secrets, extraFiles or encryption keys. Main fixes it (`a5fd551a`). See 5b.
- Your six distinct devenv revs across the project locks is actually 26 (58 locks, 2 unreadable). No project sets `require_version`.

## Q1. Pinning devenv system-wide

**ANSWER (a): the CLI compares version strings only, never revs.**
- The comparison is the CLI crate version against `src/modules/latest-version` (read as `devenv.latestVersion`). Check sites: `src/modules/update-check.nix:73-107`, `devenv-core/src/config.rs:929`, called from `devenv/src/main.rs:540`.
- An unpinned fresh project locks `devenv` to main HEAD at lock time. My test locked `a73c5b84` (2026-10-09), not the CLI rev (`q1-run1.log`).
- Whether warn or fail happens depends on how the CLI was built. `DEVENV_IS_RELEASE` is empty in the upstream flake: `nix/crate-config.nix:210` plus no `isRelease=true` anywhere. The CLI installed on this host is the flake build (`/nix/store/axhrys71…-devenv-wrapped-2.4.0`, same path as `github:cachix/devenv/v2.4.0#devenv`). The nixpkgs `devenv` has `DEVENV_IS_RELEASE=true` (`nix eval` output, `q1-cli-store-paths.txt`).
- Test results (`q1-matrix1.log`, `q1-matrix2-a5c.log`):

| CLI build | modules pin | result |
|---|---|---|
| installed (flake, isDev=1) | main or tag, any `require_version` | silent. `require_version: true` is a no-op (`PROBE isDev=1 requireMatch=1 modulesLatest=2.3.1`) |
| nixpkgs (release) | main (modules 2.4.0) | silent |
| nixpkgs (release) | tag v2.4.0 | shell prints `✨ devenv 2.4.0 is newer than devenv input (2.3.1) in devenv.lock. Run 'devenv update' to sync.` |
| nixpkgs (release) | tag v2.4.0 + `require_version: true` | FAILS: `devenv CLI version 2.4.0 does not match the modules version 2.3.1` |
| both | `a5c34429` + `require_version: true` | passes |

- The warning prints only on shell entry (`enterShell`). `devenv.warnOnNewVersion = false` silences it.
- The "CLI older than modules" case (action "-1") is read from source only. UNPROVEN by run, because I had no older CLI.

**ANSWER (b): a tag pin works, but the tag is stale.**
- `github:cachix/devenv/v2.4.0?dir=src/modules` locks to `b904dcb5…`.
- The tag's `latest-version` file says `2.3.1`. The first commit with `2.4.0` is `a5c34429421e077df6f8f133e502617bedc22206` (2026-09-26).
- That commit differs from the tag by three non-machines fixes (opentofu lsp, fish hook, mysql). Pin to it.

**ANSWER (c): `require_version` syntax** (`q1-requireversion.log`; CLI crate version is `2.4.0`, without the `+rev` suffix):
- Accepted: `true`, `false`, `"2.4.0"`, `"=2.4.0"`, `"2.4"`, `">=2.4.0"`, `">=2.4"`, `"<3.0.0"`, `"<=2.4.0"`, `"2.*"`, `">=2.4.0, <2.5.0"`.
- Mismatch exits 1: `× devenv version 2.4.0 does not satisfy the constraint '>=2.5.0' in devenv.yaml`.
- Parse errors exit 1:
  - `"~2.4"`, `"^2.4"`, `"~2.4.0"`: `Failed to parse version constraint`. Tilde and caret are NOT supported.
  - `"v2.4.0"`, `""` and `"garbage"` fail the same way.
  - unquoted `2.4` fails: `data did not match any variant of untagged enum RequireVersion`.
- String constraints are enforced by every CLI build. Only `true` depends on the release flag.

**ANSWER (d): recommended mechanism.**
1. Install one CLI system-wide from a single pin, in the NixOS core module only: the `devenv` flake input at tag `v2.4.0`, or `pkgs.devenv` from the pinned nixpkgs. Use `pkgs.devenv` if you want `require_version: true` to bite.
2. In every project, set `require_version: "2.4.0"` (exact string, always enforced) and `inputs.devenv.url: github:cachix/devenv/a5c34429421e077df6f8f133e502617bedc22206?dir=src/modules`.
3. Run the check script below from CI or a pre-commit hook.
- Do not use `require_version: true` with the tag pin on a release CLI. It fails (table above).

**Check script** (also at `devenv-pin-check.py`). Read-only. Run as `python3 -I devenv-pin-check.py --expect b904dcb5… --expect a5c34429… --cli-version 2.4.0 --repo <devenv clone> ~/Documents/Projects`.
```python
#!/usr/bin/env python3
"""Read-only. Report devenv module pins that differ from the system pin.

Usage: devenv-pin-check.py --expect REV [--expect REV ...]
         [--cli-version 2.4.0 --repo DEVENV_CLONE] ROOT_DIR
Scans ROOT_DIR/*/devenv.lock (root.inputs.devenv -> locked.rev) and the
top-level require_version key of ROOT_DIR/*/devenv.yaml. With --repo it reads
src/modules/latest-version at each rev (git show) and flags an expected rev
whose modules version differs from --cli-version. Exit 1 on any problem.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path


def lock_rev(path):
    try:
        nodes = json.loads(path.read_text()).get("nodes", {})
    except (OSError, ValueError) as err:
        return None, f"unreadable lock: {err}"
    ref = nodes.get("root", {}).get("inputs", {}).get("devenv")
    if not isinstance(ref, str):
        return None, "no devenv input (or follows path)"
    return nodes.get(ref, {}).get("locked", {}).get("rev"), ""


def require_version(path):
    if not path.exists():
        return "NO-YAML"
    for line in path.read_text().splitlines():
        m = re.match(r"^require_version:\s*(.*?)\s*(#.*)?$", line)
        if m:
            return m.group(1).strip("\"'")
    return None


def modules_version(repo, rev):
    cmd = ["git", "-C", repo, "show", f"{rev}:src/modules/latest-version"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--expect", action="append", required=True)
    ap.add_argument("--cli-version")
    ap.add_argument("--repo")
    a = ap.parse_args()
    ver, rows, bad = {}, [], 0
    for lock in sorted(Path(a.root).glob("*/devenv.lock")):
        rev, note = lock_rev(lock)
        rv = require_version(lock.parent / "devenv.yaml")
        issues = []
        if rev is None:
            issues.append(f"NO-REV({note})")
        elif rev not in a.expect:
            issues.append("REV-MISMATCH")
        if rv is None:
            issues.append("NO-require_version")
        if a.repo and rev and rev not in ver:
            ver[rev] = modules_version(a.repo, rev)
        if rev in a.expect and a.cli_version and ver.get(rev) != a.cli_version:
            issues.append(f"EXPECTED-REV-MODULES-VERSION-{ver.get(rev)}")
        bad += bool(issues)
        rows.append((lock.parent.name, (rev or "-")[:12], ver.get(rev, "-"), rv or "-", ",".join(issues) or "ok", rev or "-"))
    w = max((len(r[0]) for r in rows), default=7)
    print(f"{'project':<{w}}  {'lock-rev':<12}  {'mod-ver':<7}  {'require_version':<15}  status")
    for r in rows:
        print(f"{r[0]:<{w}}  {r[1]:<12}  {r[2]:<7}  {r[3]:<15}  {r[4]}")
    counts = {}
    for r in rows:
        counts[r[5]] = counts.get(r[5], 0) + 1
    print(f"\n{len(rows)} projects, {bad} with problems, {len(counts)} distinct revs (incl. '-' = none)")
    for rev, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {rev[:12]}  x{n}  modules-version={ver.get(rev, '-')}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
```
**Output** against `~/Documents/Projects/*/devenv.lock`, read-only (full table in `q1d-pin-check-output.txt`):
```
58 projects, 58 with problems, 27 distinct revs (incl. '-' = none)
  0fd5e6d3a9b2  x11  modules-version=2.3.1
  d1fb321e7304  x7   modules-version=2.1.2
  9d93b838def8  x6   modules-version=2.2.1
  190959a9a4bb  x5   modules-version=2.2.2
  3e42c6e8268f  x3   modules-version=2.2.0
  fe20b5cba7ab  x3   modules-version=2.4.0
  -             x2   (nixvim, nix-nvim)
  ... 19 more revs, x1 or x2 each, from modules 1.6.1 to 2.4.0
testee        b904dcb51fe4  2.3.1  -  NO-require_version,EXPECTED-REV-MODULES-VERSION-2.3.1
repoman       a73c5b84c952  2.4.0  -  REV-MISMATCH,NO-require_version
nix-meta      190959a9a4bb  2.2.2  NO-YAML  REV-MISMATCH
nixvim        -  -  -  NO-REV(unreadable lock: ... line 19)
```
- 26 distinct revs across 56 readable locks. Modules versions run from 1.6.1 to 2.4.0.
- No project sets `require_version` (56 without it, 2 locks have no devenv.yaml).
- `nixvim/devenv.lock` and `nix-nvim/devenv.lock` contain jj conflict markers (`<<<<<<< conflict 1 of 1`) and are invalid JSON.
- `testee` is the only project at the tag rev `b904dcb`, and that rev reports modules version 2.3.1.

**STATUS**: PROVEN, except the CLI-older-than-modules case, which is source-only.

## Q2. Two-host Machines layout

**ANSWER**
- `machines info` and `devenv build machines.{server,framework}` succeed with `nixpkgs = github:NixOS/nixpkgs/nixos-unstable`. `devenv-nixpkgs/rolling` also works for machines and the shell (`q2-variantA-devenv-nixpkgs.log`).
- The difference: unstable gives system label `26.11.20261008.e7439b6`, devenv-nixpkgs gives `26.11pre-git`. The code takes different paths: `machines.nix:48-60` uses `inputs.nixpkgs.lib.nixosSystem` if present, else the `nixpkgs-src` `eval-config.nix`.
- Inputs: `disko` is always required for a NixOS role (`machines.nix` throws without it). `home-manager` is required for the HM role. `nixos-facter-modules` is only needed when `hardware.facter != null`.
- With the default facter path and no report, the build fails: `path '…/.machines/framework/facter.json' does not exist` (`q2-facter-missing.log`). `hardware.facter = null` opts out.
- Generating a real report needs root, so the facter-present path is UNPROVEN.
- A separate nixpkgs for machines vs the shell is NOT an option. `machines.nix` hardcodes `inputs.nixpkgs` for the NixOS evaluator (lines 48-60) and the HM role.
- Workaround, proven: add an extra input such as `nixpkgs-shell` and take shell packages from `inputs.nixpkgs-shell.legacyPackages.<system>`. Machines stay on `inputs.nixpkgs` (`q2-separate-input.log`: shell hello from rev `c2f38fe`, machines rev `e7439b6`).
- `pkgs`, languages and services in the shell still follow `inputs.nixpkgs`.

**Fixture devenv.yaml** (verbatim; fixture files are in `fixture/server-framework/`):
```yaml
# One pinned devenv for the whole system: the CLI is exact-pinned here and the
# modules input is pinned to the first rev whose modules report version 2.4.0.
require_version: "2.4.0"
inputs:
  nixpkgs:
    url: github:NixOS/nixpkgs/nixos-unstable
  devenv:
    url: github:cachix/devenv/a5c34429421e077df6f8f133e502617bedc22206?dir=src/modules
  disko:
    url: github:nix-community/disko
    inputs:
      nixpkgs:
        follows: nixpkgs
  home-manager:
    url: github:nix-community/home-manager
    inputs:
      nixpkgs:
        follows: nixpkgs
  nixos-facter-modules:
    url: github:nix-community/nixos-facter-modules
```
**Fixture devenv.nix** (verbatim). `vmPort`, `mkNixos` and `outputs.vm-bootstrap` exist only to boot the QEMU VM.
```nix
{ pkgs, lib, inputs, config, ... }:
let
  vmPort = 22733;
  mkNixos = extraModules: inputs.nixpkgs.lib.nixosSystem {
    system = "x86_64-linux";
    specialArgs = { inherit inputs; };
    modules = [ ./nixos/core.nix ./nixos/vm-test.nix ] ++ extraModules;
  };
in
{
  packages = [ pkgs.jq pkgs.openssh ];

  machines.server = {
    system = "x86_64-linux";
    target.host = "root@127.0.0.1:${toString vmPort}";   # real: "root@server.lan"
    target.sshOpts = [
      "-o" "IdentitiesOnly=yes"
      "-o" "IdentityFile=${config.devenv.root}/.vm/id_ed25519"
      "-o" "UserKnownHostsFile=${config.devenv.root}/.vm/known_hosts"
    ];
    hardware.facter = null;
    nixos = { imports = [ ./nixos/core.nix ./nixos/server.nix ./nixos/vm-test.nix ]; };
    home-manager = import ./home/andrew.nix;
    deploy.rollbackTimeout = 60;
  };

  machines.framework = {
    system = "x86_64-linux";
    hardware.facter = null;
    nixos = { imports = [ ./nixos/core.nix ./nixos/framework.nix ]; };
    home-manager = { imports = [ ./home/andrew.nix ./home/framework.nix ]; };
  };

  outputs.vm-bootstrap = (mkNixos [ ]).config.system.build.vm;
}
```
- Modules: `nixos/core.nix` (state version, `nix.settings` incl. Attic cache, user `andrew` uid 1000, root key, sshd), `nixos/server.nix` (Postgres 17, nginx, gitDaemon, atticd), `nixos/framework.nix` (disko layout with placeholder by-id disk, sway, pipewire, NetworkManager, fwupd), `nixos/vm-test.nix` (fixture only), `home/andrew.nix`, `home/framework.nix`.
- Outputs: `devenv machines info` lists both machines with roles `nixos, home-manager`. `devenv build machines.framework` returns `build.nixos`, `home-manager`, `deployer`, `diskoScript`, `diskoFormatScript` and `diskoMountScript` (`q2-build-framework.log`). The server toplevel is `/nix/store/b5qwiqsb…-nixos-system-server-26.11.20261008.e7439b6` (`q2-build-server.log`).

**STATUS**: PROVEN.

## Q3. Real deploy against a VM

**ANSWER**: check, plan, `deploy --yes`, status, change-and-redeploy, rollback, watchdog and the HM role all work against the QEMU VM (loopback SSH port 22733). Details are in the `q3-*.log` files.
- `check`: only two warnings (`current-facts-unavailable`, `access-analysis-incomplete`). `status` before the first deploy: `{"phase":"uninitialized"}`.
- `plan` exits 1 if the target lacks `/nix/var/nix/profiles/system`: `Could not observe server for deployment preview` (`q3-02-plan.log`). A bare qemu-vm has no profile. I ran `nix-env -p /nix/var/nix/profiles/system --set …` to create it. A normally installed NixOS has it.
- `plan` prints `Closure: +53 / -24` and `Saved plan: plan-…`. Plan JSON is `"version": 4` (`q3-02b-plan.json`).
- `apply plan-UIe35fej…` also worked (`q3-14-plan-apply.log`).
- Successful deploy: `phase: succeeded`. The HM role ran afterwards as `andrew` (home links, `profile-1-link`). A deploy that only changes the HM role works too (git email changed, NixOS closure unchanged).
- Change and redeploy: adding `/etc/fixture-marker = "v2"` gave `Closure: +3 / -2`. Marker present, status succeeded.
- `devenv machines rollback server`: no output, exit 0. Marker gone, system back to the previous store path, new profile link `system-6-link`. Status `operation: rollback, phase: succeeded`. HM was not rolled back (documented, not retested).
- Target state after success:
  - `/var/lib/devenv-machines/{current.json,lock}` (dir 0700, files 0600).
  - `/nix/var/nix/gcroots/devenv-machines/executor` plus `deployment-<id>/{executor,previous,requested}`.
  - `/nix/var/nix/profiles/system-N-link` generations 1 to 8, failed deploys included.
  - `/etc/devenv/machine-facts.json`, and `devenv-machines-recover.service` active.
- Watchdog (`q3-12-healthcheck-fail.log`), with `deploy.healthCheck = "false"`:
  - The worker switched, ran the check, and failed at 17:39:34.
  - The system stayed on the new config until the deadline. Rollback ran at 17:40:34 (`rollbackTimeout` = 60 s).
  - The controller printed `Transaction … was rolled back on server: Command '[…devenv-machine-health-check]' returned non-zero exit status 1`. Total 1:27. Status `phase: rolled-back`.
  - Changing the health check changes the executor store path.
- Pitfall found: any failed systemd unit makes `switch-to-configuration` exit 4, so the whole deploy is a failure and rolls back.
  - Attempt 1: I gave `atticd` a bad key in a bootstrap system, so a unit was already failed. The deploy and its rollback both exited 4, and the status was `phase: rollback-failed` (`q3-03-deploy1.log`, `q3-04-failure-diag.log`).
  - Attempt 2: `atticd` had no key (`q3-06`, `q3-07`). The deploy rolled back cleanly.
  - Attempt 3: `atticd` with a valid throwaway key passed (`q3-08`).
- Fixture artefact, not a devenv bug: the first VM shared the host store over virtiofs, and virtiofsd ran out of file descriptors. Later runs use `useNixStoreImage = true`.
- `hostname` inside the VM stayed `nixos` after switching to a config with `hostName = "server"`. NixOS does not change the live hostname on switch.

**STATUS**: PROVEN. Reboot-recovery is UNPROVEN. The direct-boot VM cannot test it.

## Q4. Self-deploy

**ANSWER**: yes. A VM with `target.host = "root@localhost"` and devenv inside deployed to itself (`q4-*.log`). `self: deployed`, status succeeded, a marker `self-v1` landed, and a second deploy `self-v2-by-andrew` also worked. Each NixOS transaction took about 6 s.
- Required SSH config:
  - sshd running, and a key authorized for `root`. I used `ssh-keygen` as root plus `authorized_keys`; declarative `users.users.root.openssh.authorizedKeys.keys` also works.
  - The client key readable by the user running devenv.
  - A `known_hosts` entry: devenv's default `StrictHostKeyChecking=accept-new` adds it.
- Without a key: `ssh root@localhost 'set -eu …' exited with exit status: 255`. devenv hides ssh stderr; raw ssh says `Permission denied (publickey,keyboard-interactive)` (`q4-02`).
- Running as root inside the VM failed: `Failed to open Nix store ─▶ error: cannot remount "/nix/store" writable: not in a private mount namespace`.
  - `NIX_REMOTE=daemon` fixes it. The VM's store is an overlay mounted read-only, so this may be VM-specific. On real NixOS: UNPROVEN.
- Running as `andrew` (wheel, so in `trusted-users`) worked without `NIX_REMOTE`. This needs a private key for `andrew`, `PATH=/run/current-system/sw/bin`, and `XDG_RUNTIME_DIR`.
- Deploying from the user, not from root, is the clean pattern.

**STATUS**: PROVEN in the VM.

## Q5. Secrets and caches

**5a ANSWER**: no conflicting substituter config. Put the Attic URL and key in `nix.settings` in core.
- Source: no `substituters`/`nix.settings` text in `machines.nix`, `machines/*`, or `machines.rs` at v2.4.0.
- Diff: a plain `nixosSystem` of the same modules (no devenv modules) vs the machines-built framework toplevel. `nix.conf` is IDENTICAL. The only `/etc` difference is `devenv/machine-facts.json` (`q5a-nixconf-diff.txt`).
- The VM `/etc/nix/nix.conf` after deploy matches (`q5a-vm-nixconf.txt`).
- NixOS itself appends `https://cache.nixos.org/`, so the list shows it twice. Harmless.
- The only substituter setting devenv makes is `builders-use-substitutes=true` (`devenv-nix-backend/src/backend.rs:1751`). It is controller-side and only with `--use-machines-as-builders`.
- The CLI inside the VM read the VM's own substituters and retried the dead Attic host `attic.fixture.invalid`. It then disabled that cache for 60 s. A dead cache URL slows controller builds.

**5b ANSWER**: `install.secrets` and `install.extraFiles` land correctly, but only with a CLI that has the fix after 2.4.0.
- With the 2.4.0 CLI, `devenv machines install` hangs forever at the first `nix copy` (the disko script) when the machine has any local file payload.
  - Reproduced twice (10+ min and a second run). The hung `nix copy` ran with `NIX_SSHOPTS` containing `-o PermitLocalCommand=no`; the remote `nix-store --serve` sat idle.
  - Cause: the install SSH policy (`SENSITIVE_INSTALL_SSH_OPTS`) forces `PermitLocalCommand=no`, but Nix waits for a LocalCommand `echo started`.
  - Upstream issue #3254 (CLOSED) matches, fixed in main by `a5fd551a` (#3255, 2026-10-08).
  - Without local payloads the default opts are used and `nix copy` works (all my deploys). That path was not run on `install`.
- With devenv from main (`nix build github:cachix/devenv/a73c5b84…#devenv`, `2.4.1+a73c5b8`, from the devenv cachix cache): `install --phases disko,install inst` completed, rc=0 (`q5b-04-install-main-cli.log`).
  - Target was the VM's second disk, `/dev/disk/by-id/virtio-INSTALLDISK`, mounted at `/mnt`, with SecretSpec provider `env` and dummy value `dummy-bootstrap-value-123`.
  - `/mnt/var/lib/bootstrap/token` mode 400 root:root; `/mnt/var/lib/bootstrap/extra` mode 640 root:root; parent dir 0700.
  - The value does not appear in the VM store or the local toplevel (`q5b-05-landed-files.log`).
- Pitfalls:
  - A pinned `known_hosts` entry is required (the install policy forces `StrictHostKeyChecking=yes`). I pointed `UserKnownHostsFile` at a pre-seeded file.
  - Install refuses unless the NixOS config gives root an SSH key or password.
  - `install.extraFiles` keys containing a dot break `machines info` on both 2.4.0 and main: `Failed to get attribute '/var/lib/bootstrap/extra.txt': attribute … not found` (`q5b-01-extrafiles-dot-bug.log`). A dotted `install.secrets` key such as `/var/lib/bootstrap/token.txt` worked. Use dotless `extraFiles` names, or `install.secrets`.
  - The docs say bootstrap files are written only by `install`, not by `deploy`.

**5c ANSWER**: no signature is needed when the receiving SSH user on the target is root. `trusted-users` on the VM is `root root @wheel`, and `require-sigs = true`.
- An unsigned, locally built path copied to `ssh://root@127.0.0.1:22733` succeeded.
- The same kind of path to `ssh://plain@…` (a user not in wheel) failed: `cannot add path … because it lacks a signature by a trusted key` (`q5c-nix-copy-signatures.log`). `--no-check-sigs` on the client did not help.
- The controller's local user does not matter; the receiving user does. Running as local root on the controller: UNPROVEN, since I had no root.

**STATUS**: 5a PROVEN. 5b PROVEN with the main CLI. It is a documented hang on 2.4.0. 5c PROVEN.

## Q6. Upgrade risk: v2.4.0 `b904dcb5` to main `a73c5b84` (2026-10-09)

**ANSWER**: 24 commits, 1 touches Machines.
- `a5fd551a` changes only the `NIX_SSHOPTS` string that `machines install` builds (adds `PermitLocalCommand=yes` and `LocalCommand=echo started`).
- No change to:
  - `src/modules/machines.nix`, `machines/{deploy.nix,deploy.py,facts.nix,recovery.nix}`, or `docs/…/machines.md`. Option names are unchanged.
  - Machines subcommands and flags (`cli.rs` hunks are process-name completion only).
  - Plan format (version 4, `devenv-machine-plan-v1` observation header) or target paths (`/var/lib/devenv-machines`, `/nix/var/nix/gcroots/devenv-machines`, `.devenv/machine-plans/`).
- Main's `Cargo.toml` is `2.4.1` (unreleased). Main's `latest-version` is still `2.4.0`, so a 2.4.1 CLI against modules `a5c34429` would warn "newer than devenv input".
- The interface is brand new. v2.3.1 `machines.nix` had 4 options. The 5632-line machines CLI and options landed in one commit, `a833ae1c` (#3073), on release day 2026-09-24. The docs say "Experimental… may change."
- Expect churn. Pin the CLI and the modules to the same release and diff `machines.nix` and `machines.rs` on every bump.

**STATUS**: PROVEN by `git diff v2.4.0 origin/main`.

## Cleanup
Temp dir and VMs removed. Other agents' qemu processes were not touched.
