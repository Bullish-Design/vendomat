# W3: devman `homeManagerModules.default` as a scratch module — 2026-10-15

<!-- Provenance: a subagent built and ran the scratch module on 2026-10-15. Source tarball and logs:
~/.local/state/vendomat/p22/w3/ (w3-scratch.tar.gz, equivalence.log, equivalence-negative.log,
vm-nixos.log, vm-hm-run1-fail.log, vm-hm-pass.log, hm-units.txt, hm-mutable-units.txt). Live scratch
flake: /tmp/p22-proofs/w3/flake/. The orchestrator did not rerun the commands. devman was read only. -->

This record backs the devman part of the concept ("Export a `homeManagerModules.default`") and phase
4. It is a scratch flake. devman, nix-meta, and nix-systems are unchanged.

## Question

Can `nix/nixos-module.nix` split into shared options, a neutral service description, and two
translators? Does the NixOS translator keep producing exactly today's units? Does the Home Manager
translator run the Dagu user unit?

## Inputs

- devman `main` `d9bd7465` as a flake input (`git+file:...?rev=`), read only. nixpkgs `55bfb4d7`,
  Home Manager `5a9d300b`, Nix 2.34.7. The VM tests need KVM, which the machine has.
- `devman-modules/options.nix` (302 lines): the option block, sliced from lines 404 to 694 of the
  original (930 lines). `lingerUsers` moved out.
- `devman-modules/plane.nix` (463 lines): the original `let` block (lines 25 to 400: config files,
  `installConfig`, `reloadScript`, `cli`, `linkAdapter`, the loopback predicate) plus a new neutral
  description. It reads `cfg` and returns `units`, `paths`, `packages`, and `assertions`. It sets no
  NixOS or Home Manager option.
  A unit is an attribute set with `description`, `wantedBy`, `after`, `environment`, `pathRoots`,
  `pathPackages`, `type`, `execStartPre`, `execStart`, `restart`, `restartSec`, `unsetEnvironment`,
  `startLimit`, and `restartTriggers`.
- `devman-modules/nixos.nix` (56 lines): the translator to `systemd.user.services.*.serviceConfig`.
  It owns `lingerUsers`, `users.users.<u>.linger`, `environment.systemPackages`, and
  `environment.pathsToLink`.
- `devman-modules/home-manager.nix` (84 lines): the translator to `Unit`, `Service`, and `Install`
  sections. It differs in five ways:
  1. `PATH` is explicit in `Environment=`: the `servicePath` roots (`bin` and `sbin`), then
     coreutils, findutils, grep, sed, and systemd. NixOS adds those four packages itself; Home
     Manager does not.
  2. `restartTriggers` become `X-Restart-Triggers` lines, which sd-switch reads.
  3. The packages go into `home.packages` through one `buildEnv` with `pathsToLink = [ "/bin"
     "/share/devman" ]`. W6 found that `devman` and `devman-link` clash on
     `lib/python*/devman_contract` otherwise.
  4. `servicePath` gets a Home Manager default without `/etc/profiles/per-user/%u`.
  5. It sets no `linger`. Lingering stays on the machine.
- `devman-modules/devlayer.nix` (53 lines, from W2): a home-level layer. A tool adds a module with
  `devlayer.modules.<name>`; the layer is one store directory whose `default.nix` imports them; an
  activation step writes the pointer. The devman translator adds `devman-link.nix`: the link
  module with `/run/current-system/sw/bin/devman-link` replaced by the store path of `devman-link`
  (the concept asks for exactly this).
- `flake.nix` exports `nixosModules.default` and `homeManagerModules.default`. Both set `cliInputs`
  from devman's own inputs, as devman's `nixosModules.default` does.

## Method and results

| # | Check | Result |
| --- | --- | --- |
| 1 | `nixos-unit-equivalence-store`: two NixOS evaluations, devman's own `nixosModules.default` and the scratch NixOS translator, same options; `diff -u` of the generated `dagu.service` and `devman-watch.service` text | identical, 42 lines (store paths of the scripts included) |
| 2 | `nixos-unit-equivalence-mutable`: the same with a mutable registry; adds `devman-dagu-reload.service` and `.path` | identical, 65 lines |
| 3 | Negative control: change `restartSec` from 5 to 6 in the neutral description | the check fails and prints `-RestartSec=5` / `+RestartSec=6` |
| 4 | `vm-nixos`: devman's own `dagu-store-registry` VM test, imported from the devman input, run with the scratch NixOS module | passes: 7 subtests, including a real run (`demo.probe` Succeeded) |
| 5 | `homeConfigurations.tester.activationPackage` and `tester-mutable` | both build; the mutable one holds `devman-dagu-reload.{path,service}` |
| 6 | `vm-hm`: a NixOS VM whose machine half is a lingering user. A standalone Home Manager generation is activated by that user with `<generation>/activate`. No NixOS Home Manager module is in the VM. | passes: 10 subtests (below) |

