# S1: the `vendomat.yaml` accepted subset

**Date:** 2026-10-11. **Status:** spike record. Fixtures are NON-PRODUCTION. No ID is allocated here.
**Fixtures:** `evidence/fixtures/s1-yaml/` in this workspace. **Logs:** `~/.local/state/vendomat/p20/2026-10-11/S1/`.

## 1. Question and hypotheses

Question: which exact YAML subset does the linter accept, and which implementation enforces it?

| # | Hypothesis | Verdict |
| --- | --- | --- |
| H1 | The existing `src/vendomat/yamlsubset.py` can serve. | Disproved (section 4.1). |
| H2 | A strict node walk over PyYAML or ruamel.yaml gives exact errors. | Partly disproved: it works, but locations and codes are weaker, and it adds a dependency (4.1, 4.5). |
| H3 | StrictYAML fits. | Disproved: it has no scalar types (4.1). |
| H4 | A hand parser can be correct, if a library is the test oracle. | Supported: 0 divergences in 12,000 random trees and 800,000 mutants (4.3). |
| H5 | Unquoted keys can stay, if values must be quoted. | Supported with an identifier rule for keys (3.2). |
| H6 | Block scalars are needed. | Supported by devenv option types (3.3). |
| H7 | A key-name recognizer can find secret fields with few false positives. | Supported on 547 devenv names; limits in 5. |

## 2. Exact inputs

| Item | Value |
| --- | --- |
| Host | Linux 6.18.38, load average 16 during timing (wall times are noisy; use CPU times) |
| Nix | 2.34.7 |
| nixpkgs | `c8f90650c15282fa8656a041bfbbd2403997a9a7` (`nixpkgs-src` node of the workspace `devenv.lock`; `devenv-nixpkgs` is `256551e4`) |
| Python | 3.14.7 (the workspace asks for >= 3.13; 3.13 was not run) |
| Libraries | PyYAML 6.0.3 (libyaml present), ruamel.yaml 0.19.1 (no C extension in this env), strictyaml (store path 1.7.3, module attribute says 1.6.2) |
| Library env | `nix build --no-link --impure --expr 'let p=import (builtins.getFlake "github:NixOS/nixpkgs/c8f9…").outPath {}; in p.python3.withPackages (ps: [ps.ruamel-yaml ps.pyyaml ps.strictyaml])'` |
| Today's parser | `src/vendomat/yamlsubset.py`, imported read only via `sys.path` |
| devenv module source | newest `*-source/src/modules` in the local store (`7lsasdm…`). Its revision was not matched to the lock revision `fe20b5cb`. Used only to read option types. |

Commands (run from `evidence/fixtures/s1-yaml/`, with `PY` the env python and `YAMLSUBSET_DIR` set to `src/vendomat`):

```text
$PY -I run_s1.py LOG/run1            # corpus tables, diagnostics, canonical JSON
$PY -I fuzz.py LOG/fuzz-seedN 3000 200000 N     # N = 1..4
$PY -I timing.py $PWD LOG/timing-input/a29.yaml 100 <vendomat venv python>
$PY -I secrets_check.py LOG/devenv-option-leaf-names.txt
$PY -I determinism.py LOG/det
$PY -I baseline_probe.py
$PY -I bigfile.py 3000
./nix_checks.sh LOG/run1/canon
```

Files: `hand.py` (candidate d, stdlib only, also the secret recognizer), `evlint.py` (candidates b1 and b2 over one walk), `corpus.py` (53 accepted and 115 rejected cases), the runner and probe scripts above.

## 3. Decisions with evidence

### 3.1 Candidates

| | Candidate | Dependency | Source of locations | Duplicate keys |
| --- | --- | --- | --- | --- |
| a | `yamlsubset.py` as is | none | line only, from its own lines | second key only, one line number |
| b1 | event walk over PyYAML | `pyyaml` (YAML 1.1) | event marks | own check |
| b2 | event walk over ruamel.yaml | `ruamel.yaml` (YAML 1.2) | event marks | own check |
| c | StrictYAML | `strictyaml` plus `ruamel.yaml` and `python-dateutil` | exception marks | built in |
| d | hand parser, `hand.py` | none | own, exact | own check, names both lines |

Why (a) exists: Vendomat depends on Typer only, and the file reads `devenv.yaml` fragments, which hold flow collections and plain strings. It is a different grammar by design.

### 3.2 Keys and implicit scalars (question 2)

