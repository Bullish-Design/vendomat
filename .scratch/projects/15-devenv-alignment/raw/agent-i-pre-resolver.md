<!-- Raw final report of Agent I (pre-resolver and generated inputs, sonnet), 2026-10-09. Extracted unedited from the agent transcript (longest hand-back). Raw logs: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/. -->

All seven questions have fixture results on devenv 2.4.0+b904dcb (nix 2.34.7, direnv 2.37.1). The main surprise is Q5: a failing task does not stop `devenv shell`, so the staleness check is an assertion instead.

Source reads use /nix/store/n1zz8rrfw0sx39dizqj4a6468lxga71q-source, which is `nix flake prefetch github:cachix/devenv/b904dcb5…` (rev b904dcb51fe48c30db250038241507f60752f222).

Raw log dir: `~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-i/` (called `$L` below). It holds the `q*.txt` logs, `fixtures/` and `scripts/`.
- Full prototype: `$L/scripts/vendomat_sync.py`
- Direnv function: `$L/scripts/vendomat.direnv.sh`
- Lock summariser and benchmarks: `$L/scripts/{lockinfo,bench,bench2}.py`

Fixture: a temp dir with bare repos lib-a, lib-b and lib-c, served by my own `git daemon` on 127.0.0.1:39721 (lib-a and lib-c tagged v1 and v2, lib-b v1).
- lib-c is a flake with no inputs.
- lib-b has flake inputs nixpkgs (`github:cachix/devenv-nixpkgs/rolling`) and lib-c v1. Its `devenv/devenv.yaml` declares lib-c and `devenv/devenv.nix` reads `inputs.lib-c.name`.
- lib-a has flake inputs nixpkgs and lib-b v1.

Cleanup: the daemon is stopped, the port is free, and the temp dir and its files are removed. I removed the direnv allow and deny entries my test created; the allow count is back to 13.

## Q1. Generated fragment import
ANSWER
- **Locking:** Yes. Workspace `devenv.yaml` contained only `imports: [./.vendomat]`. All fragment inputs landed in the workspace's own `devenv.lock`, and the workspace `devenv.nix` used `inputs.lib-a` and `inputs.lib-c`.
- **Update:** `devenv update` works (exit 0).
- **Relative URLs:** Both `path:./frag-lib` and `./frag-lib` inside the fragment resolve against the FRAGMENT dir, not the workspace. The lock holds `.vendomat/frag-lib`, matching config.rs:762-846. A decoy `frag-lib` in the workspace was not used.

EVIDENCE (`q1-shell.log`, `q1-lock.txt`, `q1b-update-relpath.txt`)
```
A=av1 C=cv1
root inputs: {"devenv":"devenv","lib-a":"lib-a","lib-c":"lib-c_2","nixpkgs":"nixpkgs_2"}
node lib-a inputs={'lib-b':'lib-b','nixpkgs':['nixpkgs']}   <- one-level follows applied
devenv update exit=0
FRAG=FRAGMENT-DIR-COPY FRAG2=FRAGMENT-DIR-COPY      (decoy was WORKSPACE-DIR-DECOY)
frag-lib  {'path': '.vendomat/frag-lib', 'type': 'path'}
frag-lib2 {'path': './.vendomat/frag-lib', 'type': 'path'}
```
Without `lib-b.inputs.lib-c.follows`, this lock has two lib-c nodes and two nixpkgs nodes. The lock also contains a root `devenv` input.

STATUS: PROVEN.

## Q2. Precedence
ANSWER
- **Workspace over fragment:** The workspace `devenv.yaml` wins over the fragment, and `devenv.local.yaml` wins over both.
- **Whole-entry replacement:** A winning entry replaces the whole input entry. It does not merge fields.
  - The fragment's `lib-a.inputs.nixpkgs.follows` was lost when the workspace redeclared `lib-a` with only a `url`. lib-a's nixpkgs became its own node `nixpkgs_2`.
  - The fragment's `flake: false` on `frag-lib` was lost when the workspace redeclared `frag-lib` with only a `url`. With the override removed, the lock shows `"flake": false` again.
- **Practical rule:** An override in the workspace or local yaml must restate `inputs.*.follows` and `flake` itself.

