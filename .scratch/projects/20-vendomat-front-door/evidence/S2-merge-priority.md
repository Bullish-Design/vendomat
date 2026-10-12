# S2: native merge and priority for YAML-generated option data

**Date:** 2026-10-11. **Status:** observation record. Nothing here is a passed project 20 gate.

## 1. Question and hypotheses

Question: when a generated module reads `.vendomat/config.json` with `builtins.fromJSON` and sets
options, which value wins against an imported library module and against `devenv.nix`? Which errors
appear, and what do they cite?

Hypotheses before the run:

- H1. `DOOR-006` (YAML beats a plain library definition and loses to `devenv.nix`) is not reachable
  with Nix priorities, because a library plain definition and a `devenv.nix` plain definition have the
  same priority (100).
- H2. A plain YAML definition gives native behavior: equal priority and different scalar values stop
  with both locations.
- H3. The generated module can set `_file`, so errors cite `vendomat.yaml` and not a store path.
- H4. A package string becomes a derivation by walking `options`, with no infinite recursion.
- H5. An untracked or ignored `config.json` is read and invalidates the eval cache.

## 2. Exact inputs

| Item | Value |
| --- | --- |
| devenv CLI (all real runs) | `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv`, `devenv 2.4.0+fb5d382 (x86_64-linux)` (fork, v2.4.0-vendomat.3). Every run in `logs/real/` and `logs/real-matrix.txt` prints this version. The host PATH devenv (`2.4.0+b904dcb`) was not used. |
| Nix | 2.34.7 |
| nixpkgs input | `github:cachix/devenv-nixpkgs/rolling`, locked by copying the pruned `devenv.lock` of the vendomat repo: rev `256551e45f6303e142ab4a98be1bf243feb77dc0` (nixpkgs-src `c8f90650c15282fa8656a041bfbbd2403997a9a7`) |
| devenv module source in the lock | `cachix/devenv` rev `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4` |
| Fast harness lib and pkgs | store path of nixpkgs-src `c8f9065...` (`/nix/store/n9vyi4yygxdfdmjimmfzqsg802m16s0a-source`), `lib.evalModules`, fetched offline by narHash |
| Disk check | `btrfs filesystem usage /` before heavy runs: metadata 84.5% used, unallocated 6.09 GiB (inside the limits) |
| Work area | `~/.local/state/vendomat/p20/2026-10-11/S2/` (`fast/`, `ws1`-`ws6`, `ws3-lib`, `ws4-lib`, `tools/`, `logs/`) |
| Fixtures | `.scratch/projects/20-vendomat-front-door/evidence/fixtures/s2-merge/` (copy of harness, tools, and the generated-module prototype `ws5/.vendomat/generated-module.nix`) |

Commands (all from a disposable workspace; `DV` is the fork path above):

```bash
# fast matrix (plain lib.evalModules)
nix-instantiate --eval --strict --json fast/h.nix --argstr mode matrix --argstr type <T> [--argstr genMode leaf]
nix-instantiate --eval --strict --json fast/h.nix --argstr mode one --argstr type <T> --argstr L p --argstr G p --argstr U 0
nix-instantiate --eval --strict --json fast/misc.nix --argstr case <name>     # packages, paths, null, unknown, freeform, function
nix-instantiate --eval --strict --json fast/loc.nix  --argstr case <name>     # _file variants
# real devenv matrix (tools/case.py writes lib/module.nix, .vendomat/devenv.nix, .vendomat/config.json, devenv.nix)
tools/batch-real.sh          # runs "$DV eval vtest.probe.<key>" per option and case
tools/batch5.sh              # prototype generated module (ws5): errors, packages, paths
$DV eval <attr> ; $DV shell -- printenv FOO ; $DV build shell ; $DV info
```

Workspace layout for the real runs: `devenv.yaml` imports `./lib/module.nix` (library: declares
`vtest.*` options and sets definitions) and `./.vendomat` (generated module, reads `./config.json`).
`devenv.nix` holds the user definitions. Test options: real `env.FOO`, `packages`,
`languages.python.enable`, `enterShell`; custom `vtest.str`, `vtest.int`, `vtest.lstr`.

## 3. Expected

Native module semantics: the lowest priority number wins (`mkForce`=50, plain=100, `mkDefault`=1000,
option default=1500). Equal priority merges when the type can merge (lists, lines, attribute sets,
submodules) and conflicts when it cannot (scalars with different values).

## 4. Actual results