Decision: keys may be plain if they match `[A-Za-z_][A-Za-z0-9_-]*` and are not `true false null yes no on off` in any letter case. Any other key is quoted. A dot in a key is never a path separator. A key is never read as a boolean, number, or null. Plain values are only `true`, `false`, `null`, and decimal integers. Everything else is quoted.

Evidence from `baseline_probe.py` (`k: <value>`; the rows that differ between loaders are the hazard):

| Plain value | PyYAML (1.1) | ruamel (1.2) | Subset |
| --- | --- | --- | --- |
| `no`, `No`, `NO`, `off` | `False` | string | reject |
| `yes`, `on` | `True` | string | reject |
| `3.10` | `3.1` | `3.1` | reject (`float`) |
| `1e3` | string | `1000.0` | reject |
| `0o12` | string | `10` | reject |
| `012` | `10` | `12` | reject |
| `1:30` | `90` | string | reject |
| `2024-01-01` | `date` | `date` | reject |
| `~`, empty | `None` | `None` | reject (`null-form`, `empty-value`) |

Two loaders read `012` as two different integers. This is the evidence for "reject, do not guess". No devenv module declares a float option (`grep types.float\|types.number` over the devenv modules: 0), so the subset has no floats. A version such as `3.10` must be quoted.

Empty value: a bare `key:` is rejected. YAML reads it as null, so a missing value would silently become null. Write `null`.

Empty collections: exactly `[]` and `{}` (no inner space) are accepted. A user needs them to override a module default list with an empty list; omission would mean "not defined". All other flow collections are rejected.

### 3.3 Multi-line strings (question 3)

Decision: accept `|` (clip) and `|-` (strip). Reject `>`, `|+`, and indentation digits. A quoted string must end on its line.

Evidence: in the devenv modules, `types.lines` appears 43 times (26 in `services/`). `enterShell` is `lines`, `scripts.<n>.exec` is `oneOf [str path]`, `processes.<n>.exec` is `str` ("Bash code to run"), `files.<n>.text` is `str`, and `services.postgres.initialScript` is `nullOr str` ("multiple SQL commands"). Without `|` a ten-line `enterShell` becomes one `"set -e\nfor f in *.txt; do\n  echo \"$f\"\ndone\n"` line. The block scalar costs about 50 lines in `hand.py`. The fuzz run (4.3) found three divergences from the oracles in that code; all are fixed.

Also needed: block lists of maps. `services.postgres.initialDatabases` is `listOf submodule` (6 such options in devenv). `yamlsubset.py` rejects them.

### 3.4 Error format (question 9)

`vendomat.yaml:LINE:COL: KEY.PATH: reason`. Line and column are 1-based; column counts characters (bytes for non-UTF-8 faults). The key path uses `.` for map keys, `[i]` for list items, `<root>` for the top, and quotes a key that is not an identifier. A duplicate-key message names both lines. The full gallery for all 115 rejected cases is `run1/diagnostics.txt`. Examples:

```text
vendomat.yaml:1:9: python: floats are not accepted (3.10); quote a version or text, or use native Nix for a float option
vendomat.yaml:1:10: country: the word 'No' reads as a boolean or null in some YAML versions; write true, false, or null, or quote it: "No"
vendomat.yaml:4:5: x.y.k: duplicate key "k"; first defined on line 3
vendomat.yaml:2:5: packages[0]: unquoted text 'ripgrep' is a string; quote it: "ripgrep"
vendomat.yaml:1:1: "services.postgres.enable": plain key 'services.postgres.enable' must match [A-Za-z_][A-Za-z0-9_-]*; quote it
vendomat.yaml:4:3: d: merge keys (<<) are not accepted
vendomat.yaml:1:4: a: anchors (&) are not accepted
vendomat.yaml:1:4: a: flow collections are not accepted; only exactly [] and {} (no inner space)
vendomat.yaml:1:3: a: the key has no value; write null, "", [], {}, or a nested block
vendomat.yaml:3:15: services.app.password: recognized secret field with a literal value; keep private values out of vendomat.yaml (use SecretSpec and a *File option)
```

Known weak message: a file whose first line is a bare quoted string reports "expected ':'" instead of "root is not a map" (R80).

### 3.5 Package references and paths (questions 6 and 7)

Syntax layer: every package reference and every path is a quoted string. Nothing in the file marks its type. The linter cannot check them before the schema exists.