EVIDENCE (`q2a-workspace-wins.txt`, `q2a2-merge-shallow.txt`, `q2b-local.txt`)
```
fragment lib-a v1, workspace lib-a v2:          A=av2   lib-a ref=refs/tags/v2 inputs={'lib-b':'lib-b','nixpkgs':'nixpkgs_2'}
fragment v1, devenv.local.yaml v2:              A=av2
fragment v1, workspace v2, devenv.local.yaml v1: A=av1
frag-lib, fragment-only:      {"flake": false, "locked": {"path": ".vendomat/frag-lib"...
frag-lib, workspace override: {"locked": {"path": "frag-lib", "type": "path"} ...   (no "flake" key)
```
The source ordering at config.rs:681-745 is source, then imports, then base, then `devenv.local.yaml`. I did not read the merge implementation itself. The whole-entry behaviour comes from the fixtures only.

STATUS: PROVEN by fixture. The merge mechanism is UNPROVEN because I did not read the loader code.

## Q3. The #2205 gap
ANSWER
- **Failure reproduced:** Without the pre-resolver, `imports: [lib-b/devenv]` with only lib-b declared fails with `attribute 'lib-c' missing`.
- **Fix works:** After `vendomat_sync.py` runs, the workspace enters the shell. `LIB_B_SEES_C=c`.
- **Lock:** It has exactly one lib-c node and one nixpkgs node, plus nixpkgs' own `nixpkgs-src` sub-input.
- **Imports in the fragment:** `imports: [lib-b/devenv]` inside the generated `.vendomat/devenv.yaml` is honoured (tested).
- **Fetch method:** The script uses `nix flake prefetch --json`.
- **Follows:** It reads the `devenv.yaml` under the store path and recurses into nested `imports`. It asks `nix flake metadata --json --no-write-lock-file` for each input's own direct inputs. It emits one-level follows for every shared name. It skips a follow when the source differs, and writes a `note:` line.
- **Limits:** A conflict between two imported yaml files exits with an error; a registry entry wins silently. The mini YAML parser handles only block maps, scalar lists, `{}` and `[]`.

EVIDENCE (`q3a-failure-baseline.txt`, `q3b-prototype.txt`)
```
error: attribute 'lib-c' missing        (devenv/devenv.nix:2:22)

vendomat sync: 3 inputs, 1 imports, digest b519f0183869        (0.5 s warm)
.vendomat/devenv.yaml:
imports: - "lib-b/devenv"
inputs: lib-b {url, inputs: {lib-c: {follows: "lib-c"}, nixpkgs: {follows: "nixpkgs"}}}
        lib-c {url}   nixpkgs {url}
B_SEES_C=c
root inputs: {"devenv","lib-b","lib-c","nixpkgs"}
lib-b inputs={'lib-c':['lib-c'],'nixpkgs':['nixpkgs']}
node count by source: {'cachix/devenv':1,'lib-b':1,'lib-c':1,'cachix/devenv-nixpkgs':1,'NixOS/nixpkgs':1}
```
`vendomat.json` registry, the same file used in Q3 to Q6:
```
{"inputs": {"nixpkgs": {"url": "github:cachix/devenv-nixpkgs/rolling"},
            "lib-b": {"url": "git://127.0.0.1:39721/lib-b?ref=refs/tags/v1"}},
 "imports": ["lib-b/devenv"]}
```
The workspace `devenv.yaml` is `imports: [./.vendomat]`.

