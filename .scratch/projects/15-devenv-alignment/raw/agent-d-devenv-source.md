<!-- Raw final report of Agent D (devenv source at fe20b5c, sonnet). Two reports: the first run, then the follow-up run, 2026-10-09. Extracted unedited from the agent transcript. Model output: an observation here is the agent's claim, not a Vendomat gate. -->

Agent D report: devenv source claims verified at the pinned revs.

Setup and commands (all succeeded)
- Temp dir: `/tmp/devenv-src.l6Lr`. The clone is `/tmp/devenv-src.l6Lr/devenv`, checked out at fe20b5cb (HEAD message "fix(test): report disabled process dependencies before startup (#3239)").
- I also added a git worktree of the CLI rev at `/tmp/devenv-src.l6Lr/cli-b904dcb`.
- Fixtures: `/tmp/devenv-fixture.9acX` and `/tmp/devenv-fixture2.XPGw`. Remove all three directories when done.
- Commands run:
  - `git clone --filter=blob:none https://github.com/cachix/devenv`
  - `git checkout fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4`
  - `git merge-base --is-ancestor b904dcb fe20b5cba7ab` returned ANCESTOR.
  - `devenv --version` printed `devenv 2.4.0+b904dcb (x86_64-linux)`.
  - `devenv machines <sub> --help` for each subcommand.
  - `nix eval --expr 'builtins.parseFlakeRef "..."'` with system nix 2.34.7. Pure parse, no fetch.
  - `devenv machines info`, `devenv build machines.web.build.nixos` (fails at eval by design), and `devenv shell -- printenv FROM_SHARED`.
  - I never ran machines apply, deploy, install, rollback or switch, and I ran nothing as root.
- Revision gap: b904dcb is 17 commits behind fe20b5c. `git diff b904dcb fe20b5c` touches only these files: `cli.rs`, `daemon_processes.rs`, `devenv/mod.rs` (process-daemon and completion changes), `files.nix`, `treefmt.nix`, `opentofu.nix`, `mysql.nix`, `latest-version`, and `hook.fish`. Machines, imports, outputs, lock, profiles, cachix and flake files are identical at both revs. All claims below hold for both revs unless noted.
- Paths are relative to the clone root `/tmp/devenv-src.l6Lr/devenv`. Line numbers are at fe20b5c.

## 1. Machines

1. Definition site | `src/modules/machines.nix:757-760` | `machines = lib.mkOption { type = lib.types.attrsOf machineOptions; ... description = "Machines for NixOS, home-manager, and nix-darwin.";` | VERIFIED
2. Old name `configurations` renamed | `machines.nix:753` | `(lib.mkRenamedOptionModule [ "configurations" ] [ "machines" ])` | VERIFIED
3. Role options | `machines.nix:301` `nixos` (`nullOr unspecified`), `:568` `home-manager`, `:581` `nix-darwin`, `:317` `hardware.facter`. Also `system` (default `pkgs.stdenv.system`), `target.host`, `target.sshOpts`, `install.{kexec.image,kexec.postSshPort,extraFiles,secrets,secretspec.*,encryptionKeys,copyHostKeys}`, `deploy.healthCheck`, `deploy.rollbackTimeout` (`ints.between 30 600`, default 300, `:636`) | VERIFIED
4. Disko options | `machines.nix:145` `disko.nixosModules.disko` is added to every NixOS machine. `build.diskoScript` `:660`, plus `diskoFormatScript` and `diskoMountScript`. There is no `machines.<n>.disko` option. The user writes `disko.devices...` inside the `nixos` module. | VERIFIED
5. Facter | `machines.nix:319` `default = ".machines/${name}/facter.json";`. The `facter.nixosModules.facter` module is added only when `hardware.facter != null` (`:132-138`). `:329`: "Set to `null` to opt this machine out of facter". | VERIFIED
6. Build and setup subcommands, plus outputs | Subcommands: `check, apply, plan, status, rollback, info, install, deploy` (`devenv/src/cli.rs:1324-1470`). There is NO `machines build` (`devenv machines build --help` gives "unrecognized subcommand"). Build with `devenv build machines.<n>[.build.<role>]` (`docs/src/content/docs/machines.md:54-56`). Outputs `build.nixos`, `build.home-manager`, `build.nix-darwin`, `build.deployer` and the disko scripts are `output`-typed options (`machines.nix:604-675`). | VERIFIED (`build` is not a subcommand)
7. Implementation files | CLI enum: `devenv/src/cli.rs:1324`. Dispatch: `devenv/src/main.rs:1583-1659`. Implementation: `devenv/src/devenv/machines.rs`.
   - `machines_info` `:1168`, `machines_install` `:1229`, `install_one_machine` `:1579`
   - `machines_deploy` `:2410`, `machines_plan` `:2500`, `machines_check` `:2720`
   - `machines_apply` `:2785`, `machines_status` `:2988`, `machines_rollback` `:3031`
   - `run_machine_transaction` `:3055`, `build_machine_role` `:3172` (runs `devenv build machines.{name}.build.{role}`)
   - NixOS target executor: `src/modules/machines/deploy.py`, wrapped by `src/modules/machines/deploy.nix`.
   | VERIFIED
8. Install requires disko | `machines.nix:127-128` `if disko == null then throw (outerConfig.lib._mkInputError diskoInputArgs)`. `:118` comment: "Requires `inputs.disko` (always, because disko is the declarative partitioning layer...". `docs/.../machines.md:26`: "NixOS machines require the disko input, even when you only deploy to an existing host". Empirical (fixture 1): `devenv build machines.web.build.nixos` errored with "To use 'machines.<name>.nixos', run the following command: $ devenv inputs add disko github:nix-community/disko --follows nixpkgs". | VERIFIED
9. Install requires nixos-facter | Conditional. The facter input is required only if `hardware.facter != null`, and the default is a non-null path (`machines.nix:132-134`). `hardware.facter = null` removes the requirement for the evaluation. However, the install pipeline's `facter` phase still runs `nixos-facter` on the target unless you drop it with `--phases` (`machines.rs:74` `const NIXOS_FACTER_COMMAND: &str = "nixos-facter";`, `:1935`). Install writes `.machines/<name>/facter.json` and runs `git add --intent-to-add` (`machines.rs:1950-1966`). | VERIFIED (conditional)
10. Install is SSH-only, remote target | `machines.rs:1274-1275` `"machines.{name} does not have `target.host` set. `devenv machines install` always operates over SSH."`. `:1267-1268` rejects machines without a `nixos` role. `:1850-1852` requires root (uid 0) on the target. The default pipeline is `kexec, facter, disko, install, reboot` (`cli.rs:1104-1111`). `install_kexec` (`:1877`) runs `curl --fail -L {url} | tar xzf - -C /root && /root/kexec/run` over SSH. Its default URL is the nixos-images kexec tarball (`:688`). `install_disko` (`:1983`) copies the disko script to the target with `nix copy` and runs it over SSH. There is NO option to target a local block device. `machines.nix:263` says `target.host` unset is "only valid for `home-manager`", and `machines.md:47` says "Setting it to `localhost` still uses SSH". If you boot your own installer, skip kexec with `--phases facter,disko,install,reboot` (`machines.md:131`). The target is still reached through SSH. | VERIFIED. Inference, not tested: `root@localhost` plus `--phases` could in principle operate on the local host's disks, but no code path supports a local device.
11. Confirmation before formatting | NONE for `install`. Docs: `machines.md:133` `:::caution[Install wipes disks without a confirmation prompt]` and `:135` "there is no dry run or automatic resume". The `Install` args in `cli.rs:1380-1431` have no `--yes` or `--force`. The only safeguards are that at least one explicit name is required (`cli.rs:1427` "`install` never runs bare because it wipes disks") and a refusal when the NixOS config has no root auth (`machines.rs:1664`). `--stop-after-disko`, `--no-reboot`, `--phases` and `--disko-mode disko|format|mount` exist (`cli.rs:1389-1420`). | VERIFIED (no prompt)
12. Deploy and apply confirmation | `deploy` has `--yes` ("Apply the displayed fleet plan without an interactive confirmation.", `cli.rs:1437`). The prompt is `dialoguer::Confirm::new().with_prompt("Apply this fleet plan?").default(false)` (`machines.rs:2455-2458`). Non-interactive without `--yes` fails: "Deployment needs confirmation. Run interactively, pass --yes, or review and apply saved plan {id}" (`:2452`). `apply <plan>` has no prompt; it applies a saved or exported reviewed plan. `plan` saves to `.devenv/machine-plans/<id>/plan.json` (`:2790-2796`, `docs/.../machines.md:179`). | VERIFIED
13. Rollback mechanism | `devenv machines rollback <name>` calls `run_machine_transaction(... executable=MACHINE_EXECUTOR, toplevel=None ...)` (`machines.rs:3031-3052`). That runs `{executable} rollback {id}` on the target (`:3067-3070`). `MACHINE_EXECUTOR` is `/nix/var/nix/gcroots/devenv-machines/executor/bin/devenv-machine-deploy` (`:75`). On the target `deploy.py:547-550`: `["nix-env", "--profile", str(self.profile), "--set", previous]` then `[previous + "/bin/switch-to-configuration", "switch"]`, where `profile=Path("/nix/var/nix/profiles/system")` (`:54`). `previous` comes from the recorded `state["previousSystem"]` (`:545`), not from a generation index. Automatic rollback: a systemd transient watchdog restores the previous system if the controller does not confirm within `deploy.rollbackTimeout`. A NixOS unit `devenv-machines-recover` recovers after a reboot (`src/modules/machines/recovery.nix`). `docs/.../machines.md:203`: "`rollback` restores the previous recorded NixOS system after its service stops." It requires a recorded transactional deployment (`cli.rs:1363`). nix-darwin and home-manager have no rollback (`machines.md:224,249`). | VERIFIED
14. Sharing modules across machines | The `nixos`, `home-manager` and `nix-darwin` options take `unspecified` modules, so any shared Nix module can be reused. `machines.md:45`: "The imported file is a normal NixOS module." `machines.nix:141-142` passes `specialArgs = { inherit inputs self; }`. The test fixture `tests/machines-mixed/devenv.nix` defines four machines in one `devenv.nix`. No special sharing mechanism exists beyond the module system. There are no tags (`machines.md:286` "There are no machine tags or CLI group selectors"). Use `profiles` to vary the machine set (same line). | VERIFIED by reading (no dedicated sharing feature)
15. Machine inputs | Taken from the same `inputs` argument as devenv.nix, i.e. `devenv.yaml` inputs resolved to `devenv.lock`.
   - NixOS: `inputs.nixpkgs.lib.nixosSystem` if it exists (`machines.nix:48-50`). Otherwise it imports `eval-config.nix` from `inputs.nixpkgs.inputs."nixpkgs-src"` (the devenv-nixpkgs case, `:51-60`).
   - home-manager: `inputs.nixpkgs.legacyPackages.${machine.system}` (`:208`).
   - Optional inputs, each `or null`: `inputs.disko`, `inputs.nixos-facter-modules`, `inputs.nix-darwin`, `inputs.home-manager` (`:40-43`).
   - Missing inputs give a `devenv inputs add ...` hint (`:6-37`).
   Empirical: a `machines.web` definition evaluated under the pinned modules through `devenv machines info`. The table printed web (x86_64-linux, root@web.invalid, nixos) and me (home-manager, "(no target)"). | VERIFIED

