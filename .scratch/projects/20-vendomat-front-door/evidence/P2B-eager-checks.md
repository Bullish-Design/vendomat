# B: eager checks for a Nix-typed catalog module

Date: 2026-10-12. Nothing inside the Vendomat repository changed.
All files are under `~/.local/state/vendomat/p20/2026-10-12/B-eager-checks/`.

## Common inputs

- Fork: `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv`.
  `devenv version` prints `devenv 2.4.0+fb5d382 (x86_64-linux)`. Every `ws/` log starts with it.
- Nix 2.34.7. nixpkgs lib: `/nix/store/n9vyi4yygxdfdmjimmfzqsg802m16s0a-source/lib`.
- Lock: copy of the S2 `ws5/devenv.lock` (devenv-nixpkgs rev 256551e4).
- Fast harness: `fast/` (`catalog.nix`, `h.nix`, `run.sh`, cases in `fast/t/`).
- Real workspace: `ws/`. `devenv.yaml` imports `./catalog.nix`. The catalog reads
  `config.devenv.root + "/vendomat.toml"` with `builtins.fromTOML`.
  The read sits in an inner module with `_file = "vendomat.toml"`.
- Catalog options: `programs` (listOf str), `languages.python.enable` (bool),
  `languages.python.version` (nullOr str), `services.postgres.enable` (bool), `env` (attrsOf str).
- Mapping: `packages`, `env`, `languages.python.enable`, `services.postgres.enable`.
  `languages.python.version` is NOT mapped. It is the "unused field" in the tests.
- User `devenv.nix` has task `demo:mark` and an `enterTest` hook. Both write a marker file.
  A marker proves the work ran.
- Variants: `ws/variants/catalog-*.nix`. Runners: `ws/run-matrix.sh`, `ws/q3.sh`.
- Logs: `logs/`. Files named `*-raw.log` keep ANSI colors. The others are stripped.
- The fork has no `--show-trace` flag. It prints the full Nix trace by default.

## Q1. Unknown key

- Hypotheses: H1 the module system rejects an undeclared key with no extra code.
  H2 it is lazy and accepts it.
- Inputs: `ws/cases/unknown-table.toml` (`[languages.rust] enable = true`),
  `unknown-top.toml` (`bogus = 1`), `typo.toml` (`enabled = true` under python).
  Variant `catalog-noguard` (no forcing at all) and `catalog-simple`.
- Command: `ws/run-matrix.sh none unknown-top` and `ws/q3.sh catalog-simple unknown-table unknown-top typo`.
- Expected: H1 gives an error before work. Actual: H1. rc=1 on `shell`, `test`, `build shell`,
  `build languages.python.package`, `tasks run`. No marker file appeared. Log
  `logs/matrix-noguard-unknown-top.log`, `logs/q3-simple.log`.
- Quoted:
  - `error: The option `vendomat.bogus' does not exist. Definition values:`
  - `- In `vendomat.toml': 1`
  - `Did you mean `vendomat.env', `vendomat.programs' or `vendomat.languages'?`
  - typo: `The option `vendomat.languages.python.enabled' does not exist` ... `Did you mean `vendomat.languages.python.enable' or ...version'?`
- Proves: an unknown key stops every tested command, with no forcing code. The message
  names the option path, the file, and gives a spelling hint. Noise: about 121 lines.
  The error is the last 3 to 6 lines.
- Why: the module system checks the whole `config` for undeclared options when anything reads it.
- Inference: the same holds for any command that reads one `config` attribute.
- Unproved: unknown key inside `attrsOf` or a free-form option (not declared in this fixture).

## Q2. Eager forcing

- Hypotheses: H1 `builtins.toJSON` or `deepSeq` in an always-read value forces all fields.
  H2 an `assertions` entry is enough. H3 a throw at module `config` level is enough.
- Baseline (laziness, L1 in the fork): variant `catalog-noguard`, case `unused-badtype`
  (`languages.python.version = 3.13`). Actual: rc=0 on all five commands.
  A bad value in an unused field passes. Log `logs/matrix-noguard-unused-badtype.log`.