Core of the script (`main()`, verbatim; the full file is `$L/scripts/vendomat_sync.py`, 279 lines):
```python
def main(ws):
    ws = Path(ws).resolve()
    reg_bytes = (ws / "vendomat.json").read_bytes()
    reg = json.loads(reg_bytes)
    top = {k: dict(v) for k, v in reg["inputs"].items()}
    direct = set(top)
    imports = []
    notes = []
    resolved = {}

    def add(name, spec, origin):
        if name in top:
            if top[name]["url"] == spec["url"]:
                return
            if name in direct:
                notes.append(f"{name}: registry url wins over {origin}")
                return
            sys.exit(f"vendomat sync: conflict on input '{name}': {top[name]['url']} vs {spec['url']} ({origin})")
        top[name] = {"url": spec["url"], **({"flake": False} if spec.get("flake") is False else {})}

    def walk(imp):
        if imp in imports:
            return
        imports.append(imp)
        inp, _, sub = imp.partition("/")
        if inp not in top:
            sys.exit(f"vendomat sync: import '{imp}' names unknown input '{inp}'")
        pf = prefetch(top[inp]["url"])
        resolved[imp] = {"narHash": pf["hash"], "rev": pf["locked"].get("rev")}
        yml = Path(pf["storePath"]) / sub / "devenv.yaml"
        if not yml.exists():
            return
        doc = parse_yaml(yml.read_text())
        for name, spec in (doc.get("inputs") or {}).items():
            add(name, spec, imp)
        for nested in doc.get("imports") or []:
            if not nested.startswith("."):
                walk(nested)

    for imp in reg.get("imports", []):
        walk(imp)

    leaf = set(reg.get("leaf", ["nixpkgs"]))
    flatten = bool(reg.get("flatten"))
    done = set()
    todo = [n for n in top if top[n].get("flake") is not False]
    while todo:
        x = todo.pop(0)
        if x in done:
            continue
        done.add(x)
        for n, orig in direct_inputs_of(top[x]["url"]).items():
            if n == x:
                continue
            if n not in top and flatten and x not in leaf:
                url = original_to_url(orig)
                if url is None:
                    notes.append(f"{x}.{n}: cannot flatten type {orig['type']}")
                    continue
                top[n] = {"url": url}
                todo.append(n)
            if n in top:
                same = same_source(top[n]["url"], orig)
                if same is False:
                    notes.append(f"{x}.{n}: not followed, source differs from top-level {n}")
                    continue
                top[x].setdefault("inputs", {})[n] = {"follows": n}

    out = ws / ".vendomat"
    out.mkdir(exist_ok=True)
    yaml_text = emit_yaml(top, imports)
    (out / "devenv.yaml").write_text(yaml_text)
    (out / "devenv.nix").write_text(NIX_TEMPLATE)
    full = sha(json.dumps({"registry": reg, "resolved": resolved, "inputs": top}, sort_keys=True))
    (out / "digest").write_text(
        f"digest {full}\nregistry {sha(reg_bytes)}\nfragment {sha(yaml_text)}\n"
    )
    for n in notes:
        print("note:", n, file=sys.stderr)
    print(f"vendomat sync: {len(top)} inputs, {len(imports)} imports, digest {full[:12]}")
```
The helpers `parse_yaml`, `emit_yaml`, `prefetch`, `metadata`, `direct_inputs_of`, `original_to_url`, `same_source` and `sha` are not pasted here; they are in the file. `NIX_TEMPLATE` is under Q5.

STATUS: PROVEN. This is a prototype: only git and github source types are handled, and the YAML subset is limited.

## Q4. Flatten nested follows
ANSWER
- **Result:** Yes. With `"flatten": true` the generator lifted lib-b and lib-c to top level. It wrote `lib-a.inputs.lib-b.follows: lib-b`, `lib-b.inputs.nixpkgs.follows: nixpkgs`, and the same for lib-c and nixpkgs.
- **Lock:** One nixpkgs node and one of each lib-a, lib-b and lib-c. The workspace used `inputs.lib-a`, `inputs.lib-b` and `inputs.lib-c`.
- **Sub-node:** `nixpkgs-src` is nixpkgs' own single sub-input.
- **Nested form not retested:** I did not rerun the known nested-follows drop here.

EVIDENCE (`q4-flatten.txt`)
```
registry: inputs nixpkgs, lib-a(v1); "flatten": true
CHAIN=a-b-c
root inputs: {"devenv","lib-a","lib-b","lib-c","nixpkgs"}
lib-a inputs {'lib-b': ['lib-b'], 'nixpkgs': ['nixpkgs']}
lib-b inputs {'lib-c': ['lib-c'], 'nixpkgs': ['nixpkgs']}
nodes whose key starts with nixpkgs: ['nixpkgs', 'nixpkgs-src']
```
STATUS: PROVEN.

