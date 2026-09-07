# mkMaturinWheel — build a maturin/PyO3 crate into a *wheel*, once, in the Nix store.
#
# The output ($out) is a directory containing a single built `.whl`. Nothing is installed;
# the wheel is an inert, content-addressed artifact that any number of repos can later
# install from (via UV_FIND_LINKS) without re-running cargo/maturin. This is the one place
# the expensive native compile happens.
#
# The wheel this builder emits is the *published* artifact, not a second opinion about it:
# it carries a manylinux platform tag and no RUNPATH, so the same bytes install from the
# store and from a GitHub release. Two steps make that true, and both are silent when
# missed (gitman project 35, §G3):
#
#   1. `--compatibility <tag>` — without it maturin stamps the bare `linux_x86_64` tag,
#      which no ordinary Linux host accepts.
#   2. the crate's own `relocate_wheel.py` — maturin applies the tag on request but leaves
#      the extension's RUNPATH pointing into `/nix/store`, so the tag states something the
#      artifact does not keep.
#
#   mkWheel { pname = "pyjutsu"; src = inputs.pyjutsu; }
#     -> /nix/store/…-pyjutsu-0.20.0/pyjutsu-0.20.0-cp313-abi3-manylinux_2_39_x86_64.whl
{ pkgs, python }:

{ pname
, src
  # Version is cosmetic (store-path name only); maturin reads the real version from the
  # crate. Default: parse it out of the crate's Cargo.toml so bumps need no edit here.
, version ? (builtins.fromTOML (builtins.readFile "${src}/Cargo.toml")).package.version
  # The platform tag maturin stamps. `null` keeps maturin's default (bare `linux_x86_64`).
, compatibility ? "manylinux_2_39"
  # Crate-relative path to the relocation script. Reused from the crate, never reimplemented
  # here: the crate owns the definition of "portable" for its own extension.
, relocateScript ? "scripts/relocate_wheel.py"
}:

# A manylinux tag on a wheel that still carries a store RUNPATH is a false promise. Refuse
# to build that combination at eval time rather than publish it.
assert compatibility != null -> relocateScript != null;

pkgs.stdenv.mkDerivation {
  inherit pname version src;

  # Pre-fetch every crates.io dependency into the store so `maturin build` runs fully
  # offline inside the sandbox. Trivial for these libs — their Cargo.lock has no git deps.
  cargoDeps = pkgs.rustPlatform.importCargoLock {
    lockFile = "${src}/Cargo.lock";
  };

  nativeBuildInputs = [
    pkgs.maturin
    pkgs.cargo
    pkgs.rustc
    pkgs.rustPlatform.cargoSetupHook # consumes `cargoDeps`, wires cargo to the vendor dir
    python # fixes the abi3 interpreter / wheel tag
    # A crate may pin a faster linker in its committed `.cargo/config.toml` (pyjutsu sets
    # `-fuse-ld=mold` for the link-heavy jj-lib cdylib). That flag is applied to the release
    # build here too, so `mold` must be on PATH in the sandbox or the link fails with
    # `collect2: cannot find 'ld'`. Vend the linker the crates we build ask for.
    pkgs.mold
    # `relocate_wheel.py` shells out to patchelf to clear the RUNPATH.
    pkgs.patchelf
  ];

  buildPhase = ''
    runHook preBuild
    export HOME="$TMPDIR"            # cargo/maturin want a writable HOME
    # devenv exports `_PYTHON_HOST_PLATFORM=linux_x86_64`, which OVERRIDES --compatibility
    # and silently stamps the bare tag. Nothing sets it in the sandbox today; unset it so a
    # future impure build cannot reintroduce the bug.
    unset _PYTHON_HOST_PLATFORM
    maturin build \
      --offline \
      --release \
      --interpreter ${python}/bin/python3 \
      ${pkgs.lib.optionalString (compatibility != null) "--compatibility ${compatibility}"} \
      --out dist
    runHook postBuild
  '';

  # Strip the store RUNPATH from the built wheel, using the crate's own script.
  postBuild = pkgs.lib.optionalString (relocateScript != null) ''
    if [ ! -f "${relocateScript}" ]; then
      echo "mkMaturinWheel: ${pname} declares relocateScript=${relocateScript}, which the source tree does not carry" >&2
      exit 1
    fi
    for wheel in dist/*.whl; do
      ${python}/bin/python3 "${relocateScript}" "$wheel"
    done
  '';

  installPhase = ''
    runHook preInstall
    mkdir -p "$out"
    cp dist/*.whl "$out"/
    runHook postInstall
  '';

  # The crate's own `cargo test`/pytest suite is the source repo's job, not the wheel's.
  doCheck = false;
}
