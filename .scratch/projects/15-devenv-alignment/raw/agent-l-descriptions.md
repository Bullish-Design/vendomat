<!-- Raw final report of Agent L (modules built from library descriptions, sonnet), 2026-10-09. Extracted unedited from the agent transcript (longest hand-back). Raw log: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-l/. -->

AGENT L REPORT. devenv 2.4.0+b904dcb, nix 2.34.7, nixpkgs e7439b6b, devenv modules a5c34429, disko and home-manager follow nixpkgs, `hardware.facter = null`.
Raw log (every command with exact output): ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-l/cmds.log
Same dir: module-final.nix (full module), module-prototype-base.nix, vendomat-flake.nix, knappy-flake.nix and .lock, face-check.sh, q7-timing.txt, q3-both.txt, n2-build.json, fixture-workspace-N2/, env.sh.
Own git daemon on 127.0.0.1:39520 is stopped. The temp dir is removed. No sudo, no disks, `server` untouched. No VM was started. No `machines install|deploy|apply|rollback` was run.

The session was interrupted once. Before the cleanup I checked that the temp dir and daemon still existed. Work had already passed the point your message named, so I did not redo it.

**Q1 Builder.**
ANSWER: Yes to all four parts.
EVIDENCE:
- The builder is in the module (below). The import list depends only on `inputs` and `self`. Eval ran with no recursion.
- Excluded inputs: `self`, `devenv`, `nixpkgs`, and any input whose outPath equals `self.outPath`.
- Nothing enabled, shell derivation: workspace A has no library inputs. Workspace B has knappy and tool2 as inputs, disabled. Both were built in the same path, and `devenv build shell` gave `/nix/store/n0b0zbq4y0wcgqg92a4372qx70mq3q9c-devenv-shell` for A, B, A. (A first run in two different directories differed only by DEVENV_ROOT; I fixed that by using one path.)
- The same check with `--no-eval-cache` is in Q6 (face-check 1, shell PASS).
- Enabled (`knappy.enable = true; port = 9191`): `devenv shell` printed `knappy=/nix/store/vihmyy5x…-knappy/bin/knappy port=9191 extra=devenv tool2=none`.
- `devenv eval processes.knappy.exec` gave `"knappy serve --port 9191"`.
- `devenv up --detach` then `devenv processes list` gave `knappy ready restarts: 0`. `devenv processes logs knappy` showed `knappy serve --port 9191`. `devenv processes down` stopped it, and no `sleep 3600` was left.
- Both libraries enabled: both binaries are on PATH. `hello` (added only by tool2's `extra.nixos`) is absent from the devenv shell.
STATUS: PROVEN.

**Q2 Library has no Vendomat input.**
ANSWER: Yes.
EVIDENCE:
- `jq -c '.nodes|keys' flake.lock` gives `["nixpkgs","root"]`. `grep -c vendomat flake.lock` gives 0.
- `nix flake show --no-write-lock-file .` shows `packages … default: package 'knappy'` and `vendomat: unknown`.
- `nix eval --json .#vendomat.name` gives `"knappy"`.
- `nix flake check --no-build .` ends with `warning: unknown flake output 'vendomat'` and `all checks passed!`. The warning is harmless but it will show for every library.
- The workspace lock shows `.nodes.knappy.inputs = {"nixpkgs":["nixpkgs"]}`. Only the root node refers to `vendomat`.
STATUS: PROVEN.

**Q3 Fallbacks and conflicts.**
ANSWER: All three behave as specified.
EVIDENCE:
- Hand-written only (library `hand`, options at `vendomat.libs.hand.enable`): `devenv eval vendomat.libs env.HAND` gives `hand.enable true`, `env.HAND "on"`. The shell shows `HAND=on` next to knappy.
- Both a description and `devenvModules.default`: `error: vendomat: input(s) 'both' export both a \`vendomat\` description and \`devenvModules.default\`. Export one.` Exit 1.
- Same `name`: `error: vendomat: two inputs use the same library name:\n  name 'knappy': inputs 'dupname', 'knappy'`. Exit 1.
- Finding about my test method: an earlier run of the "both" case returned a stale success. Cause: I swapped same-size, same-mtime `devenv.yaml` files with `rsync -a` and kept `.devenv/`. The stale state survived even with `--no-eval-cache` (test P and Q in cmds.log). Fresh runs and all later runs (`.devenv/` wiped on each switch) error correctly. Why devenv does this: UNPROVEN. It is a risk for any tool that rewrites `devenv.yaml` fast, such as `vendomat sync`.
STATUS: PROVEN.

**Q4 NixOS and Home Manager targets.**
ANSWER: Both targets are built from the same descriptions. I chose the simplest placement:
- Both sides are set inside `vendomat.inventory.test.nixos`, which is a NixOS module.
- NixOS-side values: `vendomat.libs.knappy.*`, written directly in that module.
- User-side values: `home-manager.users.alice.vendomat.libs.knappy.*`, written inside that module.
- No new option is needed. The NixOS face adds the Home Manager face with `home-manager.sharedModules` when the host imports `home-manager.nixosModules.home-manager`.
EVIDENCE:
- Disabled, with 2 libraries as inputs: the toplevel is `/nix/store/gbibqyd1…-nixos-system-nixos-26.11.20261008.e7439b6`. It is identical to workspace A (no libraries). The drvPath is `114ys1jx…drv` in both.
- Disabled, details: `nix-store -qR` of the toplevel has 0 matches for knappy or tool2. There is no `sw/bin/knappy`. There is no knappy unit in `etc/systemd/system`. The values `systemd.services.knappy` and `home-manager.users.alice.systemd.user.services.knappy` are absent ("attribute … not found"). `systemPackages` and `home.packages` have 0 matches. `firewall.allowedTCPPorts = []`.
- NixOS enabled (N2: knappy enabled with port 9191 and `service.enable`, tool2 enabled): `sw/bin` has `hello knappy tool2`.
- N2 `systemd.services.knappy.serviceConfig.ExecStart` is `/nix/store/6czmaa8s…-knappy-start`, and `wantedBy = ["multi-user.target"]`.
- N2 built `etc/systemd/system/knappy.service` has `Description=knappy (Vendomat)`, `ExecStart=/nix/store/6czmaa8s…-knappy-start`, `WantedBy=multi-user.target`.
- N2 `knappy-start` content: `export PATH=/nix/store/vihmyy5x…-knappy/bin:$PATH` then `exec knappy serve --port 9191`. `etc/systemd/system/multi-user.target.wants/` has `knappy.service`.
- Home Manager side only (N3: HM `knappy.enable`, port 7070, `service.enable`; NixOS side off): `home.packages` contains `…-knappy`. `systemd.user.services.knappy.Service.ExecStart` is `…/zbxadnf9…-knappy-start`, with `Install.WantedBy = ["default.target"]`. Built `home-manager-files/.config/systemd/user/knappy.service` has `ExecStart=/nix/store/zbxadnf9…-knappy-start`, `Description=knappy (Vendomat)`. That script ends with `exec knappy serve --port 7070`. The NixOS side stays off: knappy `enable false`, no `systemd.services.knappy`, firewall `[]`.
- Options exist at `vendomat.libs.knappy.{enable,port,service.enable}` in NixOS and HM. In devenv: `enable` and `port` only.
UNPROVEN:
- I did not start the systemd units (no VM). I proved only the unit files and the ExecStart script.
- I did not test a host that does not import the Home Manager NixOS module. By construction it skips the HM face.
STATUS: PROVEN for evaluation and build. The running units are UNPROVEN.

**Q5 extra.**
ANSWER: Each `extra.<target>` lands only in its target. Lists merge.
EVIDENCE:
- knappy's `extra.nixos.networking.firewall.allowedTCPPorts = [cfg.port]` is absent from devenv and from HM. The devenv and HM evaluations succeed, though neither has a `networking.firewall` option, so the content did not leak.
- Devenv shell: `KNAPPY_EXTRA=devenv`. HM: `home.sessionVariables.KNAPPY_EXTRA = "home-manager"`. NixOS `environment.sessionVariables` has 0 KNAPPY_EXTRA matches.
- Merge in N2: `allowedTCPPorts = [9000, 9191]` (tool2 and knappy). `systemPackages` has `tool2`, `hello-2.12.3` (tool2 `extra.nixos`) and `knappy`.
- With the NixOS side off and HM on (N3), the NixOS firewall list stays `[]`. An HM enable does not turn on the NixOS `extra`.
STATUS: PROVEN.

**Q6 Inertness check.** `face-check.sh <workspace> <input> [host] [user]` is in the log dir. It evaluates the workspace with the library input and again without it, in the same path, using `--no-eval-cache`. It compares `shell.drvPath`, the NixOS toplevel drvPath, and the HM `home.activationPackage.drvPath`.
RESULTS:
- Check 1, knappy disabled: three PASS lines. Shell `np7cgy4z…devenv-shell.drv`, NixOS `114ys1jx…drv`, HM `fa10d8bg…home-manager-generation.drv`. Exit 0.
- Positive control (knappy enabled on the NixOS side): the NixOS drv becomes `7vhyc81m…` instead of `114ys1jx…`. The HM drv with HM-side knappy enabled becomes `7k156nn0…` instead of `fa10d8bg…`. The shell with knappy enabled differs (`l9cwd27m…` vs `n0b0z…`). So the comparison catches real changes. The script itself reported FAIL for the NixOS target with "without=EVAL-FAILED". Reason: the workspace sets `vendomat.libs.knappy.enable`, and that option vanishes when the input is removed. The check has to run on a workspace that does not set the library's options.
- Negative control (hand-written `leaky` module that sets `env.LEAKY` while disabled): `FAIL shell with=…f11zvv83… without=…k7if0izk…`, NixOS and HM PASS. Exit 1.
STATUS: PROVEN for devenv, NixOS and HM with knappy. Hand-written `nixosModules` and `homeManagerModules` are not imported by the builder, so the check does not cover them.

**Q7 Cost.** `devenv --no-eval-cache eval`, median of 5, ms. Raw runs in q7-timing.txt.

| Libraries (all described, disabled) | `shell.drvPath` | NixOS toplevel `.drvPath` |
|---|---|---|
| 0 (Vendomat module only) | 1143 | 9346 |
| 2 | 1181 | 9069 |
| 10 | 1187 | 9261 |
| 10, all enabled | 1582 | 9746 |

- Disabled libraries cost about 40 ms for the shell, and the NixOS differences are noise.
- Enabling 10 libraries adds about 400 ms to the shell and about 400 ms to NixOS.
- Each run excludes the one warm-up run that creates the lock.
STATUS: PROVEN.

**Changes to DESC-001's proposed shape**
1. `packages`: I wrote `self.packages.${pkgs.stdenv.hostPlatform.system}` instead of `pkgs.system`. I did not test `pkgs.system` here, so whether it warns on this nixpkgs is UNPROVEN.
2. `service` returns `{ exec }`, and the builder uses only `exec`. The builder wraps it in a `<name>-start` script that puts the library packages on PATH (systemd has no PATH for a bare `knappy`). Other keys from `service`, such as environment or user, are ignored. The spec should list which keys it allows.
3. `options` must not define `enable` or `service`. The builder throws if it does.
4. `service.enable` exists only in NixOS and HM. In devenv, an enabled library with a `service` gets the process `processes.<name>.exec` with no second switch. `service.enable` has effect only when `enable` is true.
5. `extra.<target>` is a plain attribute set of config. The builder wraps it in `mkIf cfg.enable`.
6. HM is attached through `home-manager.sharedModules`, only when the host imports the Home Manager NixOS module (`options ? home-manager`). The spec should say that the workspace imports `inputs.home-manager.nixosModules.home-manager` in its NixOS module.
7. The `name` is required. A missing `name` throws and names the input.

**Final module.** Full file: `agent-l/module-final.nix`. It is the prototype (`module-prototype-base.nix`) with exactly three edits: the `isFace` block is replaced by the builder below, `imports` is replaced, and the inventory wrapper uses `imports = [ (guardModule host) ] ++ libNixosModules ++ [ h.nixos ];`. The guard, pin check (it ran green: `vendomat:check` passed), cache push, paths and profiles are unchanged and were not re-tested beyond that.

New `imports`:
```nix
  imports =
    (lib.mapAttrsToList
      (n: i: lib.setDefaultModuleLocation "inputs.${n}.devenvModules.default" i.devenvModules.default)
      handWritten)
    ++ (lib.mapAttrsToList
      (n: m: lib.setDefaultModuleLocation "inputs.${n}.vendomat (devenv)" m.devenv)
      built);
```
Builder block (replaces `isFace`):
```nix
  candidates = lib.filterAttrs
    (n: i: !(lib.elem n [ "self" "devenv" "nixpkgs" ]) && (i.outPath or null) != self.outPath)
    inputs;
  hasDesc = i: i ? vendomat;
  hasHand = i: (i ? devenvModules) && (i.devenvModules ? default);
  describedAll = lib.filterAttrs (_: hasDesc) candidates;
  bothInputs = lib.attrNames (lib.filterAttrs (_: i: hasDesc i && hasHand i) candidates);
  handWritten = lib.filterAttrs (_: i: hasHand i && !hasDesc i) candidates;
  nameOf = n: d: d.name or (throw "vendomat: input '${n}' exports a vendomat description with no `name`.");
  byName = lib.groupBy (x: x.name) (lib.mapAttrsToList (n: i: { input = n; name = nameOf n i.vendomat; }) describedAll);
  clashes = lib.filterAttrs (_: l: lib.length l > 1) byName;
  described =
    if bothInputs != [ ] then
      throw "vendomat: input(s) ${lib.concatMapStringsSep ", " (n: "'${n}'") bothInputs} export both a `vendomat` description and `devenvModules.default`. Export one."
    else if clashes != { } then
      throw "vendomat: two inputs use the same library name:\n${lib.concatStringsSep "\n" (lib.mapAttrsToList (name: l: "  name '${name}': inputs ${lib.concatMapStringsSep ", " (x: "'${x.input}'") l}") clashes)}"
    else describedAll;

  mkLibModules = inputName: d:
    let
      name = nameOf inputName d;
      hasService = d ? service;
      optionsFor = lib': withService:
        let own = (d.options or (_: { })) lib'; in
        if own ? enable || own ? service
        then throw "vendomat: input '${inputName}': description options must not define `enable` or `service`. Vendomat defines them."
        else own
          // { enable = lib'.mkEnableOption "the ${name} library"; }
          // lib'.optionalAttrs (withService && hasService) { service.enable = lib'.mkEnableOption "the ${name} service"; };
      extraFor = args: (d.extra or (_: { })) args;
      launcher = pkgs: cfg: pkgs.writeShellScript "${name}-start" ''
        export PATH=${lib.makeBinPath (d.packages pkgs)}:$PATH
        exec ${(d.service { inherit pkgs cfg; }).exec}
      '';
      hmModule = { config, lib, pkgs, ... }:
        let cfg = config.vendomat.libs.${name}; ex = extraFor { inherit cfg pkgs lib; }; in
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
      nixosModule = { config, lib, pkgs, options, ... }:
        let cfg = config.vendomat.libs.${name}; ex = extraFor { inherit cfg pkgs lib; }; in
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
            (lib.optionalAttrs (options ? home-manager) { home-manager.sharedModules = [ hmModule ]; })
          ];
        };
      devenvModule = { config, lib, pkgs, ... }:
        let cfg = config.vendomat.libs.${name}; ex = extraFor { inherit cfg pkgs lib; }; in
        {
          options.vendomat.libs.${name} = optionsFor lib false;
          config = lib.mkIf cfg.enable (lib.mkMerge [
            { packages = d.packages pkgs; }
            (lib.optionalAttrs hasService { processes.${name}.exec = (d.service { inherit pkgs cfg; }).exec; })
            (ex.devenv or { })
          ]);
        };
    in
    { devenv = devenvModule; nixos = nixosModule; homeManager = hmModule; };

  built = lib.mapAttrs (n: i: mkLibModules n i.vendomat) described;
  libNixosModules = lib.mapAttrsToList
    (n: m: lib.setDefaultModuleLocation "inputs.${n}.vendomat (nixos)" m.nixos)
    built;
```
Not tested here: a `flake = false` input (the filter leaves it out because it has no `vendomat` or `devenvModules` attribute; agent K proved the same case for the prototype).

**Library flake** (`agent-l/knappy-flake.nix`; its `flake.lock` has only the `nixpkgs` node):
```nix
{
  description = "knappy: a demo library with a Vendomat description. It has no Vendomat input.";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";
  outputs = { self, nixpkgs }:
    let forAll = nixpkgs.lib.genAttrs [ "x86_64-linux" ]; in
    {
      packages = forAll (system: {
        default = nixpkgs.legacyPackages.${system}.writeShellScriptBin "knappy" ''
          echo "knappy $*"
          [ "$1" = serve ] && exec sleep 3600
        '';
      });
      vendomat = {
        name = "knappy";
        packages = pkgs: [ self.packages.${pkgs.stdenv.hostPlatform.system}.default ];
        options = lib: {
          port = lib.mkOption { type = lib.types.port; default = 8080; description = "Listen port."; };
        };
        service = { pkgs, cfg }: { exec = "knappy serve --port ${toString cfg.port}"; };
        extra = { cfg, pkgs, lib }: {
          devenv.env.KNAPPY_EXTRA = "devenv";
          nixos.networking.firewall.allowedTCPPorts = [ cfg.port ];
          homeManager.home.sessionVariables.KNAPPY_EXTRA = "home-manager";
        };
      };
    };
}
```

**Other notes**
- The devenv.nix of the fixture workspace imports `inputs.vendomat.devenvModules.default`. The NixOS role is `vendomat.inventory.test.nixos` (files in `agent-l/fixture-workspace-N2/`).
- `devenv eval` cannot read a quoted attribute such as `systemd.units."knappy.service"`. Use `systemd.services.knappy…` paths instead.
- Raw log path: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-l/cmds.log
