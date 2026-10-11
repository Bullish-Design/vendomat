# Step 0 probe: devenv evaluation surfaces

**Date:** 2026-10-10. **Status:** Observed. These are facts about upstream devenv at one pin. They
are not a passed harness gate.

Raw logs and fixture files: `~/.local/state/vendomat/p17-probe/` (outside the repository).

## Inputs

| Item | Value |
| --- | --- |
| devenv CLI | `devenv 2.4.0+b904dcb (x86_64-linux)`, `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0` |
| Nix | `nix (Nix) 2.34.7` |
| `devenv` input (module source) | `cachix/devenv` `a73c5b84c9527760f009232988466763068f9f61`, store source `/nix/store/12d8y6galxjc35m0fcdb494cr4caxp23-source` |
| `nixpkgs` input | `cachix/devenv-nixpkgs` `c2f38fe7f9e04d9aadd354d380f2bd40531d9737` (`rolling`) |
| `nixpkgs-src` | `NixOS/nixpkgs` `c7def046b9a883d46974757852106483d741586f` |

The probe project did not pin `inputs.devenv`. devenv selected `a73c5b84` for the module source. That
is not the fork base `b904dcb`. The option counts below belong to `a73c5b84`.

Fixture `simple/devenv.nix` (final form):

```nix
{ pkgs, ... }: {
  languages.python.enable = true;
  env.GREETING = "hi";
  packages = [ pkgs.jq ];
  services.postgres.enable = true;
  enterShell = "echo hi";
}
```

`simple/devenv.yaml` holds only `inputs.nixpkgs.url: github:cachix/devenv-nixpkgs/rolling`.

## Observations

**O1. `devenv eval` evaluates config attributes to JSON.**
Command: `devenv eval env.GREETING languages.python.enable enterShell packages services.postgres.port`.
Result: exit 0, 2.58 s wall time on a warm store. The output is one JSON object keyed by the attribute
path. `packages` is a list of store path strings. `enterShell` is the merged string, with text from
devenv's own modules and store paths in it.

**O2. `devenv eval` reaches only `devenv.config.*`.**
Command: `devenv eval options.languages.python.enable.type.name`.
Result: `attribute devenv.config.options.languages.python.enable.type.name not found`.

**O3. Evaluation enforces module checks.**
With `languages.python.version = "3.12"` and no `nixpkgs-python` input, `devenv eval` exited 1 with
`To use 'languages.python.version', run the following command: devenv inputs add nixpkgs-python ...`.

**O4. `devenv repl` reads commands from standard input.**
`printf 'builtins.attrNames devenv\n:q\n' | devenv repl` printed the names `config`, `devenv`, `info`,
`inputs`, `options`, `optionsJSON`, `pkgs`, `processProxyEnabled`, `project`, `shell`.
`devenv.options` is the `nixosOptionsDoc` result (`optionsAsciiDoc`, `optionsCommonMark`,
`optionsJSON`, `optionsNix`). Source: `devenv-nix-backend/bootstrap/bootstrapLib.nix:463-580`.

**O5. `devenv.optionsJSON` builds from the repl.**
Command: `printf ':b devenv.optionsJSON\n:q\n' | devenv repl`.
Result: `/nix/store/r7s6g7id0ilhk8q9y0jhql2zlylv60m3-options.json/share/doc/nixos/options.json`,
442 kB, 1144 options, 45 top-level names (`services` 379, `languages` 314, `process` 72,
`claude` 69, `tasks` 61, `processes` 55, `machines` 31). It holds 104 distinct `type` strings. The
`type` field is a human description, such as
`16 bit unsigned integer; between 0 and 65535 (both inclusive)`. The `default` field is Nix source
text, such as `"5432"`, not a JSON value.

**O6. `devenv.project` is the `lib.evalModules` result with typed options.**
`import probe.nix devenv.project` in the repl gave structured types:
`services.postgres.port` has `type.name = "unsignedInt16"`; `packages` has `type.name = "listOf"`
with `nestedTypes = [ "elemType" ]`; `env` has `type.name = "submodule"` with
`nestedTypes = [ "freeformType" ]`.

**O7. `definitionsWithLocations` gives the contribution of each file.**
`options.languages.python.enable.definitionsWithLocations` returned one entry:
`{ file = ".../simple/devenv.nix"; value = true; }`. `options.enterShell` lists three files:
`top-level.nix`, `update-check.nix`, and the fixture. A filter on the fixture path gave
`env = [ { GREETING = "hi"; } ]` and `packages = [ [ "/nix/store/hyz22a0l...-jq-1.8.2-bin" ] ]`.
`env.GREETING` is not an option; `env` is a freeform submodule, so its value appears at `env`.

**O8. `extendModules` evaluates an added module in the same process.**
`devenv.project.extendModules { modules = [ { services.redis.enable = true; scripts.hello.exec = "echo hello"; } ]; }`
gave `config.services.redis.enable = true` and a `scripts` definition
`{ hello = { exec = "echo hello"; }; }`. The file of an inline module is `<unknown-file>`. A module
given as a path keeps its path (inference from module system behavior; not yet tested here).

**O9. nixpkgs ships the tree-sitter Nix grammar for Python.**
`nix eval --raw nixpkgs#python3Packages.tree-sitter-grammars.tree-sitter-nix.name` printed
`python3.13-python-tree-sitter-nix-0.3.0+unstable20251203`.

## Inferences

- I1. The harness can read typed options and per-file definitions through `devenv repl`.
  `devenv eval` cannot reach them. (From O2, O4, O6, O7.)
- I2. Merged config values are a poor test oracle. They hold text from devenv's own modules and
  store hashes. Per-file definitions are a better oracle. (From O1, O7.)
- I3. One repl process can evaluate many candidate modules through `extendModules`. This lowers the
  cost of each case below the 2.6 s of one `devenv eval` start. (From O1, O8; cost not measured.)
- I4. The model generator should read `type.name` and `nestedTypes`, not the description strings
  in `optionsJSON`. (From O5, O6.)
- I5. A harness pin must set `inputs.devenv`. Without it, the module source drifts from the CLI.
  (From the input table.)
