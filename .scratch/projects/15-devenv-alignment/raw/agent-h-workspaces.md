<!-- Raw final report of Agent H (devenv workspace gaps by fixture, sonnet), 2026-10-09. Extracted unedited from the agent transcript (longest hand-back). Model output: an observation here is the agent's claim, backed by the raw logs it names under ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/. -->

AGENT H REPORT. devenv 2.4.0+b904dcb, nix 2.34.7, 2026-10-09.
Source tree: /nix/store/n1zz8rrfw0sx39dizqj4a6468lxga71q-source (rev b904dcb). Written "src:" below.
Raw log dir: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-h/ (50 files; INDEX.txt, qN-* per question, scripts).
Fixture: own `git daemon` on 127.0.0.1:39517. Repos lib-a, lib-b, lib-c with tag v1.0.0, plus lib-b v1.1.0, lib-d, lib-e. nixpkgs pinned to devenv-nixpkgs 256551e. No access to `server` beyond one read-only `git ls-remote git://server/devman`. Temp dir removed. My daemon is stopped. The only git daemon still running is the server's own on 9418.
Caveat: the host is named `server`, so the Q8 hostname profile matched this machine.

## Q1. Transitive inputs via devenv.yaml
ANSWER: Yes. The lock holds lib-b and lib-c nodes. `inputs.lib-a.packages.<sys>.default` builds and runs. Single-level `follows` works. Deeper nested `follows` is silently ignored.
EVIDENCE:
- ws1 devenv.yaml declares only nixpkgs and lib-a (`git://127.0.0.1:39517/lib-a?ref=refs/tags/v1.0.0`). `devenv shell -- sh -c lib-a` printed "hello from lib-a / lib-b / lib-c".
- Lock summary (q1-lock-summary.txt):
  - `root inputs: {'devenv','lib-a','nixpkgs':'nixpkgs_4'}`
  - `lib-a | git ... rev=5422765833 | ref=refs/tags/v1.0.0 | inputs={'lib-b':'lib-b',...}`
  - `lib-b | ... rev=18b37debf9 | inputs={'lib-c':'lib-c',...}`
  - `lib-c | ... rev=060a9900d3`
- Lock node for lib-a: `locked:{type:git, url, rev, narHash, revCount, ref}`, `original:{type:git, ref:refs/tags/v1.0.0, url}`.
- The `inputs` argument in devenv.nix has only the top-level keys: self, lib-a, nixpkgs, devenv (q5-eval-inputpaths.log). `inputs.lib-b` does not exist there. `inputs.lib-a.inputs.lib-b.inputs.lib-c.outPath` works.
- ws2 adds `lib-a.inputs.nixpkgs.follows: nixpkgs`. The lock then shows `lib-a ... inputs={'lib-b':'lib-b','nixpkgs':['nixpkgs']}`, so lib-a follows the root nixpkgs (c2f38fe7). Shell works.
- ws3 adds `lib-a.inputs.lib-b.inputs.nixpkgs.follows: nixpkgs`. The lock still shows `lib-b ... 'nixpkgs':'nixpkgs_2'` (256551e). Nothing was applied and no error was raised.
- src: devenv-nix-backend/src/lib.rs:116-154 builds overrides one level deep only. Line 141 skips a nested input with neither url nor follows, which is what the `lib-b:` wrapper in ws3 is.
STATUS: PROVEN.

## Q2. Importing a module exported as a flake attribute
ANSWER: It works. There is no infinite recursion unless `imports` reads `config`.
EVIDENCE (ws4, lib-c as a flake input, q2-*.log):
- A: `{ inputs, ... }: { imports = [ inputs.lib-c.devenvModules.default ]; }` gave `LIB_C_MODULE=yes` and `hello from lib-c`.
- B: an inline module `({ inputs, ... }: { imports = [ inputs.lib-c.devenvModules.default ]; })` inside `imports` worked.
- D: a separate `./mod.nix` with the same body worked.
- H (ws5): `inputs.lib-a.inputs.lib-b.devenvModules.default` worked. The lock stayed unchanged.
- Failure F: `imports = lib.optional (config.env ? FOO) inputs.lib-c.devenvModules.default;` gave `error: infinite recursion encountered`. The context says "you probably reference `config` in `imports`".
- Failure G: `imports = [ inputs.lib-c ]` gave `Expected a module, but found a value of type "flake"`.
- Failure E: `lib.mkIf` inside `imports` gave `you're trying to define a value of type 'lambda'`.
STATUS: PROVEN.