### The Home Manager VM test

The VM has user `tester` (uid 1000, `linger = true`) and no devman NixOS module. The generation
(and a second one with `queues.light = 7`) is registered through `virtualisation.additionalPaths`.

| Subtest | Result |
| --- | --- |
| before activation | `Linger=yes`; no Dagu unit exists |
| activate generation 1 as `tester` | the step prints `devlayerPointer: wrote /home/tester/.local/state/devlayer/current.nix -> ...-devlayer` |
| the Dagu user unit starts | `dagu` reaches `active`; `systemctl --user cat dagu` shows `Environment=PATH=`, `UnsetEnvironment=SHELL`, `X-Restart-Triggers`, and no `/etc/profiles/per-user`; the fragment is `~/.config/systemd/user/dagu.service` |
| the pointer | a regular file naming the layer; `devman-link.nix` holds `<store>/devman-link-0.6.0/bin/devman-link reconcile`, and the text `/run/current-system/sw/bin/devman-link` is absent |
| the config | `dags_dir` is the store registry; `@DEVMAN_REGISTRY@` and `@DAGU_HOME@` are substituted; `max_concurrency: 4` is present; the registry holds only `dags`, `generation.json`, `projects` |
| the API | `/api/v1/health` answers on loopback; `demo.check`, `demo.probe`, `beta.check`, `beta.format` are listed |
| a run | `dagu enqueue demo.probe` runs; `metadata.jsonl` holds a `succeeded` record in the project directory |
| the watcher | `devman-watch` is `active`; a store registry installs no reload unit |
| generation 2 | `activate` of the second generation changes `MainPID` of `dagu` (sd-switch restarted it through `X-Restart-Triggers`), and `config.yaml` shows `max_concurrency: 7` |
| stability | `dagu` stays active for 10 s and still lists `demo.probe` |

Two runs of `vm-hm` failed before the pass. The first stopped on a lint error in my test script (an
unneeded `f` prefix). The second failed at the run subtest (`vm-hm-run1-fail.log`): my test script lacked
`DAGU_HOME` in the user's environment, so `dagu enqueue` created the example DAGs in
`~/.config/dagu`. I fixed the script; the module needed no change.

### A defect in my own check

The first version of the equivalence check wrote `diff -u a b && echo identical`. Under `set -e` a
failing command inside an `&&` list does not stop the shell, so the check passed with `RestartSec=6`
on one side. The negative control (row 3) exposed it. The final check runs `diff -u` on its own
line. This is the failure that project 22 rule 4 describes.

## Findings

1. **The split is mechanical.** About 680 of the 930 lines moved unchanged into `options.nix` and
   `plane.nix`. Each translator is under 90 lines.
2. **The NixOS translator keeps the generated units byte for byte,** for both registry kinds,
   including the store paths of `installConfig`, `reloadScript`, and the CLI wrapper. `nixosModules`
   can keep its name and behaviour.
3. **The Home Manager translator runs the real plane.** Home Manager activation as the user starts
   Dagu and the watcher, renders the config, serves the API, runs a workflow, restarts on a config
   change, and writes the pointer, with lingering as the only machine input.
4. **`buildEnv` needs `pathsToLink` in a home.** Without it, `devman` and `devman-link` collide
   (W6 finding 3).
5. **The Dagu client needs `DAGU_HOME` in the user's shell.** The `dagu` command reads
   `~/.config/dagu` by default, while the unit uses `~/.local/share/dagu`. `devman` passes
   `--dagu-home` itself. The translator should set `home.sessionVariables.DAGU_HOME`. The NixOS
   module has the same gap today.
6. **The devman version in `home.packages` is the input's (`devman-0.8.0` from `main`),** not nix-meta's
   0.7.0 tag. The unit text names it. A tag bump moves it.
7. **`/run/current-system/sw` stays in the default `servicePath`.** It is harmless on a machine with
   no such path, but a non-NixOS home would not need it.

## Verdict

**Holds.** devman can export `homeManagerModules.default` from a shared options file, a neutral
description, and two translators. The NixOS output does not change. The Dagu user unit runs from a
standalone Home Manager generation in a VM, with the pointer step and the layer.

## Unproved

- Changes in the devman repository. Nothing was committed there; the module needs a devman project
  and its own tests.
- A real switch on `andrew@server`, and the move of the unit from the NixOS module to the home
  (phase 4). Two units of the same name would collide on ports 8080 and 50055.
- A mutable registry in a VM (the generation builds; the VM used a store registry).
- The agent workflows and the link reconcile through the layer in a real repository shell.
- `home.sessionVariables.DAGU_HOME`, and Home Manager's `systemd.user.startServices` behaviour with
  the reload path unit.
