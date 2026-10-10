# Live release candidate and demo, 2026-10-10

This record separates observed results from open gates. Raw command reports are under
`~/.local/state/vendomat/v6/releases/`. The demo smoke log is under
`~/.local/state/vendomat-demo/runs/20261010T175452Z/`.

## Inputs and commands

| Item | Exact input |
| --- | --- |
| Host | `server`, x86_64-linux; Nix 2.34.7; Testee 0.5.1 |
| Patched devenv | `git://server/devenv?ref=refs/tags/v2.4.0-vendomat.2`, commit `e2acb5b02b8627602e223128a082ecfd024850ab`; CLI `devenv 2.4.0+e2acb5b` at `/nix/store/3mfmgg65mf08h7rhwd7w4f2vvcr9ia9i-devenv-wrapped-2.4.0` |
| Vendomat | `git://server/vendomat?ref=refs/tags/v0.7.0-rc.1`, commit `275bf06fb83cbb9ec3f3c001331b4f8822db67e4`; tagged package `/nix/store/fc2vg8hk72xl1lk71n88vrbv89i31sis-vendomat-0.7.0-rc.1` |
| Demo sources | `git://server/vendomat-demo?ref=refs/tags/v0.2.0`, commit `487012f1007b199be0b68171be6e927aa0acb883`; directories `sources/greeting`, `sources/greeting-defaults`, `sources/marker`, `sources/marker-defaults`, `sources/unused` |
| Host Attic | Client `attic-client 0.1.0` from `/nix/store/9r5fng0g7gkaq8ym3v4vhdyysvhywhx2-attic-0-unstable-2026-06-26`; private cache `vendomat` at `http://127.0.0.1:8089/vendomat` |

The fork materialization command was `python3 -I devenv-dist/materialize
~/.local/state/vendomat/v6/releases/devenv-v2.4.0-vendomat.2 --verify`.
It matched `devenv-dist/RESULT`. A `jj git push --remote collection --tag` published the fork tag.
`nix flake prefetch --json` over `git://server` returned the commit and `dir=src/modules`.
`nix build --no-link --print-out-paths
'git://server/devenv?ref=refs/tags/v2.4.0-vendomat.2#devenv' --accept-flake-config`
returned the existing patched CLI path above.

`testee verify --full` passed in run `20261010T174524Z-dd85f52ea655`.
`testee check e2e` passed in run `20261010T174603Z-254271e3df45`: 330 tests passed.
The first end to end run failed one release test because an editable package reported
`0.7.0-rc.1`, while the built command reported `0.7.0rc1`. The test now accounts for that
Python version spelling. The first run is `20261010T173707Z-6f8696382d75`.

## Collection and demo observations

Both Vendomat and the demo source tags were pushed to the collection and to GitHub.
`nix flake prefetch --json` over the collection returned each recorded commit.
The demo's `vendomat sync`, with `VENDOMAT_DEVENV` set to the patched CLI, exited 0.
It wrote eight inputs and two imports. `devenv.lock` records all three commits above.
`vendomat check` returned `clean` with the same CLI.

The command `scripts/smoke` ran with the tagged Vendomat package and patched devenv CLI.
It exited 0. Both selected module values matched. Changing `vendomat.toml` changed the
greeting in the shell. Removing the unselected input left the shell derivation equal.
The two template files stayed byte-identical. The demo record is in
[`vendomat-demo/EVALUATION.md`](../../../../../../vendomat-demo/EVALUATION.md).

The source collection push used the local repository path on `server`. An earlier
`ssh://server` push failed with `Permission denied (publickey)`.
The collection read route and tagged builds passed. A tag push from another host remains open.

## Attic observations

The private cache returned HTTP 401 for `nix-cache-info` without a credential and HTTP 200
with the configured pull token. `attic cache info vendomat` returned the private endpoint and
public key `vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA=`.
An authenticated `nix path-info --store http://127.0.0.1:8089/vendomat` found a path
that the upload reported as complete.

The first `attic push vendomat` used the default five jobs. It uploaded paths, then
returned upload errors. `atticd` logged `Connection pool timed out` on `upload-path`
at 17:47:38 UTC and 17:56:12 UTC. A one-job retry uploaded more paths but also saw
timeout errors. Its log is `attic-push-j1.log`; the service log is
`atticd-upload.journal.log`.

The server config is `/nix/store/gwf4nvxwq27nfnczzybnpns8bdj5vkc2-checked-attic-server.toml`:
SQLite database and local storage on `/mnt/wd_green1`, with 64 KiB average chunks. The
timeouts happen on larger paths (boost, ncurses, libgit2). This record does not establish the cause.

Resume pushes of the patched CLI closure, one job at a time, ended as follows:

| Run | Log | Result |
| --- | --- | --- |
| Vendomat closure, last run | `attic-push-vendomat.log` | 5 paths uploaded, 0 errors |
| devenv closure, run 1 | `attic-push-devenv-j1.log` | 30 paths requested; 26 uploaded, 4 errors |
| devenv closure, retry 1 | `attic-push-devenv-retry1.log` | 4 paths uploaded, 0 errors |

A `narinfo` check with the pull token covered every path in each closure
(`nix-store -qR`). The Vendomat closure has 35 paths and 0 missing. The devenv closure has
68 paths and 0 missing.

Cold substitution command, run on `server` after both checks above:

```text
nix copy --from http://127.0.0.1:8089/vendomat \
  --to "local?root=<state>/releases/cold-store" \
  --option netrc-file <state>/releases/cache-netrc \
  --option trusted-public-keys vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA= \
  --option substituters '' \
  <vendomat-0.7.0-rc.1 path> <devenv-wrapped-2.4.0 path>
```

It exited 0 and copied 103 paths into an empty root store. Signature checking stayed on.
`cold-store/nix/store/*-vendomat-0.7.0-rc.1/bin/vendomat --version` printed
`vendomat 0.7.0rc1`. The log is `cold-substitution.log`.

## Cold dry-run of the fork package (`DVN-006`)

Command, run on `server` against an empty root store:

```text
nix build --dry-run --accept-flake-config --store "local?root=<state>/releases/cold-store2" \
  --option substituters "http://127.0.0.1:8089/vendomat https://cache.nixos.org" \
  --option netrc-file <state>/releases/cache-netrc \
  --option trusted-public-keys "vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA= cache.nixos.org-1:..." \
  'git://server/devenv?ref=refs/tags/v2.4.0-vendomat.2#devenv'
```

It exited 0. The output reported `these 40 paths will be fetched (0.0 KiB download, 320.4 MiB
unpacked)` and no `will be built` section. The log is `dvn006-dry-run2.log`.

Evaluation built four small derivations on the cold host before it printed that result:
`devenv-nixpkgs-patched.drv` and three `cabal2nix-*` derivations. They come from import from
derivation during flake evaluation. They are not part of the output closure, so Attic does not
hold them. An earlier run with Attic as the only substituter failed on `zlib` instead. The first
log is `dvn006-dry-run.log`.

Reading: the literal `DVN-006` command passes. The "build nothing" half holds for the CLI
closure but not for evaluation. A host that must build nothing needs those four derivations in
a substituter too.

## Scope

This run proves the tagged workspace source flow and patched devenv shell on `server`. It
also proves a signed, authenticated cold substitution of the Vendomat and patched devenv
closures from the host Attic into an empty root store.

It does not prove:

- machine activation or the server system build;
- a cross-host collection tag push;
- a substitution from another host, over Tailscale;
- an upload that needs no retry. Pushing the full closures needed one-job retries and failed
  uploads on large paths under the default settings. The cause is open.