## Q5. Staleness check
ANSWER
- **Task variant:** A task with `before = ["devenv:enterShell"]` that exits 1 CANNOT fail shell entry. `devenv shell -- sh -c 'echo SHELL-ENTERED'` still ran the command and exited 0. The source says so: devenv/src/devenv/mod.rs:2239-2241, "Task failures are logged as warnings but don't prevent shell entry", and the comment at 2257, "Shell entry proceeds even if some tasks fail".
- **Working variant:** An assertion in the generated `.vendomat/devenv.nix` fails evaluation, so `devenv shell` exits non-zero with the message. It is evaluated on every entry. The eval cache did not hide the change: the file read and hash are re-evaluated when the file changes.
- **Reading outside the store:**
  - `config.devenv.root` is the real project dir, not a store path (`/tmp/agent-i.3HA4vm/ws5` in the test).
  - A task read `vendomat.json` there at run time.
  - The assertion reads the root files at eval time with `builtins.readFile`, `builtins.hashFile` and `builtins.pathExists`, using `/. + "${root}/…"`.
- **Digest file:** Lines `digest <sha>`, `registry <sha of vendomat.json bytes>` and `fragment <sha of .vendomat/devenv.yaml>`.
- **What it detects:** The check compares only the registry and fragment hashes, so it works offline. It does not detect a moved tag; `devenv.lock` pins that.

EVIDENCE (`q5-staleness.txt`, `q5a-task-cannot-fail-shell.txt`)
```
task variant:  "task sees root=/tmp/agent-i.3HA4vm/ws5 sha=01cb07eb6a95"
               "✖ Running devenv:enterShell … (dependency failed)"
               SHELL-ENTERED root=/tmp/agent-i.3HA4vm/ws5     rc=0
assertion:
fresh                          SHELL-ENTERED   exit=0
edit vendomat.json, no sync    error: Failed assertions:
                               - vendomat: STALE. vendomat.json changed since the last sync. Run: vendomat sync
                               exit=1
revert bytes                   exit=0
hand-edit fragment             - vendomat: STALE. .vendomat/devenv.yaml was edited by hand. Run: vendomat sync   exit=1
re-sync                        exit=0
delete digest                  - vendomat: .vendomat/digest is missing. Run: vendomat sync   exit=1
```
`NIX_TEMPLATE` (the `.vendomat/devenv.nix` the script writes), verbatim:
```nix
# Generated by vendomat sync. Do not edit.
# A failing enterShell task does NOT stop `devenv shell` (devenv/src/devenv/mod.rs:2239-2241).
# An evaluation error does. So the freshness check is an assertion, evaluated on every shell entry.
{ lib, config, ... }:
let
  root = config.devenv.root;
  digestPath = /. + "${root}/.vendomat/digest";
  registryPath = /. + "${root}/vendomat.json";
  fragmentPath = /. + "${root}/.vendomat/devenv.yaml";
  recorded =
    key:
    let
      hits = lib.filter (l: lib.hasPrefix "${key} " l) (lib.splitString "\n" (builtins.readFile digestPath));
    in
    if hits == [ ] then "missing" else lib.removePrefix "${key} " (builtins.head hits);
  haveDigest = builtins.pathExists digestPath;
in
{
  assertions = [
    {
      assertion = haveDigest;
      message = "vendomat: .vendomat/digest is missing. Run: vendomat sync";
    }
    {
      assertion = !haveDigest || builtins.hashFile "sha256" registryPath == recorded "registry";
      message = "vendomat: STALE. vendomat.json changed since the last sync. Run: vendomat sync";
    }
    {
      assertion = !haveDigest || builtins.hashFile "sha256" fragmentPath == recorded "fragment";
      message = "vendomat: STALE. .vendomat/devenv.yaml was edited by hand. Run: vendomat sync";
    }
  ];
}
```
STATUS: PROVEN. The task design is DISPROVEN for failing shell entry. An interactive `devenv shell` was not run; the claim rests on the source comment and on the `-- cmd` run.

