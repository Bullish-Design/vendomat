# vendomat devenv module — point a repo's uv at the prebuilt wheelhouse, deliver the
# shared command toolchain, and install usage-gated dependency knowledge.
#
# TWO DELIVERY SHAPES, ONE FILE (project 039).
#
#   * Machine delivery (the target): the machine's NixOS module installs this file at
#     `/run/current-system/sw/share/vendomat/consumer-module.nix` and the central
#     overlay imports it. The consumer repository declares no vendomat flake input.
#     The store paths come from `machine.json`, which the same package installs
#     beside this file.
#   * Input delivery (the compatibility fallback): a repository still imports
#     `vendomat/modules` through its own devenv.yaml input. Kept for one release.
#
# REPOSITORY-SCOPED SETTINGS COME FROM `vendomat.toml`.
#
# The module reads `${config.devenv.root}/vendomat.toml` with `builtins.fromTOML`.
# An absent file means every default. The option declarations below stay for one
# release as a compatibility fallback: the fallback keeps the migration reversible
# without making the compatibility option part of the new interface.
#
#   [vendor]              Face A — vendored native wheels
#   enable = true
#   libs = [ "pyjutsu" ]  install-only; never build these from source
#   self = "pyjutsu"      the lib this repo IS; excluded from `libs`
#   noBuild = false       forbid uv from building `libs` from source
#   sharedCargo = true    sccache + one shared CARGO_TARGET_DIR
#
#   [vendor.publish]
#   enable = true         install the pre-push publisher when vendomat.toml exists
#
#   [toolchain]           Face D — the shared command closure
#   enable = true
#   mode = "store"        "store" or "editable"
#   roster = "core"
#
#   [knowledge]           Face B — per-dependency knowledge skills
#   enable = false
#   skillsDir = ".claude/skills"
{ pkgs, lib, config, inputs, ... }:

