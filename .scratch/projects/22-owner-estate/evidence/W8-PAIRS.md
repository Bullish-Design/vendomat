# W8: the machine and home pairs with comparison checks — 2026-10-15

<!-- Provenance: a subagent built and ran the prototype on 2026-10-15. Source copy and logs:
~/.local/state/vendomat/p22/w8/ (flake.nix, flake.lock, pairs/, checks/, flake-check.log,
negative.json, real.nix, real-nix-meta.json). Live scratch flake: /tmp/p22-proofs/w8/flake/. The
orchestrator did not rerun the commands. -->

This record backs OI-12 (options a and d) and the cross-layer rule of the concept. It is a scratch
flake. nix-meta, nix-systems, and every tool repository are unchanged.

## Question

Can each of the four machine/home pairs (atuin, agentman, mnemonix, secrets) get one source for its
shared values and a check that compares the two evaluated halves? Does each check fail when one half
drifts? Do the checks work on nix-meta's real configuration?

## Inputs

- Scratch flake with inputs `nixpkgs`, `home-manager`, `pytuin` (rev `b6be6d2`, as in W6), `atuout`
  (rev `57b2cb7`), `mnemonix` (tag `v0.2.7`), and `nix-secrets` (tag `v0.1.4`). The lock reuses W6's
  nodes.
- One NixOS configuration (`nixosConfigurations.machine`) and one Home Manager configuration
  (`homeConfigurations."andrew@machine"`). Both import the real modules of the owners:
  `pytuin.nixosModules.pytuin-server`, `mnemonix.nixosModules.mnemonix`,
  `nix-secrets.nixosModules.secrets`, `mnemonix.homeManagerModules.mnemonix`, and plain
  `programs.atuin`, `services.postgresql`, `programs.zsh`.
- `pairs/<pair>.nix` defines, for each pair, `constants`, a `machine` module, and a `home` module.
  Both modules read the same `constants`. In the final design `constants` is what the owning tool's
  flake exports (OI-12 a). Here it sits in the scratch repository, because only pytuin exports
  anything usable today (its atuin package).

| Pair | Shared source | Machine half | Home half |
| --- | --- | --- | --- |
| atuin | pytuin's `packages.atuin` (18.23.0); uid 1000; server port 8888; serve path `/atuin` | `services.pytuin.server`, explicit `users.users.andrew.uid` | `programs.atuin.package`, daemon socket `/run/user/<uid>/atuin.sock`, `sync_address` |
| agentman | role, database, socket directory, identMap name | `services.postgresql` `ensureDatabases`, `ensureUsers`, `authentication`, `identMap` | user unit with `AGENTMAN_DATABASE_URL=postgresql+asyncpg://<role>@/<db>?host=<dir>` |
| mnemonix | `apiPort 8891`, `uiPort 9991`, `projectsRoot`, `memprojectsFile` | `services.mnemonix.hindsight` | `programs.mnemonix.apiUrl` built from the same port |
| secrets | secret names, directory `/run/secrets`, owner, group, mode | `nix-secrets.secrets.activeNames` and overrides, which become `sops.secrets` | zsh init lines that read `/run/secrets/<name>` |

## Checks

`checks/compare.nix` holds one function per pair, `compare.<pair> machineConfig homeConfig`. It
returns `{ ok; mismatches }`, a list of strings. `checks.x86_64-linux.pair-<pair>` is a derivation
that exits 1 and prints the mismatches when the list is not empty.

A check reads the evaluated halves, not the constants. It therefore finds a mismatch even when
someone edits one half and not the constants.

| Check | What it compares |
| --- | --- |
| atuin | server package store path and client package store path; their versions; the socket path against the machine's own uid; the client `sync_address` against the server's serve path |
| `pair-atuin-versions` | runs `atuin --version` and `atuin-server --version` from the two packages and compares the version word (build step) |
| agentman | parses the URL in the home unit into role, database, and socket directory; requires the role in `ensureUsers`, the database in `ensureDatabases`, the socket directory in `unix_socket_directories`, an `identMap` line from the home user to the role, and a `peer` rule for the role in `pg_hba` |
| mnemonix | `services.mnemonix.hindsight.apiUrl` against `programs.mnemonix.apiUrl`; both `projectsRoot` and `memprojectsFile` |
| secrets | scans the home's zsh init for every `/run/secrets/<name>`; requires each name in `sops.secrets`, owned by the home user (or mode 0444), at the path `/run/secrets/<name>`. Zero references is itself a mismatch, so the scan cannot pass while it finds nothing. |

## Results