- Sink tests (first round, `ws/sinks/*.nix`, `logs/matrix-<sink>-unused-badtype.log`):
  a `builtins.seq (builtins.toJSON config.vendomat)` placed in `env`, `enterShell`,
  `assertions`, or `name`. Result for every sink: `shell`, `test`, `build shell`,
  `tasks run` fail (rc=1, no marker). `build languages.python.package` passes (rc=0).
  That output does not read the sink value.
- Wrapper construct (works on all five). Every mapped leaf passes through `guard`:
  `guard = v: builtins.deepSeq cfg v;` with `cfg = config.vendomat`, and
  `packages = guard (...)`, `env = guard cfg.env`, `languages.python.enable = guard ...`,
  `services.postgres.enable = guard ...`.
  Command: `ws/run-matrix.sh none unused-badtype` with `variants/catalog-simple.nix`.
  Actual: rc=1 on `shell -- touch`, `test`, `build shell`, `build languages.python.package`,
  `tasks run demo:mark`. No `ran-*.marker` file exists after any run. The good case
  (`vendomat.toml` from `cases/good.toml`) gives rc=0 and the markers appear.
  Logs: `logs/matrix-deepseq-unused-badtype.log`, `logs/matrix-deepseq-good.log`.
  Quoted: `error: A definition for option `vendomat.languages.python.version' is not of type `null or string'. Definition values:` / `- In `vendomat.toml': 3.13`.
- `builtins.seq (builtins.toJSON cfg) v` works the same (also with package-valued options; see Q4 d).
- Cycles: H3 FAILED. `config = if bad != [] then throw ... else {...}` gives
  `error: infinite recursion encountered` (the option set needs this module's config keys).
  Log `logs/q5-throwcfg-two-errors.log`. The leaf wrapper has no cycle.
  The check must sit in leaf values, not at module `config` level.
- Edits to `vendomat.toml` took effect on every run, so the eval cache sees the TOML read.
- Proves: `deepSeq cfg` inside each mapped leaf stops all five commands before any work.
- Inference: a catalog that maps every option to a native option needs the wrapper on
  one always-read leaf only. The fixture wraps all leaves to win the race against a native
  option error (see Q3).
- Unproved: outputs that read no mapped leaf (e.g. an unrelated `build <attr>`).
  Also `devenv up`, `devenv shell` with `--profile`, and the eval cache across a bad then good edit.

## Q3. Error quality

- Hypotheses: H1 the error names the file and field. H2 a TOML line number appears.
  H3 one cheap step improves it.
- Command: `ws/q3.sh catalog-simple CASE...` (`-q --no-tui` flags). Log `logs/q3-simple.log`.
- Actual last lines (native message, variant `catalog-simple`):
  - number for string: `error: A definition for option `vendomat.env.PORT' is not of type `string'. Definition values:` / `- In `vendomat.toml': 5432`
  - string for bool: `... `vendomat.services.postgres.enable' is not of type `boolean'` / `- In `vendomat.toml': "yes"`
  - bad list element: `... option `vendomat.programs."[definition 1-entry 2]"' is not of type `string'` / `- In `vendomat.toml': 7`
  - invalid TOML: `error: while parsing TOML: [error] toml::parse_array: expected value-separator `,` or closing `]`` / ` --> fromTOML` / ` 2 | [env]` / `^-- here`
  - unknown package, `lookup` returns null: `A definition for option `packages."[definition 3-entry 2]"' is not of type `package'` / `- In `.../ws/catalog.nix': null` (bad: names catalog.nix, not the program).
- Findings:
  - H1 yes for type errors: file name `vendomat.toml` (from `_file`), full option path, and the value.
  - H2 no for type errors. `fromTOML` drops positions. The string `vendomat.toml:<line>` never appears.
    A TOML syntax error shows the TOML source line but names `fromTOML`, not the file.
  - `--show-trace` is not needed and does not exist in the fork. The trace is always printed.
  - Noise: 331 to 359 lines per type error, 121 for unknown key, 243 for invalid TOML,
    about 1150 for the unknown-package case. Useful lines: 2 (type), 3 to 6 (unknown key).
    Colors add escape codes. `-q` and `--no-tui` did not shorten it (one run printed 5 lines once; not reproducible).
