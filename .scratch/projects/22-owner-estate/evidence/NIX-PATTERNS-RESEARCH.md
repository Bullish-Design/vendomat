# Upstream practice: multi-host Nix, Home Manager, flake composition — 2026-10-13

<!--
Provenance: written by a subagent from web research.
All sources were fetched or searched on 2026-10-13.
Some fetches returned only page summaries. Items marked "unverified" have no primary source.
-->

**Rule for this file.** A documented upstream fact is evidence about the upstream tool. It is never a passed gate. No claim here proves that a vendomat or devman gate passes.

## 1. Repository structure patterns

### Widely agreed

- Match the structure to the size of the config. One thread concluded that 1-2 hosts may not justify an elaborate structure. Most voices warned against early over-design. https://discourse.nixos.org/t/how-do-you-structure-your-nixos-configs/65851
- flake-parts is the common flake module layer. It mirrors the flake schema. Ecosystem modules add the opinions. https://flake.parts and https://community.flake.parts/nixos-flake
- snowfall-lib is a weak choice now. Its README has a call for maintainers and says it is "effectively unmaintained for some time now". It builds on flake-utils-plus. https://github.com/snowfallorg/lib

### Maturity and lock-in, by tool

- **Dendritic pattern.** Every non-entry file is a top-level module. Each file implements one feature across all classes (NixOS, Home Manager, darwin). Files share values through the top-level config, not through `specialArgs`. The pattern is "merely a pattern", not a library. It usually runs on flake-parts. It also works with plain `lib.evalModules`. `import-tree` imports the files. The author lists anti-patterns: `specialArgs` pass-through, many named low-level modules, and overuse of `enable` options. https://github.com/mightyiam/dendritic and https://discourse.nixos.org/t/the-dendritic-pattern/61271
  - Code lock-in is low, because the files are plain modules. The cost is the mental model (`deferredModule`, flake-parts).
- **ez-configs.** A flake-parts module. It builds nixos, darwin, and Home Manager configs from the directory layout. It has one maintainer. https://github.com/ehllie/ez-configs
- **nixos-unified** (formerly nixos-flake). A flake-parts module. It unifies NixOS, darwin, and Home Manager. It has an activation app that works over SSH. https://community.flake.parts/nixos-flake
- **flakelight.** An alternative to flake-parts with less boilerplate. https://discourse.nixos.org/t/flakelight-a-new-modular-flake-framework/32395
- **blueprint (numtide).** One thread poster recommended it as a standard folder structure. The thread gives little detail. https://discourse.nixos.org/t/how-do-you-structure-your-nixos-configs/65851
- **haumea.** Unverified. No current maintenance evidence found.

### Contested or opinion

- "Cleanest today" for multi-class fleets: the dendritic pattern has the most momentum. The 65851 thread says it "appears gaining traction for multi-host, multi-OS setups". Supporters cite locality of behaviour. https://discourse.nixos.org/t/the-dendritic-pattern-in-response-to-comments-in-how-to-define-the-default-package-for-a-nixos-module-in-a-nix-flake/77326
- Critics say the pattern adds overhead and confuses new users. One critic calls such frameworks "substitutes for our poor documentation". Critics say it pays off mainly when one person manages several module systems at once. Same thread.
- Inference (not sourced): standalone Home Manager removes most of the dendritic benefit, because the NixOS half and the Home Manager half no longer share files. A light version fits better. Put shared Home Manager modules in a `homeModules` output. Keep the NixOS side a plain list of imports.

## 2. Home Manager standalone vs module

### Widely agreed