Evidence for 6-14 is source plus `--help` output. Item 15 is also backed by the `info` fixture run.

## 2. imports and inputs

1. `imports` option doc | `devenv-core/src/config.rs:356-362` `/// A list of relative paths, absolute paths, or references to inputs to import `devenv.nix` and `devenv.yaml` files.` with `merge = schematic::merge::append_vec` | VERIFIED
2. Resolution of `<input>/<path>` (Nix side) | `devenv-nix-backend/bootstrap/bootstrapLib.nix:134-160`, quoted in two blocks.
   - Prefix cases: `importModule = path: if lib.hasPrefix "path:" path then ... else if lib.hasPrefix "/" path ... "./" ... "../"`
   - Input-name fallback: `name = builtins.head paths; input = inputs.${name} or (throw "Unknown input ${name}"); subpath = ...; devenvpath = input + lib.optionalString (subpath != "") "/${subpath}"; in tryImport devenvpath path`
   `tryImport` (`:120-132`) returns `<dir>/devenv.nix` and `<dir>/devenv.local.nix` (if present) or throws "`<path>/devenv.nix` file does not exist". A path ending in `.nix` is used directly. The first path segment names an input. | VERIFIED
3. Rust handling of file-style imports | `config.rs:1006` `is_file_import` treats only `./`, `../` and `/` as file imports. `collect_import_files` (`:1273`) collects `devenv.yaml` files only for directories that exist locally. `resolve_import_path` (`:1222`) rejects escapes outside the git root or project dir: "Import path '{}' resolves outside the ... which is not allowed" (`:1098`). Maximum depth is 100. | VERIFIED
4. Whether an imported directory's own `devenv.yaml` inputs are merged | Local path imports: MERGED. All imported `devenv.yaml` files are loaded as `source_yamls, imported_yamls, base` (`config.rs:683-691`), then `devenv.local.yaml` last (`:725`). `inputs`, `imports` etc. merge per field, with the base winning (comment `:681-682` "Load the source first, then imports, then base last so base takes precedence."). Input-style imports (`shared`, `devenv/examples/x`): their `devenv.yaml` is IGNORED. `docs/.../composing-using-imports.mdx:33-34`: "Composing ``devenv.yaml`` files is now supported for local files (relative and absolute paths). Remote inputs are not yet supported for ``devenv.yaml`` imports." Empirical, fixture 2: a `path:` input `shared` (`flake: false`) with `devenv.nix` setting `env.FROM_SHARED` and a `devenv.yaml` declaring input `extra-from-shared`. After `devenv shell`, `printenv FROM_SHARED` gave `yes`. The resulting `devenv.lock` root inputs were `['devenv','nixpkgs','shared']`, so `extra-from-shared` was NOT merged. | VERIFIED
5. `follows` | `config.rs:189-192` `pub follows: Option<String>`; `config.rs:228-239` url and follows together is an error ("url and follows cannot both be set for the same input"). `devenv-nix-backend/src/lib.rs:111-113` `flake_input.set_follows(follows_path)?`. Nested overrides: `input.inputs` map with `set_overrides` (`:117-154`, nested `set_follows` at `:147`). `follows` names are plain strings; `nixpkgs` is always followable (`config.rs:1383`). Docs `docs/.../inputs.md:140` "`follows` are specified by name. Nested inputs can be referenced by name using `/` as a separator." | VERIFIED
6. `flake: false` | `config.rs:183-188` `/// Does the input contain `flake.nix` or `devenv.nix`. /// Default: `true`.` `pub flake: bool`. It passes into `FlakeInput::new(&flake_ref, input.flake)` (`lib.rs:95`). The Nix side then treats the input as a non-flake source (`outPath`) for imports. | VERIFIED
7. URL parsing and schemes | URLs are parsed by Nix's own flake-ref parser through the C API: `devenv-nix-backend/src/lib.rs:89-93` `FlakeReference::parse_with_fragment(fetch_settings, flake_settings, &parse_flags, url)`, with `set_preserve_relative_paths(true)` at `:84`. devenv adds only the relative-path normalisation of `path:`, `./` and `../` URLs (`config.rs:776-845`). Docs list `github:`, `gitlab:`, `git+ssh://`, `git+https://`, `git+file:///`, `hg+...`, `sourcehut:`, `tarball+https://`, `path:`, `file+https://`, `file:///` (`docs/.../inputs.md:75-117`). Plain `git://` is NOT in the docs list. Local parse test with system nix 2.34.7 (devenv bundles its own Nix libs, so confirm against its version):
   - `git://example.com/repo?ref=main` parses to `{ ref = "main"; type = "git"; url = "git://example.com/repo"; }`
   - `git+file:///tmp/x` parses to `{ type = "git"; url = "file:///tmp/x"; }`
   - `path:/tmp/x` parses to `{ path = "/tmp/x"; type = "path"; }`
   Fetching was not tested. | `git+file` and `path:` VERIFIED. `git://` UNDOCUMENTED; parses under nix 2.34.7.
8. Lock inputs default | `lib.rs:162` `nixpkgs_url = "github:cachix/devenv-nixpkgs/rolling"`, `:175` `devenv_url = "github:cachix/devenv?dir=src/modules"`, added when absent | VERIFIED
9. `devenv.local.yaml` | `config.rs:14` `const YAML_LOCAL_CONFIG: &str = "devenv.local.yaml";` loaded after base (`:725-745`). Docs `docs/.../files-and-variables.mdx:20-25`. | VERIFIED

## 3. outputs