### 4.1 Fast matrix, scalar types (str, int, enum, nullOr str, package; bool the same when values differ)

Result of the option value. L = library definition, G = generated (YAML) definition, U = `devenv.nix`.
`yaml`/`lib`/`user` name the winner. `ERR` = conflicting definitions. Rows are L. Columns are G.
G priorities: `p`=plain, `o100`=`mkOverride 100` (identical to plain), `o90/o75/o60`, `d`=`mkDefault`,
`f`=`mkForce`. U=0 means no `devenv.nix` definition.

| L \ G | 0 | p | o100 | o90 | o75 | o60 | d | f |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | - | yaml | yaml | yaml | yaml | yaml | yaml | yaml |
| p | lib | ERR | ERR | yaml | yaml | yaml | lib | yaml |
| d | lib | yaml | yaml | yaml | yaml | yaml | ERR | yaml |
| f | lib | lib | lib | lib | lib | lib | lib | ERR |

With `devenv.nix` (U) added, for G=p: U=plain with L=0 gives ERR (yaml vs user); U=plain with L=d gives
ERR; U=`mkForce` gives user for every L except L=f (ERR). For G=o90/o75/o60 and U=plain, yaml wins
silently over `devenv.nix`. For G=d and U=plain, user wins. Equal values from two sources never
conflict (bool rows with L=U=true). Full tables for all 12 types: `logs/matrix-<type>.json`, printed
by `tools/show.py`.

Result: this equals native Nix. `mkOverride 100` is plain. Any `mkOverride` below 100 beats a plain
definition in both the library and `devenv.nix`, so no priority puts YAML strictly between two plain
definitions (H1 confirmed).

### 4.2 Fast matrix, composite types

Same priority rules, but the merge unit differs.

| Type | Plain L, plain G, plain U | Notes |
| --- | --- | --- |
| `listOf str`, `listOf package` | Concatenation. Module order is not the list order (see 4.4). | `mkBefore` puts the library first, `mkAfter` last. `mkForce` list drops every plain list. `mkDefault` list is dropped by any plain list. Two `mkForce` lists concatenate (no ERR). |
| `lines` (`enterShell`-like), `separatedString ":"` | Concatenated with `\n` or `:`. | Same priority filter as lists. |
| `attrsOf str` | Merged per key. A different value on the same key is `ERR` on the key (`t.astr.k`). | Whole-value priority (below) is the trap. |
| `submodule` | Merged per field. A conflict names the field (`t.sub.a`). | Same trap. |
| `nullOr str` | `null` from YAML is a value. YAML `null` vs a library string: `ERR` "defined both null and not null". | |

**Granularity trap.** When the generated module wraps the whole option value, the wrapper acts at the
option level and drops lower-priority definitions of the whole option. Fast matrix, `attrsOf str`,
L plain `{k=lib,l=L}`, G `mkOverride 90 {k=yaml,y=Y}`: result `{k=yaml,y=Y}`, the library key `l` is
lost. With a per-key wrapper (`genMode leaf`) the result is `{k=yaml,l=L,y=Y}`. Logs:
`logs/matrix-astr.json`, `logs/matrix-leaf-astr.json`, `logs/matrix-leaf-sub.json`. A library that sets
`t.sub = mkDefault {...}` as a whole value still loses to a YAML per-field definition at plain priority
(different granularity). Plain YAML definitions without a wrapper avoid the trap.

### 4.3 Real devenv matrix (pinned fork), `logs/real-matrix.txt`, compact table `logs/real-matrix-compact.txt`

`yaml` here is the generated module with `_file = "vendomat.yaml"`. Each cell comes from `devenv eval
vtest.probe.<key>` with only that option defined in the three sources.

