<!-- Raw final report of Agent A (devenv docs and releases, sonnet), 2026-10-09. Extracted unedited from the agent transcript. Model output: an observation here is the agent's claim, not a Vendomat gate. -->

Research report: what released devenv (2.4.0) already provides. Pages were read as raw HTML from devenv.sh. CLI claims come from `devenv ... --help`. Release notes come from `gh release view`. Option claims come from the 2.4.0 reference page and `src/modules/machines.nix` on main. Docs base URL: https://devenv.sh. I wrote scratch copies to /tmp/dv-research and /tmp/dv-scripts. I changed no repository files.

Entry format: claim | source | version | OBS (page says) or INF (my reading) | status.

## 1. Machines (the whole feature is EXPERIMENTAL)

- The page says "Experimental. Machines are new in devenv 2.4. The interface may change before it is declared stable." | /machines/ ; release v2.4.0 "Machines (experimental)" | 2.4.0 (2026-09-24) | OBS | experimental
- A machine is "a NixOS, nix-darwin, or home-manager configuration defined in devenv.nix". Roles are `nixos`, `nix-darwin`, `home-manager`. A machine needs a name and at least one role. Names: start with a letter or underscore, then letters, digits, `_` or `-`. | /machines/ | 2.4.0 | OBS | experimental
- Commands (`devenv machines --help`): `info`, `check`, `plan`, `apply`, `deploy`, `install`, `status`, `rollback`. Machine builds go through `devenv build machines.<name>`, or `...build.nixos` for one role. There is no `machines build` subcommand. | `devenv machines --help`; /machines/ | 2.4.0 | OBS | experimental
- Option surface (/reference/options/#machines):
  - `machines.<name>.system` (default `pkgs.stdenv.system`)
  - `.nixos`, `.nix-darwin`, `.home-manager` (each: null or an unspecified module)
  - `.target.host`, `.target.sshOpts`
  - `.hardware.facter` (default `.machines/<name>/facter.json`; null opts out)
  - `.deploy.rollbackTimeout` (30..600, default 300) and `.deploy.healthCheck` (root shell, default `true`)
  - `.install.copyHostKeys`, `.install.encryptionKeys`, `.install.extraFiles.<path>.{source,owner,mode}`
  - `.install.kexec.image`, `.install.kexec.postSshPort`
  - `.install.secrets.<path>.{secret,owner,mode}`
  - `.install.secretspec.{execution,profile,provider,extraPackages}`
  - | reference/options | 2.4.0 | OBS | experimental
- The old `configurations` option is still a compatibility alias. | /machines/ | 2.4.0 | OBS | experimental
- disko is required for every NixOS machine, "even when you only deploy to an existing host". Command: `devenv inputs add disko github:nix-community/disko --follows nixpkgs`. The source throws a lazy error if `inputs.disko` is missing and a NixOS role is built. | /machines/ ; machines.nix lines 118-130 | 2.4.0 | OBS | experimental
- nixos-facter-modules is required only if `hardware.facter` is non-null. The default is the path `.machines/<name>/facter.json`. Set `hardware.facter = null` and supply your own hardware config to skip it. First install runs nixos-facter in the installer and saves the report, and the docs say to commit it. | /machines/ ; reference/options | 2.4.0 | OBS | experimental
- Extra inputs: `home-manager` for HM roles, `nix-darwin` for darwin roles. | machines.nix lines 31-43 | 2.4.0 | OBS (source) | experimental
- Install is DESTRUCTIVE with NO confirmation prompt. The page says "Install wipes disks without a confirmation prompt ... there is no dry run or automatic resume." The blog says "Installation partitions and formats disks without prompting". `install` has no `--yes` flag (checked in `devenv machines install --help`). It "never runs bare" and requires explicit machine names. | /machines/ ; /blog/2026/09/24/devenv-24-machines/ ; CLI help | 2.4.0 | OBS | experimental
- Install phases run in this order: kexec, facter, disko, install, reboot. Flags: `--phases`, `--stop-after-disko`, `--no-reboot`, `--max-concurrent`, `--use-machines-as-builders`, `--disko-mode {disko|format|mount}`. | CLI help; /machines/ | 2.4.0 | OBS | experimental
  - Default `disko` mode: "Destroy existing partitions, create new layout, mount".
  - `format`: create missing structures, no destroy phase.
  - `mount`: mount an existing layout without repartitioning.
  - The system builds BEFORE disko touches disks. A build failure stops before partitioning. The target may already be in the temporary installer.
  - "Phase selection does not check whether omitted steps succeeded."
- Install target is a REMOTE host over root SSH with kexec: "connects to a Linux host over root SSH, boots a temporary NixOS installer with kexec". Requirements: root SSH, kexec support, `tar`, `curl`, about 1 GB free RAM. The host need not run NixOS beforehand. If kexec is unavailable, boot an installer yourself and run `--phases facter,disko,install,reboot`. `target.host` omitted is valid only for home-manager. `target.host = "localhost"` "still routes through SSH". | /machines/ ; reference `target.host` | 2.4.0 | OBS | experimental
- The docs do NOT describe installing onto a local second drive of the running machine. | /machines/ | n/a | OBS (absence) | -
  - INF: a local install is not a supported path. Pointing `target.host` at localhost with the kexec phase would try to kexec the running machine.
  - Skipping kexec (`--phases facter,disko,install`) over SSH to localhost is untested and undocumented.
  - Treat a local second-drive install as unproven.
- The docs warn that `/dev/sda` names move between boots. They say to use `/dev/disk/by-id/` or `/dev/disk/by-path/`, and to test the disko layout in a VM first. They do not mention `by-partuuid` or `by-uuid`. | /machines/ | 2.4.0 | OBS | experimental
- Several machines in one `devenv.nix`: yes. `machines` is an attrset. `deploy` with no names selects every machine that has `target.host`. Local HM-only machines must be named. | /machines/ ; CLI help | 2.4.0 | OBS | experimental
  - Build, review and target checks cover all selected machines. Remote outputs are copied before any activation.
  - Machines activate one at a time in name order. `--max-concurrent N` sets the batch size. A failed batch stops later batches. "the fleet is not one transaction."
  - There are no machine tags or group selectors. The docs suggest profiles: `devenv --profile staging machines deploy`.
- Shared modules across machines: the docs describe none. The `nixos` value is an ordinary NixOS module, for example `import ./nixos/server.nix`. | /machines/ | 2.4.0 | OBS (absence) | experimental
  - INF: share code with ordinary Nix `imports`, functions and `let` bindings inside `devenv.nix`.
  - Source, observed: the NixOS role is evaluated as `nixosSystem { specialArgs = { inherit inputs self; }; modules = [ {hostPlatform} disko.nixosModules.disko ./machines/recovery.nix ./machines/facts.nix machine.nixos ... facter ]; }`.
  - NixOS modules therefore receive `inputs` and `self`, and devenv injects its own recovery modules.
  - `inputs.nixpkgs` is the SAME nixpkgs input as the dev shell (default `devenv-nixpkgs/rolling`). The code has a special path because devenv-nixpkgs is not a plain flake. | machines.nix lines 45-60, 141-181 | main (2.4.0 era) | OBS (source)
- home-manager can be a standalone machine. A machine that omits `target.host` activates locally. A machine with `target.host` activates over SSH. HM is evaluated via `homeManagerConfiguration` with `pkgs = inputs.nixpkgs.legacyPackages.<system>`, `extraSpecialArgs = { inherit inputs self; }` and `modules = [ machine.home-manager ]`. The activation wrapper runs as `home.username`. | /machines/ ; machines.nix lines 195-250 | 2.4.0 | OBS | experimental
- A combined system plus HM role: `install` provisions only NixOS. `deploy` activates the system role first, then HM as `home.username`. If HM fails after NixOS succeeds, NixOS stays applied. NixOS rollback does NOT revert HM files. The docs advise pinning the user's UID and GID on a new host. | /machines/ | 2.4.0 | OBS | experimental
- Rollback is NixOS only:
  - Activation runs in a systemd service on the target under a lock. A watchdog restores the previous system if activation fails, a health check fails, or the controller cannot confirm before the deadline.
  - Recovery can also run after reboot once NixOS reaches userspace. It "cannot fix early boot failure, reverse application data changes, or undo activation scripts".
  - `status` reports `pending`, `rolled-back`, `rollback-failed` or `unknown`. A new deploy is blocked while the outcome is unknown. `rollback <name>` restores the previous recorded system and needs "a recorded transactional deployment".
  - State lives on the target in `/var/lib/devenv-machines` and `/nix/var/nix/gcroots/devenv-machines/`.
  - nix-darwin and home-manager have NO automatic rollback. NixOS deploy does not repartition or reboot after a kernel change.
  - | /machines/ ; release v2.4.0 | 2.4.0 | OBS | experimental
- `check`: compares declared SSH access with facts read from the target, without building. It blocks reviewed deployments that disable SSH or root login, and warns about port or admin-key changes. `check --json` is available. | /machines/ | 2.4.0 | OBS | experimental
- `plan` builds and records the system, access facts and closure changes. `apply plan-...` uses the exact outputs, re-checks the machine, and rejects stale plans. Plans live in `.devenv/machine-plans/<id>/`. `plan --json` exports a plan. `deploy` and `apply` confirm unless `--yes`. | /machines/ ; CLI help | 2.4.0 | OBS | experimental
- Machine secrets:
  - The docs say to use sops-nix or agenix for ongoing secrets.
  - Install-time bootstrap options: `install.encryptionKeys` (before disko), `install.extraFiles` (after nixos-install), `install.secrets` (SecretSpec values), `install.copyHostKeys`.
  - Use string paths, not Nix path literals, so keys stay out of the store. Owners are numeric `uid:gid`. `install.secrets` modes reject group-write and other-user bits.
  - `execution = "local"` (default) resolves on the workstation and streams over SSH. `"target"` resolves in the installer. Bootstrap files are written ONLY by `install`, never refreshed by `deploy`.
  - Installs that send local secrets require a pre-pinned known host key and disable forwarding.
  - | /machines/ ; reference/options | 2.4.0 | OBS | experimental
- Cross-arch: `--use-machines-as-builders` (deploy and install) needs the C-Nix backend. Remote-builder SSH auth goes in a host alias, not `target.sshOpts`. | /machines/ | 2.4.0 | OBS | experimental

## 2. Module composition

- devenv.yaml `imports` accept relative paths, absolute paths, or input-relative references: "A list of relative paths, absolute paths, or references to inputs to import devenv.nix and devenv.yaml files." Example: `imports: [ devenv/examples/scripts ]`. | /composing-using-imports/ ; /reference/yaml-options/ | input imports from before 1.10; later releases fix edge cases | OBS | released
- Paths starting with `/` resolve from the git root. Parent imports (`../api/devenv.nix`) are allowed. | /blog/2025/10/07/devenv-110-monorepo-nix-support-with-devenvyaml-imports/ | 1.10 | OBS | released
- Local imports merge BOTH `devenv.nix` and `devenv.yaml` (inputs, `allowUnfree`). The 1.10 blog says "imports from inputs still only load Nix configurations (#2205)". The docs page says "Remote inputs are not yet supported for devenv.yaml imports." | blog 1.10; /composing-using-imports/ | 1.10 and current | OBS | released, limited
- Issue #2205 "Allow importing devenv.yaml from inputs" is still OPEN. The comment says a "two-pass locking" fix is planned. | `gh issue view 2205 -R cachix/devenv` | open as of 2026-10-09 | OBS
- INF: a repo imported through an input does NOT bring its own `devenv.yaml` inputs. The consumer must declare every input the imported modules need. A transitive local import chain does merge yaml. Release 2.1 fixed imports overriding the base project's `inputs`, so the base now wins. Release 2.2 fixed a transitively imported directory without its own `devenv.yaml` being dropped.
- `--from path:<dir>` loads the source's `devenv.yaml` (inputs and imports) merged. `--from` with a non-path source only works with projects that use `devenv.nix` alone. | release v2.2 ; blog 2.0 | 2.2 / 2.0 | OBS | released
- Remote repo import pattern: an input with `flake: false` (or the default) plus `imports: [ name ]`. Example: `inputs.shared-config: {url: path:../shared-config/, flake: false}`, then `imports: [shared-config]`. "The sibling shared-config repository only needs a devenv.nix file." The full config merges: packages, processes, services, outputs, env. | /composing-using-imports/ ; /guides/polyrepo/ | 2.0 (polyrepo); 2.2 fixed `path:` input edit tracking | OBS | released
- Selective access without merging: `inputs.<name>.devenv.config.outputs.<x>` with `flake: false`. | /guides/polyrepo/ ; blog 2.0 | 2.0 | OBS | released
- `outputs` semantics: `outputs.<name> = <derivation>` in `devenv.nix`. Language helpers: `config.languages.rust.import ./app {}` (crate2nix) and `config.languages.python.import ./app {}` (uv2nix). `devenv build` builds all outputs and prints JSON `{"outputs.rust-app": "/nix/store/..."}`. `devenv build outputs.rust-app` builds one. Custom options can use `config.lib.types.outputOf <type>` or `output`. | /outputs/ ; /guides/migrating-to-20/ ("devenv build returns JSON") | 2.0 JSON form | OBS | released
- A convention for one repo exporting devenv AND NixOS AND home-manager modules: NOT documented. The `extending` page covers only devenv modules (a shared module with options plus `imports`), and mentions `disabledModules`. | /extending/ ; grep of all fetched docs for nixosModules/homeModules found nothing | - | OBS (absence)
  - INF: write plain module files. Import the NixOS and HM ones into `machines.<n>.nixos` and `.home-manager`. Import the devenv ones through `imports`. Machine modules receive `inputs`/`self` automatically, so cross-repo modules arrive via `devenv.yaml` inputs.

## 3. Per-workspace layering

- direnv: `.envrc` with `eval "$(devenv direnvrc)"` and `use devenv` (v1.4+). Flags pass through, for example `use devenv --option services.postgres.enable:bool true`. `devenv init --include-envrc` writes it; since 2.2 `init` no longer creates `.envrc` by default. | /integrations/direnv/ ; release v2.2 | 1.4 / 2.2 | OBS | released
- Native alternative without direnv: `eval "$(devenv hook bash)"` (zsh, fish, nu also work), plus `devenv allow` and `devenv revoke`. It spawns a subshell. Since 2.2 it detects a project by `devenv.nix`, not `devenv.yaml`. | /auto-activation/ ; release v2.1, v2.2 | 2.1 | OBS | released
- `devenv.local.nix` and `devenv.local.yaml`: "Same as devenv.nix, but not meant to be committed ... developers can override some things". `devenv.local.yaml` was added in 1.10. 2.3 stopped `devenv --from` loading the CURRENT directory's `devenv.local.nix`. | /files-and-variables/ ; blog 1.10 ; release v2.3 | 1.10 / 2.3 | OBS | released
- Profiles (1.9 blog "Scaling Nix projects using modules and profiles"):
  - Define with `profiles.<name>.module = {...}` and optional `extends = [...]`. Select with `--profile` (repeatable), or `profile:` in `devenv.yaml`.
  - `profiles.hostname.<name>` and `profiles.user.<name>` exist and auto-activate on hostname and username.
  - Priorities are automatic and deterministic. Base is lowest, then hostname, then user, then `--profile` (the last flag wins). `extends` resolves parents before children. 2.2.1 fixed package-valued options so they override without `lib.mkForce`.
  - A profile that reads its own config values must be a function `{ config, ... }:`.
  - `devenv allow` persists profiles. `devenv --profile X allow` saves them for auto-activation. Plain `devenv allow` clears the saved selection.
  - | /profiles/ ; /reference/options/ ; /auto-activation/ ; release v2.2.1 | 1.9 (2.2.1 fix) | OBS | released
- `lib.mkDefault` conventions: the docs give no general convention. The only explicit mention is that dotenv values use `lib.mkDefault`, so `devenv.nix` `env` wins. | /integrations/dotenv/ | 1.11-era / 2.3 parser | OBS | released
- `enterShell` and tasks: `devenv:enterShell` and `devenv:enterTest` are built-in events. A task with `before = [ "devenv:enterShell" ]` runs as part of shell entry. `after` and `before` are two views of one edge. `@started`, `@ready`, `@succeeded`, `@completed` set the required state. `devenv tasks run` defaults to `--mode before` since 2.1. `wantedBy` (2.4) selects a task whenever a listed task runs, without ordering it. | /tasks/ ; releases v2.1, v2.4.0 | 2.1 / 2.4 | OBS | released
- `require_version` in `devenv.yaml` (true, or a constraint like `>=2.1`) enforces the CLI version. | /reference/yaml-options/ ; release v2.1 | 2.1 | OBS | released

## 4. Flake integration and the lock

- Flake integration ships `devenv.lib.mkShell { inherit inputs pkgs; modules = [...]; }` and the flake-parts `inputs.devenv.flakeModule` with `perSystem.devenv.shells.<name>`. Enter with `nix develop --no-pure-eval`. | /guides/using-with-flakes/ ; /guides/using-with-flake-parts/ | long-standing | OBS | released
- The docs' own comparison table. The devenv CLI has these; Flakes do NOT:
  - designed for developer environments
  - built-in container support
  - GC protection
  - lazy-tree faster evaluation
  - evaluation caching
  - pure evaluation (flakes are impure by default)
  - secretspec.dev
  - running processes when testing
  - Both have: external inputs, shared remote configs, cross-project references.
  - | /guides/using-with-flakes/ | current | OBS | released
  - Page text: flakes have "performance limitations and reduced features compared to the dedicated devenv CLI".
- Lock ownership: CLI mode uses `devenv.lock`, created or updated "when you use devenv on the project". Flake mode: "This will evaluate the inputs to your flake, create a flake.lock lock file". `devenv.yaml` is not read in flake mode (INF from the page; the docs never state it outright). Inputs and `nixConfig` go in `flake.nix`. | /pinning/ ; /guides/using-with-flakes/ | current | OBS plus INF
- `devenv update [NAME]` updates `devenv.lock` from `devenv.yaml` inputs. `devenv update nixpkgs-multiverse` refreshes one input. `devenv inputs add <name> <url> --follows <input>` edits `devenv.yaml`. 2.1 fixed a new input forcing a re-fetch of all inputs. | `devenv update --help`; /pinning/ ; release v2.1 | current | OBS | released
- Input URL forms (same as Nix flakes): `github:`, `gitlab:`, `git+ssh://`, `git+https://`, `git+file://`, `hg+*`, `sourcehut:`, `tarball+https://`, `path:`, `file+https://`, `file:///`. `git://` is not listed. `path:` inputs "don't respect .gitignore and will copy the entire directory to the Nix store"; the docs suggest `git+file` instead. `flake: false` is supported (default true). `follows` accepts `base-project/nixpkgs` style nested names. | /inputs/ ; /reference/yaml-options/ | current | OBS | released
- 2.2 fixed `path:` input edits not taking effect, and GitHub inputs failing when git `insteadOf` rewrites to SSH. | release v2.2 | 2.2 | OBS
- `devenv-nixpkgs` rolling: default `inputs.nixpkgs.url: github:cachix/devenv-nixpkgs/rolling`. Default `git-hooks` input `github:cachix/git-hooks.nix` is shown on /inputs/, but 2.0 removed it from the defaults (see unconfirmed). | /inputs/ ; /reference/yaml-options/ | current | OBS
- Other `devenv.yaml` keys: `nixpkgs.allow_unfree`, `permitted_unfree_packages`, `permitted_insecure_packages`, `allow_broken`, `allowlisted_licenses`, `blocklisted_licenses`, `cuda_support`, `per_platform`, `inputs.<n>.overlays`, `impure`, `clean`, `shell`, `strict_ports`, `backend`, `profile`, `secretspec.*`. Nix-side `overlays = [...]` is also supported. | /reference/yaml-options/ ; /overlays/ | current | OBS | released

## 5. Hosts, paths, secrets

- No host inventory, named paths or drive-identity feature was found. Closest items:
  - `target.host`, plus `profiles.hostname.<name>` for activating config by machine hostname.
  - Disk selection happens only inside the NixOS disko config (`/dev/disk/by-id/...`).
  - `.machines/<name>/facter.json` per host holds disk IDs and MACs; the docs say to commit it.
  - | /machines/ ; /profiles/ | 2.4 | OBS (absence) plus INF
- SecretSpec ships bundled (secretspec 0.7.2 in 2.0, 0.17.0 by 2.2). `secretspec.toml` declares `[profiles.<name>]` with keys. Selection: `--secretspec-provider`, `--secretspec-profile`, `secretspec.{enable,provider,profile}` in `devenv.yaml`, or `SECRETSPEC_PROFILE` and `SECRETSPEC_PROVIDER`. Resolved secrets appear in `config.secretspec.secrets`. The docs recommend `secretspec run -- cmd` instead of putting secrets in the shell env. | /integrations/secretspec/ ; blog 2.0 ; release v2.2 | 2.0 | OBS | released
- Providers (from secretspec.dev/concepts/providers/): keyring, dotenv, env, file, SOPS (v0.17+, needs CLI), age, EJSON, 1Password, LastPass, Bitwarden, pass/gopass, Vault, OpenBao, AWS, GCP, Azure, systemd-credential, Kubernetes and more. Provider aliases and per-secret provider chains are supported. The page says "SOPS" support depends on the bundled CLI. 2.2 fixed SOPS being unavailable in the bundled CLI. | https://secretspec.dev/concepts/providers/ ; release v2.2 | 2.2 for SOPS in devenv | OBS | released (SecretSpec is a separate project)
- Machines pair SecretSpec with sops-nix: bootstrap the age key via `install.secrets`, then sops-nix handles later rotation. | /machines/ | 2.4.0 | OBS | experimental

## 6. Services vs processes

- Services are "a higher-level abstraction over processes": pre-configured interfaces for existing software. Documented services (sidebar): adminer, blackfire, caddy, cassandra, clickhouse, cockroachdb, couchdb, dynamodb-local, elasticmq, elasticsearch, garage, httpbin, influxdb, kafka, keycloak, mailhog, mailpit, meilisearch, memcached, minio, mongodb, mosquitto, mysql, nats, nginx, nixseparatedebuginfod, opensearch, opentelemetry-collector, postgres, prometheus, rabbitmq, redis, rustfs, sqld, tailscale, temporal, tideways, trafficserver, typesense, varnish, vault, wiremock. State persists in `$DEVENV_STATE`. They start with `devenv up` (`-d` for background). | /services/ ; /processes/ | current | OBS | released
- The native process manager (Rust, default since 2.0) replaced process-compose. It provides `after` dependencies with `@ready`-style suffixes, restart policies, ready probes (exec, http, notify), socket activation, watchdog, file watching, automatic port allocation, Linux capabilities, `devenv processes list/start/stop/restart/logs`, and `devenv up -d` / `devenv down`. Alternatives selected with `process.manager.implementation`: process-compose, overmind, mprocs, hivemind, honcho. | /processes/ ; blog 2.0 ; /guides/migrating-to-20/ | 2.0 | OBS | released
- Converting devenv services or processes into systemd units or machine services: NOT documented. systemd is mentioned only for compatible readiness (`NOTIFY_SOCKET`), socket-activation and watchdog protocols, and in `wantedBy` as an analogy. The Machines page never maps `services.*` or `processes.*` into a `nixos` role. | /processes/ ; /tasks/ ; /machines/ | - | OBS (absence)
  - INF: a machine's NixOS role is evaluated separately from the dev-shell config, so you would set `services.postgresql` in the NixOS module yourself.
- Containers: `devenv container build/copy/run <name>` (needs `nix2container` and `mk-shell-bin` inputs). Predefined `shell` and `processes` containers. | /containers/ | current | OBS | released

## 7. Caching

- `cachix.pull` (list, default `[ "devenv" ]`), `cachix.push` (name or null; it is also added to pull), and `cachix.enable`. Integration is described as "seamless integration with binary caches hosted by Cachix". Auth: `CACHIX_AUTH_TOKEN`, the Cachix CLI file, or SecretSpec (`secretspec.cachix_auth_token: true` or a custom secret name, 2.2). Push is often put in `devenv.local.nix` for CI. | /binary-caching/ ; reference/options ; release v2.2 | current | OBS | released
- Trusted users: devenv registers `cachix.pull` caches as substituters with their keys. "On a multi-user install ... the Nix daemon ... only accepts substituters and keys requested by users listed in trusted-users" or from `trusted-substituters`. Otherwise it silently builds locally. Check with `nix store info` (`Trusted: 1`). Alternative: add `extra-substituters` and `extra-trusted-public-keys` to the daemon config. | /binary-caching/ | current | OBS | released
- Generic substituters: no dedicated devenv option exists. Only Cachix-named caches are wired. `--nix-option NAME VALUE` passes raw Nix settings, and the daemon config or `nixConfig` (flake mode) covers generic caches. | CLI help; /binary-caching/ ; cachix.nix source | current | OBS plus INF
- Attic: the docs mention no Attic support (grep of all fetched docs found nothing). Issue #1539 "Support custom binary caches" (asks for push to Attic and others) is still OPEN. | `gh issue view 1539 -R cachix/devenv` | open | OBS
- devenv does not assume GitHub for inputs (it supports many URL schemes). It does default to Cachix for cache integration and to `github:cachix/devenv-nixpkgs/rolling` for nixpkgs. | /inputs/ ; /binary-caching/ | current | INF

## 8. Testing

- `devenv test` builds the env and runs `enterTest`. Processes and services are started and stopped automatically. `devenv.isTesting` lets a config differ under test. The helper `wait_for_port <port> <timeout>` is provided. `enterTest` runs `.test.sh` if it exists. `--override-dotfile` uses a temporary `.devenv`. 2.4 fixed `devenv shell` wrongly running test setup. 2.1 fixed orphaned processes after test failures. | /tests/ ; `devenv test --help` ; releases | current | OBS | released
- Git hooks: `git-hooks.hooks.<id>.enable`, custom hooks via `entry`, `files`, `types`. Hooks run in `devenv test` ("Verify formatting in CI: Run devenv test"). In a shell, `devenv:git-hooks:install` runs as an enterShell task and installs the hook. The generated config file is a symlink and need not be committed. 2.0 swapped `pre-commit` for `prek`. The `git-hooks` input must be added explicitly, and the `pre-commit-hooks` alias was removed. | /git-hooks/ ; /guides/migrating-to-20/ | 2.0 | OBS | released
- Tasks as test steps: a task with `before = [ "devenv:enterTest" ]` runs before tests. `devenv:enterTest` depends on `devenv:enterShell`. `devenv test` runs the graph in `all` mode, and `wantedBy = [ ]` on enterTest keeps shell entry from running it. | /tasks/ | 2.4 for the `wantedBy` fix | OBS | released
- `devenv-run-tests` (the repo's test runner) reports closure sizes (2.3). | release v2.3 | 2.3 | OBS

## Could not confirm

1. Whether devenv ever reads `devenv.yaml` in flake mode (`mkShell` / flakeModule). The docs say neither yes nor no. The comparison table implies no.
2. Whether a repo imported through an input can bring its own inputs. #2205 is open, and the 1.10 post says input imports load only Nix config. The latest docs repeat that remote inputs are unsupported for yaml imports. I did not test this.
3. Whether `git://` URLs work as input URLs. They are not listed. `git+https`, `git+ssh`, `git+file`, `path:` and `flake: false` are listed.
4. Docs inconsistency: /inputs/ says the default `devenv.yaml` includes `git-hooks`, but the 2.0 release notes and migration guide say it was removed from the defaults.
5. Local second-disk install through `machines install`. It is undocumented. I did not test it, and testing could destroy disks.
6. A documented `lib.mkDefault` layering convention across `devenv.nix`, `devenv.local.nix` and profiles. None found. The mechanism is the module system plus profile priorities.
7. A shared-module convention across devenv, NixOS and home-manager. None documented. My composition advice is an inference from the machines.nix source.
8. Whether `machines.<name>.nixos` accepts a list of modules. The option type is "unspecified". The example is a single module or a function, and `imports` inside it should work.
9. Any devenv-to-systemd conversion of services. None found.
10. Exact introduction version of hostname/user profiles. They appear in the 1.9 blog; the docs gave no finer detail.
11. Pinned module rev `fe20b5...` was not compared with the 2.4.0 reference. The reference page is for main (it reports `latestVersion` 2.4.0).
12. WebFetch's summarizer wrongly claimed that `install` has a `--yes` flag. I verified against the raw page and `devenv machines install --help`: there is no such flag. `--yes` exists only on `deploy` and `apply`.