1. Option | `src/modules/outputs.nix:3-16` `outputs = lib.mkOption { type = config.lib.types.outputOf lib.types.attrs; default = { }; ... description = "Nix outputs for `devenv build` consumption."` | VERIFIED
2. Types | `outputs.nix:21-32` `output = lib.types.anything // { name = "output"; ...}` and `outputOf = t: mkOptionType { name = "outputOf"; ... }` | VERIFIED
3. `devenv build` | `devenv/src/devenv/mod.rs:2620-2680`. With no args it runs `eval_devenv(&["build"])` and flattens each leaf, where a string or an object with `outPath` counts as a leaf (`:2648-2656`). With args it evaluates `build.{attr}` per argument (`:2658-2665`). The Nix side `build` is defined in `bootstrapLib.nix:~590` (`build = build project.options config`). Its walker (`bootstrapLib.nix:~486-535`) collects options whose type name is `output` or `outputOf`. It also recurses into `attrsOf submodule` options such as `machines` (comment: "Recurse into `attrsOf submodule` options (e.g. `machines`) so that output-typed sub-options inside each submodule entry become build targets"). Consequence: bare `devenv build` also builds every machine's `build.*` outputs. The only output-typed options in `src/modules` are `outputs` and the `machines.*.build.*` options (`rg 'types\.output'`). Docs `docs/.../outputs.mdx`: "To build all defined outputs, run: `devenv build`". | VERIFIED
4. Language `import` helpers | `docs/.../outputs.mdx` says "Rust: Uses `crate2nix`", "Python: Uses `uv2nix`" (docs claim, not exercised) | VERIFIED as documented upstream

## 4. profiles and local files

1. Options | `src/modules/profiles.nix:27-51`. `profiles` is a submodule with `freeformType = lazyAttrsOf (submodule { extends = listOf str; module = deferredModule })`. It has two namespaces: `hostname` ("Profile definitions that are automatically activated based on the machine's hostname.") and `user` (".. based on the username."). | VERIFIED
2. CLI | `devenv/src/cli.rs:359-364` `#[arg(short = 'P', long = "profile", global = true, ...)] pub profiles: Vec<String>` (repeatable) | VERIFIED
3. Application and order | `bootstrapLib.nix:276` `orderedProfiles = hostnameProfiles ++ userProfiles ++ manualProfiles;`. Hostname and username come from `NixArgs.hostname/username` (`devenv-core/src/nix_args.rs:373-377`). `extends` is resolved depth-first with cycle detection, parents first (`:279-293`, `expandedProfiles` `:307`). Each profile module gets `profilePriority = (lib.modules.defaultOverridePriority - 1) - index` (`:330`), so later profiles win. Leaf-typed options (str, int, bool, enum, path, package, float, anything, nullOr thereof) are wrapped in `mkOverride`. The result is `baseProject.extendModules { modules = allPrioritizedModules; }` (`:433`). If no profiles are active, `baseProject` is used unchanged. Docs `docs/.../profiles.mdx:93-98`: "Base configuration always loads first and has the lowest precedence. Hostname profiles activate next, followed by user profiles. Manual profiles passed with `--profile` have the highest precedence; if you pass several profiles, the last flag wins. Extends chains resolve parents before children". Aggregate options (lists, attrsOf) merge as usual; they are not overridden. | VERIFIED
4. Module load order | `bootstrapLib.nix:231-246`: `devenv_imports ...`, then `devenv_root + "/devenv.nix"` (via `importModule`), then `devenv.local.nix` if it exists (`:236-238`), then `cli_options` (the `-O/--option` values, `:244-245`). `devenv.local.nix` is a normal module merged after `devenv.nix`. It has no special priority, so conflicting plain definitions error unless `mkForce`/`mkDefault` is used. Imported directories also pick up their own `devenv.local.nix` (`tryImport` `:120-127`). | VERIFIED
5. `devenv.local.yaml` order | After base: imported yamls, then base, then `devenv.local.yaml` (`config.rs:683-745`), so local wins | VERIFIED

## 5. Flake integration

1. Exports | `flake.nix:313` `flakeModule = self.flakeModules.default; # Backwards compatibility`; `:314-315` `flakeModules = { default = import ./flake-module.nix self; readDevenvRoot = ... }`; `:330-331` `lib = { mkConfig = ...; mkEval = ...; mkShell = args: ... config.shell // { inherit config; ci = config.ciDerivation; }` (`:372-379`). There is no `nixosModules` output. | VERIFIED
2. Flake mode flags | `flake.nix:357` `devenv.flakesIntegration = true;` and `:359` `devenv.warnOnNewVersion = false;`. Option `devenv.flakesIntegration`: `src/modules/update-check.nix:16-23` "Tells if devenv is being imported by a flake.nix file". | VERIFIED
3. `devenv.root` | `src/modules/flake-compat.nix:133-139` assertion `config.devenv.root != ""` with message "devenv was not able to determine the current directory. See https://devenv.sh/guides/using-with-flakes/". `:142` `devenv.root = lib.mkDefault (builtins.getEnv "PWD");` (needs `--impure`). `flake.nix:314-326` offers `readDevenvRoot` as the alternative. | VERIFIED
4. Reduced CLI in flake mode | `flake-compat.nix:35-80` is a shim `devenv` with only `up`, `test`, `tasks`, `version`. Quote `:68-69`: "This is a flake integration wrapper that comes with a subset of functionality from the flakeless devenv CLI." Unsupported: any other command (usage exit 1). `up` fails with "No 'processes' option defined" when `processes == {}` (`:86-89`). `up`, `test` and `tasks` re-enter `nix develop .#<shell> --impure` (`:20-30`). | VERIFIED
5. Unsupported integrations in flake mode | `integrations/secretspec.nix:55-61` assertion `!(config.secretspec.enable && config.devenv.flakesIntegration)`: "SecretSpec integration is not supported when using devenv with Nix Flakes." `integrations/dotenv.nix:157-164`: "The dotenv integration is loaded by the devenv CLI and is not supported by the flake integration." `docs/.../guides/using-with-flakes.md:35-48` comparison table: Built-in container support ✗, Protection from garbage-collection ✗, Faster evaluation (lazy trees) ✗, Evaluation caching ✗, Pure evaluation ✗ ("`impure` by default"), secretspec.dev ✗, Running processes when testing ✗. `flake-module.nix:74-76` comment: "TODO(sander): container support is undocumented and is specific to flake-parts, ie. the CLI shim doesn't support this." `devenv-up` and `devenv-test` packages are deprecated via `lib.warn`. `machines.nix` has no flake-mode assertion, but the CLI `machines` commands are not in the shim. | VERIFIED

## 6. Lock

1. File and format | `devenv-core/src/paths.rs:9` `pub const DEFAULT_LOCK_FILE: &str = "devenv.lock";`. It is the Nix flake lock format: `devenv.lock` has `"nodes": {...}`, `"root"`, `"version"` (checked `version=7`, `root='root'` on the lock copy). It is parsed and written by Nix's `LockFile` (`devenv-nix-backend/src/lib.rs:189-200`, `:207-218`). The NAR-hash-style `locked` fields (`rev`, `narHash`, `lastModified`, `dir`) are the same as `flake.lock`. | VERIFIED
2. Write or update | `lib.rs:230-300` `lock_inputs`: `InputsLocker::new(...).with_inputs(...).source_path(root/devenv.nix).mode(LockMode::Virtual).use_registries(true)` plus `update_input(name)` or `update_all()`, then `write_lock_file`. `write_lock_file` skips the write if the content is unchanged ("to preserve mtime for direnv", `:206`). `validate_lock_file` (`:311`) creates the file when missing or unparseable, and otherwise rewrites it only if `new_lock.has_changes(&old_lock)` (`:369-374`). Wrapped in `lock.rs:update/validate_and_load`. The default is "Validating lock" on every run. Docs `docs/.../inputs.md:181`: "When you run any of the commands, `devenv` resolves inputs ... into a commit revision and writes them to `devenv.lock`." `devenv update [name]` updates. `use_registries(true)` means flake registries are consulted. | VERIFIED
3. Project `flake.lock` | devenv itself NEVER reads a project `flake.lock`. The only `flake.lock` reads in the repo are repo tooling, tests, and flake-compat shims (`default.nix:3`, `shell.nix:3`, `src/modules/tasks/package.nix:9`; `rg 'flake\.lock'`). In flake mode, Nix's own `flake.lock` governs inputs. | VERIFIED (no project `flake.lock` read)
4. Fingerprint | `compute_lock_fingerprint` (`lib.rs:~385`) hashes per-node fingerprints (git rev, or narHash for tarball/path) with BLAKE3 and feeds the eval cache. | VERIFIED
5. Resolution to Nix inputs | `bootstrap/default.nix` + `resolve-lock.nix` (flake-compat adaptation from lix) turn `devenv.lock` into the `inputs` attrset: "`lockFile = builtins.fromJSON (builtins.readFile lockFilePath);`" (`resolve-lock.nix:8`) | VERIFIED

## 7. Secrets

