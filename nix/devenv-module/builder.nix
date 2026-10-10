# The face builder (DESC-002, DESC-003, VMOD-013, VMOD-014, VMOD-015).
#
# It reads each flake input's `vendomat` description and builds three modules: devenv, NixOS, and
# Home Manager. Every option sits under `vendomat.libs.<name>` (FACE-005). Nothing changes until
# `enable = true` (FACE-002). A library needs no Vendomat input to be described (MOD-013).
#
# This file depends on `inputs` and `self` only, never on `config`, so a module's `imports` can use it.
{ lib, self, inputs }:
let
  # Inputs the builder never reads. `self` here is the Vendomat flake. The infrastructure inputs are
  # imported by the machine layer itself, and their default modules are not Vendomat faces (VMOD-017).
  skipNames = [ "self" "devenv" "nixpkgs" "disko" "home-manager" "sops-nix" ];

  candidates = lib.filterAttrs
    (n: i: !(lib.elem n skipNames) && (i.outPath or null) != self.outPath)
    inputs;

  # A hand-written library marks itself `vendomat = { name = "<name>"; faces = "hand"; }`. Only a marked
  # input has its `devenvModules.default`, `nixosModules.default`, and `homeManagerModules.default`
  # imported (VMOD-018). A flake that merely exports `nixosModules.default` is never imported: such a
  # module need not follow FACE-005, and it may declare options that a host imports by hand.
  isMarkedHand = i: (i ? vendomat) && (i.vendomat.faces or null) == "hand";
  hasDescription = i: (i ? vendomat) && !(isMarkedHand i);
  hasDevenvFace = i: (i ? devenvModules) && (i.devenvModules ? default);
  hasNixosFace = i: (i ? nixosModules) && (i.nixosModules ? default);
  hasHomeFace = i: (i ? homeManagerModules) && (i.homeManagerModules ? default);

  described = lib.filterAttrs (_: hasDescription) candidates;
  markedHand = lib.filterAttrs (_: isMarkedHand) candidates;

  handKeys = [ "name" "faces" ];
  checkedHand = lib.mapAttrs
    (n: i:
      let
        d = i.vendomat;
        extra = lib.subtractLists handKeys (lib.attrNames d);
      in
      if !(d ? name) then
        throw "vendomat: input '${n}' marks hand-written faces with no `name`."
      else if !(builtins.isString d.name && validName d.name) then
        throw "vendomat: input '${n}': name ${builtins.toJSON d.name} must match [a-z][a-z0-9-]*."
      else if extra != [ ] then
        throw "vendomat: input '${n}' (library '${d.name}') marks hand-written faces and also exports ${lib.concatStringsSep ", " extra}. Export a description or hand-written faces, not both."
      else d)
    markedHand;
  handWritten = markedHand;

  allowedKeys = [ "name" "packages" "options" "service" "extra" ];

  validName = n: builtins.match "[a-z][a-z0-9-]*" n != null;

  # Fail with the input name. A description is data from another repository, so check it before use.
  checked = inputName: d:
    let
      unknown = lib.subtractLists allowedKeys (lib.attrNames d);
    in
    if !(d ? name) then
      throw "vendomat: input '${inputName}' exports a vendomat description with no `name`."
    else if !(builtins.isString d.name && validName d.name) then
      throw "vendomat: input '${inputName}': description name ${builtins.toJSON d.name} must match [a-z][a-z0-9-]*."
    else if !(d ? packages) then
      throw "vendomat: input '${inputName}' (library '${d.name}') has no `packages` in its description."
    else if unknown != [ ] then
      throw "vendomat: input '${inputName}' (library '${d.name}'): unknown description key(s) ${lib.concatStringsSep ", " unknown}; allowed: ${lib.concatStringsSep ", " allowedKeys}."
    else d;

  checkedAll = lib.mapAttrs (n: i: checked n i.vendomat) described;

  byName = lib.groupBy (x: x.name) (
    (lib.mapAttrsToList (n: d: { input = n; name = d.name; }) checkedAll)
    ++ (lib.mapAttrsToList (n: d: { input = n; name = d.name; }) checkedHand));
  clashes = lib.filterAttrs (_: l: lib.length l > 1) byName;

  validated =
    if clashes != { } then
      throw "vendomat: two inputs use the same library name:\n${lib.concatStringsSep "\n" (lib.mapAttrsToList (name: l: "  name '${name}': inputs ${lib.concatMapStringsSep ", " (x: "'${x.input}'") l}") clashes)}"
    else checkedAll;

  # Build the three modules of one described library.
  mkLibModules = inputName: d:
    let
      name = d.name;
      hasService = d ? service;
      optionsFor = lib': withService:
        let own = (d.options or (_: { })) lib'; in
        if own ? enable || own ? service
        then throw "vendomat: input '${inputName}': description options must not define `enable` or `service`. Vendomat defines them."
        else own
          // { enable = lib'.mkEnableOption "the ${name} library"; }
          // lib'.optionalAttrs (withService && hasService) { service.enable = lib'.mkEnableOption "the ${name} service"; };
      extraFor = args: (d.extra or (_: { })) args;
      # One script puts the library packages on PATH, then runs the description's `exec` (DESC-003).
      launcher = pkgs: cfg: pkgs.writeShellScript "${name}-start" ''
        export PATH=${lib.makeBinPath (d.packages pkgs)}:$PATH
        exec ${(d.service { inherit pkgs cfg; }).exec}
      '';

      homeManager = { config, lib, pkgs, ... }:
        let
          cfg = config.vendomat.libs.${name};
          ex = extraFor { inherit cfg pkgs lib; };
        in
        {
          options.vendomat.libs.${name} = optionsFor lib true;
          config = lib.mkIf cfg.enable (lib.mkMerge [
            { home.packages = d.packages pkgs; }
            (lib.optionalAttrs hasService (lib.mkIf cfg.service.enable {
              systemd.user.services.${name} = {
                Unit.Description = "${name} (Vendomat)";
                Service.ExecStart = "${launcher pkgs cfg}";
                Install.WantedBy = [ "default.target" ];
              };
            }))
            (ex.homeManager or { })
          ]);
        };

      nixos = { config, lib, pkgs, options, ... }:
        let
          cfg = config.vendomat.libs.${name};
          ex = extraFor { inherit cfg pkgs lib; };
        in
        {
          options.vendomat.libs.${name} = optionsFor lib true;
          config = lib.mkMerge [
            (lib.mkIf cfg.enable (lib.mkMerge [
              { environment.systemPackages = d.packages pkgs; }
              (lib.optionalAttrs hasService (lib.mkIf cfg.service.enable {
                systemd.services.${name} = {
                  description = "${name} (Vendomat)";
                  wantedBy = [ "multi-user.target" ];
                  serviceConfig.ExecStart = "${launcher pkgs cfg}";
                };
              }))
              (ex.nixos or { })
            ]))
            # The Home Manager face rides along only when the host imports the Home Manager NixOS module.
            (lib.optionalAttrs (options ? home-manager) { home-manager.sharedModules = [ homeManager ]; })
          ];
        };

      devenv = { config, lib, pkgs, ... }:
        let
          cfg = config.vendomat.libs.${name};
          ex = extraFor { inherit cfg pkgs lib; };
        in
        {
          options.vendomat.libs.${name} = optionsFor lib false;
          config = lib.mkIf cfg.enable (lib.mkMerge [
            { packages = d.packages pkgs; }
            (lib.optionalAttrs hasService { processes.${name}.exec = (d.service { inherit pkgs cfg; }).exec; })
            (ex.devenv or { })
          ]);
        };
    in
    { inherit devenv nixos homeManager; };

  built = lib.mapAttrs mkLibModules validated;

  loc = n: what: m: lib.setDefaultModuleLocation "inputs.${n}.${what}" m;
in
{
  inherit built handWritten checkedHand;

  # Module lists for `imports` (devenv) and for each host (NixOS).
  devenvImports =
    (lib.mapAttrsToList (n: i: loc n "devenvModules.default" i.devenvModules.default)
      (lib.filterAttrs (_: hasDevenvFace) handWritten))
    ++ (lib.mapAttrsToList (n: m: loc n "vendomat (devenv)" m.devenv) built);

  nixosImports =
    (lib.mapAttrsToList (n: i: loc n "nixosModules.default" i.nixosModules.default)
      (lib.filterAttrs (_: hasNixosFace) handWritten))
    ++ (lib.mapAttrsToList (n: m: loc n "vendomat (nixos)" m.nixos) built);

  # Hand-written Home Manager faces ride along through the NixOS module, as built ones do.
  homeManagerShared =
    lib.mapAttrsToList (n: i: loc n "homeManagerModules.default" i.homeManagerModules.default)
      (lib.filterAttrs (_: hasHomeFace) handWritten);
}