| Check | Layer | Evidence |
| --- | --- | --- |
| String is quoted; no `pkgs` marker | syntax | corpus A32 |
| Attribute path matches `[A-Za-z_][A-Za-z0-9_'-]*(\.[A-Za-z_][A-Za-z0-9_'-]*)*` | schema (needs the option type) | proposal; empty and trailing-dot forms resolve to nothing (`nix_checks.sh` 5) |
| Attribute exists in the pinned nixpkgs | evaluation, with `tryEval` | `python313Packages.requests` resolves; `no-such-package` is missing; `nodePackages.typescript-language-server` THROWS (removed alias) |
| `pkgs.ripgrep` is also accepted by a path walk | inference for the schema spike | `pkgs.pkgs` exists; decide whether to forbid a `pkgs.` prefix |
| Relative string `./scripts/x.sh` becomes a Nix path | type layer, only for options of type `path` | `lib.types.path.check "./scripts/x.sh"` is false; `check "/abs"` is true; an `evalModules` option `oneOf [str path]` keeps the string `./scripts/x.sh` |

The last row matters: `scripts.<n>.exec` is `oneOf [str path]`. A string always wins as `str`. A user cannot name a file there from YAML. Use native Nix for it, or let the schema spike decide a rule.

### 3.6 Secret recognizer (question 8, DOOR-014)

Rule, as implemented in `hand.is_secret_key` and `hand.find_secrets`:

1. Split the key into lower-case words (camelCase, snake_case, kebab-case, UPPER_SNAKE).
2. If the last word is `file path dir env name helper command cmd authentication policy length url`, the key is not a secret field.
3. Otherwise the key is a secret field if any word is `password passwd passphrase secret token credential credentials`, or two adjacent words are `api key`, `private key`, `secret key`, `auth key`, or `signing key`.
4. The linter rejects a value only when it is a non-empty string. Booleans, numbers, `null`, `""`, maps, and lists pass. The rule applies to a map entry at any depth.

A `*File` option is a path, not a secret value, so it passes. `hashedPassword` is rejected: the hash lands in the store and in `/nix/store` is world readable, so `hashedPasswordFile` is the safe form.

Results (`secrets_check.py`): 27 names that must be flagged and 53 names that must pass, 0 mismatches (these lists were written by the spike author and tuned on the same session, so they show the rule works, not that it generalizes). Independent scan of 547 option leaf names in the devenv modules: the word rule flags 11, and all 11 are real secret options (`adminToken apiKey client-token initDatabasePassword initialAdminPassword password rpcSecret secret secretKey server-token token`). A naive substring rule (`pass|secret|token|key|cred|auth|priv`) flags 25 and wrongly includes `apiKeyHelper`, `keyFile`, `hasRootAuth`, `disableBypassPermissionsMode`, `secrets`, `secretspec`, `sslCertificateKey`, `copyHostKeys`, `key.converter`. `PasswordAuthentication: false` and `passwordFile: "…"` pass.

Not found by design: `searchOnlyKey`, `accessKey`, `encryptionKeys`, a password inside a URL (`postgres://u:pw@h/db`), a password inside an SQL string (`initialScript`), and any custom key name. Section 2 of the concept already says this.

## 4. Results

### 4.1 Corpus (question 1; at least 40 accepted and 40 rejected)

53 accepted cases (CONCEPT example, realistic devenv and Basix files, block scalars, edge cases, a 5,000-character string, a 1,000-item list, 60 levels) and 115 rejected cases (every case in questions 4, 5, 2, and 8, plus syntax faults). "Correct" for an accepted case means the parsed tree equals the expected tree in type and value. For a rejected case it means the reject code, line, and column all equal the expected values, which the author wrote before the run (a few were corrected by reasoning before the first run; cases R111 to R115 and A53 and A54 were added after the fuzz run found the faults they cover).

| Implementation | Accepted: correct | Accepted: wrong value | Accepted: wrongly rejected | Rejected: rejected | code ok | code+line ok | code+line+col ok | Rejected: wrongly accepted | Crashes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| d: hand parser | 53 | 0 | 0 | 115 | 115 | 115 | 115 | 0 | 0 |
| b1: PyYAML events | 53 | 0 | 0 | 111 | 98 | 89 | 89 | 4 | 0 |
| b2: ruamel events | 53 | 0 | 0 | 111 | 98 | 86 | 86 | 4 | 0 |
| c: StrictYAML | 21 | 29 | 3 | 47 | 2 | 0 | 0 | 68 | 0 |
| a: `yamlsubset.py` today | 17 | 20 | 16 | 46 | 2 | 0 | 0 | 69 | 0 |
| PyYAML `safe_load`, no lint | 51 | 2 | 0 | 28 | n/a | n/a | n/a | 87 | 0 |
| ruamel safe load, no lint | 53 | 0 | 0 | 33 | n/a | n/a | n/a | 82 | 0 |

