# mkMaturinWheel — build a maturin/PyO3 crate into a *wheel*, once, in the Nix store.
#
# The output ($out) is a directory containing a single built `.whl`. Nothing is installed;
# the wheel is an inert, content-addressed artifact that any number of repos can later
# install from (via UV_FIND_LINKS) without re-running cargo/maturin. This is the one place
# the expensive native compile happens.
#
#   mkWheel { pname = "pyjutsu"; src = inputs.pyjutsu; }
#     -> /nix/store/…-pyjutsu-0.8.0/pyjutsu-0.8.0-cp313-abi3-linux_x86_64.whl
{ pkgs, python }:

{ pname
, src
  # Version is cosmetic (store-path name only); maturin reads the real version from the
  # crate. Default: parse it out of the crate's Cargo.toml so bumps need no edit here.
, version ? (builtins.fromTOML (builtins.readFile "${src}/Cargo.toml")).package.version
}:

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
  ];

  buildPhase = ''
    runHook preBuild
    export HOME="$TMPDIR"            # cargo/maturin want a writable HOME
    maturin build \
      --offline \
      --release \
      --interpreter ${python}/bin/python3 \
      --out dist
    runHook postBuild
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