- Cheap steps tested:
  1. `_file = "vendomat.toml"` on the inner module: works (above).
  2. Own message (variant `catalog-all`): `tryEval (deepSeq o.value true)` per option over
     `lib.collect lib.isOption options.vendomat`, then `throw` from `guard`. Uses
     `o.definitionsWithLocations`, `o.type.description`. About 8 lines of Nix.
     Output: `vendomat.toml: `services.postgres.enable' must be boolean, found string "yes"`
     (logs `logs/q3-all.log`). Better wording, same trace noise (303 lines).
  3. Print only from the last `error:` line: `... | awk '/^ *error:/{f=1} f'` leaves 1 to 5 lines.
     Log `logs/q3-awk-filter.log`. This needs a wrapper; I tested it in the shell only.
- Not tested: per-table `_file` (e.g. `vendomat.toml [languages]`). Imports cannot depend on
  `config.devenv.root`, so a per-table split needs a path known without config.
  `mkDefinition` does not push into nested option sets. Inference only.
- Unproved: a TOML line number for a type error. No source gives it.

## Q4. Program names

- Hypotheses: H1 raw `pkgs.${name}` gives a clear error. H2 `or throw` gives a one-line
  message. H3 a `coercedTo` type works with the eager check. H4 a pre-check can list all unknown names.
- Command: `ws/q3.sh catalog-pkg-{a-raw,b-throw,c-list,d-coerce} good unknown-pkg unknown-pkg-multi`.
  Logs `logs/q4-a-raw.log`, `q4-b-throw.log`, `q4-c-list.log`, `q4-d-coerce.log`.
- Actual:
  - a, `pkgs.${name}`: `error: attribute 'nosuchpkg' missing`. No file, no field. About 1280 lines. Dotted names would fail (inference, not run).
  - b, `attrByPath (splitString "." n) (throw "...") pkgs`: `error: vendomat.toml: programs: nixpkgs has no package `nosuchpkg'`. One line. First unknown only. About 1310 lines.
  - c, a list check before `guard` (`filter (n: attrByPath ... == null) cfg.programs`):
    `error: vendomat.toml: programs: nixpkgs has no package named `nosuchpkg', `alsomissing'`. All names, one line, 318 lines. Good case rc=0.
  - d, `listOf (coercedTo str (n: attrByPath ... (throw ...) pkgs) package)` with
    `builtins.seq (builtins.toJSON cfg)` as the guard: good case rc=0, and the bad case gives the b message.
    `deepSeq` on package values was not tried (inference: it would walk derivation attributes).
- Proves: variants b, c, d give one clear line. c names every bad program. d keeps one
  typed option, so "unknown name" is a type error, but `toJSON` must replace `deepSeq`.
- Inference: `pkgs ? name` is true for removed aliases that throw on use; c does not catch these.
- Unproved: cost of `toJSON` on many packages. Alias handling. Nested names such as `python3Packages.requests` through c (code supports them; not run).

## Q5. Multiple errors

- Hypotheses: H1 Nix reports only the first error. H2 it reports all.
- Inputs: `ws/cases/two-errors.toml` (four bad fields). Variants `catalog-simple`, `catalog-all`.
  Fast harness: `fast/t/two-errors.toml` (`logs/fast-types.log`).
- Actual: native messages report only one: `vendomat.env.GREETING ... 5` (`logs/q5-simple-two-errors.log`).
  The fast harness also reports only `vendomat.env.PORT`. Unknown key plus type error:
  the unknown key wins (checked first). With `catalog-all` the single `throw` lists all four fields
  (`logs/q5-guard-two-errors.log`, `logs/q3-awk-filter.log`).
  Unknown package versus type error: the first guard in the chain wins (c: unknown package first).
- User cost: with native messages, a learner with N bad fields needs N edit-and-run cycles
  (about 6 to 9 s each here), and unknown keys need a separate cycle before type errors.
  With the 8-line `tryEval` check, all type errors appear in one run. Unknown keys and unknown
  programs still need their own run unless the check is extended.
- Unproved: whether a learner reads a 300-line trace without the awk filter.

## Verdict inputs

Native types alone give a correct file, a field, and a value, but with 120 to 360 lines
of trace and one error per run, and no line number. They need the guard to be eager.
