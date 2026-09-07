# mkPythonCli — build one first-party CLI as a Nix Python application (Face D).
#
# CONCEPT 03 §3.3: a command must be a Nix Python application, not a copy inside a shared
# virtualenv. §8.1 names the mapping from `pyproject.toml` to Nix as the principal cost of
# this project, and warns that a per-tool ad hoc override approach becomes unmaintainable.
# So the mapping lives here, once:
#
#   * metadata (name, version, scripts, build backend) is READ from pyproject.toml, never
#     restated — a literal version in a nix file already drifted once in this repo;
#   * every runtime dependency is resolved through `depMap`, an explicit name -> nixpkgs
#     attribute table. An unmapped dependency THROWS, naming the tool and the dependency.
#     A Nix build may not reach the network, so the alternative to a throw is a build that
#     fails much later with a much worse message.
#
#   mkPythonCli { pname = "copyroom"; src = inputs.copyroom; }
#   mkPythonCli { pname = "gitman"; src = inputs.gitman; extraDeps = [ pyjutsu ]; }
{ pkgs, python }:

let
  inherit (pkgs) lib;
  py = python.pkgs;

  # PEP 503 normalisation, enough for a dependency head: "PyYAML" -> "pyyaml",
  # "pytest_json_report" -> "pytest-json-report".
  normalize = name: builtins.replaceStrings [ "_" "." ] [ "-" "-" ] (lib.toLower name);

  # PEP 508 head: "pydantic-ai-slim[openai]>=2,<3" -> "pydantic-ai-slim".
  requirementName = req:
    let m = builtins.match "[[:space:]]*([A-Za-z0-9._-]+).*" req;
    in if m == null then throw "mkPythonCli: unparseable requirement ${req}" else normalize (builtins.head m);

  # The only place a first-party CLI's third-party dependencies are named. Keep it sorted.
  # A dependency that nixpkgs does not carry is NOT added here with a guess — it gets a
  # derivation of its own and an entry pointing at it.
  defaultDepMap = {
    click = py.click;
    copier = py.copier;
    jinja2 = py.jinja2;
    pydantic = py.pydantic;
    pytest = py.pytest;
    pyyaml = py.pyyaml;
    ruff = pkgs.ruff;
    tomlkit = py.tomlkit;
    typer = py.typer;
    ty = pkgs.ty;
  };

  buildSystems = {
    "hatchling.build" = [ py.hatchling ];
    "setuptools.build_meta" = [ py.setuptools ];
  };
in

{ pname
, src
  # Extra runtime dependencies that are not third-party lookups — a Vendomat-built
  # derivation such as the pyjutsu wheel package, passed in by the caller.
, extraDeps ? [ ]
  # Additional or overriding name -> package entries, for a dependency this repo
  # materialises itself.
, depMap ? { }
  # Console scripts to DROP from the output. CONCEPT 03 §3.2 requires the roster closure to
  # fail on duplicate executable names; a generic script name (copyroom ships `demo`) would
  # be the first collision, and it is not part of the manager contract.
, excludeScripts ? [ ]
  # Dependency names to ignore. For a dependency that the CLI declares but does not import
  # at run time; state the reason at the call site.
, ignoreDeps ? [ ]
}:

let
  pyproject = builtins.fromTOML (builtins.readFile "${src}/pyproject.toml");
  project = pyproject.project;
  backend = pyproject.build-system.build-backend;

  table = defaultDepMap // depMap;
  ignored = map normalize ignoreDeps;

  resolve = req:
    let name = requirementName req;
    in
    if builtins.elem name ignored then null
    else table.${name} or (throw
      ''
        mkPythonCli: ${pname} depends on "${name}", which has no entry in depMap.
        Add it to lib/mkPythonCli.nix (nixpkgs carries it) or materialise a derivation
        for it first. A nix build cannot fetch it at build time.
      '');

  dependencies = extraDeps ++ (lib.filter (d: d != null) (map resolve (project.dependencies or [ ])));

  build-system = buildSystems.${backend} or (throw
    "mkPythonCli: ${pname} uses build backend \"${backend}\"; known: ${lib.concatStringsSep ", " (builtins.attrNames buildSystems)}");

  scripts = builtins.attrNames (project.scripts or { });
  kept = lib.subtractLists excludeScripts scripts;
in

python.pkgs.buildPythonApplication {
  inherit pname src dependencies build-system;
  # Read, never restated: a hand-written literal in this repo's flake drifted to 0.2.3 while
  # the source said 0.3.1, and every installed hook then named a wrong version.
  version = project.version;
  pyproject = true;

  # Tests run in each tool's own devenv (testee), not at nix-build time: they need the
  # tool's dev dependencies and a writable repo, and a first-party test failure must not
  # be able to block every consumer's shell.
  doCheck = false;

  postFixup = lib.optionalString (excludeScripts != [ ]) ''
    rm -f ${lib.concatMapStringsSep " " (s: "$out/bin/${s}") excludeScripts}
  '';

  passthru = {
    # What the roster closure joins on, and what the provenance manifest reports.
    commands = kept;
    pythonVersion = python.pythonVersion;
  };

  meta = {
    description = project.description or "${pname} — a first-party CLI";
    mainProgram = if builtins.elem pname kept then pname else lib.head (kept ++ [ pname ]);
  };
}