- secretspec integration. Option module: `src/modules/integrations/secretspec.nix:20-50` (read-only `enable`, `profile`, `provider`, `secrets`). Secrets come from the `secretspec` module arg, or from the `SECRETSPEC_SECRETS` env var in flake mode (`:3-18`). With enable, it sets `env.SECRETSPEC_PROFILE` / `env.SECRETSPEC_PROVIDER` via `mkDefault` (`:64-72`). Rust side: `secretspec` crate 0.21 (`Cargo.toml:125`), `devenv/src/devenv/mod.rs:~4346` `secretspec::Secrets::load_from(&secretspec_path)`, `validate()`, then `SecretsNeedPrompting` on missing required values (`:4360-4368`). Config: `devenv-core/src/config.rs:441-471` `SecretspecConfig { enable, profile, provider, cachix_auth_token }`. CLI flags `--secretspec-profile`, `--secretspec-provider`. | VERIFIED
- sops. NOT FOUND as a devenv integration. The only hits are `machines.nix` help text (`install.secretspec.extraPackages` example "targetPkgs.sops targetPkgs.pass", `machines.nix:~463`), `docs/.../machines.md:302` ("Use sops-nix or agenix in your NixOS or home-manager modules for ongoing secret management"), and a unit test using provider string "sops" (`nix_args.rs:512`). SecretSpec providers (provider names) are resolved inside the upstream crate, not in this repo. | NOT FOUND (as a built-in)
- Machines bootstrap secrets: `install.secrets` / `install.extraFiles` / `install.encryptionKeys` use string paths that never enter `/nix/store` (`machines.nix:~384-536`). They are resolved locally or on the target (`install.secretspec.execution = "local" | "target"`). They are written only by `install`, not `deploy` (`machines.md:338`). | VERIFIED

## 8. Caching

1. Options | `src/modules/cachix.nix:11-14` `enable` (bool, default `true`); `:17-23` `pull` (listOf str, default `[]`, `apply = lib.unique`); `:25-29` `push` (nullOr str, default null, "This cache is also added to `cachix.pull`."); `:44` `cachix.pull = [ "devenv" ] ++ (lib.optional (cfg.push != null) config.cachix.push);`; `package` / `binary` options. | VERIFIED
2. Passing to Nix | `devenv-core/src/cachix.rs:190-207`:
   - `.map(|cache| format!("https://{cache}.cachix.org"))`
   - `settings.insert("extra-substituters".to_string(), pull_caches.join(" "));`
   - `settings.insert("extra-trusted-public-keys".to_string(), keys.join(" "));`
   These land in `StoreSettings` (`store_settings.rs:20-28`) and `apply_substituters_and_keys` (`devenv-nix-backend/src/backend.rs:1598-1612`: `store.add_substituter(...)`, `store.add_trusted_public_keys(...)`) on the opened store. Auth via a managed netrc file. A failure to add logs `tracing::warn!` and continues. The public keys come from the Cachix API (`devenv/src/devenv/cachix.rs:40` `CACHIX_API_URL = "https://cachix.org/api/v1"`). Auth token order: `CACHIX_AUTH_TOKEN` env, then SecretSpec, then the Cachix dhall config (`cachix.rs:122-136`; `docs/.../binary-caching.mdx:69-78`). | VERIFIED
3. Non-Cachix substituters | NOT supported through `cachix.*`: pull entries are always rewritten to `https://<name>.cachix.org`. A generic Nix path exists: CLI `--nix-option <NAME> <VALUE>` ("Pass additional options to nix commands ... `--option` flag", from `devenv --help`) and the user's own `nix.conf`. Substituters configured in the daemon or `nix.conf` still work ("Nix will continue to substitute binaries from any caches you may have configured externally", `binary-caching.mdx:196`). I did not test an Attic cache. | VERIFIED (no Attic or generic substituter option); `--nix-option` seen only in `--help`
4. Trusted user | Not required for devenv to run. Quote `docs/.../binary-caching.mdx:96-104`: the daemon "only accepts substituters and keys requested by users listed in `trusted-users`, or substituters already present in `trusted-substituters`. For anyone else the daemon drops the request and builds every path that is missing from `cache.nixos.org` locally, without an error in the shell." Alternative: put `extra-substituters` and `extra-trusted-public-keys` in the daemon config (`:117-128`). Code: `is_trusted_client()` exists in the backend (`backend.rs:1159-1161`, `cnix_store.rs:55-57`) but is not used as a gate. The only reference is a log-bridge test about the "not a trusted user" warning (`logger.rs:259-260`). Machines: copying closures to a target needs the invoking user trusted on the target or signed paths (`machines.md:298,360`). | VERIFIED
5. Push | The Cachix daemon client is in `devenv-nix-backend/src/cachix_daemon.rs`. Initialisation is skipped when `cachix.enable = false` or `offline` mode (`devenv/src/devenv/cachix.rs:~48-54`). | VERIFIED

## 9. Services and process managers

- `src/modules/services/` has 45 entries: adminer, blackfire, caddy, cassandra, clickhouse, cockroachdb, couchdb, dynamodb-local, elasticmq, elasticsearch, garage, httpbin, influxdb, kafka-connect, kafka, keycloak, mailhog, mailpit, meilisearch, memcached, minio, mongodb, mosquitto, mysql, nats, nginx, nixseparatedebuginfod, opensearch, opentelemetry-collector, postgres, prometheus, rabbitmq, redis, rustfs, sqld, tailscale, temporal, tideways, trafficserver (directory), typesense, varnish, vault, wiremock. All are auto-listed by `top-level.nix:334` `listEntries ./services`. | VERIFIED
- Postgres: `services/postgres.nix:1-60`. It is a devenv `processes.postgres` service. Data lives under `config.env.DEVENV_RUNTIME/postgres` (`runtimeDir`, `:17`), and ports are allocated through `processes.postgres.ports.main.value`. | VERIFIED (not exhaustively read)
- NixOS or systemd bridge: NOT FOUND. `rg systemd src/modules/services/*.nix` gives no matches. There is no `nixosModules` output in `flake.nix`/`flake-module.nix` (`rg 'nixosModules'` hits only `machines.nix:136,145`, consuming facter and disko). The services are process definitions, usable only in devenv shells and process managers. The only systemd emitted by the repo is the machines recovery unit and the transient watchdog (`src/modules/machines/recovery.nix`, `deploy.py`), not a service bridge. | NOT FOUND
- Process managers (`src/modules/process-managers/`): `process-compose`, `native`, `hivemind`, `honcho`, `mprocs`, `overmind`. Default: `src/modules/processes.nix:447-455` `default = if config.devenv.cli.version != null && lib.versionAtLeast config.devenv.cli.version "2.0" then "native" else "process-compose";` with `defaultText = lib.literalMD "`native` for devenv 2.0+, `process-compose` otherwise"`. So the default is `native` for the pinned CLI 2.4. | VERIFIED

## 10. Testing

- `devenv test` | `devenv/src/devenv/mod.rs:2517-2603`. Phases: (1) configure shell, (2) run tasks rooted at `devenv:enterTest` (includes git-hooks run), (3) build `devenv.config.test`, (4) start processes if any (`ReturnAfterStart`), (5) run the test script in the shell, (6) stop processes (`down`), then report "Tests passed :)" or bail "Tests failed". | VERIFIED
- `enterTest` | `src/modules/tests.nix:5-8` `enterTest = lib.mkOption { type = lib.types.lines; description = "Bash code to execute to run the test."; };`. `test = writeShellScript "devenv-test" 'set -euo pipefail ${config.enterTest}'` (`:16-23`). The module adds `wait_for_port` and `wait_for_processes` helpers (`mkBefore`) and runs `./.test.sh` if present (`mkAfter`). `devenv.isTesting` option at `:10-14`. | VERIFIED
- git-hooks module | `src/modules/integrations/git-hooks.nix` (option `git-hooks`, `:105`). The input is `inputs.git-hooks or inputs.pre-commit-hooks or tryGetInput` (`:20-22`). Task `devenv:git-hooks:run` with `before = [ "devenv:enterTest" ]` (`:~293-297`). The default `devenv.yaml` includes `git-hooks: url: github:cachix/git-hooks.nix` (`docs/.../inputs.md:13-14`). In flake mode `flake.nix:343` notes "TODO: deprecate default git-hooks input". | VERIFIED

## 11. Experimental, TODO and planned-change markers

1. `docs/src/content/docs/machines.md:5-7` `:::caution[Experimental] ... Machines are new in devenv 2.4. The interface may change before it is declared stable.` | VERIFIED
2. `docs/src/content/docs/blog/2026/09/24/devenv-24-machines.md:25` "Machines are experimental, and we'd like feedback from people using it on real hosts." | VERIFIED
3. `docs/.../composing-using-imports.mdx:34` "Remote inputs are not yet supported for ``devenv.yaml`` imports." Signals planned work, the only imports-related marker. | VERIFIED
4. `docs/.../machines.md:296` "This flag currently requires the C-Nix backend. Plain `devenv build` does not accept it." (about `--use-machines-as-builders`) | VERIFIED
5. `machines.md:135` (install): "there is no dry run or automatic resume." | VERIFIED
6. `machines.md:224,249`: no automatic rollback for nix-darwin or home-manager; "There is no `machines install` for macOS." | VERIFIED
7. `src/modules/machines.nix:752-753` the `configurations` to `machines` rename (an earlier name was renamed). | VERIFIED
8. `devenv-core/src/config.rs:310,337,2741` `TODO(v3.0): remove deprecated alias` / `remove these fields` (for `per-platform` and the camelCase aliases `allowUnfree`, `permittedInsecurePackages` and similar), plus `config.rs:265 // TODO: executables?`. These are the only config-related TODOs; none concern imports or lock. | VERIFIED
9. Nothing marked experimental, unstable or TODO in `outputs.nix`, `profiles.nix`, `lock.rs`, or the lock and import code. The only match was `nixos-unstable` strings.