## Q3. Importing a module directory from an input
ANSWER: Confirmed. lib-b's `devenv/devenv.yaml` (which declares lib-c) is not merged. The workaround works.
EVIDENCE:
- ws6 devenv.yaml: input lib-b, `imports: [lib-b/devenv]`. The shell failed with:
  `at /nix/store/bzrmr0z1h0i4kg8dqxlypg95nwxvjvzz-source/devenv/devenv.nix:2:16: packages = [ inputs.lib-c.packages... ]` followed by `error: attribute 'lib-c' missing / Did you mean lib-b?` (q3-fail.log).
- The lock has a `lib-c` node, but only as lib-b's own flake input. It is not a top-level input.
- Workaround: the workspace also declares lib-c. This gave `LIB_B_DIR_MODULE=yes` and `hello from lib-c`. The lock then holds two nodes for the same rev (`lib-c` and `lib-c_2`).
- De-duplication: `lib-b.inputs.lib-c.follows: lib-c` leaves one `lib-c` node (q3-dedup.log).
- src: docs/src/content/docs/guides/polyrepo.mdx, caution block: "devenv.yaml from imported projects is not evaluated".
STATUS: PROVEN.

## Q4. Offline collection
ANSWER: Mixed.
- With the Nix fetcher cache intact, `devenv shell` works with the remote down. It works with `.devenv` present and with `.devenv` removed. `--offline` is not needed.
- With an empty Nix fetcher cache and the source still in the store, `devenv shell` fails, with and without `--offline`. This confirms the claim in PR #3244.
- `devenv update` fails but exits 0.
EVIDENCE (daemon killed; `git ls-remote` gave "Connection refused"):
1. `devenv shell -- true`: exit 0.
2. `devenv shell --offline -- true`: exit 0.
3. `devenv update` and `devenv update lib-a`: print `fatal: unable to connect to 127.0.0.1` and `✖ error: Failed to fetch git repository 'git://127.0.0.1:39517/lib-a'`. Exit code 0. `devenv.lock` is unchanged.
4. `rm -rf .devenv`, then `devenv shell -- true`: exit 0 (default `~/.cache/nix` fetcher cache).
5. `.devenv` removed and `XDG_CACHE_HOME` pointed at an empty dir:
   - `devenv shell -- true` exit 1. `devenv shell --offline -- true` exit 1.
   - Both end with `while fetching the input 'git://127.0.0.1:39517/lib-a?ref=refs/tags/v1.0.0&rev=5422...&shallow=1'` and `error: Failed to fetch git repository`.
   - The same source was in /nix/store (`nix path-info` of the lib-a store path succeeded).
6. Warm `.devenv` eval cache plus empty fetcher cache plus daemon down: exit 0.
- Cause, src devenv-nix-backend/bootstrap/resolve-lock.nix:89: `builtins.fetchTree` runs for every locked node on bootstrap.
- `--offline` does only two things (src devenv-nix-backend/src/backend.rs:1692-1698): `substituters=""` and `connect-timeout=1`.
- PR #3244 (OPEN) fixes this by deriving the store path from `narHash`. I did not apply the PR; the fix is read from its diff only.
STATUS: PROVEN. I did not test whether PR #3244 actually fixes it.