Notes on the rows:

- b1 and b2 wrongly accept R86 (`a : 1`, valid YAML that the subset rejects as layout), R113 (tab after block indent), and R114 and R115 (depth limit). The libraries cannot raise the exact code for syntax faults, so their code match drops to 98 of 115. Their "wrong value" count is 0 because they share the plain-scalar classifier of `hand.py` (a shared part, so this row does not test that classifier).
- c returns every scalar as a string, so `3` and `"3"` and `true` and `"true"` are the same value. It cannot tell a quoted string from an implicit one. It also rejects `[]` and mixed indent widths. It does not meet DOOR-012.
- a returns `"3"` for an integer, keeps `''` and `\n` unprocessed in quoted strings, rejects block scalars, lists of maps, tabs, and several documents. It accepts what the subset must reject (69 of 115) because it was built to read a trusted `devenv.yaml`.
- The no-lint loaders show why a lint is needed: 87 and 82 of 115 rejected cases pass silently.

### 4.2 Duplicate keys, anchors, and the rest (questions 4 and 5)

Every item below is a rejected corpus case with an exact code, line, and column in `diagnostics.txt`.

| Item | Cases | Result |
| --- | --- | --- |
| Duplicate key at top, nested, in a list item, plain versus quoted | R29 to R32 | `duplicate-key`, names both lines |
| Anchor (scalar, map, list item, key), alias, tag (`!!str`, custom), merge key | R01 to R06, R12, R93 to R95 | one code each |
| Flow collections (plain, quoted, nested, `[ ]`, `{ }`, `[]x`) | R07 to R11, R88, R89, R108 | `flow-collection` or `trailing-text` |
| `---`, second document, `...`, `%YAML` | R13 to R16, R105 | `document-marker`, `directive` |
| Tabs (indent, after colon, in string, first block line) | R17, R18, R76, R113 | `tab` |
| BOM, latin-1, UTF-16, CR or CRLF, NUL, ESC, DEL, U+0085, U+2028, U+FEFF | R19 to R28, R110 | `bom`, `not-utf8`, `cr`, `control-char` |
| Large ints, floats, odd int forms, negative zero | R33 to R45 | `int-range`, `float`, `int-form` |
| Comments | A22, A23, A41, A51, R90 | allowed after whitespace; `1#c` is text and rejected |
| Missing final LF, nesting over 64 levels | R111, R112, R114, R115 | `no-final-newline`, `too-deep` |

### 4.3 Differential fuzz (support for H4)

Oracle: PyYAML `safe_load` and ruamel `safe` load. Part 1 renders random trees as subset YAML with random layout (compact lists, comments, block and quoted styles) and demands that `hand.py` and both oracles return the source tree. Part 2 mutates corpus files (delete, insert, replace, duplicate line, reindent, truncate, swap) and demands that every mutant that `hand.py` accepts is accepted by both oracles with the same tree, and that `hand.py` never raises anything but a lint error.

| Seed | Trees agreeing | Mutants | Accepted | Rejected | Crashes | Divergences |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 3,000 of 3,000 | 200,000 | 17,102 | 182,898 | 0 | 0 |
| 2 | 3,000 of 3,000 | 200,000 | 17,093 | 182,907 | 0 | 0 |
| 3 | 3,000 of 3,000 | 200,000 | 16,989 | 183,011 | 0 | 0 |
| 4 | 3,000 of 3,000 | 200,000 | 17,239 | 182,761 | 0 | 0 |

The first, shorter runs found three divergences in `hand.py`, fixed before the final runs: a file with no final LF changes a block scalar's last newline; a block of blank lines only returned spaces; the libyaml scanner rejects a tab right after the first text line's indent. A review (not the fuzz) found a fourth fault: a 100-level file raised a Python recursion error. Each fix has a corpus case now. The final four seeds ran on the fixed code.

### 4.4 Canonical JSON (question 10)

Output: `json.dumps(tree, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` plus one LF, UTF-8.

