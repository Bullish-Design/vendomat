# F2: hand-off of `vendomat.yaml` data to the Nix catalog module

Date: 2026-10-12. Nothing inside the Vendomat repository changed.
All files are under `~/.local/state/vendomat/p20/2026-10-12/F2-yaml-handoff/` (`$D` below).

## Common inputs

- Fork: `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv` (`devenv 2.4.0+fb5d382`). Used by absolute path in every wrapper and direct run.
- Stock devenv on PATH: `2.4.0+b904dcb`. Testee runs this one (`devenv eval ...` from PATH).
- Nix 2.34.7. Testee 0.6.1 (`~/.nix-profile/bin/testee`). direnv 2.37.1. Python 3.13.14 (nix env, stdlib only, run with `-I`).
- `btrfs filesystem usage /` at start: unallocated 31 GiB, metadata 75 % used. Gate passed.
- Workspace lock: copy of the B-eager-checks `ws/devenv.lock` (devenv-nixpkgs 256551e4). Testee fixtures use the Vendomat `devenv.lock` copy.
- Parser: `$D/bin/vyaml.py`, 173 lines (about 150 for the parser; about 20 for the `--nix` and `--text` modes that H3 needs). Output: JSON (or Nix with `--nix`). Every scalar is a string. Maps and lists only.
- Catalog module: `$D/tmpl/catalog.nix.in` (from B-eager-checks `catalog-all`). The `@@DATA@@` line is the only difference between candidates. `bool` options use `coercedTo (enum ["true" "false"]) (s: s == "true") bool`. `version` and `name` are `str`. `_file = "vendomat.yaml"`.
- Candidate workspaces: `ws-h1` (getEnv), `ws-h2` (file), `ws-h3` (plain `builtins.exec`), `ws-h3b` (exec with `pathExists` and `readFile`, see below), `ws-h3c` (h3b with an exec counter).
- Wrappers: `bin/vendomat-h1`, `bin/vendomat-h2` (stand-ins for the host `vendomat`). `bin/devenv-h3` is the fork with `NIX_CONFIG` set (stand-in for a `nix.conf` setting; it parses nothing).
- Probe: `bin/probe.sh ENTRY...` runs `ENTRY -v --no-tui shell -- sh -c 'echo SEEN ...'`. `-v` is needed to see the `(cached)` mark. The shell prints the values it received.
- Base data: `cases/base.yaml` (`version: 3.10`, `name: no`, `enable: "false"` for postgres, `enable: true` for python).

## Parser check (all candidates)

- Command: `$PYB -I bin/vyaml.py cases/X.yaml`. Log `logs/parser-unit.log`.
- Actual: tab `vendomat.yaml:2:1: tabs are not accepted; use spaces`. Anchor `1:6`, alias `1:4`, tag `1:4`, flow `1:11`, duplicate key `3:1: duplicate key 'a'; first on line 1`, `---` `2:1`, bad indent `3:5`, empty value `1:3`, unterminated quote `1:4`. All exit 2.
- Traps: `name: no`, `version: 3.10`, `flag: yes`, `num: 012`, `null1: ~` stay the strings "no", "3.10", "yes", "012", "~".
- Proves: the cut-down parser gives `file:LINE:COL: reason` for every listed fault on these 15 inputs.
- Unproved: any fuzz or oracle comparison (the S1 hand parser had one; this one has none). Lists of maps, block scalars, and multi-line strings are not supported (rejected).

## Q1. Edit detection

Sequence (`bin/q1.sh ENTRY`): baseline, unchanged rerun, value change 3.10 to 3.11, same-size edit 3.11 to 3.12 with `touch -r` (size 159 and mtime equal before and after, shown in the log), add key `env.EXTRA`, delete the file, restore the file. Each step runs `shell` and prints the value the shell saw.

| Step | H1 getEnv (wrapper) | H2 file (wrapper) | H3 plain exec (direct fork) | H3b exec + readFile (direct fork) |
| --- | --- | --- | --- | --- |
| unchanged rerun | (cached), correct | (cached), correct | (cached), correct | (cached), correct |
| value change | re-eval 2.4 s, 3.11 | re-eval 4.1 s, 3.11 | (cached), STALE 3.10 | re-eval 4.2 s, 3.11 |
| same-size, mtime restored | re-eval, 3.12 | re-eval, 3.12 | (cached), STALE | re-eval, 3.12 |
| add key | re-eval, EXTRA=yes | re-eval, EXTRA=yes | (cached), STALE | re-eval, EXTRA=yes |
| delete file | re-eval, defaults ("unset") | re-eval, defaults | (cached), STALE (old values) | re-eval, defaults |
| restore | re-eval, 3.10 | re-eval, 3.10 | (cached), 3.10 (never left) | re-eval, 3.10 |

