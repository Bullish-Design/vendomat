# mkPypiWheel — install one published PyPI wheel as a Nix Python package.
#
# `mkPythonCli` resolves every runtime dependency through a name -> nixpkgs attribute
# table, and throws on an unmapped name. Its own doctrine says what to do when nixpkgs
# cannot supply one: "it gets a derivation of its own and an entry pointing at it."
# This is the builder for that derivation.
#
# It installs the PUBLISHED wheel rather than building from source, for the same reason
# `pyjutsu-package` does: the wheel is the artifact of record, the build already happened
# once at the publisher, and a nix build cannot reach the network to repeat it. A pure
# Python wheel is `py3-none-any`; a native one must be an abi3 manylinux wheel, which
# carries no store RUNPATH and needs only the manylinux-permitted libraries.
#
# Every caller states WHY the dependency is here — nixpkgs carries no such package, or
# carries a version the consumer's own metadata rejects. Without that, the next reader
# cannot tell an entry that is still needed from one nixpkgs has since caught up with.
#
# It takes a python PACKAGE SET (`py`), not an interpreter, because every entry belongs to
# an overlay: a standalone derivation that pins `idna` while the rest of the closure still
# resolves nixpkgs' `idna` produces two of them, and buildPythonPackage refuses a closure
# with a duplicate distribution. Overriding the set instead rebuilds every dependent
# against the pinned version, so there is only ever one.
{ pkgs, py }:

{ pname
, version
  # The wheel's own filename on PyPI. Kept verbatim: the installer parses the basename for
  # the distribution metadata, and a store path prefixes it with a hash, which is not a
  # valid wheel filename. So the file is copied back under this name before installing.
, filename
  # sha256 of that exact file, as PyPI reports it.
, hash
  # Runtime dependencies, as derivations.
, dependencies ? [ ]
  # Why nixpkgs cannot supply this. Required — see the header.
, reason
}:

assert reason != "";

let inherit (pkgs) lib; in

py.buildPythonPackage {
  inherit pname version dependencies;
  format = "other";

  # PyPI's modern download path is hash-derived and cannot be reconstructed from
  # metadata. The legacy layout — packages/<python tag>/<initial>/<dist>/<filename> —
  # still resolves, and every field of it is already in the filename, so nothing here
  # is restated by hand.
  src =
    let
      parts = lib.splitString "-" filename;          # dist-version-pytag-abi-platform.whl
      dist = builtins.elemAt parts 0;
      pythonTag = builtins.elemAt parts 2;
    in
    pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/${pythonTag}/${builtins.substring 0 1 dist}/${dist}/${filename}";
      sha256 = hash;
    };

  dontUnpack = true;
  nativeBuildInputs = [ py.pypaInstallHook ];

  installPhase = ''
    runHook preInstall
    mkdir -p dist
    cp "$src" "dist/${filename}"
    pypaInstallPhase
    runHook postInstall
  '';

  # The publisher tested it. Re-running a test suite here needs the dev extras and a
  # writable tree, and a third-party test failure must not block every consumer's shell.
  doCheck = false;

  passthru.pypiReason = reason;
}