| L G U | env.FOO | packages | python.enable | enterShell | vtest.str | vtest.int | vtest.lstr |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 p 0 | yaml | jq | false | yaml | yaml | 2 | yaml |
| p p 0 | ERR | hello,jq | ERR | lib,yaml | ERR | ERR | lib,yaml |
| d p 0 | yaml | jq (lib list dropped) | false | yaml | yaml | 2 | yaml |
| p d 0 | lib | hello | true | lib | lib | 1 | lib |
| f p 0 | lib | hello | true | lib | lib | 1 | lib |
| p o90/o75/o60 0 | yaml | jq | false | yaml | yaml | 2 | yaml |
| p o100 0 | ERR | hello,jq | ERR | lib,yaml | ERR | ERR | lib,yaml |
| 0 p p | ERR | cowsay,jq | ERR | user,yaml | ERR | ERR | user,yaml |
| 0 p f | user | cowsay | true | user | user | 3 | user |
| 0 o90 p | yaml | jq | false | yaml | yaml | 2 | yaml |
| p o90 p | yaml | jq | false | yaml | yaml | 2 | yaml |
| d p f | user | cowsay | true | user | user | 3 | user |
| p p p | ERR | cowsay,hello,jq | ERR | user,lib,yaml | ERR | ERR | user,lib,yaml |
| d d 0 | lib | [] | ERR | [] | ERR | ERR | lib,yaml |
| f f 0 | yaml (see note) | hello,jq | ERR | lib,yaml | ERR | ERR | lib,yaml |
| 0 f f | yaml (see note) | cowsay,jq | ERR | user,yaml | ERR | ERR | user,yaml |
| b p 0 / a p 0 | | hello,jq / jq,hello | | lib,yaml / yaml,lib | | | lib,yaml / yaml,lib |
| b p p / a p p | | hello,cowsay,jq / cowsay,jq,hello | | lib,user,yaml / user,yaml,lib | | | lib,user,yaml / user,yaml,lib |

Notes on the real matrix:

- Every real option behaves as the fast matrix predicts. `env` (an attribute set) shows the
  granularity trap: `env.FOO = mkForce "lib"` is a per-key definition inside a plain `env`; the
  generated whole-value `mkForce {FOO=...}` on the option `env` wins at the option level, so cells
  `f f 0` and `0 f f` show `yaml` and no ERR.
- `d d 0`: `packages` and `enterShell` are `[]` because devenv core modules define both options at
  plain priority, and a plain definition drops every `mkDefault` list or text.
  A library `mkDefault` on a list option is silently dropped in real devenv.
- `mkOverride 90` on `packages` drops devenv core packages. Direct proof (`logs/packages-core-dropped.txt`):
  with G plain the evaluated list is `bash-interactive, jq, pkg-config-wrapper`; with G `mkOverride 90`
  it is `jq` only.
- Plain list order in real devenv is `devenv.nix` first, then the library, then the generated module
  (`p p p` row). In the fast harness the order was the reverse of the module list. Do not rely on order.
- `devenv shell -- printenv FOO`, `devenv build shell`, `devenv info`, and `devenv eval` all stop with
  the same conflict error. No build starts.
- `env.FOO` accepts an integer from YAML (`{"env":{"FOO":5}}` gave `5`): the `env` type is permissive.

### 4.4 Priority of a stronger library definition

A library `mkForce` (or any priority below 100) beats plain YAML silently. The fast matrix and the
real matrix (`f p 0`) give the library value with no error and no trace of the YAML value.
`options.<path>.definitionsWithLocations` lists only the winning definitions (fast test
`logs/ignored-detect.txt`: defs `[lib.nix]`, `highestPrio` 50). A generated module could test that no
definition carries a `vendomat.yaml` file and report the loss. This was shown for one scalar only. It is
not proved for composite types.

### 4.5 Error texts (verbatim) and locations

All real runs: `devenv 2.4.0+fb5d382`. The workspace root is `~/.local/state/vendomat/p20/2026-10-11/S2/wsN`.

Conflict, library (relative import) and YAML with `_file = "vendomat.yaml"` (`logs/real/`, ws2):

```
error: The option `env.FOO' has conflicting definition values:
- In `vendomat.yaml': "yaml"
- In `/home/andrew/.local/state/vendomat/p20/2026-10-11/S2/ws2/lib/module.nix': "lib"
Use `lib.mkForce value` or `lib.mkDefault value` to change the priority on any of these definitions.
```

Conflict, YAML vs `devenv.nix` (also the text of `devenv shell`, `build shell`, `info`):

```
error: The option `env.FOO' has conflicting definition values:
- In `vendomat.yaml': "yaml"
- In `/home/andrew/.local/state/vendomat/p20/2026-10-11/S2/ws2/devenv.nix': "user"
Use `lib.mkForce value` or `lib.mkDefault value` to change the priority on any of these definitions.
```

Library location by input kind (ws3 `path:`, ws4 `git+file:`):

- `path:` input: the live path, `/home/.../ws3-lib/module.nix`. devenv 2.4.0 locks it as `{"type":"path","path":...}` with no hash. An edit of the library file is read at once.
- `git+file:` input: a store path, `/nix/store/8myrqsqpaizr21a7bkjj25gcdhwk43g6-source/module.nix`. The lock has no `rev`, only `ref: refs/heads/master`.
- The error never names the input. A store path does not tell the user which input it came from.