## Other findings

- Fixtures: `devenv machines info` ran against the pinned module rev (devenv input `github:cachix/devenv/fe20b5cb...?dir=src/modules`, lock copied from vendomat's `devenv.lock`; I did not edit vendomat). `devenv.lock` is written to the cwd, so the `/tmp` fixture lock was written too.
- Doc and source mismatch candidates: none found. One nuance is that `docs/.../machines.md:26` says disko is required "even when you only deploy". The source agrees (`machines.nix:127`).

Remove with `rm -rf /tmp/devenv-src.l6Lr /tmp/devenv-fixture.9acX /tmp/devenv-fixture2.XPGw` (the worktree lives inside `/tmp/devenv-src.l6Lr`). I keep the clone in place for follow-up claims.

---

# Follow-up report

Agent D report: devenv source at the pinned revs. Format: claim | file:line | quote | status. Paths are relative to the devenv repo root.

SETUP
- Clone at /tmp/devenv-src.l6Lr/devenv. The coordinator asked for removal, so I deleted it with the three fixtures. `/tmp/devenv-0a76b85` and similar dirs are devenv runtime dirs, not mine.
- `git checkout fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4` gave "HEAD is now at fe20b5cb fix(test): report disabled process dependencies before startup (#3239)".
- `git merge-base --is-ancestor b904dcb fe20b5c` gave ANCESTOR. 17 commits separate them (`git log b904dcb..fe20b5c`).
- Those 17 commits touch only: files.nix, treefmt, opentofu, mysql, process-name completion in cli.rs, and daemon/start code in devenv/mod.rs. They do not touch machines.nix, machines.rs, the machines part of cli.rs, config.rs, bootstrapLib.nix, outputs, profiles or the lock code (`git diff --stat`). Everything below holds for both revs.
- `git rev-parse 'v2.4.0^{commit}'` printed b904dcb51fe48c30db250038241507f60752f222. `git tag --points-at b904dcb5` printed `latest` and `v2.4.0`. VERIFIED: that rev is the v2.4.0 tag.
- Local `devenv --version` is `devenv 2.4.0+b904dcb`.
- I ran no apply, deploy, install or rollback command and no root command.

1. MACHINES
- Defined in `src/modules/machines.nix`, imported by `src/modules/top-level.nix:314`. VERIFIED.
- `machines` is an `attrsOf machineOptions` | machines.nix:757-760 | "Machines for NixOS, home-manager, and nix-darwin." | VERIFIED.
- Option names | machines.nix | VERIFIED:
  - `system` (default `pkgs.stdenv.system`)
  - `target.host` (257), `target.sshOpts`
  - `nixos` (301), `home-manager` (568), `nix-darwin` (581), all `nullOr unspecified`
  - `hardware.facter` (317), default `".machines/${name}/facter.json"` (319), `null` allowed (329)
  - `install.kexec.image`, `install.kexec.postSshPort`, `install.extraFiles`
  - `install.secretspec.{execution,provider,profile,extraPackages}`, `install.secrets`, `install.encryptionKeys`, `install.copyHostKeys`
  - `deploy.healthCheck` (625), `deploy.rollbackTimeout` (636, between 30 and 600, default 300)
  - internal build outputs `build.{nixos,deployer,nix-darwin,home-manager,diskoScript,diskoFormatScript,diskoMountScript}` (604-672)
- `configurations` is an alias | machines.nix:753 | `(lib.mkRenamedOptionModule [ "configurations" ] [ "machines" ])` | VERIFIED.
- disko is required for every NixOS role, lazily | machines.nix:127-128 | "if disko == null then throw (outerConfig.lib._mkInputError diskoInputArgs)" | VERIFIED. The comment at 118 says "Requires `inputs.disko` (always...".
  - Empirical check: in a fixture without a disko input, `devenv build machines.web.build.nixos` failed with "To use 'machines.<name>.nixos', run the following command: $ devenv inputs add disko github:nix-community/disko --follows nixpkgs".
- facter is required only when `hardware.facter != null`, and the default is non-null | machines.nix:132-134 | "if machine.hardware.facter != null then if facter == null then throw (... facterInputArgs)" | VERIFIED. `hardware.facter = null` opts out (329).
- Optional inputs: `inputs.disko`, `inputs.nixos-facter-modules`, `inputs.nix-darwin` and `inputs.home-manager` are all `or null` | machines.nix:40-43 | VERIFIED. Each throws only when a machine uses it (187, 201).
- NixOS evaluation | machines.nix:141-149 | "(nixosSystemFor machine.system) { specialArgs = { inherit inputs self; }; modules = [ { nixpkgs.hostPlatform = machine.system; } disko.nixosModules.disko ./machines/recovery.nix ./machines/facts.nix machine.nixos" | VERIFIED. The facter modules and `facter.reportPath` are appended after these.
- Machines use the same `inputs.nixpkgs` as the shell. `nixosSystemFor` is at machines.nix:48 and uses `inputs.nixpkgs.lib.nixosSystem`, or `eval-config.nix` from `inputs.nixpkgs.inputs."nixpkgs-src"` for devenv-nixpkgs. Home Manager uses `inputs.nixpkgs.legacyPackages.${machine.system}` (208) with `homeManager.lib.homeManagerConfiguration` and `extraSpecialArgs = { inherit inputs self; }`. VERIFIED.
- Inputs come from devenv.yaml and are locked in devenv.lock. The module argument `inputs` is the lock-resolved input set (bootstrapLib.nix `specialArgs = inputs // { inherit inputs ...}`, ~line 247). VERIFIED.
- Several machines can share modules. `nixos`, `home-manager` and `nix-darwin` are ordinary modules, so `import ./x.nix` works (docs/src/content/docs/machines.md:45, "The imported file is a normal NixOS module"). No sharing mechanism exists beyond that. machines.md:286 says "There are no machine tags or CLI group selectors." VERIFIED.
- CLI subcommands | devenv/src/cli.rs:1324-1470 and `devenv machines --help` | check, apply, plan, status, rollback, info, install, deploy. There is NO `build` subcommand. Local help prints "unrecognized subcommand 'build'". Use `devenv build machines.<n>` (machines.md:16). VERIFIED.
- Implementation files:
  - Dispatch: devenv/src/main.rs:1583-1660.
  - All logic: devenv/src/devenv/machines.rs. Functions: `machines_info` 1168, `machines_install` 1229, `machines_deploy` 2410, `machines_plan` 2500, `machines_check` 2720, `machines_apply` 2785, `machines_status` 2988, `machines_rollback` 3031, `run_machine_transaction` 3055, `nix_copy` 3181.
  - Target-side executor: src/modules/machines/deploy.py (wrapped by deploy.nix).
- Info | `machinesMeta` evaluated via `eval_devenv(&["devenv.config.machinesMeta"])` (machines.rs:2483-2488). It does not build. The fixture `devenv machines info` printed the table of me and web. VERIFIED.
- Install needs disko always, and facter unless `hardware.facter = null`. See the two throws above. The facter phase runs in the pipeline (machines.rs:1936-1943) and writes `.machines/<name>/facter.json`. `git add --intent-to-add` failure is non-fatal. VERIFIED.
- Install is SSH to a remote host only; it cannot take a block device.
  - machines.rs:1275 | "`devenv machines install` always operates over SSH." Missing `target.host` is an error.
  - machines.rs:1268 | "`devenv machines install` only applies to NixOS machines."
  - machines.rs:1851 | "install requires root SSH access".
  - kexec: machines.rs:1904 | "curl --fail -L {url_q} | tar xzf - -C /root && /root/kexec/run", from the nixos-images tarball (688 and 677).
  - Disko runs on the target (1983-2005). No local disk path exists anywhere. NOT FOUND for any local-disk install.
- Install has no confirmation prompt and no `--yes`.
  - machines.md:133 | ":::caution[Install wipes disks without a confirmation prompt]".
  - machines.md:135 | "there is no dry run or automatic resume".
  - cli.rs:1380-1430: no `yes` field on Install. `rg 'Confirm::new'` hits only machines.rs:2455 (deploy).
  - cli.rs:1427 | "`install` never runs bare because it wipes disks." Names are required.
  - Only protections: the root-auth check at machines.rs:1664 ("refusing to install... target would boot locked out"), and a build-before-disko order (machines.rs:1680-1690, "Realise the complete replacement before any disk mutation"). VERIFIED.
- Install phases | cli.rs:1104-1111 and machines.rs:1623-1815 | kexec, facter, disko, install, reboot. Flags `--phases`, `--stop-after-disko`, `--no-reboot`, `--disko-mode {disko|format|mount}` (cli.rs:1114-1124), `--max-concurrent`, `--use-machines-as-builders`. Preflight (machines.rs:1816-1865) needs uid 0, tar and curl. VERIFIED.
- Deploy confirms unless `--yes`.
  - machines.rs:2449-2465 | "Deployment needs confirmation. Run interactively, pass --yes, or review and apply saved plan {id}" and `dialoguer::Confirm::new().with_prompt("Apply this fleet plan?").default(false)`.
  - `apply` takes a saved plan and has no prompt and no `--yes` (cli.rs:1331-1342; machines.rs:2785-2802). VERIFIED.
- Rollback is a recorded transaction, not a NixOS generation list.
  - machines.rs:3031-3053 runs `{MACHINE_EXECUTOR} rollback <id>` over SSH.
  - deploy.py:545-550 | `previous = self.validate_system(state["previousSystem"]); nix-env --profile <profile> --set previous; previous/bin/switch-to-configuration switch`.
  - Profile is `/nix/var/nix/profiles/system` (deploy.py:54).
  - Deploy does the same with `--set requested` then `switch-to-configuration switch` (deploy.py:405-409).
  - Checks the previous system is active afterwards (deploy.py:553-555).
  - Automatic rollback via a systemd watchdog timer: `systemd-run ... --on-active=<rollbackTimeout>s` (deploy.py:326-330, timer name `devenv-machine-watchdog-<id>.timer` at 215/395).
  - Boot-time recovery service: src/modules/machines/recovery.nix:4-20, `systemd.services.devenv-machines-recover`, runs `executor recover` if `/var/lib/devenv-machines/current.json` exists.
  - State dirs: deploy.py:52-53 | `directory=Path("/var/lib/devenv-machines")`, `roots=Path("/nix/var/nix/gcroots/devenv-machines")`. machines.rs:75 | executor at `/nix/var/nix/gcroots/devenv-machines/executor/bin/devenv-machine-deploy`.
  - nix-darwin and home-manager have no automatic rollback (machines.md:224, 249). VERIFIED.
- Agent A item 4 (state dirs and watchdog unit on the target): VERIFIED.

2. IMPORTS / INPUTS
- Entry types | devenv-core/src/config.rs:356-362 | "A list of relative paths, absolute paths, or references to inputs to import `devenv.nix` and `devenv.yaml` files." Merge is `append_vec`.
- Rust resolves only file imports. `is_file_import` is true for `./`, `../` and `/` (config.rs:1006). `resolve_import_path` (1222) joins to the base path or git root and checks `validate_within_root` (1040, "resolves outside the git repository... not allowed"). An entry like `shared/sub` is `base.join("shared/sub")`; it is not a directory, so `collect_import_files` (1273) skips it. VERIFIED.
- Input imports are resolved in Nix | devenv-nix-backend/bootstrap/bootstrapLib.nix:134-163 | `importModule`; the else branch (lines ~155-161) runs `name = head (splitString "/" path); input = inputs.${name} or (throw "Unknown input ${name}"); devenvpath = input + "/" + subpath; tryImport devenvpath path`. `tryImport` (120-132) loads `<dir>/devenv.nix` plus `devenv.local.nix` if present, and throws "<path>/devenv.nix file does not exist" otherwise. A path ending in `.nix` is used as the file. Also accepted: `path:` prefix, `/abs`, `./rel`, `../rel` (resolved against devenv_root). VERIFIED.
- An imported input's own devenv.yaml inputs are IGNORED. Empirical test: a `path:` flake:false input `shared` held devenv.nix (setting `env.FROM_SHARED`) and devenv.yaml (declaring `extra-from-shared`). With `imports: [shared]`, `devenv shell -- printenv FROM_SHARED` printed "yes". The resulting devenv.lock root inputs were `['devenv','nixpkgs','shared']`, so `extra-from-shared` was not merged. docs composing-using-imports.mdx:34 | "Remote inputs are not yet supported for ``devenv.yaml`` imports." The blog (2025/10/07 devenv-110) says "imports from inputs still only load Nix configurations". I did not verify issue #2205; the docs link text is mangled and I did not go online. Agent A's claim about #2205 is NOT FOUND in source.
- Local file imports DO merge devenv.yaml. config.rs:683-687 | "let load_order = source_yamls.iter().chain(imported_yamls.iter()).chain(base_yaml...)". Comment at 681: "Load the source first, then imports, then base last so base takes precedence." `devenv.local.yaml` loads last (725-740). Input URLs of local imports are rewritten relative to their yaml (config.rs:762-846). Depth limit: `MAX_IMPORT_DEPTH` 100 (1281). A directory import without devenv.yaml still loads its devenv.nix (1344-1360). VERIFIED.
- Inputs struct | config.rs:178-205 | `url`, `flake` (default true), `follows`, `inputs` (nested overrides), `overlays`.
  - `url` and `follows` together are an error (`FlakeInputError::UrlAndFollowsBothSet`, 219-231).
  - The Nix side is devenv-nix-backend/src/lib.rs:75-157. `FlakeInput::new(&flake_ref, input.flake)` carries the `flake` bool; `set_follows` is at 113 (top level) and 147 (nested); `set_overrides` is at 154. A follows value may be nested via `/` (inputs.md:140).
  - Defaults added if absent: nixpkgs `github:cachix/devenv-nixpkgs/rolling` (lib.rs:162) and devenv `github:cachix/devenv?dir=src/modules` (175).
- URL parsing is done by Nix's own flake-reference parser through the C API (`FlakeReference::parse_with_fragment`, lib.rs:89 and 163), with `set_preserve_relative_paths(true)` (84). Devenv has no URL parser of its own. docs inputs.md:60-100 list:
  - `github:`, `gitlab:`, `sourcehut:`
  - `git+ssh://`, `git+https://`, `git+file://`
  - `hg+...`, `tarball+https://`
  - `path:`, `file+https://`, `file:///`
  - `git://` is NOT listed.
- `git://` works anyway.
  - `nix eval --expr 'builtins.parseFlakeRef "git://example.com/repo?ref=main"'` (system Nix 2.34.7) gave `{ ref = "main"; type = "git"; url = "git://example.com/repo"; }`. The same parser accepts `git+file`, `path:` and `git+git://`.
  - Real fixture: devenv.yaml with `devman: { url: "git://server/devman?ref=refs/tags/v0.7.0", flake: false }` plus the nixpkgs input and the devenv input pinned to fe20b5c. `devenv update devman` exited 0 (re-run: `exit=0`).
  - Lock node devman: `type: git`, `url: git://server/devman`, `ref: refs/tags/v0.7.0`, `rev: 4c9927ada27a5c12a5ee2acdf8ad85648f7aafa1`, `revCount: 514`, `lastModified: 1789478635`, `narHash: sha256-pKf7QG4dLxfqakacpc9Yzbuo+rFY0ZcEhQoTgv4/jts=`, `flake: false`. VERIFIED (undocumented but functional with devenv 2.4.0).
- Relative `path:` and `./` input URLs are rewritten against the declaring yaml (config.rs:762-846). `path:` inputs are copied whole and do not respect .gitignore (inputs.md:100-105). VERIFIED.

3. OUTPUTS
- `outputs` | src/modules/outputs.nix:3-18 | `outputs = lib.mkOption { type = config.lib.types.outputOf lib.types.attrs; default = { }; ... description = "Nix outputs for `devenv build` consumption."`. Types `output` and `outputOf` are defined at outputs.nix:20-35. VERIFIED.
- `bootstrapLib.nix` `build` (~line 466) walks the options. It collects options whose type name is `output` or `outputOf`, and recurses into `attrsOf submodule` options (that is how `machines.<n>.build.*` is found). It is exposed as `build = build project.options config` (~line 558).
- Only `outputs` and the machines build options use these types (`rg 'types\.output'`: outputs.nix:4, machines.nix:5).
- `devenv build` | devenv/src/devenv/mod.rs:2620-2680 | with no attributes it does `eval_devenv(&["build"])`, flattens the JSON, and builds every leaf that is a string or has `outPath`. With attributes it evaluates `build.<attr>`; if evaluation fails it builds the attribute as given. Output looks like `{ "outputs.rust-app": "/nix/store/..." }` (outputs.mdx). VERIFIED. Consequence: bare `devenv build` also builds every `machines.<n>.build.*` role that evaluates to non-null.

4. PROFILES
- Options | src/modules/profiles.nix:27-49 | `profiles` is a submodule with a freeform `lazyAttrsOf` of `{ extends : listOf str; module : deferredModule }`, plus `profiles.hostname` and `profiles.user` using the same profile type. VERIFIED.
- Activation | bootstrapLib.nix:261-276 | `orderedProfiles = hostnameProfiles ++ userProfiles ++ manualProfiles`. Hostname and user profiles activate only if the name exists under `profiles.hostname` or `profiles.user`. Manual profiles come from `active_profiles` (`--profile` / `-P`, cli.rs:359-364). VERIFIED.
- Priority | bootstrapLib.nix:330 | `profilePriority = (lib.modules.defaultOverridePriority - 1) - index`. Later in the list gets a lower number, which means higher precedence.
  - Order is base < hostname < user < manual.
  - Among manual profiles the last flag wins.
  - `extends` parents resolve before children (`resolveProfileExtends`, ~280-300).
  - `mkOverride` is applied only to leaf option types (str, int, bool, enum, path, package, float, anything, and nullOr of those; lines ~340-360). Lists and attrs merge normally. This is a caveat: the profile override applies only to those types.
  - Result is applied with `baseProject.extendModules` (433). docs profiles.mdx:93-98 match. VERIFIED.
- Module load order (bootstrapLib.nix:231-246): `devenv_imports`, then `devenv_root/devenv.nix`, then `devenv.local.nix` if it exists, then `cli_options` (`-O` / `--option`). All use the same module priority, so `devenv.local.nix` overrides only with `mkForce` or on non-conflicting options. Hostname and username come from `hostname::get()` etc. (devenv/src/devenv/mod.rs:4164, NixArgs at 4182). YAML: `devenv.local.yaml` loads last (config.rs:725). VERIFIED.

5. FLAKE INTEGRATION
- Exports | flake.nix:313-315 `flakeModule` (alias) and `flakeModules.default = import ./flake-module.nix self`; `readDevenvRoot` at 316. `lib.mkConfig` 331, `lib.mkEval` 333, `lib.mkShell` 372. There is no `nixosModules` output (`rg nixosModules` hits only machines.nix:136 and 145). VERIFIED.
- `mkEval` | flake.nix:355-359 | "devenv.flakesIntegration = true; devenv.warnOnNewVersion = false". It does not read devenv.yaml. `rg devenv.yaml` over flake.nix, flake-module.nix and src/modules finds only comments, error text and the `require_version` description. The inputs come from `args.inputs` (flake.nix:343-348). Default input: `git-hooks` only, with comment "# TODO: deprecate default git-hooks input" (flake.nix:343). VERIFIED: devenv.yaml is not read in flake mode.
- Unsupported or reduced in flake mode:
  - src/modules/flake-compat.nix:130-142: assertion `config.devenv.root != ""` with "devenv was not able to determine the current directory"; `devenv.root = lib.mkDefault (builtins.getEnv "PWD")`, which is impure.
  - flake-compat.nix:35-78: a shim `devenv` wrapper supports only `up`, `test`, `tasks` and `version`. Its text: "This is a flake integration wrapper that comes with a subset of functionality from the flakeless devenv CLI."
  - integrations/secretspec.nix:55 | `assertion = !(config.secretspec.enable && config.devenv.flakesIntegration)`, "SecretSpec integration is not supported when using devenv with Nix Flakes".
  - integrations/dotenv.nix:157 | assertion: "not supported by the flake integration".
  - guides/using-with-flakes.md comparison table: built-in containers, GC protection, lazy trees, eval caching, pure eval, secretspec.dev and "Running processes when testing" are all "✗" for flakes.
  - flake-module.nix:74-75 | "TODO(sander): container support is undocumented and is specific to flake-parts, ie. the CLI shim doesn't support this."
  - The `devenv-up` and `devenv-test` packages are deprecated via `lib.warn` (flake-module.nix:64-86).
  - The `machines` module is imported through top-level.nix:314, so it exists in `mkEval`. There is no flakes-specific assertion in machines.nix and no CLI path from a flake. `devenvPackageFor` (machines.nix:~58-78) has a flake-consumer branch.
  - Agent A item 7: devenv.yaml is not read in flake mode. VERIFIED.

6. LOCK
- Path: devenv-core/src/paths.rs:9 | `pub const DEFAULT_LOCK_FILE: &str = "devenv.lock";`.
- The format is Nix's flake lock. devenv-nix-backend/src/lib.rs:200-230 uses Nix's `LockFile`/`InputsLocker` through the C API (`LockFile::parse`, `lock_file.to_string()`). The nixpkgs-style schema has `nodes`, `root`, `version` (7 in my fixture), and nodes with `locked`/`original`. Verified by `python -I` on the copied lock. resolve-lock.nix:1-3 adapts lix flake-compat (`lockFile.root`).
- Writing: lib.rs:207-218 `write_lock_file` writes only if content changed, "to preserve mtime for direnv". Locking (lib.rs:230-290) uses `LockMode::Virtual` and `use_registries(true)` (257-258, 361-362). A restrictive umask guard is used (276-280).
- `validate_lock_file` (lib.rs:311) creates the lock if it is missing or unparseable, and rewrites it when `has_changes` (lib.rs:~370). Update: `lock_inputs` with `update_input(name)` or `update_all()`; CLI `devenv update [name]`.
- A project `flake.lock` is NOT read by the CLI. Non-test `flake.lock` references are only default.nix, shell.nix and src/modules/tasks/package.nix (devenv's own repo files), plus a flake.lock comment in flake-compat.nix. Flake mode uses the host flake's lock. VERIFIED. Empirically, `devenv.lock` was written to the project directory.

7. SECRETS
- `secretspec` crate 0.21 (Cargo.toml:125). `devenv/Cargo.toml:11` builds a `secretspec` binary. Flow: devenv/src/devenv/mod.rs:4326-4375 (`Secrets::load_from(secretspec.toml)`, provider and profile from devenv.yaml or the `--secretspec-*` flags, then `validate()`; missing secrets raise `SecretsNeedPrompting`). The values go to Nix as the `secretspec` module arg and to `config.secretspec.secrets` (read-only) (src/modules/integrations/secretspec.nix:7-95). It sets only `SECRETSPEC_PROFILE` and `SECRETSPEC_PROVIDER` in env (secretspec.nix:64-72). devenv.yaml: `SecretspecConfig` has enable, profile, provider and `cachix_auth_token` (config.rs:441-471). VERIFIED.
- sops: there is no sops integration in devenv. Matches in the source are the secretspec provider name in a test (nix_args.rs:512) and machines.nix text (example `extraPackages = targetPkgs: [ targetPkgs.sops ... ]`, docs machines.md:349). In machines, sops/agenix is guided at machines.md:302 | "Use sops-nix or agenix in your NixOS or home-manager modules". NOT FOUND as a feature.
- Machine install secrets come from the active SecretSpec profile (machines.nix:439-470, machines.rs:1342-1500); never in the store.

8. CACHING
- Options | src/modules/cachix.nix:11-31 | `cachix.enable` (bool, default true), `cachix.pull` (listOf str, default `[ ]`, `apply = lib.unique`), `cachix.push` (nullOr str, default null), `cachix.package`.
- Config at line 44: `cachix.pull = [ "devenv" ] ++ (lib.optional (cfg.push != null) config.cachix.push);`. So effective pull defaults to ["devenv"] (docs binary-caching.mdx: "devenv.cachix.org is added to the list of pull caches by default"). VERIFIED.
- Substituters are Cachix-only. devenv-core/src/cachix.rs:196 | `.map(|cache| format!("https://{cache}.cachix.org"))`, set as `extra-substituters` (199) and `extra-trusted-public-keys` (207, keys fetched from `https://cachix.org/api/v1`, devenv/src/devenv/cachix.rs:40). The netrc is `machine {cache}.cachix.org` (cachix.rs:~231). The settings go to the store through `apply_substituters_and_keys` (devenv-nix-backend/src/backend.rs:1598-1612, `store.add_substituter` / `add_trusted_public_keys`). `StoreSettings` (store_settings.rs:19-30) is generic, but "Today the producer is `CachixManager`" (store_settings.rs:7). There is no option for a non-Cachix substituter. NOT FOUND. For others use `--nix-option NAME VALUE` (devenv --help, "Nix options") or Nix config. Agent A item 8 VERIFIED.
- Trusted user is not required by devenv itself. binary-caching.mdx:108-117 | "(the daemon) only accepts substituters and keys requested by users listed in trusted-users... For anyone else the daemon drops the request and builds every path... locally, without an error in the shell." devenv-nix-backend/src/logger.rs:259 knows the warning "ignoring the client-specified setting 'trusted-public-keys', because it is a restricted setting and you are not a trusted user". `is_trusted_user` exists (backend.rs:1159, cnix_store.rs:55) but only core/backend.rs:67 forwards it. VERIFIED.

9. SERVICES AND PROCESSES
- src/modules/services/ (50 entries): adminer, blackfire, caddy, cassandra, clickhouse, cockroachdb, couchdb, dynamodb-local, elasticmq, elasticsearch, garage, httpbin, influxdb, kafka-connect, kafka, keycloak, mailhog, mailpit, meilisearch, memcached, minio, mongodb, mosquitto, mysql, nats, nginx, nixseparatedebuginfod, opensearch, opentelemetry-collector, postgres, prometheus, rabbitmq, redis, rustfs, sqld, tailscale, temporal, tideways, trafficserver, typesense, varnish, vault, wiremock. Loaded via `listEntries ./services` (top-level.nix:334).
- postgres.nix is a process-based module. It uses `config.env.DEVENV_RUNTIME` (`runtimeDir`, line ~20), `config.processes.postgres` ports (line ~15), and `services.postgres.{package,extensions,listen_addresses,port,initialDatabases}` (lines ~13-60).
- No service module emits systemd units and none is usable in NixOS. `rg systemd src/modules/services/*.nix` found nothing. There is no `nixosModules` export and no bridge. The machines code is a separate path. The only systemd use is in machines (`recovery.nix`, `deploy.py`) and a comment in processes.nix:180. VERIFIED.
- Process managers: process-managers/{native,process-compose,hivemind,honcho,mprocs,overmind}.nix. Default: processes.nix:447-455 | `default = if config.devenv.cli.version != null && lib.versionAtLeast config.devenv.cli.version "2.0" then "native" else "process-compose"`. VERIFIED.

10. TESTING
- tests.nix:5-24 | `enterTest` (lines, "Bash code to execute to run the test.") and `test` (internal package `writeShellScript "devenv-test" ''set -euo pipefail; ${config.enterTest}''`). `devenv.isTesting` (tests.nix:10).
- It also defines `wait_for_port` and `wait_for_processes` (process-compose and native branches), and runs `./.test.sh` if present (end of the file).
- `Devenv::test` | devenv/src/devenv/mod.rs:2517-2590. Phases:
  1. Configure the shell.
  2. Run `devenv:enterTest` tasks (includes `devenv:git-hooks:run`).
  3. Build `devenv.config.test`.
  4. Start processes if any (`ReturnAfterStart`).
  5. Run the test script in the shell.
  6. Stop processes.
  - Failure message: "Tests failed :(".
- git-hooks module: src/modules/integrations/git-hooks.nix (`options.git-hooks` at 105). It takes `inputs.git-hooks` or `inputs.pre-commit-hooks`. If neither exists it uses `config.lib.tryGetInput`, with default `github:cachix/git-hooks.nix` (git-hooks.nix:21-28). Task `devenv:git-hooks:run` is `before = [ "devenv:enterTest" ]` (git-hooks.nix:296). Default devenv.yaml also adds the `git-hooks` input (inputs.md:11-14). VERIFIED.

11. EXPERIMENTAL / TODO MARKERS (relevant ones)
- docs machines.md:5-7 | ":::caution[Experimental] Machines are new in devenv 2.4. The interface may change before it is declared stable." VERIFIED (extra claim a).
- docs blog 2026/09/24/devenv-24-machines.md:25 | "Machines are experimental, and we'd like feedback from people using it on real hosts."
- machines.md:296 | "This flag currently requires the C-Nix backend."
- machines.rs docs: "There are no machine tags or CLI group selectors" (machines.md:286).
- composing-using-imports.mdx:34 | "Remote inputs are not yet supported for ``devenv.yaml`` imports."
- blog 2026/03/05 devenv-20: "`--from` only works with projects that use `devenv.nix` alone; projects that also rely on `devenv.yaml` for extra inputs aren't supported yet".
- flake.nix:343 | "# TODO: deprecate default git-hooks input".
- flake-module.nix:74 | container support TODO (above).
- config.rs:310, 337, 2741 | "TODO(v3.0): remove deprecated alias" / camelCase aliases. There is no TODO or "unstable" marker in outputs.nix, profiles.nix or the lock code. `machines.rs` has no experimental comment.

COORDINATOR EXTRA CLAIMS (a to g)
- (a) Experimental: VERIFIED, machines.md:5-7. The concept doc says "2.4.1" but the pinned CLI and modules are 2.4.0 and a 2.4.1-pre commit ("c0f1824e Next release is 2.4.1" is in the range). machines.md is the same text at both revs.
- (b) disko is required even for deploy-only use: VERIFIED, machines.nix:127-128 and machines.md:26 | "NixOS machines require the disko input, even when you only deploy to an existing host". Reason: `nixosEval` always adds `disko.nixosModules.disko` (145).
- (c) Facter report per host: VERIFIED, with a correction. The default is `.machines/<name>/facter.json` (machines.nix:319). Your concept doc's `./hardware/<host>.json` is the documented override (machines.md:154 and the option example at machines.nix:~335). The report is generated by `install` over SSH and must be committed. `hardware.facter = null` removes the need for a report and for the facter input (machines.md:154; machines.nix:329-331).
- (d) Install partitions without confirmation, no dry run, no resume: VERIFIED, machines.md:133-135, plus the CLI has no `--yes`.
- (e) Install = kexec, facter, disko, install, reboot: VERIFIED, cli.rs:1104-1111 and machines.rs:1623-1815. Order of effects: preflight, kexec, facter, root-auth check, build, encryption keys, disko, nixos-install, extra files, bootstrap secrets, host keys, reboot.
- (f) Closure transfer, V5 NAT-009: VERIFIED.
  - machines.rs:3181-3205 `nix_copy` runs `nix copy --to <uri> <store_path>` with `NIX_SSHOPTS`. The URI is `ssh://[user@]host[:port]` (machines.rs:508-521, `String::from("ssh://")`). It is `ssh://`, not `ssh-ng://`.
  - No `--substitute-on-destination` and no `-s` flag appears anywhere in machines.rs (`rg 'substitute'` finds nothing). So the controller uploads the closure it has. The target does not fetch from its own substituters on this path.
  - Deploy and apply copy every planned output (the system, the executor, and darwin or home-manager outputs) in `apply_machine_plan` (machines.rs:2886-2897) before activation. Install copies the disko script and the toplevel the same way (machines.rs:1995-1999, 2007-2022).
  - Remote builders are separate: `--use-machines-as-builders` (`resolve_builders_config`, machines.rs:566).
  - machines.md:298 | "The target must accept the copied paths: make the invoking user trusted with `nix.settings.trusted-users`, or sign the paths with a key the target trusts. Otherwise the copy can fail with a missing trusted signature. Devenv enables substituters for these builders." Troubleshooting row at machines.md:360.
  - The statement "does not substitute through Attic" is true in effect: devenv never passes target-side substitution. The only substituters devenv itself sets are the Cachix pull list on the controller.
- (g) Local apply: CONTRADICTED for NixOS.
  - `apply` and `deploy` do not call `nixos-rebuild`. `rg nixos-rebuild` in devenv/src and src/modules/machines* finds nothing.
  - NixOS and nix-darwin require `target.host` (machines.rs:2519-2527 | "machines.{name}.{role} requires target.host for system deployment"). The NixOS activation always goes over SSH to the executor (`activate_machine_plan`, machines.rs:2942-2955), where `target.as_ref().unwrap()`.
  - `target.host = "localhost"` still goes over SSH (machines.nix:263-264 | "Setting it to `"localhost"` is not the same as omitting it: `"localhost"` still routes through SSH."). It also needs root SSH (machines.rs:3000-3004, "Deployment status requires root SSH"; deploy.py runs as root).
  - Local in-process activation exists only for home-manager without `target.host` (machines.rs:2963-2975, `process::Command::new(&activate)`; machines.md:47). The machine's hostname is never compared to the local host (`rg hostname devenv/src/devenv/machines.rs` finds no match logic). A matching hostname gives no special treatment.
  - Host identity is used only to dedupe install targets (machines.rs:441-558).
- Deploy trust (coordinator follow-up 5): deploy needs root SSH for NixOS (machines.md:47 | "NixOS deployment and installation require root SSH"; preflight machines.rs:1851 for install and machines.rs:3000-3004 for status). The deploying user does not need to be a Nix trusted user on the target for ordinary nix copy if the paths are signed by a key the target trusts. SSH as root makes the copy trusted because the store connection is root. machines.md:298 and 360 describe the trusted-user problem for remote builders and non-root copies. nix-darwin deployments with a non-root user need passwordless sudo (machines.md:47, 224).

Extra caveats
- Local `devenv machines info` and the git:// test ran with my fixtures only; no machine was contacted.
- Fixtures used devenv.lock copied from the vendomat repo (read-only copy).
- I did not verify GitHub issue #2205 or any online resource.