## Q5. Store path of a locked input
ANSWER: No built-in command prints it.
- `devenv info` lists only the top-level inputs, with URL and rev, and no store paths.
- `devenv inputs` has only `add`.
- `devenv eval inputs.lib-a.outPath` fails with `attribute devenv.config.inputs.lib-a.outPath not found`.
- `devenv print-dev-env` exists (hidden) but prints the shell script only.
Working paths:
(a) Expose paths through a devenv option, then `devenv eval outputs.inputPaths`. Verified in ws7 with this devenv.nix:
`outputs.inputPaths = lib.mapAttrs (_: i: i.outPath) inputs;`
Output: `"lib-a": "/nix/store/9bzvbwmm7p575yj483l9shd2b31k0ff9-source"`. The nested `outputs.nested` paths printed for lib-b (`bzrmr0z1...`) and lib-c (`yb6kvr3b...`).
(b) Read `devenv.lock` with plain nix. This needs no fetch and no network (works with the daemon down). Verified:
`nix eval --impure --raw --expr 'import ./lockpath.nix { lock = ./devenv.lock; node = "lib-a"; }'`
gave `/nix/store/9bzvbwmm7p575yj483l9shd2b31k0ff9-source`, the same path as (a). It also worked for lib-b and lib-c. `nix path-info` confirmed all three paths are valid.
(c) `builtins.fetchTree <locked node>` also gave the same path. It needs the remote or the fetcher cache (see Q4).
lockpath.nix (verbatim, also in the log dir):
```nix
# usage: nix eval --impure --raw --expr 'import /tmp/agent-h-scripts/lockpath.nix { lock = ./devenv.lock; node = "lib-a"; }'
{ lock, node }:
let
  locked = (builtins.fromJSON (builtins.readFile lock)).nodes.${node}.locked;
in
builtins.unsafeDiscardStringContext (derivation {
  name = "source";
  system = "builtin";
  builder = "builtin:fetchurl";
  outputHashMode = "recursive";
  outputHash = locked.narHash;
}).outPath
```
The trick comes from the PR #3244 diff.
UNPROVEN: `nix flake archive` against devenv.lock. I did not test it, and devenv.lock has no flake.nix.
STATUS: PROVEN for (a) and (b).

## Q6. Tag-pin enforcement
ANSWER: The script below works. It uses the standard library only and has a restricted YAML parser. It checks `devenv.yaml` and the whole `devenv.lock`.
Results (q6-check.log), each run with `python -I check_pins.py <dir> --collection 127.0.0.1`:
- ws1 (good): `ok: every git input is pinned to refs/tags/...`, exit 0.
- ws8 (lib-c pinned `?ref=main`): exit 1.
  `FAIL devenv.yaml: lib-c: ref is 'main', need refs/tags/...: git://127.0.0.1:39517/lib-c?ref=main`
  `FAIL devenv.lock: node lib-c_2: original ref is 'main', need refs/tags/... (git://127.0.0.1:39517/lib-c)`