- Standalone is the documented choice for users who want to manage the home directory apart from the system. The module form builds user profiles during `nixos-rebuild`. https://nix-community.github.io/home-manager/nix-flakes.html
- Module form: every user change needs `nixos-rebuild`, so it needs sudo. The `home-manager` CLI is unavailable. Standalone needs a bootstrap step and a separate `home-manager switch`. https://discourse.nixos.org/t/what-is-the-recommended-way-to-use-home-manager-in-nixos/78319 and https://discourse.nixos.org/t/need-help-assembling-home-manager-configuration/78447
- Module form gives the `osConfig` argument and the `home-manager.backupFileExtension` option. Standalone takes the backup extension as a flag (`-b backup`). https://discourse.nixos.org/t/what-is-the-recommended-way-to-use-home-manager-in-nixos/78319
- Profile paths. Default and standalone: `~/.nix-profile`. With `home-manager.useUserPackages = true` (module form): `/etc/profiles/per-user/$USER`. The session variables file moves with it: `$HOME/.nix-profile/etc/profile.d/hm-session-vars.sh` or `/etc/profiles/per-user/$USER/etc/profile.d/hm-session-vars.sh`. In module form the default activation unit is `home-manager-$USER.service`. https://nix-community.github.io/home-manager/installation/nixos.html
- `useGlobalPkgs` exists only in module form. It saves one nixpkgs evaluation and removes the `NIX_PATH` dependency. With it on, set overlays and nixpkgs config at the system level. https://nix-community.github.io/home-manager/installation/nixos.html and https://nix-community.github.io/home-manager/nix-flakes.html
- Standalone has no shared pkgs. nixpkgs comes from the Home Manager flake input. Inference: keep that input aligned with the system input yourself, for example with `follows`.
- Rollback. Standalone keeps its own Home Manager generations, apart from the system. Unverified: no primary source. One user complained of too many generations in module form. https://tech.aufomm.com/my-nixos-journey-home-manager/
- Linger. NixOS has the option `users.users.<name>.linger`. It keeps the user manager running after logout, so services start at boot. Put it in the NixOS half. https://discourse.nixos.org/t/adding-nixos-option-for-systemd-user-lingering/28762
- Home Manager is often the better owner of user services. NixOS-installed user units do not restart on `nixos-rebuild switch`. https://wiki.nixos.org/wiki/Systemd/User_Services
- Secrets with sops-nix. The Home Manager module is a subset of the system module. It runs as a systemd user service named `sops-nix`, not as an activation script. It decrypts to `$XDG_RUNTIME_DIR/secrets.d` and links at `$HOME/.config/sops-nix/secrets`. Standalone needs `home.homeDirectory` set and an age key the user can read. The key cannot have a password. A service that reads a secret needs `After = [ "sops-nix.service" ]`. https://github.com/Mic92/sops-nix
- `home-manager.inputs.nixpkgs.follows` removes the compatibility assumption between Home Manager and the nixpkgs revision. The manual says to use it carefully, especially on unstable. https://nix-community.github.io/home-manager/nix-flakes.html

### Contested or opinion

- Using both forms for one user. The thread advice is to commit to one form. The thread says a mix "creates configuration conflicts and requires unsupported workarounds". https://discourse.nixos.org/t/need-help-assembling-home-manager-configuration/78447
- Inference (not sourced): write shared Home Manager modules against `config`, `lib`, and `pkgs` only. Export them as `homeModules.*`. Guard any `osConfig` use. Import them from `homeConfigurations.<user>@<host>`. To avoid two Home Managers on one user, never import the Home Manager NixOS module on a host that uses standalone.
- Inference: the headless server needs a one-time manual age key bootstrap per machine.

## 3. Composing many flakes

### Widely agreed

- Without `follows`, the input graph is a tree. Each encounter of the same flake makes a separate node. This produces duplicate nixpkgs nodes. The fix is `inputs.<x>.inputs.nixpkgs.follows = "nixpkgs"`. A follows path is slash-separated, for example `dwarffs/nixpkgs`. https://nix.dev/manual/nix/2.28/command-ref/new-cli/nix3-flake.html and https://docs.clan.lol/guides/nixpkgs-flake-input
- Tools that find or fix duplicates:
  - `nix-melt` views `flake.lock` in a terminal. https://docs.rs/nix-melt/
  - `nix-auto-follow` rewrites the lock so all references to a dependency share one node. https://fzakaria.com/2024/07/31/automatic-nix-flake-follows
  - `flake-checker` checks that nixpkgs inputs are recent and on a supported branch. It accepts CEL policies. https://determinate.systems/tools/nix-flake-checker/
  - A manual check also works: read `flake.lock` for repeated nixpkgs entries.
- Local sources. `path:` copies the whole directory. `git+file:` includes only files known to git and warns on a dirty tree. https://nix.dev/manual/nix/2.28/command-ref/new-cli/nix3-flake.html
- `--override-input <name> path:/abs/dir` redirects an input for one command. It works on `nix build` and `nixos-rebuild`. With a dirty overridden input, Nix does not write the lock file. https://discourse.nixos.org/t/workflow-for-developing-multiple-related-flakes/16291 and https://discourse.nixos.org/t/i-there-a-nixos-rebuild-flake-redirect/73918
- Inference from standard Nix semantics (no source fetched): a `flake = false` input is a plain source tree. It has no inputs of its own, so it adds no duplicate nodes.

