<!-- Raw final report of Agent B (devenv GitHub roadmap, sonnet), 2026-10-09. Extracted unedited from the agent transcript. Model output: an observation here is the agent's claim, not a Vendomat gate. -->

Research on devenv changes that could break or obsolete Vendomat V5. All data comes from live `gh` and web sources, read 2026-10-09. I changed nothing except scratch files in /tmp.

Status key: RELEASED means in a tag up to v2.4.0 (2026-09-24), or merged before the pinned modules rev. PLANNED means an open PR, open issue, or milestone. EXPERIMENTAL means merged but flagged in the docs.

Basis for the status facts:
- Releases: `gh release list`. CHANGELOG.md and `docs/src/content/docs/**` on main (main is 17 commits ahead of v2.4.0).
- Pinned modules rev fe20b5c is dated 2026-09-29 and is 17 commits ahead of v2.4.0.
- Milestones: only "2.4" (open) and "2.5" (open, items #2863 and #1010). No milestone has a due date. No 3.0 milestone exists, and GitHub Discussions are disabled.
- Entry format below: `#N | title | state | dates | target | summary | how known`. URL pattern is `https://github.com/cachix/devenv/pull/N` or `/issues/N`.

## (a) Machines (NixOS, home-manager, nix-darwin)

- #3073 | devenv machines | MERGED, EXPERIMENTAL | opened 2026-08-07, merged 2026-09-24 | v2.4.0 | `machines.<name>` with roles `nixos`, `nix-darwin`, `home-manager`. Commands: info, check, plan, apply, deploy, status, rollback, install. Uses disko, nixos-facter and kexec. | v2.4.0 release notes, docs/machines.md ("Experimental... may change before stable").
- #2092 | Support configurations: nixos/home-manager/nix-darwin | MERGED | 2025-08-11 to 2025-09-18 | v1.9-era | Earlier `configurations` option. It now survives only as a rename alias to `machines`. | PR body; machines.md "Reference".
- #3255 | fix(machines): prevent nix copy from hanging on fresh SSH connections | MERGED 2026-10-08 | CHANGELOG "2.4.1 (unreleased)" | Fixes #3254. CLI only (`machines.rs`), so the installed 2.4.0 CLI still hangs. Trigger: `devenv machines install` with no open SSH connection, at the disko upload step. | PR file list; CHANGELOG.
- #3242 | Machines: non-root SSH with sudo for NixOS | OPEN, PLANNED (a question) | 2026-09-30 | none | The docs say "NixOS deployment and installation require root SSH." There is no maintainer reply yet. | Issue and docs.
- #3226 | Feedback devenv machines - flake configurations | OPEN | 2026-09-25 | none | Users ask for `machines.<name>` to accept an already-composed `nixosConfigurations.*`, `darwinConfigurations.*` or `homeConfigurations.*`. domenkozar only suggests `nixos = inputs.systems.nixosModules.server;`, i.e. a module from an input. | Issue thread.
- #3232 | feat: Allow deploy time secrets | OPEN, PLANNED | 2026-09-28 | none | Proposes `machines.<n>.deploy.secrets`, refreshed on every deploy. Today SecretSpec secrets are written only by `install`. | Issue.
- Source facts from `src/modules/machines.nix` on main:
  - `machine.nixos` has type `nullOr unspecified`. devenv builds the system itself with `inputs.nixpkgs` and injects `disko.nixosModules.disko`, `recovery.nix` and `facts.nix`. It passes `specialArgs = { inputs, self }`.
  - The disko input is required for every NixOS machine, even a deploy-only one.
  - home-manager uses `inputs.nixpkgs.legacyPackages`.
  - Rollback exists for NixOS only. nix-darwin and home-manager have none.
  - Machines do not accept a prebuilt system.
- Roadmap statement: domenkozar posted on NixOS Discourse (https://discourse.nixos.org/t/devenv-2-4-machines/80271, post #15, 2026-09-28). He says a plugin system will come "probably after devenv 3". He says he is splitting tools out (secretspec, Casita). On deploy-rs: "it's tied to flakes" (post #7).

## (b) Cross-repository imports, outputs, exporting modules

- #2205 | Allow importing devenv.yaml from inputs | OPEN | 2025-10-07 | none | Today an imported project's `devenv.yaml` is not evaluated; only its `devenv.nix` is. The docs warn about this in guides/polyrepo.mdx. | Issue and doc caution.
- #3055 | feat: compose devenv.yaml from remote inputs | OPEN PR, PLANNED | 2026-07-31, last activity 2026-10-06 | none | Fixes #2205. Remote `devenv.yaml` files are loaded recursively. The importer's `devenv.lock` stays the single lock; imported lockfiles are not merged. Root wins on duplicate inputs, and a shared `nixpkgs` reuses the root one. No maintainer review yet; the author asked for one. | PR body and comments.
- #3167 | fix(cli): load YAML from remote --from sources | OPEN PR | 2026-09-08 | none | Remote `--from` sources load their `devenv.yaml`, `devenv.local.yaml`, imports and inputs. Adds an out-of-tree devenvs guide. | PR.
- #3096 | merge devenv.yaml of a --from flake reference | OPEN draft PR | 2026-08-16 | none | A flake-reference `--from` is fetched like `path:`. The reference is no longer recorded in `devenv.lock`; the PR says to pin it with an explicit rev. | PR body.
- RELEASED, v2.0: `inputs.<name>.devenv.config.<opt>` for polyrepo references (VersionCompatibility 2.0, polyrepo.mdx). Release v2.2 added `--from` bindings via `devenv allow`, with profiles persisted (release notes; blog 2026-07-28). v2.2 also fixed transitive `imports` dropping directories.
- #2521 | Profiles don't work with cross-project references | OPEN | 2026-02-24 | none | Documented as a caution in polyrepo.mdx.
- #2219 | Sharing devenv.lock in monorepos | OPEN | 2025-10-14 | none | There is no way to inherit a parent's pins. The workaround is `follows`.
- No convention exists for exporting devenv, NixOS or home-manager modules from one repo. The documented route is `imports: [input/path]`, which merges `devenv.nix`. Modules exposed as flake `nixosModules` are consumed by `machines.*.nixos` only through `inputs.<x>.nixosModules.<y>` (#3226).

## (c) Flake integration and lock ownership

- RELEASED, v2.0: native CLI is the default path. devenv uses a C FFI to Nix (blog 2026-03-05). Docs call the flake route a lesser one (guides/using-with-flakes.md "reduced features"). `devenv.lock` is the native lock.
- #2610 | Enable native process manager for flake integration users | OPEN PR | 2026-03-12 | none | The native manager does not work through `devenv.lib.mkShell`; the process manager falls back to process-compose when `cli.version` is null. | PR body.
- #1418 | devenv.flakeArgs to avoid --no-pure-eval | OPEN PR (2024-09-05). #2539 | flake-parts `nix fmt` and `flake check` | OPEN PR (2026-03-03). #2223 | standard-nix wrapper | OPEN PR (2025-10-15).
- #3101 | Build failure with inputs.nixpkgs.follows on recent nixpkgs (nix 2.35 boost patch conflict) | OPEN | 2026-08-18 | none | Hits a flake that takes devenv as an input and follows a recent nixpkgs. The failure is in boost, below nix-util 2.35.2.
- #3244 | fix(bootstrap): reuse locked inputs already in the store | OPEN PR | 2026-10-01 | none | `devenv shell` currently fails if a locked input's remote is unreachable, even when the store already holds it. | PR body.
- No source says flake or flake-parts support will be dropped. I searched issues, docs and code for "remove flake", "drop flake" and "deprecate flakes" and found nothing. There is no plan for a new lock format.
- The only dated deprecation: the 2.0 blog says "devenv 0.x is now deprecated. Support will be dropped entirely in devenv 3." The text does not define "0.x"; I read it as the old module and CLI lifecycle. No 3.0 date exists. #2901 ("Initialize from shell.nix/flake.nix") and #404 ("local flake.nix as input", open since 2023) are open.

## (d) Inputs fetching

- docs/inputs.md lists github, gitlab, `git+ssh`, `git+https`, `git+file`, hg, sourcehut, tarball, `path:`. Plain `git://` is not listed.
- RELEASED, v2.2: GitHub inputs resolve over SSH when git `insteadOf` rewrites HTTPS to SSH (fix of #2842). v2.2 also fixed local `path:` edits not invalidating the eval cache. v2.1: `imports` no longer override the base `inputs` (#2728). v2.1: adding one input no longer re-fetches all others (#2688).
- #1637 | Evaluation caching doesn't work for git+ssh inputs | OPEN since 2024-12-08. Not verified against 2.x.
- Default `nixpkgs` is `github:cachix/devenv-nixpkgs/rolling`, per docs/inputs.md and yaml-options. I found no announced change to this default. `git-hooks` is listed as a default input in inputs.md, but the 2.0 breaking-change notes say it is optional now, so the docs disagree.
- `machines.nix` has a special path because devenv-nixpkgs lacks `lib.nixosSystem`. It rebuilds the evaluator from `inputs.nixpkgs.inputs.nixpkgs-src`. A nixpkgs input that is not devenv-nixpkgs works via `lib.nixosSystem`.
- Docs advise `follows: nixpkgs` when adding disko, home-manager and nix-darwin.
- #2258 (input-of-input pins, OPEN) and #2262 (`devenv inputs develop`, OPEN, 2025-11-05) are open.

## (e) Profiles, hostname and user profiles, devenv.local

- RELEASED, v1.9: profiles, with priority tiers: base < hostname < user < `--profile`. Profiles can use `extends`. v2.2.1 fixed profiles overriding package-valued options without `mkForce`. v2.2 and v2.2.1 persist profiles with `devenv allow`.
- machines.md says there are no machine tags or groups. Use profiles, e.g. `devenv --profile staging machines deploy`.
- #2177 | auto-activate profiles by folder | OPEN (2025-09-23). #2521 as above.
- `devenv.local.nix` and `devenv.local.yaml` exist. v2.3 fixed `--from` loading the current directory's `devenv.local.nix` (release notes). #3167 would load a remote source's `devenv.local.yaml`.

## (f) Secrets

- RELEASED, v2.4.0: `machines.*.install.secrets` and `install.secretspec` (execution local or target) write bootstrap files only at install. Docs say to use sops-nix or agenix for runtime secrets. Release v2.2: SecretSpec 0.17 and `secretspec.cachix_auth_token`. v2.2.x exports `SECRETSPEC_PROFILE` and `SECRETSPEC_PROVIDER`.
- #3232 as above (OPEN). #3220 | uv private-registry credentials via secretspec | OPEN (2026-09-25).
- #3247, #3248, #3249 | OPEN PRs (2026-10-03) keeping SecretSpec `as_path` files alive for print-dev-env, exec'd commands and detached process managers. They fix files being deleted too early.
- #2875 | fnox as alternative backend | CLOSED (2026-05-26).

## (g) Caching

- Cachix is built in. Docs mention only Cachix: `cachix.pull` and `cachix.push`. Release v2.3.1 re-fetched public signing keys (#3178, merged 2026-09-11). Fixes of Cachix netrc handling and duplicate substituters landed in v2.2 and v2.3.1.
- #1539 | Support custom binary caches (Attic) | OPEN since 2024-10-17, with repeated "deal breaker" comments and no maintainer response. Attic is named in the issue body.
- #3175 | `cachix.pull` substituters never reach the Nix daemon on multi-user installs | OPEN | 2026-09-10 | none | devenv sets substituters only in its own process. Docs now say a user outside `trusted-users` silently builds locally.
- #3116 | Adopt devenv-cache-action as official action | OPEN (2026-08-24).
- No generic-substituter option exists in devenv.yaml (checked the yaml-options headings). `devenv build machines.<name>` is documented as a way to fill a cache.

## (h) Services and processes as systemd units

- RELEASED, v2.0: the native Rust process manager is the default. It supports sd_notify readiness, a watchdog, socket activation and Linux capabilities. Process-compose is opt-in. v2.3 added a localhost process proxy (off by default) and `processes.<n>.shutdown`.
- No source says devenv services become systemd units on machines. Only the `machines.*.deploy.healthCheck` and rollback service are systemd-based on the target. #3232 mentions restarting units for secrets. #614 (microvm as processes) is open.
- Open and unreleased: #3221 (run tasks after the manager stops, PR, 2026-09-25), #2978 (process-compose lifecycle commands, PR), #2890 (interactive-shell start, draft PR), #3245 (opt-in nono sandbox in devenv.yaml, PR, 2026-10-01). #1010 (sandbox issue) sits in milestone 2.5 alongside #2863.

## (i) Testing and git-hooks

- RELEASED, v2.0: the `git-hooks` input is optional and must be added to devenv.yaml. `pre-commit` was replaced by `prek`. `devenv test` is in the CLI; the flake route lacks process start in tests. v2.4.0: `devenv shell` no longer runs test setup (#3184).
- OPEN: #3168 (`devenv test` exits 0 when a declared process fails to start), #2881 (derivations as tests), #2463 (native task integration for git-hooks), #2511 (prek worktree logic).
- `devenv-run-tests` can fail on closure size via `max_closure_size` (v2.3).
- Breaking: `devenv tasks run` default mode became `before` (v2.1). `devenv build` outputs JSON (v2.0). Task names containing `::` are rejected (2.4.1, unreleased).

## (j) Deprecations and breaking changes

- v2.0 breaking: `git-hooks` not default, `container --copy` removed, `build` returns JSON, native process manager default.
- v2.2 breaking: x86_64-darwin dropped; the shell hook detects projects by `devenv.nix` only; `devenv init` no longer creates `.envrc`.
- v2.1: `require_version` added in devenv.yaml.
- "devenv 0.x deprecated, dropped in devenv 3" (2.0 blog). A plugin system is "probably after devenv 3" (Discourse post #15).
- v2.4.0 notes: process-manager metadata stays compatible and "no public Nix options changed".

## Top risks for a design that generates flake.nix, reads devenv.yaml inputs from a private git:// collection, uses mkModules (devenv/nixos/homeManager faces), and keeps NixOS machines in a separate nix-meta flake

1. **`devenv machines` overlaps the nix-meta flake and wants to own machine composition.**
   - What changes: `machines.<n>.nixos` takes a module, not a `nixosConfiguration`, and devenv injects disko and its own modules.
   - Evidence: `machines.nix`; #3226 (maintainer answer is "port it", or pass `nixosModules`); Discourse post #7.
   - Mitigation: expose each NixOS machine as `nixosModules.<m>` from nix-meta and reference it as `machines.<m>.nixos = inputs.nix-meta.nixosModules.<m>`.
   - Caveat: the module must tolerate the injected disko, facts and recovery modules. A module that already imports disko or uses an incompatible `system` can break.
2. **The Machines interface is explicitly experimental and moving fast.**
   - Evidence: 2.4.0 on 2026-09-24; five machines items in 15 days (#3073, #3254, #3255, #3242, #3232); docs say the interface "may change".
   - Pinned modules fe20b5c lack the #3255 fix, and the installed 2.4.0 CLI hangs on install without an open SSH connection.
   - Sub-risks: root SSH is mandatory for NixOS (#3242); `machines install` wipes disks with no confirmation prompt, where Vendomat's own rules differ; disko is mandatory even for deploy-only hosts.
3. **Remote `devenv.yaml` composition is not released.**
   - Today an imported project's `devenv.yaml` is ignored (#2205, polyrepo.mdx). If a design depends on collection-provided `devenv.yaml` inputs flowing into consumers, it will not work on 2.4.0. #3055 would change the semantics: root wins, no merged locks. It has no maintainer review (#3055, #3167, #3096).
4. **Lock ownership stays with devenv.lock. A generated flake.nix is a second lock.**
   - `devenv.lock` is native and stays the single graph under #3055. The flake route is documented as second-class: no native process manager (#2610), `--no-pure-eval` or a `devenv.root` hack, no eval cache. Consuming devenv as a flake input with `nixpkgs.follows` breaks on recent nixpkgs (#3101).
   - I found no plan to remove flakes. I also found no flake-first plan.
5. **Private `git://` inputs.**
   - `git://` is not a documented scheme (inputs.md lists `git+ssh`, `git+https`, `git+file`). Eval caching with git+ssh is a known open bug (#1637, not verified on 2.x). Release v2.2 changed GitHub-over-SSH resolution. #3244 shows `devenv shell` failing offline even for locked inputs. Check the exact fetch scheme in a fixture on the pinned tools before relying on it.
6. **Cache assumptions.**
   - Docs and tooling assume Cachix. Attic or other substituters have no first-class option (#1539 open, no maintainer comment). On multi-user Nix, `cachix.pull` substituters do not reach the daemon (#3175). Vendomat should configure Attic through Nix config itself, not devenv.
7. **Module export conventions and cross-project profiles.**
   - There is no convention for exporting devenv, NixOS and home-manager faces from one repo. `inputs.<x>.devenv.config` references ignore the consumer's profiles (#2521). `machines.*.home-manager` and `nixos` use devenv's `inputs.nixpkgs`. A different nixpkgs in the collection can produce version skew; follow the doc's `follows nixpkgs` advice.
8. **Secrets.**
   - SecretSpec covers install-time bootstrap only. Deploy-time secrets are still a proposal (#3232). Runtime secrets are left to sops-nix or agenix. Three `as_path` lifetime PRs are pending (#3247–#3249).
9. **Deprecation horizon.**
   - "0.x dropped in 3" (2.0 blog) and a plugin system after 3 (Discourse) imply a possible 3.0 break. Nothing concrete is announced. Use `require_version` to pin the CLI.

## What I could not confirm

- A roadmap page or RFC for 3.0 or 2.5. The 2.5 milestone has only #2863 and #1010. I did not fetch devenv.sh/roadmap, and my web searches found none. Discussions are disabled on GitHub.
- What the "devenv 0.x" deprecation covers.
- Whether plain `git://` or private git hosts work as input URLs on 2.4.0, and whether #1637 still reproduces.
- Whether the modules rev fe20b5c is exactly what the CLI resolves for Vendomat's pinned inputs (I compared dates and commit distance only).
- Whether #3055, #3167 or #3096 will merge or ship in 2.5. Any maintainer reply on #3242 or #3232. Whether a prebuilt-system option comes to Machines.
- Whether any 2.x setting makes devenv itself use nixpkgs `nix.settings` substituters (not found in yaml-options, not tested).
- The Discourse thread was read through a summarizing fetch, so the quoted statements are paraphrased. Check posts #7 and #15 directly.