- ws9 (yaml pins lib-d to a tag, but lib-d's own flake input uses `?ref=main`): exit 1.
  `FAIL devenv.lock: node lib-c: original ref is 'main', ...`
  Only the lock walk catches this.
- Input with no ref: exit 1, with a yaml failure and a "locked original ref differs from yaml ref None" failure.
- Flow-style YAML (`inputs: {lib-a: ...}`): exit 2, "unsupported YAML value". Missing directory: exit 2.
Limits: a git tag can move. The lock `rev` is the real pin, so the check also requires a 40-hex `rev`. The script does not re-check the remote. github: and other non-git inputs are skipped. The YAML parser only handles block-style devenv.yaml and fails closed.
check_pins.py (verbatim):
```python
#!/usr/bin/env python3
"""Read-only tag-pin check for devenv.yaml and devenv.lock.

Usage:  python -I check_pins.py DIR [--collection HOST ...]

Fails (exit 1) when:
  * a git input in devenv.yaml has no ref=refs/tags/... in its URL;
  * a git node in devenv.lock (direct or transitive) has no original ref
    under refs/tags/, or no 40-hex locked rev;
  * a git input in devenv.yaml has no matching node in devenv.lock.

An input is a git input when its URL scheme is git, git+*, or when its
host matches a --collection HOST. Exit 2 means the check could not run
(unreadable file or YAML outside the supported subset). The script only
reads files. It uses the standard library only.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


class Unsupported(Exception):
    pass


def _strip_comment(line):
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"" and (i == 0 or line[i - 1] in " :-"):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text):
    text = text.strip()
    if text[:1] in "{[&*|>!%@`" and text != "[]":
        raise Unsupported(f"unsupported YAML value: {text!r}")
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    if text == "[]":
        return []
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text in ("", "~", "null"):
        return None
    return text


def parse_yaml(text):
    """Parse the block-style YAML subset that devenv.yaml uses."""
    rows = []
    for no, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise Unsupported(f"line {no}: tab indentation")
        line = _strip_comment(raw)
        if not line.strip() or line.strip() == "---":
            continue
        rows.append((no, len(line) - len(line.lstrip(" ")), line.strip()))

    def block(i, indent):
        if i >= len(rows):
            return None, i
        if rows[i][2].startswith("- "):
            items = []
            while i < len(rows) and rows[i][1] == indent and rows[i][2].startswith("- "):
                items.append(_scalar(rows[i][2][2:]))
                i += 1
            return items, i
        mapping = {}
        while i < len(rows) and rows[i][1] == indent:
            no, _, body = rows[i]
            if body.startswith("- "):
                raise Unsupported(f"line {no}: list item inside mapping")
            key, sep, rest = body.partition(":")
            if not sep or (rest and not rest.startswith(" ")):
                raise Unsupported(f"line {no}: expected 'key: value'")
            key = _scalar(key)
            i += 1
            if rest.strip():
                mapping[key] = _scalar(rest)
            elif i < len(rows) and rows[i][1] > indent:
                mapping[key], i = block(i, rows[i][1])
            elif i < len(rows) and rows[i][1] == indent and rows[i][2].startswith("- "):
                mapping[key], i = block(i, indent)
            else:
                mapping[key] = None
        if i < len(rows) and rows[i][1] > indent:
            raise Unsupported(f"line {rows[i][0]}: bad indentation")
        return mapping, i

    if not rows:
        return {}
    value, end = block(0, rows[0][1])
    if end != len(rows):
        raise Unsupported(f"line {rows[end][0]}: trailing content")
    return value


def is_git_url(url, hosts):
    parts = urlsplit(url)
    return (
        parts.scheme == "git"
        or parts.scheme.startswith("git+")
        or (parts.hostname or "") in hosts
    )


def url_ref(url):
    values = parse_qs(urlsplit(url).query).get("ref", [])
    return values[0] if values else None


def check(directory, hosts):
    problems = []
    root = Path(directory)
    config = parse_yaml((root / "devenv.yaml").read_text())
    lock = json.loads((root / "devenv.lock").read_text())
    nodes = lock["nodes"]
    root_inputs = nodes[lock["root"]].get("inputs", {})

    def walk(inputs, trail):
        for name, spec in (inputs or {}).items():
            if not isinstance(spec, dict):
                continue
            url = spec.get("url")
            path = "/".join(trail + [name])
            if url and is_git_url(url, hosts):
                ref = url_ref(url)
                if not (ref or "").startswith("refs/tags/"):
                    problems.append(f"devenv.yaml: {path}: ref is {ref!r}, need refs/tags/...: {url}")
                if not trail:
                    key = root_inputs.get(name)
                    node = nodes.get(key) if isinstance(key, str) else None
                    if node is None:
                        problems.append(f"devenv.lock: {path}: no locked node (run devenv update)")
                    elif (node.get("original") or {}).get("ref") != ref:
                        problems.append(
                            f"devenv.lock: {path}: locked original ref "
                            f"{(node.get('original') or {}).get('ref')!r} differs from yaml ref {ref!r}"
                        )
            walk(spec.get("inputs"), trail + [name])

    walk(config.get("inputs"), [])

    for key, node in nodes.items():
        locked, original = node.get("locked") or {}, node.get("original") or {}
        if locked.get("type") != "git":
            continue
        ref = original.get("ref") or ""
        if not ref.startswith("refs/tags/"):
            problems.append(f"devenv.lock: node {key}: original ref is {ref!r}, need refs/tags/... ({original.get('url')})")
        if not re.fullmatch(r"[0-9a-f]{40}", locked.get("rev", "")):
            problems.append(f"devenv.lock: node {key}: locked rev is not 40 hex characters")
    return problems


def main(argv):
    args, hosts, directory = argv[1:], set(), None
    while args:
        arg = args.pop(0)
        if arg == "--collection" and args:
            hosts.add(args.pop(0))
        elif directory is None and not arg.startswith("-"):
            directory = arg
        else:
            print(__doc__, file=sys.stderr)
            return 2
    if directory is None:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        problems = check(directory, hosts)
    except (OSError, KeyError, ValueError, Unsupported) as error:
        print(f"check_pins: cannot check: {error}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        return 1
    print("ok: every git input is pinned to refs/tags/...")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```
STATUS: PROVEN on the fixtures.

## Q7. Pushing workspace outputs to a cache
ANSWER: Outputs are plain store paths and `attic push` can take them. devenv has no generic post-build hook. Its own push is Cachix-only.
EVIDENCE:
- `devenv build outputs.hello outputs.viaLib` printed JSON: `{"outputs.hello": "/nix/store/dgkngqq6...-ws-hello", "outputs.viaLib": "/nix/store/7ypvvg7p...-lib-a"}`.
- `nix path-info` confirms valid store paths. `nix path-info -r` on lib-a shows the closure includes the lib-b and lib-c paths.
- Attic client (nixpkgs `attic-client`, `.../9r5fng0g...-attic-0-unstable-2026-06-26/bin/attic`): `attic push <CACHE> [PATHS]...` has `--stdin` and `--no-closure`. `attic watch-store <CACHE>` exists.
- So the push command is `devenv build outputs.x | python -I -c '<print the JSON values>' | attic push <cache> --stdin`.
- UNPROVEN: an actual upload or `watch-store` pick-up. There is no Attic server in this environment. `attic push demo <path>` with an empty HOME gave `Error: No servers are available.`
- devenv's own push, src:
  - src/modules/cachix.nix: options `cachix.enable|pull|push|package|binary`. `push` is a single Cachix cache name.
  - devenv/src/devenv/cachix.rs:
    - `init` returns None when `--offline` or `cachix.enable=false`.
    - `cachix.push` starts a cachix daemon, `OwnedDaemon::spawn` (lines 144-170).
    - It registers `MpscObserver` through `cnix.add_realized_observer` (lines ~190-230). That observer queues every realized path to the daemon.
    - The daemon drains at shutdown (300 s).
  - devenv-nix-backend/src/cachix_daemon.rs:279-285 runs `cachix daemon run [--dry-run] --socket <sock> <cache>`.
  - devenv/src/devenv/cachix.rs:419-431 finds the binary via `which cachix`, else builds `config.cachix.package`.
  - devenv-core/src/cachix.rs handles netrc and trusted keys.
- Tasks at v2.4.0: `devenv tasks list` shows only `devenv:container:copy`, `devenv:enterTest`, `devenv:enterShell`, `devenv:files`, `devenv:files:cleanup`. There is no `devenv:build` task. A grep of src, devenv, devenv-core and devenv-nix-backend finds no `devenv:build` or `devenv:post*`. src/modules/tasks.nix:497-509 defines only enterShell and enterTest. `Commands::Build` (devenv/src/main.rs:1431-1441) runs `devenv.build` and prints the JSON, with no task run.
STATUS: PROVEN for the store-path and source claims. The Attic upload is UNPROVEN.

## Q8. Profiles across imports
ANSWER:
- Profiles defined in an imported module activate. This holds for `imports:` directory imports, for a flake-attribute module, and for manual `--profile`.
- Cross-project references (`inputs.X.devenv.config`, issue #2521) do not apply the referenced project's profiles. That is confirmed.
EVIDENCE:
- ws11 (`imports: [lib-b/devenv-profiles]`, lib-b v1.1.0):
  - Hostname profile for `server`, user profile for `andrew`: `PROFILE_HOST_FROM_LIB=active` and `PROFILE_USER_FROM_LIB=active`.
  - `profiles.hostname.otherhost` did not activate.
  - `devenv shell --profile libprofile` added `PROFILE_MANUAL_FROM_LIB=active`.
- ws12 (`inputs.lib-b.devenvModules.profiles` in `imports`): `PROFILE_HOST_FROM_FLAKEMODULE=active`.
- ws13 (local control file): same result as ws11.
- ws15 (`imports: [lib-e]`, merged lib-e project): `E_VAR=from-hostname-profile`. With `--profile manual-e`: `E_VAR=from-manual-profile`.
- ws14 (`inputs.lib-e.devenv.config.env.E_VAR`, referenced rather than merged):
  - With the host matching lib-e's `profiles.hostname.server`, I read `SEEN_E_VAR=base`. The hostname profile was not applied, so this confirms #2521 for hostname profiles.
  - `devenv shell --profile manual-e` failed with `error: Profile 'manual-e' not found. Available profiles: hostname, manual-ws, user`.
  - `--profile manual-ws` (the consumer's own profile) worked.
- Side finding: `inputs.X.devenv` on a `flake: false` input fails with `error: nixpkgs input required`.
  - src: devenv-nix-backend/bootstrap/bootstrapLib.nix:603.
  - Cause: resolve-lock.nix:145 passes the node's own lock inputs as `allInputs`. A non-flake node has none.
  - It works only when the input's flake.nix declares `nixpkgs` and `devenv` inputs. The `devenv` input must not use `?dir=src/modules`; with it I got `.../src/modules/src/modules/top-level.nix does not exist`. With the plain URL it worked (lib-e v1.2.0).
  - The polyrepo guide's `flake: false` example therefore does not work for a repo with only a devenv.nix. UNPROVEN: whether it works with a lock file inside that repo.
STATUS: PROVEN.

## Devenv gaps a Vendomat layer must fill
1. (Q1, Q3) Transitive devenv.yaml inputs are not followed (#2205). Only the flake.nix inputs of a flake input come along. The workspace must declare every input a devenv.yaml-imported module uses, and add `follows` to avoid duplicate lock nodes. Vendomat can generate or verify that closure.
2. (Q1) Nested `follows` deeper than one level is silently dropped (src: lib.rs:141). Vendomat must warn on it or flatten it into top-level inputs.
3. (Q2) The flake-attribute module pattern works, so no gap. The pitfall is `config` inside `imports` (infinite recursion). Vendomat docs and lint should say so.
4. (Q4) `devenv update` exits 0 on fetch failure. Vendomat must read the lock diff or the error text, not the exit code.
5. (Q4) `devenv shell` fails with the remote down when the Nix fetcher cache is cold, even if the source is in the store. `--offline` does not help. Vendomat needs a pre-flight that checks the store with lockpath.nix, or must wait for PR #3244.
6. (Q5) devenv has no command that prints input store paths. Vendomat needs a command such as `lockpath.nix`, or an `outputs.inputPaths` convention, to feed Attic or audits.
7. (Q6) devenv accepts branch refs and has no pin policy. Vendomat must ship the check (the script above) in verify and CI, including the lock walk for transitive nodes.
8. (Q7) devenv's push path is Cachix-only and has no `devenv:build` task or post-build hook. Vendomat must wrap `devenv build` and pipe the paths to `attic push --stdin` (or run `attic watch-store`). The Attic upload is still unproven.
9. (Q8) Profiles from `inputs.X.devenv.config` references are not applied (#2521), and `inputs.X.devenv` needs a flake input with nixpkgs and devenv inputs. Vendomat should use `imports` for profile-bearing modules and avoid the reference pattern.