- Logs: `logs/q1-h1.log`, `q1-h2.log`, `q1-h3.log`, `q1-h3b.log`.
- Hypothesis for H1: the fork's eval cache keys on `getEnv` values. Result: supported. A changed `VENDOMAT_DATA` forced a re-eval each time. Unchanged data stayed cached.
- H2: the cache tracks the content of the read file. Rewriting the same bytes on each run (new mtime) stayed `(cached)`. A same-size edit with restored mtime was seen.
- H3 plain: the eval cache does NOT track what `builtins.exec` reads. Every edit stayed `(cached)` and silent. This is the worst result.
- H3b fix: Nix reads the file itself (`builtins.pathExists`, `builtins.readFile`) and passes the text to the parser as an argument (`--text`). The cache then tracks the file. Deleting and restoring the file also worked. Catalog line: `let p = config.devenv.root + "/vendomat.yaml"; in if builtins.pathExists p then builtins.exec [ python "-I" parser "--nix" "--text" (builtins.readFile p) ] else {}`.
- Proves: H1, H2, H3b see all five edits on this fork. H3 plain does not see any.
- Inference: the same cache rule holds for other commands that read `config` (not run; only `shell` and, for the counter, `test`).
- Unproved: very large files, concurrent edit during a run, a symlinked `vendomat.yaml`.

## Q2. Entry points

Logs: `logs/q2-clone.log`, `q2-more.log`, `q2-h1-direct-*.log`, `q2-h1-envleak.log`, `q2-direnv.log`.

| Case | H1 | H2 | H3 plain | H3b |
| --- | --- | --- | --- | --- |
| Fresh `git clone`, via wrapper | works (8.5 s cold) | works | n/a | n/a |
| Fresh clone, direct fork, setting present | n/a | n/a | works | works |
| Fresh clone, direct fork, no wrapper | FAILS: `error: [json.exception.parse_error.101] ... empty input` (578 lines) | FAILS: `error: path '.../.devenv/vendomat-data.json' does not exist` (586 lines) | n/a | n/a |
| Fresh clone, direct fork, setting missing | n/a | n/a | FAILS: `error: attribute 'exec' missing` (575 lines) | same |
| Direct fork after an edit, old state present | STALE and silent when `VENDOMAT_DATA` leaks from a wrapper-started shell (shell carries it: length 169) | STALE and silent: yaml 3.11, shell saw 3.10, `(cached)` | STALE (see Q1) | current |
| direnv `use devenv` (fork first on PATH, isolated state) | FAILS (same JSON error) | FAILS (same path error) | current at 3.10, STALE after edit | current, 3.11 after edit |

- Hypothesis: a direct fork run with H1 or H2 fails or goes stale. Result: supported. H1 fails when the env var is unset and goes stale when it leaks. H2 goes stale when a generated file exists and fails on a fresh clone.
- A cached eval hides a missing setting. In a clone that ran once with the setting, a direct run without the setting printed `(cached)` and succeeded (`logs/q2-more.log`, third case). A fresh clone showed the true failure.
- Proves: only H3b works from a fresh clone through direct fork and direnv with no wrapper, if the setting is present.
- Inference: a catalog guard (`if getEnv == "" then throw "run through vendomat"`) would shorten the H1 error. Not run.
- Unproved: the stale H1 case through direnv with a leaked variable.

## Q3. Testee

Setup: `testee-fx/t-h1`, `t-h2`, `t-h3`, `t-h3b`, each a git repo with `devenv.yaml` (inputs `nixpkgs`, `nixpkgs-python`, `testee` v0.6.1; imports `testee/nix/testee.nix` and `./catalog.nix`), the Vendomat `devenv.lock`, and one check `seen` that passes only if `$VM_PY_VERSION` is `3.10`. No `testee.prepare` needed. Testee runs `devenv eval testee.manifestJson shell.drvPath` from PATH with a fixed environment (source: `testee/runner/provenance.py`). The kept variables are HOME, USER, LOGNAME, PATH, LANG, LC_ALL, TZ, TERM, NIX_PATH, NIX_REMOTE, NIX_SSL_CERT_FILE, SSL_CERT_FILE, and XDG_* dirs. `NIX_CONFIG`, `NIX_USER_CONF_FILES`, and `VENDOMAT_DATA` are dropped.