## Q6. direnv hook
ANSWER
- **No-change cost:** A no-change run does not call sync and takes about 0.34 to 0.40 s wall, almost all of it `use devenv`.
- **Sync triggers:** Sync runs when the digest file is missing, the registry hash differs, or the fragment hash differs.
- **Overhead of the function:** I could not isolate it cleanly. Stubbed, 20 calls took 1.9 s wall but only 0.44 s of CPU, so about 95 ms wall per call is mostly process spawn, and the number is noisy.
- **Re-evaluation:** `direnv export bash` also re-evaluates `.envrc` each time, at about 0.40 s.

`.envrc` (`$L/fixtures/ws6.envrc`; the path in `VENDOMAT_SYNC` is the real script path):
```
export VENDOMAT_SYNC="python3 -I $L/scripts/vendomat_sync.py"
source ./vendomat.direnv.sh
eval "$(devenv direnvrc)"
use_vendomat
```
`vendomat.direnv.sh`, verbatim:
```bash
# Sourced by .envrc. Defines use_vendomat.
# Needs: VENDOMAT_SYNC (command that syncs one workspace dir), sha256sum, awk.
_vendomat_sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
_vendomat_recorded() { awk -v k="$1" '$1 == k { print $2 }' "$2" 2>/dev/null; }

use_vendomat() {
  local root="${1:-$PWD}"
  local digest="$root/.vendomat/digest"
  # Make direnv reload when the registry or the digest changes.
  watch_file "$root/vendomat.json" "$digest"
  local stale=""
  [ -f "$digest" ] || stale="no digest"
  [ -z "$stale" ] && [ "$(_vendomat_sha "$root/vendomat.json")" != "$(_vendomat_recorded registry "$digest")" ] && stale="registry changed"
  [ -z "$stale" ] && [ "$(_vendomat_sha "$root/.vendomat/devenv.yaml")" != "$(_vendomat_recorded fragment "$digest")" ] && stale="fragment edited"
  if [ -n "$stale" ]; then
    log_status "vendomat: $stale; running sync"
    if ! $VENDOMAT_SYNC "$root"; then
      log_error "vendomat: sync failed"
      return 1
    fi
  fi
  use devenv
}
```
EVIDENCE (`q6-direnv-exec.txt`, `q6b-timing.txt`)
```
A no digest:      direnv: vendomat: no digest; running sync -> "vendomat sync: 3 inputs…" -> ENTERED B_SEES_C=c   4.27 s (first)
B no change x2:   direnv: using devenv (no sync line)        0.395 s, 0.383 s
C registry edit:  direnv: vendomat: registry changed; running sync   2.45 s total
D no change:      0.335 s
direnv export bash x2 (no change): 0.411 s, 0.403 s
```
STATUS: PROVEN with `direnv exec` and `direnv export bash`. Interactive prompt-hook behaviour was not tested.

## Q7. Speed
ANSWER: The fragment import adds no material cost. I ran `devenv shell -- true` 15 times warm and 7 times with `--no-eval-cache`, interleaving the three workspaces to cancel drift.
- A: inputs and imports inline in `devenv.yaml`, no fragment.
- B: fragment with an empty `devenv.nix`.
- C: fragment with the freshness assertion.

EVIDENCE (`q7-speed.txt`, `q7-speed-no-eval-cache.txt`)
```
warm (eval cache hit):   A median 0.175 s | B 0.173 s | C 0.176 s
--no-eval-cache (full eval): A 1.642 s | B 1.673 s | C 1.707 s
```
In the full-eval case the fragment costs about 30 ms and the assertion about 35 ms more. On a warm eval-cache hit the three are indistinguishable.

STATUS: PROVEN for this fixture (3 inputs). Cost with many inputs was not measured.

## Other findings
1. The workspace entry replaces the fragment entry per input (Q2), so the generator must warn when a workspace or local yaml redeclares a generated input.
2. Imports listed inside the fragment's `devenv.yaml` are honoured, so the workspace yaml can be only `imports: [./.vendomat]`.
3. The pre-resolver needs network or a warm Nix cache at sync time only. Shell entry needs no sync.
4. UNPROVEN: behaviour when the same input name has different URLs in two imported yaml files (the script errors by design, but I did not run that path). Also not run: `flake: false` inputs through the follows pass, and non-git, non-github source types.