Generated module location, real devenv (`logs/real-location-modes.txt`) and fast (`logs/location-fast.txt`):

| Generated module form | Location printed |
| --- | --- |
| No `_file` | the module file path, `.../ws2/.vendomat/devenv.nix` (in an inline module: `<unknown-file>`) |
| `_file = "vendomat.yaml"` | `vendomat.yaml` |
| `lib.setDefaultModuleLocation "vendomat.yaml" {...}` (attrs or function) | `vendomat.yaml` |
| `_file` on a parent with an inner `imports` module | `vendomat.yaml` |
| One module per top-level key, `_file = "vendomat.yaml#env"` | `vendomat.yaml#env` |
| Per-key `_file` with a line sidecar (`ws5`) | `vendomat.yaml:9 (key nope)` |

The location never shows the data file `config.json`. A path in `_file` is printed as written. A
relative path `./x` in `_file` is made absolute by Nix.
The module citation can reach a key and a line only if the generator writes a line map (sidecar
`lines.json`) next to `config.json`. The line map is a generator output, not a Nix feature. The
`_file` string is free text: no device was found in the module system to give the option path
of the YAML key beyond what the message already prints (the option path).

Unknown option (ws5, `logs/real5-matrix.txt`):

```
error: The option `vtest.nope' does not exist. Definition values:
- In `vendomat.yaml (key vtest)': 1

Did you mean `vtest.apps', `vtest.nul' or `vtest.probe'?
```

```
error: The option `languages.pythn' does not exist. Definition values:
- In `vendomat.yaml (key languages)':
    {
      enable = true;
    }

Did you mean `languages.python', `languages.php' or `languages.kotlin'?
```

```
error: The option `nope' does not exist. Definition values:
- In `vendomat.yaml:9 (key nope)':
    {
      x = 1;
    }

Did you mean `name', `apple' or `ci'?
```

Type errors (all name `vendomat.yaml`):

```
error: A definition for option `vtest.str' is not of type `string'. Definition values:
- In `vendomat.yaml:4 (key vtest)': null                    # null for a non-nullable option

error: A definition for option `languages.python.enable' is not of type `boolean'. Definition values:
- In `vendomat.yaml:8 (key languages)': "yes"

error: A definition for option `vtest.fn' is not of type `function that evaluates to a(n) string'. Definition values:
- In `vendomat.yaml:5 (key vtest)': "x"                      # function-typed option

error: The option `t.nul` is defined both null and not null, in `vendomat.yaml' and `lib-defs.nix'.   # fast
error: A definition for option `packages' is not of type `list of package'. TypeError: Definition values:
- In `vendomat.yaml (key packages)': "jq"                    # string where a list is needed
error: A definition for option `t.path' is not of type `absolute path'. Definition values:
- In `vendomat.yaml': "./src"                                # relative path, no conversion (fast)
error: The option `t.settings.a' has conflicting definition values:    # freeform json type
- In `vendomat.yaml': 1
- In `lib-defs.nix': 0
```

Package conflict (fast; both locations, value shown as derivation):

```
error: The option `t.pkg' is defined multiple times while it's expected to be unique.

Definition values:
- In `vendomat.yaml': <derivation jq-1.8.2>
- In `lib-defs.nix': <derivation hello-2.12.3>
```

Package reference errors from the prototype (named by key path, not by the module system):

