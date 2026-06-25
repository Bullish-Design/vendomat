# vendomat devenv module — point a repo's uv at the prebuilt wheelhouse so its native
# dependencies install as ready-made wheels instead of being recompiled per repo.
#
# In a consuming devenv.yaml:
#
#   inputs:
#     vendomat:
#       url: git+file:///home/andrew/Documents/Projects/vendomat
#   imports:
#     - vendomat/modules
#
# and in devenv.nix:
#
#   vendor.enable = true;
#   vendor.libs   = [ "pyjutsu" ];   # install-only; never build these from source
{ pkgs, lib, config, inputs, ... }:

let
  cfg = config.vendor;
  system = pkgs.stdenv.system;
  wheelhouse = inputs.vendomat.packages.${system}.wheelhouse;

  # A repo never vendors itself: the lib's own source repo keeps editable `maturin develop`.
  # Expressed via `vendor.self` rather than read from config.env.PROJ — reading config.env
  # here would self-recurse, since this module also *defines* env entries.
  vendoredLibs = lib.filter (l: l != cfg.self) cfg.libs;
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

    sharedCargo = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        For repos that still compile Rust (the source libs themselves): route builds through
        sccache and a single shared CARGO_TARGET_DIR, instead of a multi-GB target/ per clone.
      '';
    };
  };

  config = lib.mkIf cfg.enable (lib.mkMerge [
    {
      # uv treats the wheelhouse as an extra package source. `pyjutsu>=0.8` in a consumer's
      # pyproject now resolves to the prebuilt cp313-abi3 wheel sitting here.
      env.UV_FIND_LINKS = "${wheelhouse}";

      tasks."vendor:status".exec = ''
        echo "vendomat wheelhouse: ${wheelhouse}"
        ls -1 ${wheelhouse}
        echo "install-only libs: ${lib.concatStringsSep " " vendoredLibs}"
      '';
    }

    # Safety latch: forbid uv from building these from source. A missing/mismatched wheel
    # then fails loudly instead of silently falling back to a from-scratch maturin compile.
    (lib.mkIf (vendoredLibs != [ ]) {
      env.UV_NO_BUILD_PACKAGE = lib.concatStringsSep " " vendoredLibs;
    })

    (lib.mkIf cfg.sharedCargo {
      packages = [ pkgs.sccache ];
      enterShell = ''
        export RUSTC_WRAPPER="${pkgs.sccache}/bin/sccache"
        export CARGO_TARGET_DIR="''${XDG_CACHE_HOME:-$HOME/.cache}/bullish/cargo-target"
        mkdir -p "$CARGO_TARGET_DIR"
      '';
    })
  ]);
}