### Contested or opinion

- Monorepo or many flakes for personal modules. No authoritative source found. Unverified. Inference: many flakes give each tool its own lifecycle. A monorepo gives one lock and no cross-repo `follows`.

## 4. Stable paths for devenv imports

### Widely agreed (documented by devenv)

- `imports` accepts relative paths, absolute paths, and input references. In `devenv.yaml`, a path that starts with `/` resolves from the git repository root, not from the filesystem root. Local imports merge both `devenv.nix` and `devenv.yaml`. Input imports load Nix only. https://devenv.sh/blog/2025/10/07/devenv-110-monorepo-nix-support-with-devenvyaml-imports/ and https://devenv.sh/composing-using-imports/
- Consequence: a machine-absolute path in `devenv.yaml` `imports` does not mean what it seems to mean. The documented way to share a module is to declare it as a `path:` input and import it. https://devenv.sh/composing-using-imports/
- Since devenv 2.2, changes to files in a local `path:` input are picked up automatically. Same page.
- A `path:` input copies the whole directory to the store and ignores `.gitignore`. The docs recommend `git+file` instead. https://devenv.sh/inputs/
- `devenv.local.nix` and `devenv.local.yaml` mirror the shared files. They are not meant for git. https://devenv.sh/files-and-variables/
- `follows` in `devenv.yaml` can reuse inputs from another devenv project, for example `follows: base-project/nixpkgs`. https://devenv.sh/inputs/
- Home Manager can place a file at a fixed user path with `xdg.dataFile`. The path stays stable. The symlink target changes on each `home-manager switch`. This is standard Home Manager behavior. No source fetched.

### Unverified

- Whether a Nix path literal such as `imports = [ /home/u/.local/share/x/mod.nix ]` in `devenv.nix` evaluates under devenv 2.x. devenv 2.0 uses the Nix C API, and its docs do not state purity rules. https://devenv.sh/blog/2026/03/05/devenv-20-a-fresh-interface-to-nix/
- Pure flake evaluation rejects such paths with "access to the absolute path ... is forbidden in pure evaluation mode". https://discourse.nixos.org/t/using-home-file-name-source-in-pure-evaluation-mode/65770
- Test on the exact devenv version before design depends on it.
- The devenv 2.0 migration guide did not mention purity or imports. https://devenv.sh/guides/migrating-to-20/

## 5. Personal tools through Home Manager and registries

### Widely agreed

- Home Manager is the usual way to install user programs declaratively. `nix profile` has no equivalent of `nix-env --set`. Mixing `nix profile` with Home Manager causes conflicts, for example with the old `home-path`. https://wiki.nixos.org/wiki/Home-manager and https://discourse.nixos.org/t/installing-home-manager/46689
- The registry has four layers: global, system (`/etc/nix/registry.json`, set by `nix.registry` on NixOS), user (`~/.config/nix/registry.json`), and command-line `--override-flake`. https://nix.dev/manual/nix/2.28/command-ref/new-cli/nix3-registry.html
- The system and user registries do not resolve flake references inside `flake.nix`. They resolve references on the command line only. Same page. A registry name therefore cannot replace an input in a project flake.
- Home Manager can write the user registry with `nix.registry`. The value is an attribute set, not a string. A config can point it at its own flake inputs, so the registry matches the lock. https://discourse.nixosstag.fcio.net/t/how-to-make-nix-shell-use-my-home-manager-flake-input/29957
- `nix registry pin` pins a name to the current revision. https://nix.dev/manual/nix/2.22/command-ref/new-cli/nix3-registry-pin

### Contested or opinion

- Inference (not sourced): deliver tools as Home Manager packages on PATH, plus modules at a fixed data path. Use the registry for ad hoc `nix run` and `nix shell` only.

## Open items

1. Test the devenv absolute-path import on the installed devenv version (section 4).
2. Find a primary source for standalone Home Manager rollback behavior (section 2).
3. Check haumea maintenance if the design considers it (section 1).