| Check | Result |
| --- | --- |
| 53 accepted cases, fresh process, `PYTHONHASHSEED` 0, 12345, random | one sha256 per case: 53 of 53 |
| Same bytes from `hand.py`, PyYAML walk, ruamel walk | 53 of 53 |
| Same data, keys reordered, indent changed, comments added, quote style changed | same sha256 (`c351976e…93d0`) |
| One value changed | different sha256 |
| List order changed | different sha256 (list order is data) |
| `builtins.fromJSON` then `builtins.toJSON` in Nix 2.34.7 over all 53 files | bytes equal to the file minus the final LF: 53 of 53 |
| `${HOME}/x` and `é 😀` through `fromJSON` | literal text, no interpolation |
| `9223372036854775807`, `-9223372036854775808` | Nix `int` |
| `9223372036854775808` | Nix error "outside of Nix integer range" |
| `-9223372036854775809` | Nix silently makes a float | 

The last row is why the linter checks the int64 range: Nix would turn a too-small integer into a float without a message.

### 4.5 Startup and size (question 1)

`timing.py`, 100 fresh processes each, `python -I -c <snippet>`. CPU time is the reliable column; wall time was noisy.

| Case | Median CPU ms | Median wall ms |
| --- | --- | --- |
| bare interpreter | 26 | 27 |
| d: import, parse a 29-line file, canonical JSON | 37 | 38 |
| b1: `import yaml` only | 68 | 117 |
| b1: import, lint, canonical | 80 | 135 |
| b2: `import ruamel.yaml` only | 82 | 93 |
| b2: import, lint, canonical | 100 | 173 |
| c: `import strictyaml` only | 173 | 192 |
| reference: `import typer` (current CLI dependency) | 154 | 249 |

Parse time for a 282 KB, 21,000-line file (`bigfile.py`): d 235 ms, b1 1,554 ms, b2 3,214 ms. Dependency weight: d adds none. b1 adds one package (pure Python with optional libyaml). b2 adds `ruamel.yaml`. c adds `strictyaml`, `ruamel.yaml`, and `python-dateutil`.

## 5. Proved, inferred, unproved

**Proved on the pinned tools (fixtures and logs):**

- `hand.py` gives the expected code, line, and column for 115 of 115 rejected cases and the expected tree for 53 of 53 accepted cases.
- Every input that `hand.py` accepted in 800,000 mutants (about 68,000 accepted) and 12,000 random trees reads as the same tree in PyYAML and ruamel. No crash.
- The canonical bytes are stable across processes and hash seeds, ignore key order, comments, indent, and quote style, and survive a Nix `fromJSON` and `toJSON` round trip.
- Today's `yamlsubset.py` and StrictYAML cannot enforce DOOR-012.
- A key-name word rule flags 11 of 547 devenv option names, all real secrets, where a substring rule flags 25.

**Inference:**

- A hand parser is the better choice for Vendomat: exact locations, no new runtime dependency, 11 ms CPU over the bare interpreter, 6 times faster than the PyYAML walk on a large file. The cost is code to maintain; the fuzz harness is the guard and should run as a test with PyYAML in the `dev` group only.
- The subset is a strict subset of YAML 1.1 and 1.2 in value: any accepted file means the same in editors and in `yq`. This follows from the zero divergences but is not a proof for all inputs. The mutation fuzz only explores near the corpus.
- The recognizer false-positive rate on NixOS module option names is likely low. It was measured on devenv names only.

**Unproved:**

- Behavior on Python 3.13 (the spike ran 3.14.7).
- A real consumer's `vendomat.yaml`. No such file exists yet.
- The secret recognizer's recall. It cannot see a password in a URL, an SQL string, an `env` value with an unusual name, or a custom option.
- Reporting several errors in one run. The parser stops at the first syntax fault. Only the secret check returns all hits.
- The type layer: path conversion, package attribute resolution inside a module, and `oneOf [str path]` handling are checked at the `lib.types` level only, not in a generated module.
- The devenv module source used for option counts may not equal the revision in the lock.
- Timing was taken under load average 16.

## 6. Proposed grammar, to replace DOOR-012

`NEW:` The linter MUST read `vendomat.yaml` with this grammar and MUST reject everything else. Each rejection MUST report `file:line:column: key path: reason`.