let
  # --- the machine closure -------------------------------------------------
  # The NixOS module installs this JSON manifest beside this file. It names the
  # wheelhouse, the CLI, the toolchain closure, and the vendor knowledge tree, so
  # this module resolves the same store paths the machine pins. It reads no flake
  # input.
  machineManifestPath = "/run/current-system/sw/share/vendomat/machine.json";
  machine =
    if builtins.pathExists machineManifestPath then
      # `readFile` of a real store path attaches that path as the string's context.
      # `fromJSON` then tries to re-attribute that single context entry to every
      # embedded store-path-shaped substring it finds — cli/toolchain/vendor_root/
      # wheelhouse each name a DIFFERENT derivation than machine.json's own, so it
      # refuses with "is not allowed to refer to a store path". Discard the context
      # first: the parsed values are consumed as plain path strings below (some are
      # not store paths at all, e.g. `cli`), never as derivations needing context.
      builtins.fromJSON (builtins.unsafeDiscardStringContext (builtins.readFile machineManifestPath))
    else
      null;
  hasInput = inputs ? vendomat;

  # --- the repository manifest ---------------------------------------------
  repoManifestPath = "${config.devenv.root}/vendomat.toml";
  repoManifest =
    if builtins.pathExists repoManifestPath then
      builtins.fromTOML (builtins.readFile repoManifestPath)
    else
      { };

  # Read one dotted path from the manifest, falling back when it is absent. TOML
  # has no null, so a present key always supplies the value.
  lookup = attrs: path:
    lib.foldl'
      (current: part: if builtins.isAttrs current && current ? ${part} then current.${part} else null)
      attrs
      (lib.splitString "." path);
  fromManifest = path: fallback:
    let value = lookup repoManifest path; in
    if value == null then fallback else value;

  # The resolved settings: the manifest wins, the compatibility option is next,
  # the option default is last.
  vendorEnable = fromManifest "vendor.enable" config.vendor.enable;
  vendorLibs = fromManifest "vendor.libs" config.vendor.libs;
  vendorSelf = fromManifest "vendor.self" config.vendor.self;
  vendorNoBuild = fromManifest "vendor.noBuild" config.vendor.noBuild;
  vendorSharedCargo = fromManifest "vendor.sharedCargo" config.vendor.sharedCargo;
  publishEnable = fromManifest "vendor.publish.enable" config.vendor.publish.enable;
  toolchainEnable = fromManifest "toolchain.enable" config.vendor.toolchain.enable;
  toolchainMode = fromManifest "toolchain.mode" config.vendor.toolchain.mode;
  toolchainRoster = fromManifest "toolchain.roster" config.vendor.toolchain.roster;
  knowledgeEnable = fromManifest "knowledge.enable" config.knowledge.enable;
  knowledgeSkillsDir = fromManifest "knowledge.skillsDir" config.knowledge.skillsDir;

  # A repo never vendors itself: the lib's own source repo keeps editable
  # `maturin develop`. Expressed via `vendor.self` rather than read from
  # config.env.PROJ — reading config.env here would self-recurse, since this
  # module also *defines* env entries.
  vendoredLibs = lib.filter (l: l != vendorSelf) vendorLibs;

  # --- the store paths -----------------------------------------------------
  # Machine delivery and input delivery name the same artifacts. The machine
  # manifest wins; the flake input is the compatibility fallback.
  system = pkgs.stdenv.system;
  machineValue = key:
    if machine != null then machine.${key}
    else throw ("vendomat consumer module: machine manifest " + machineManifestPath + " lacks the '" + key + "' field");

  wheelhouse =
    if machine != null then machineValue "wheelhouse"
    else if hasInput then inputs.vendomat.packages.${system}.wheelhouse
    else throw noClosure;

  vendomatCli =
    if machine != null then machineValue "cli"
    else if hasInput then inputs.vendomat.packages.${system}.vendomat
    else throw noClosure;

  # `vendomatCli` means two different shapes: input delivery names a PACKAGE (its
  # `bin/vendomat` is the executable, and `packages = [ vendomatCli ]` puts it on
  # PATH); machine delivery names the EXECUTABLE ITSELF, `/run/current-system/sw/
  # bin/vendomat` — a stable machine path chosen so machine.json need not embed a
  # self-reference to the vendomat package it ships beside (flake.nix). That path
  # is not a store path, so it fails `types.package`'s check and must not go in
  # `packages` — it is already on every shell's PATH via the NixOS module's
  # `environment.systemPackages`. `vendomatBin` normalizes both shapes to the one
  # thing every call site actually wants: the executable to run.
  vendomatBin = if machine != null then vendomatCli else "${vendomatCli}/bin/vendomat";

  vendorRoot =
    if machine != null then machineValue "vendor_root"
    else if hasInput then "${inputs.vendomat}"
    else throw noClosure;

  toolchain =
    if machine != null then machineValue "toolchain"
    else if hasInput then inputs.vendomat.packages.${system}."repoman-toolchain-${toolchainRoster}"
    else throw noClosure;

  noClosure = ''
    vendomat consumer module: no machine closure and no vendomat flake input.
    The machine must install /run/current-system/sw/share/vendomat/machine.json
    (nix-meta imports vendomat's nixosModules.default), or the repository must
    still declare a vendomat input.
  '';
in
{
  options.vendor = {
    enable = lib.mkEnableOption "vendored native wheels from the Nix store";

    libs = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ "pyjutsu" ];
      description = ''
        Native libraries to install from the prebuilt wheelhouse instead of compiling.
        The lib named in `vendor.self` is excluded so a lib's own repo still builds editably.
      '';
    };

    self = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = ''
        Name of the library this repo *is* (if any). Excluded from `vendor.libs` so the
        source repo keeps its editable `maturin develop` build instead of vendoring itself.
      '';
    };

    noBuild = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Forbid uv from building `vendor.libs` from source (`UV_NO_BUILD_PACKAGE`).

        Off by default, and that inversion is deliberate. The store wheelhouse is an
        **accelerator**, not the source of truth: the artifact of record is the release URL
        a consumer declares in `[tool.uv.sources]`. When the store has no matching wheel,
        uv must fall back to that URL. That is not a silent fallback — the URL is the
        declaration.

        The old default made a missing or mismatched store wheel a hard resolution failure,
        which took down loci-core's devenv shell outright (gitman project 32, G3). Turn this
        on only in a repo that has no declared URL to fall back to.
      '';
    };

    sharedCargo = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        For repos that still compile Rust (the source libs themselves): route builds through
        sccache and a single shared CARGO_TARGET_DIR, instead of a multi-GB target/ per clone.
      '';
    };

    # Face D — deliver the shared command closure. Namespaced under `vendor` rather
    # than `repoman` because Vendomat may not assume RepoMan's module is present;
    # when it IS present, store mode exports REPOMAN_TOOLCHAIN_BIN for RepoMan.
    toolchain = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = ''
          Deliver the shared RepoMan command closure. ON by default: importing Vendomat
          IS the opt-in (CONCEPT 03 §6, phase 4).

          Setting this false omits the shared command closure. To develop a tool in its
          own repo, use `mode = "editable"` instead; that is a supported mode.
        '';
      };

      mode = lib.mkOption {
        type = lib.types.enum [ "store" "editable" ];
        default = "store";
        description = ''
          Where the manager commands come from (CONCEPT 03 §3.1).

          "store"    — the pinned Nix closure. The normal consumer path.
          "editable" — nothing is delivered and RepoMan's provider is left alone, so the
                       repo's own venv/checkout wins. This is what a TOOL AUTHOR wants:
                       in gitman's own repo, `gitman` must run the working tree, not an
                       older store build. First-class, never an error.
        '';
      };

      roster = lib.mkOption {
        type = lib.types.str;
        default = "core";
        description = ''
          Which roster closure to take: `packages.repoman-toolchain-<roster>`. A roster is
          added only once every tool in it builds, resolves to /nix/store, and passes its
          own doctor (CONCEPT 03 §6).
        '';
      };
    };

    publish.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        Install Vendomat's pre-push publisher when this repo declares vendomat.toml. The hook
        publishes GitHub-source commits from a disposable worktree and leaves local sources alone.
      '';
    };
  };

  # Face B — knowledge: install per-dependency SKILL.md's into this repo, gated on the deps it
  # actually uses. Independent of `vendor.enable` (Face A); a repo can take either or both.
  options.knowledge = {
    enable = lib.mkEnableOption "per-dependency knowledge skills (usage-gated SKILL.md install)";

    skillsDir = lib.mkOption {
      type = lib.types.str;
      default = ".claude/skills";
      description = ''
        Where `dep-<lib>/SKILL.md` skills install (flat siblings of repoman/devman's skills).
        An externally-set REPOMAN_SKILLS_DIR wins over this default, keeping vendomat aligned
        with repoman's skills home when both are present.
      '';
    };
  };

  config = lib.mkMerge [
    # A manifest typo must fail loudly. `toolchain.mode` misses an invalid value
    # silently otherwise, because the two `mkIf` branches below would both be false.
    {
      assertions = [
        {
          assertion = toolchainMode == "store" || toolchainMode == "editable";
          message = "vendomat: toolchain.mode must be \"store\" or \"editable\", got ${builtins.toJSON toolchainMode}.";
        }
        {
          assertion = builtins.isList vendorLibs && builtins.all builtins.isString vendorLibs;
          message = "vendomat: vendor.libs must be a list of library names.";
        }
        {
          assertion = builtins.isString toolchainRoster && toolchainRoster != "";
          message = "vendomat: toolchain.roster must be a non-empty string.";
        }
      ];
    }

    # --- Face A: vendored native wheels -------------------------------------------------------
    (lib.mkIf vendorEnable (lib.mkMerge [
      {
        # uv treats the wheelhouse as an *additional* package source, ranked alongside the
        # release URL a consumer declares. Both name the same bytes — the wheelhouse builds
        # the manylinux artifact that `vendomat publish` uploads — so either route satisfies
        # the same `uv.lock` hash, and a store miss costs a download, not a failure.
        env.UV_FIND_LINKS = "${wheelhouse}";

        tasks."vendor:status".exec = ''
          echo "vendomat wheelhouse: ${wheelhouse}"
          ls -1 ${wheelhouse}
          echo "install-only libs: ${lib.concatStringsSep " " vendoredLibs}"
        '';
      }

      # Opt-in latch, off by default. See `vendor.noBuild` for why the store must not be
      # able to fail a resolution that the declared release URL can satisfy.
      (lib.mkIf (vendorNoBuild && vendoredLibs != [ ]) {
        env.UV_NO_BUILD_PACKAGE = lib.concatStringsSep " " vendoredLibs;
      })

      (lib.mkIf vendorSharedCargo {
        packages = [ pkgs.sccache ];
        enterShell = ''
          export RUSTC_WRAPPER="${pkgs.sccache}/bin/sccache"
          export CARGO_TARGET_DIR="''${XDG_CACHE_HOME:-$HOME/.cache}/bullish/cargo-target"
          mkdir -p "$CARGO_TARGET_DIR"
        '';
      })
    ]))

    # --- Face B: per-dependency knowledge -----------------------------------------------------
    (lib.mkIf knowledgeEnable {
      # The CLI is a Nix-built package, never the consumer's venv (DESIGN issue #3). Input
      # delivery needs the package added to PATH; machine delivery already has it on every
      # shell's PATH via the NixOS module, and `vendomatCli` there is not a package at all
      # (see `vendomatBin`'s comment) — adding it here would fail `types.package`.
      packages = lib.optional (machine == null) vendomatCli;

      # The knowledge tree is the vendomat source already in the store — not bundled into the wheel.
      env.VENDOMAT_VENDOR_ROOT = "${vendorRoot}/vendor";

      # Opt-in install. Run it after the consumer's deps resolve (so uv.lock/pyproject is readable)
      # — e.g. after `repoman-sync`. Mirrors repoman-sync's resolve-then-install ordering.
      scripts.vendor-sync = {
        description = "Install per-dependency knowledge skills for the deps this repo uses (vendomat sync).";
        exec = ''
          export REPOMAN_SKILLS_DIR="''${REPOMAN_SKILLS_DIR:-${knowledgeSkillsDir}}"
          exec ${vendomatBin} sync
        '';
      };

    })

    # --- Face D: the shared command closure ---------------------------------------------------
    # Editable mode delivers NO PACKAGE: a tool's own repo keeps running its working tree.
    # That is why the guard is on the mode as well as `enable`.
    (lib.mkIf (toolchainEnable && toolchainMode == "store") (lib.mkMerge [
      {
        # On PATH for the interactive shell. The env var below is what TASKS use: a task
        # must not depend on PATH state (repoman D1), and `command -v` would let an
        # unrelated venv shadow a selected shared tool (CONCEPT 03 §4.1).
        packages = [ toolchain ];
        env.REPOMAN_TOOLCHAIN_BIN = "${toolchain}/bin";
        env.REPOMAN_TOOLCHAIN_MANIFEST = "${toolchain}/share/vendomat/toolchain.json";

        # Answers "where did this command come from?" without a guess. Read-only, and NOT
        # on the shell-entry path: a broken status check took loci-core's devenv down once
        # (gitman project 32, G3), so this is a task the user runs, not an enterShell hook.
        tasks."vendor:toolchain:status".exec = ''
          echo "toolchain: ${toolchain}"
          cat ${toolchain}/share/vendomat/toolchain.json
          echo
          ls -1 ${toolchain}/bin
        '';
      }

    ]))

    # This is independent of Face A and Face B: a manifest is the explicit per-repository opt-in.
    # `install-hook` is a no-op failure when no manifest exists and refuses to overwrite another
    # hook, which keeps importing the module safe for every devenv consumer.
    (lib.mkIf publishEnable {
      packages = lib.optional (machine == null) vendomatCli;
      enterShell = ''
        if [ -f vendomat.toml ]; then
          ${vendomatBin} install-hook
        fi
      '';
    })
  ];
}