| Candidate | Result | Log |
| --- | --- | --- |
| H1, plain `testee verify` | `testee: eval_failed: devenv eval failed: [json.exception.parse_error.101] ... empty input`, exit 2 | `q3-h1-plain.log` |
| H1, caller exports `VENDOMAT_DATA` | same failure: Testee drops the variable | `q3-h1-env.log` |
| H2, plain | `testee: module_missing: this repository does not import the Testee module` (wrong text: the path of the missing file contains "testee"), exit 2 | `q3-h2-h3-nosetting.log` |
| H2 with `testee.keep = [".devenv/vendomat-data.json"]` | same failure, one try | `q3-h2-keep.log` |
| H3b, no setting | `eval_failed: devenv eval failed: attribute 'exec' missing`, exit 2 | `q3-h2-h3-nosetting.log` |
| H3b, `XDG_CONFIG_HOME=$D/xdg` (holds `nix/nix.conf` with the setting) | GREEN at 3.10. After the edit to 3.11 in the working copy: RED (`seen` failed), so Testee saw the new data | `q3-h3b-xdg.log` |
| H3 plain, same setting | GREEN at 3.10. After the edit to 3.11: GREEN again; `seen.txt` says `PYV=3.10`. A false green verdict | `q3-h3-plain.log` |

- Proves: H1 and H2 do not work under Testee as built: Testee evaluates in its own checkout with a clean environment and has no hook before the eval. H3b works if the Nix setting comes from `nix.conf` (HOME or XDG_CONFIG_HOME). H3 plain gives wrong green verdicts.
- Inference: the `/etc/nix/nix.conf` route (NixOS `nix.settings`) also works, because Testee keeps PATH and HOME and Nix reads it. Not run (the file is generated and I did not change it).
- Unproved: a wrapper that makes Testee run the data step first (for example a `vendomat verify` that calls Testee); this needs a Testee hook that 0.6.1 does not show. `testee.keep` behavior with a file that exists at eval time.

## Q4. Errors

Logs: `logs/q4-h1.log`, `q4-h3b.log`, `q4-h3b-tab-full.log`, `q4-testee-tab.log`.