1. **File.** The file is UTF-8 without a byte order mark. Lines end with LF. A non-empty file ends with LF. The file has no control character, no DEL, no U+0080 to U+009F, no U+2028, U+2029, U+FEFF, U+FFFE, or U+FFFF. The one exception: a tab may appear inside a comment or a block scalar's text, but not in indentation, not as the first character of a block scalar's first text line, and not inside a quoted string.
2. **Document.** The file holds one block map. An empty file or a file of comments is an empty map. `---`, `...`, and directives are rejected. Maps and lists nest to at most 64 levels, counting the root as 1.
3. **Indentation.** Indentation uses spaces. A list under a key may start at the key's column or deeper.
4. **Keys.** A key is a plain key or a quoted key. A plain key matches `[A-Za-z_][A-Za-z0-9_-]*` and is not `true`, `false`, `null`, `yes`, `no`, `on`, or `off` in any letter case. A quoted key is a non-empty single-line double-quoted or single-quoted string. A dot in a key is part of the name; nesting expresses an option path. Keys in one map are unique after unquoting. `<<` and `?` keys are rejected.
5. **Values.** A value is one of:
   - a double-quoted or single-quoted string on one line. Double-quoted escapes are `\\ \" \/ \b \f \n \r \t \uXXXX`; a `\u` escape may not name a control character, a surrogate, U+007F to U+009F, U+2028, U+2029, U+FEFF, U+FFFE, or U+FFFF. A single-quoted string writes `'` as `''` and has no other escape;
   - `true`, `false`, or `null`, in lower case;
   - a decimal integer matching `-?(0|[1-9][0-9]*)`, not `-0`, within -2^63 to 2^63-1;
   - exactly `[]` or `{}`;
   - a block scalar with header `|` or `|-`, optionally followed by a comment;
   - a block map or a block list, including a list of maps and a list of lists.
6. **Rejected.** Unquoted text, including `~`, `True`, `yes`, dates, and times. Floats and every other integer form (`+1`, `012`, `0x1F`, `0o12`, `1_000`, `1e3`, `.inf`, `.nan`). A key with no value. Anchors, aliases, and tags. Folded `>`, `|+`, and indentation indicators. Every flow collection except exactly `[]` and `{}`. Multi-line quoted strings.
7. **Comments.** A `#` that starts a line or follows a space starts a comment.
8. **Secret fields.** The linter MUST reject a non-empty string value under a key whose name matches the recognizer of section 3.6. This is a key-name check; it does not detect a secret under another name.
9. **Output.** The linter MUST emit canonical JSON: object keys sorted by Unicode code point, no whitespace between tokens, literal UTF-8, list order kept, one final LF. Equal data MUST give equal bytes.
10. **Layers.** This grammar keeps every package reference and path as a string. Package syntax, path conversion, and type checks belong to the schema step.

## 7. Concept and requirement changes that follow

1. `CONCEPT.md` section 3, "The supported YAML form": replace "numbers" with "integers". Add block scalars `|` and `|-`, the exact `[]` and `{}`, and the plain-key rule. State that an option path is written by nesting, never by a dotted key.
2. `REQUIREMENTS.md` `DOOR-012`: wrong in four places. It omits block scalars, which devenv options need (`enterShell`, `exec`, `initialScript`). It says "numbers", but floats are rejected. It says it rejects "flow collections", but `[]` and `{}` are needed. It leaves "implicit strings" and the key rule undefined. Replace it with the text in section 6.
3. `CONCEPT.md` section 3 and `DOOR-002` successor text: the error names "the file, line, key, and reason". Add the column and the key path.
4. `DOOR-014`: "recognized secret fields" needs a definition. Use section 3.6. State that the linter checks key names and non-empty string values only. State that a `*File` option is a path and passes.
5. `DOOR-004`: keep. Add that the syntax step cannot check a package string, that the schema step checks the attribute syntax, and that evaluation uses `tryEval` because a removed nixpkgs alias throws.
6. `DOOR-003`: add that a top-level key such as `services.postgres.enable` is rejected; the example in section 3 of the concept already nests.
7. `PLAN.md` stage 1: build the parser as a stdlib module with this corpus as the gate. Keep the fuzz harness as a test, with PyYAML as a `dev` dependency only. Do not extend `yamlsubset.py`; it reads `devenv.yaml` and should leave when the generator stops reading it.
8. Schema and merge spikes: decide whether `oneOf [str path]` options (for example `scripts.<n>.exec`) need a path marker, and whether a `pkgs.` prefix is rejected.