```
error: vendomat.yaml: key `packages[0]': nixpkgs has no attribute `nosuchpkg'
error: vendomat.yaml: key `packages[0]': nixpkgs has no attribute `python3Packages.nosuch'
error: vendomat.yaml: key `packages[0]': nixpkgs attribute `lib' is not a package
error: vendomat.yaml: key `packages[0]': a package must be a string that names a nixpkgs attribute
error: vendomat.yaml: key `vtest.apps.a.pkg': nixpkgs has no attribute `nosuch'
```

Without the custom check, `lib.getAttrFromPath` gives `cannot find attribute 'nosuchpkg'` with no location
(`logs/misc-pkg.txt`). A non-derivation attribute such as `lib` is caught by the type check
(`... not of type 'package'. - In 'vendomat.yaml'`).

### 4.6 Package strings without a translation table

Mechanism (prototype in `fixtures/s2-merge/ws5/.vendomat/generated-module.nix`, arg `options`):
for each JSON key, walk `lib.attrByPath path null options`. If the path is an option (`lib.isOption`),
convert the value by `option.type.name` and `type.nestedTypes.elemType`:

- `package` -> `lib.attrByPath (lib.splitString "." s) null pkgs`, then check `lib.isDerivation`
- `listOf`, `attrsOf` -> map the element type
- `nullOr` -> convert the inner type
- `submodule` -> `type.getSubOptions [ ]` and convert each declared field
- anything else -> unchanged

Real devenv result (`logs/real5-ok.txt`): `packages = ["jq","python3Packages.requests"]` gave
`jq-1.8.2, python3.14-requests-2.34.2`. `languages.python.package = "python312"` gave
`python3-3.12.14-env`. `vtest.apps.a.pkg = "cowsay"` (`attrsOf submodule` with a package field) gave
`cowsay-3.8.4`. `nullOr package` with `null` gave `null`. `types.shellPackage` has `name = "package"` and works.

**No infinite recursion.** The generated module reads `options` (the declaration tree, which does not
depend on `config`) and `pkgs`. The attribute names of its `config` come from the JSON, not from
`config`. Reading `config.devenv.root` for the path case also did not recurse.

Limits found:

- The converter must test the JSON shape before it maps. `{"t":{"svc":"notattrs"}}` made a bare
  `lib.mapAttrs` fail with `expected a set but found a string` and no location. The ws5 prototype
  guards with `isList`/`isAttrs`/`isString`, so the type check then reports the right error with the
  `vendomat.yaml` location.
- Types with no static shape (`either`, `oneOf`, `coercedTo`, `attrsOf` of an `either`) pass through. A
  package inside them stays a string and the type check rejects it. `types.package` is `name = "package"`;
  a package type that renames itself would escape the check. Not tested beyond `shellPackage`.
- `attrsOf (submodule ...)` with dynamic names works because `getSubOptions` returns the declared fields.

### 4.7 Paths

- `types.path` with the string `"./src"`: error `not of type 'absolute path'` (fast).
- `types.path` with `"/etc/src"`: accepted, stays a string, no store copy.
- `types.str` with `"./src"`: accepted, stays the literal string.
- Conversion needed. The prototype turns a relative string into `"${config.devenv.root}/${s}"` for
  `path`-named types only (`logs/real5-matrix.txt`: `.../ws5/src/a`; the `str` option kept `src/a`).
  The conversion produces a string, not a Nix path value, so it does not copy into the store.
  Which workspace root to use for a module imported from another input is a design choice, not
  tested.

### 4.8 Null, unknown options, freeform, function types

- `null` for `nullOr`: accepted (`vtest.nul = null`, real devenv). `null` for a non-nullable option:
  type error with `vendomat.yaml` and the option path (above). `null` inside `listOf (nullOr str)`: kept.
- Unknown option path: the error names the option path, the definition location, and gives
  suggestions. With a per-key `_file` and a line map the location is `vendomat.yaml:<line> (key <key>)`. A
  nested unknown path (`languages.pythn`) names the full option path and prints the whole attribute set
  of that key.
- Freeform (`pkgs.formats.json {}` type, or a submodule with `freeformType`): arbitrary JSON values
  accepted, including nested lists, `null`, and floats. Merges with a library definition key by key; a list
  value concatenates (`b.c = [0]` + `[1,2]` -> `[1,2,0]`); a scalar clash on a key is `ERR` with both
  locations (`t.settings.a`). A typo in a freeform key is not an error (`enabel` was accepted).
- Function-typed option: the string or attribute set from JSON fails the type check with the text
  above. The error cites `vendomat.yaml`. JSON cannot express a function; native Nix is required.
- Wrong scalar types: `5` for `str` -> type error; `70000` for `port` -> type error naming the type;
  `8080.0` for `port` (YAML float) -> type error; `5` for `either str int` accepted;
  `true` for `either str int` -> type error.

### 4.9 Reading `config.json`, git tracking, eval cache (`logs/caching-git.txt`, ws6)

On `2.4.0+fb5d382`, `builtins.readFile ./config.json` from the generated module:

| State of `.vendomat/config.json` | Result |
| --- | --- |
| No git repository | read |
| Git repository, untracked, not ignored | read |
| Git-ignored (`.vendomat/` in `.gitignore`) | read |
| Committed, then edited (dirty) | read; the new value appears |
| Edited with the same length and the old mtime restored | new value appears (content, not mtime or size, keys the cache) |

`devenv shell -- printenv FOO` printed the changed value. No git step is needed. The path is relative
to the module, not to the git tree. A `path:` or `git+file:` library input is a different matter (4.5).
Not tested: a `github:` or `git+https:` input as a library with this module, and a workspace evaluated
from a flake (`--from`).

## 5. Proves, inference, unproved

Proved on the pinned fork (`2.4.0+fb5d382`) with the real options listed above:

1. Plain YAML definitions follow native merging. Different scalars at the same priority stop evaluation
   (`eval`, `shell`, `build shell`, `info`) with both definition locations.
2. `_file` and `lib.setDefaultModuleLocation` make the generated side cite `vendomat.yaml` (or
   `vendomat.yaml:<line> (key <key>)` with a line map). The data file and a store path do not appear.
3. The package mechanism (options walk, `package`/`listOf`/`attrsOf`/`nullOr`/`submodule`) works with no
   recursion and no table. Missing attributes can be reported with the key path.
4. No priority number puts YAML between two plain definitions. Priorities below 100 beat `devenv.nix`
   plain definitions silently and, on list and attribute-set options, drop devenv's own definitions.
5. Untracked, ignored, and dirty `config.json` files are read and invalidate the cache.

Inference (not run to completion):

- Detection of "YAML lost to a stronger definition" through `options.<path>.definitionsWithLocations`
  (one scalar tested).
- Plain list order is stable across devenv versions. Not assumed; two harnesses gave opposite orders.
- A line map (`lines.json`) from the YAML linter fits the per-key `_file` form. The prototype used
  hand-written line numbers.

Unproved:

- Behavior on the stock devenv (`b904dcb`), on other nixpkgs revs, or in `machines.*` options (NixOS
  submodule options), and for `home-manager` options.
- `either`/`coercedTo`/`oneOf` packages; relative paths in modules imported from other inputs.
- A secret canary or the schema export (other spikes).

## 6. Recommended user-facing rule

1. YAML values are plain definitions, one per option value. Vendomat never wraps them with a priority.
2. A different scalar from YAML and from a library or `devenv.nix` plain definition stops evaluation.
   The error names both locations. Equal values do not conflict.
3. Lists, `lines`, attribute sets, and submodules merge. A list from YAML joins the other lists; the
   order is not defined. Use `lib.mkBefore` or `lib.mkAfter` in `devenv.nix` when order matters.
4. A library `mkDefault` yields to YAML for scalars. A `mkDefault` list or text option is dropped when any
   plain definition exists, and devenv core defines some of these (`packages`, `enterShell`).
5. To override a library or YAML value, write `lib.mkForce` in `devenv.nix`. A stronger definition in a
   library (`mkForce`, `mkOverride` below 100) beats YAML without an error. Vendomat should report
   it only if a fixture proves the detection.
6. A value that needs a function, a store path, or a non-JSON type goes into `devenv.nix`.
7. Never document "YAML always wins" or "devenv.nix always wins". Neither is true in Nix for plain
   definitions.

## 7. Proposed replacement text

`NEW:` The config reader MUST read `.vendomat/config.json` with `builtins.fromJSON` and MUST define each
declared option value as a plain definition (priority 100), without `mkDefault`, `mkForce`, or
`mkOverride`. It MUST set a module location that names `vendomat.yaml`, and SHOULD name the top-level key and
line. Different scalar values at the same priority MUST stop evaluation with every definition location.
The module MUST convert a string to a package only for options of package type (found through the option
declarations) and MUST report an unknown nixpkgs attribute with the YAML key path. A relative string for a
path-typed option MUST become an absolute string under the workspace root. A value that JSON cannot
express MUST use `devenv.nix`. The documentation MUST state: YAML does not override a library definition,
and `devenv.nix` with `lib.mkForce` overrides both.

## 8. Logs

All under `~/.local/state/vendomat/p20/2026-10-11/S2/logs/`:

- `matrix-<type>.json`, `matrix-leaf-astr.json`, `matrix-leaf-sub.json`, `errors-fast.txt`
- `real-matrix.txt`, `real-matrix-compact.txt`, `real/<case>.<key>.log` (full devenv output per cell)
- `real5-matrix.txt`, `real5-ok.txt`, `real-location-modes.txt`, `location-fast.txt`
- `misc-pkg.txt`, `misc-rest.txt`, `caching-git.txt`, `packages-core-dropped.txt`, `ignored-detect.txt`