| # | Command | Result |
| --- | --- | --- |
| 1 | `nix flake check -L` | `all checks passed!`: `pair-atuin`, `pair-agentman`, `pair-mnemonix`, `pair-secrets` print "halves agree"; `pair-atuin-versions` prints `client: atuin 18.23.0 (78366dca...)` and `server: atuin-server 18.23.0` |
| 2 | `nix eval --json .#lib.negative` (eight broken halves) | all eight report `ok: false` with the specific mismatch (table below) |
| 3 | The same functions against nix-meta `main` `ee768f74`, `nixosConfigurations.server` and `home-manager.users.andrew` (read only, 11 s) | agentman, mnemonix, secrets agree; atuin reports one mismatch |

### Negative controls

| Control (one half broken) | Mismatch reported |
| --- | --- |
| machine uid 1001, home socket for 1000 | `atuin socket path from the machine uid: machine="/run/user/1001/atuin.sock" home="/run/user/1000/atuin.sock"` |
| machine server package set to nixpkgs `pkgs.atuin` | `atuin package store path: ...atuin-18.16.1 ... atuin-18.23.0`, and the version line |
| machine role `agentman2` | `home role agentman is not in machine ensureUsers ["agentman2"]` |
| machine `identMap` maps `root`, not the home user | `machine identMap has no line mapping user andrew to role agentman` |
| machine Hindsight `apiPort` 8888 | `mnemonix API url: machine="http://127.0.0.1:8888" home="http://127.0.0.1:8891"` |
| machine `activeNames` drops `deepseek-api-key` | `home reads /run/secrets/deepseek-api-key; the machine declares only ["subconscious-api-key"]` |
| machine secret owner `root` | `secret deepseek-api-key has owner root mode 0400; the home user andrew cannot read it` |
| home reads `/run/secrets/deepseek-key` (a one-sided rename) | `home reads /run/secrets/deepseek-key; the machine declares only [...]` |

### nix-meta today

The one mismatch is real: `atuin socket path from the machine uid: machine="/run/user//atuin.sock"`.
nix-meta leaves `users.users.andrew.uid` null and the home falls back to 1000 (`terminal.nix:22`).
The machine's own value therefore does not state the uid the home relies on. The pair needs an
explicit uid on the machine; the prototype sets one (`users.users.andrew.uid = constants.uid`).
The server and client atuin packages are the same store path in nix-meta today, so that part passes.

## Findings

1. **Four checks fit one shape.** Each pair has constants, two modules, and a pure comparison of the
   evaluated configs. Eight negative controls prove each check can fail.
2. **A check that reads only the constants proves nothing.** The prototype compares evaluated
   options. A uid, a port, a role, or a secret name that changes on one side is caught.
3. **A `grep` over home text is the weakest part.** The secrets check scans the zsh init text for
   `/run/secrets/<name>`. Pi's `apiKey` command (`!cat /run/secrets/...`) and other homes' files need
   their own scan, or a rule that every reader goes through one `secretPath` function exported by the
   constants. The second route removes the scan.
4. **Only one owner exports anything today.** pytuin exports the atuin package. mnemonix exports no
   constants (its machine module derives `apiUrl` as a read-only option). agentman has no package at
   all (W6 finding 5). OI-12 (a) therefore needs small exports from mnemonix and agentman first.
5. **The change order (machine first, home second) is not enforced here.** The checks compare the
   configurations that a person would build. They do not say which half switched. The comparison of
   the running versions (`pair-atuin-versions`) runs at build time; a run-time version check on a
   live machine remains the doctor's job.
6. **`warnOnMissingKeys` hides a gap.** nix-secrets drops a name that has no material and prints a
   warning. The secrets check reads the effective `sops.secrets`, so a dropped name becomes a
   mismatch. Without that, the home would read a file that never appears.

## Verdict

**Holds.** The four pairs each get a comparison check that passes on aligned halves and fails on
eight kinds of drift. The checks also run against nix-meta's real configuration and find the one
real gap (the machine uid).

## Unproved

- Constants exported from the owning tools' flakes. They are local files here.
- A two-flake setup (nix-systems for the machine, nix-meta for the home). The prototype puts both
  halves in one flake, so the check runs on both evaluated configs at once. With two repositories the
  home flake needs the machine's configuration as an input, which OI-12 option c rejected. Option d
  (duplicate the values, compare) needs a way to evaluate the other repository in a check.
- `sops` decryption and the Postgres peer login at run time. The machine config evaluates and its
  top-level derivation instantiates; no VM ran it.
- Pi and other secret readers outside the zsh init.