- H1 and H2 (wrapper): a subset fault prints one line and exits 2 before devenv starts: `vendomat.yaml:4:1: tabs are not accepted; use spaces`, `3:6 anchors`, `1:11 flow style`, `4:1 duplicate key 'name'; first on line 3`, `3:1 document markers`. Output is 1 line, 50 ms.
- H3b (direct fork): the parser line is the FIRST line of output (`vendomat.yaml:4:1: tabs are not accepted; use spaces`). Then 237 lines of Nix trace. The last line is `error: program ".../python3" failed with exit code 2`, which does not name the file. Total 578 lines. With a terminal that scrolls, the user sees the generic line last.
- H3b under Testee: the parser line is lost. Testee prints `testee: eval_failed: devenv eval failed: program ".../python3" failed with exit code 2`. The user sees no line number.
- Type errors (same catalog for all three, 648 lines of trace, message at the end):
  - `vendomat.yaml: `services.postgres.enable' must be boolean or (one of "true", "false") convertible to it, found string "maybe"`
  - `enable: no` and `enable: yes`: the same message with `found string "no"` and `"yes"`. Both rejected.
  - Two bad fields: both are listed in one message.
  - Unknown key (`enabled`): `error: The option `vendomat.languages.python.enabled' does not exist. Definition values:` (the user must read the next lines for `In `vendomat.yaml'`).
- The type error gives file and field, with no line number. The source of a line number would be the parser; Nix never receives it.
- Proves: a LINE:COL message reaches the user directly only when the host parser runs before devenv (H1, H2). With H3b it reaches the user only on a direct fork run, and it comes first, before a long trace.
- Unproved: a trace filter for H3b; the fork has no flag to cut the trace (B-eager-checks Q3).

## Q5. Traps

Input `err-traps.yaml`: `name: no`, `version: 3.10`, `enable: "true"`. All three candidate wrappers and H3b ran it.

- Actual: shell saw `PYV=3.10 EN=true NAME=no` (logs `q4-h1.log`, `q4-h3b.log`). The string "3.10" and the string "no" stayed text.
- `enable: no`, `enable: yes`, `enable: maybe` in a bool field: rejected with the message in Q4.
- `enable: true` unquoted is the string "true" and is accepted. `enable: "true"` quoted also gives "true". This means quoting makes no difference, which is the design intent.
- Proves: with all-string input and the `coercedTo` bool type, the `3.10` and `no` traps cannot happen on this catalog. Not by construction for fields typed with a non-string type that accepts strings (none exist in the fixture).
- Unproved: integer fields (`port: 5432` would need an `int` coercion; not tried).

## Q6. Cost

- Parser size: 173 lines, stdlib Python. Timing (`logs/q6-timing.log`): 39 ms per run, of which 30 ms is interpreter start. The parse itself is about 9 ms. A host `vendomat` parser in the same process adds the 9 ms only.
- Cached-shell time per command (5 runs): fork alone with env 361 ms, H1 wrapper 369 ms, H2 wrapper 342 ms, H3b direct 318 ms. No candidate adds a measurable cost on a cached run.
- H3 exec count (`logs/q6-exec-count.log`): the parser runs once per uncached evaluation and zero times per cached run (cold 1, cached 0, edit 1, `test` after edit 1).
- Setting routes for `allow-unsafe-native-code-during-evaluation` (logs `h3-setting-*.log`):
  - Works: `NIX_CONFIG='allow-unsafe-native-code-during-evaluation = true'`; fork flag `--nix-option allow-unsafe-native-code-during-evaluation true`; `NIX_USER_CONF_FILES`; `XDG_CONFIG_HOME/nix/nix.conf` (so also `~/.config/nix/nix.conf`).
  - Does not work: `nixConfig:`, `nix_options:`, `nix-option:`, `nixOptions:` keys in `devenv.yaml` (accepted silently, no effect; one try each, `--no-eval-cache`).
  - Without the setting `builtins.exec` does not exist: `error: attribute 'exec' missing`.
  - No per-project route was found. A per-project setting would need the flag or `NIX_CONFIG` (direnv `.envrc`), which Testee drops.
- Security (`logs/q6-security.log`): with the setting, any Nix expression the user's Nix evaluates can run any program as the user. Test: `nix eval --impure --expr 'builtins.exec [ "/bin/sh" "-c" "echo ..." ]'` printed `"ran as andrew"` with the setting and `attribute 'exec' missing` without. This covers third-party flakes, `devenv.yaml` inputs, and every `nix eval` on the machine, not only Vendomat. A cloned repository with a hostile `devenv.nix` runs code at evaluation time, before the user enters a shell, and before direnv's trust check shows anything (inference: `direnv allow` still gates `.envrc`; I did not test a hostile `devenv.nix` and ran no hostile code). The setting is a machine-wide trust change; the other candidates have none.
- Proves: H3 needs a global, unsafe Nix setting. Parser trust moves from "the Vendomat host binary" to "every Nix expression".
- Unproved: whether `--pure-eval` or `restrict-eval` blocks exec; whether the setting is accepted from a flake's `nixConfig` (`accept-flake-config = false` on this host).

## Summary table

| | H1 env | H2 file | H3 plain exec | H3b exec + readFile |
| --- | --- | --- | --- | --- |
| Edit detection | all 5 seen | all 5 seen | none seen, silent stale | all 5 seen |
| Direct fork, no wrapper | fails (JSON error) or silent stale when env leaks | silent stale; fresh clone fails | needs setting; stale | works with setting |
| Fresh clone | wrapper only | wrapper only | direct, with setting | direct, with setting |
| Direnv | fails | fails | stale | works |
| Testee | fails (env dropped) | fails (no file in checkout) | wrong GREEN | works (setting via nix.conf) |
| Error line | 1 line, wrapper | 1 line, wrapper | first line plus 237 lines of trace | same; lost in Testee |
| Traps and types | pass | pass | pass | pass |
| Cost | 0 added | 0 added | global unsafe setting | global unsafe setting |
