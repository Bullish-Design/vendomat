# Decisions from V5 preliminary verification

**State:** resolved from the recorded fixtures on 2026-10-08, except where marked open. These are
design decisions. They do not pass the implementation requirements.

| Topic | Decision | Evidence | Requirement changes | Remaining work |
| --- | --- | --- | --- | --- |
| Source URLs | Use portable remote URLs as the fleet default. Use an explicit Nix input override for a local checkout. `VENDOMAT_SOURCE_ROOT` alone does not change a flake or lock. | [PV-03](results/PV-03.md) | Add `STORE-006`, `STORE-007`; keep `STORE-001` for the clone store only | Add a generator fixture and name the reachable remote for private repos Done 2026-10-08: the remote is the collection on `server` (third session below). |
| `nixpkgs` sharing | One node is a goal for controlled graphs where every authored nested flake follows its parent. | [PV-04](results/PV-04.md) | Supersede `GEN-002` with `GEN-013`; supersede `CORE-007` with `CORE-008` | Test actual project inputs for compatibility |
| Consumer shell | **Superseded 2026-10-08 (below).** Original text: use `nix develop --impure` with the pinned devenv integration; pure root discovery failed. Kept as history. | [PV-05](results/PV-05.md) | Supersede `GEN-009` with `GEN-014`, then `GEN-014` with `GEN-019` | None. The generated shell is gone |
| Host TOML | Return a valid NixOS module. Resolve packages only at explicit package-valued option paths. Let native option types merge definitions. | [PV-06](results/PV-06.md) | Supersede `SYS-002`, `SYS-003`, `SYS-005` with `SYS-008` to `SYS-010` | Implement and test the allowlist and module wrapper |
| Module helper | Use native module merging to preserve lists. Let flakes export only the faces they implement. | [PV-07](results/PV-07.md) | Supersede `MOD-007` with `MOD-010`; supersede `INP-002` with `INP-007` | Test real authored inputs and consumer activation |
| Host edit sequence | Compare the committed host file with the current file. Run `set → diff → Gitman commit → apply`. | [PV-08](results/PV-08.md) | Add `CLI-015`; keep `CLI-012` | Prove dirty-file refusal, switch, force scope, and rollback in a disposable VM |
| Private cache bootstrap | Keep the production cache unchanged. An empty alternate store on `server` fetched a closure, but a cold installer route did not pass. | [PV-09](results/PV-09.md) | Keep `CACHE-007`, `BOOT-002`, and `BOOT-019` blocked | Choose credential and route delivery, then test a cold installer VM |
| Cache retention | Do not claim “nothing builds twice.” Retention 0 avoids time-based GC in the Attic 0.1.0 fixture, not every form of deletion. Keep upstream cache fallback when Attic skips an upstream path. | [PV-10](results/PV-10.md) | Supersede `CACHE-004` with `CACHE-009` | Decide policy for important closures and test cold upstream fallback |
| Machine core | Keep the Vendomat CLI out of the shared core. Add it through a later host delta at `.vendomat`, not `.default`. | [PV-11](results/PV-11.md) | Supersede `DEL-001` with `DEL-006`; add `DEL-007` | Prove production boot and tailnet reachability |
| Physical target | Step 0 is blocked. Do not call the 4 TB disk bare or write to it. | [PV-02](results/PV-02.md) | Keep `DISK-001` to `DISK-003` open | Obtain a read-only partition-table and signature scan; review the checker |

## Open choices

- Name a reachable remote source for each private flake before the generator is accepted.
- Choose how a fresh installer obtains the private cache route, trust key, pull credential, and source before first boot.
- ~~Confirm that the owner accepts `nix develop --impure` as the generated consumer-shell command.~~ Closed 2026-10-08: Vendomat generates no shell.
- ~~Confirm the laptop name before Step 10.~~ Closed 2026-10-08: the name is `framework`.

## Decisions of 2026-10-08, second session

These are owner decisions plus design choices that follow from [PV-13](results/PV-13.md) and
[PV-14](results/PV-14.md). They keep PV-05 and its raw logs as dated history. PV-05 remains valid
evidence about its old devenv fixture and is not a reason to require `--impure` now.

| Topic | Decision | Evidence | Requirement changes | Remaining work |
| --- | --- | --- | --- | --- |
| CLI delivery | Vendomat is a system-installed command, added by a host delta at `packages.<system>.vendomat`. It is not installed through devenv or the shared boot core. | Owner; PV-11 | Keep `DEL-006`, `DEL-007`. Add `DEL-010`, `DEL-011` | Fixture F8: the CLI is reachable from an existing project shell |
| Generated shell | **Supersedes the consumer-shell row above.** Vendomat generates no development shell and no `devenv` input. A project may write its own shell and call the installed command. Remove `nix develop --impure` from every Vendomat gate. | Owner; PV-13 F2 | Supersede `GEN-014` with `GEN-019`. Add `GEN-022` | None |
| Output bridge | The generated `flake.nix` is `outputs = inputs: import ./flake-outputs.nix inputs;`. The project owns `flake-outputs.nix`. `sync` fails if the file is missing and never opens it. | PV-13 F1, F5, F6; PV-14 | Supersede `GEN-004` with `GEN-016`. Add `GEN-018` | None |
| Module selection | The generator never scans or imports a module face. A project output names each module it uses. | PV-13 F3, F4 | Supersede `GEN-010` and `GEN-011` with `GEN-017`. Withdraw `GEN-012` | None |
| Direct inputs | One input per registry entry; no implicit `devenv` or `nixpkgs`. A project lists the `nixpkgs` it needs. | PV-14 | Supersede `GEN-001` with `GEN-015`, `GEN-003` with `GEN-020` | None |
| Follows | An explicit `[follows]` table drives the edges. Registry checks reject a non-flake child, because Nix ignores that case silently. Nix itself warns for a child with no `nixpkgs`; the generator does not fetch to check. | PV-13 F7; PV-14 | Supersede `GEN-013` with `GEN-021`. Add `REG-011`, `REG-014` | Real-input compatibility with one `nixpkgs` |
| `ref` and `rev` | The draft claim that they pass through as separate attributes failed. Emit them as URL query parameters. | PV-13 | Supersede `REG-005` with `REG-013` | None |
| Name checks | A name in both `[inputs]` and `[passthrough]` is an error. An unknown top-level table is an error. | PV-14 | Add `REG-012`, `REG-015` | None |
| Verification of absence | Check parsed input names and the lock, never `rg vendomat flake.nix`. The header names the tool, and the Nixpkgs URL contains `devenv`. | PV-13 F2 | Supersede `DEL-002` with `DEL-008`, `DEL-005` with `DEL-009`, `ISO-006` with `ISO-007` | None |
| `sync` name (**superseded in the third session below**) | `vendomat sync` in a directory with `vendomat.toml` is the V5 generator. Without that file it keeps the earlier knowledge installer, because `modules/devenv.nix` still calls it. | PV-14 | None | Retire the fallback with the knowledge layer |
| Laptop name | The laptop is `framework`. | Owner | None | None |
| Step order | Isolated registry and generator work may run before the machine steps. Machine activation and fleet acceptance keep their gates. | Owner | None | See the guide's "Revised order" |

## Decisions of 2026-10-08, third session: the source collection

The owner decided these after a clarifying exchange. They supersede the "private source host" owner
choice that an earlier version of this file listed. The framing in [PV-15](results/PV-15.md) was
wrong, and its addendum says so.

| Topic | Decision | Evidence | Requirement changes | Remaining work |
| --- | --- | --- | --- | --- |
| Two tracked things | Vendomat tracks source and build outputs. Attic holds build outputs only. Source is separate, and no step requires it to be in Attic. | Owner | `STORE-012` | None |
| Source collection | One collection on `server` at `/home/andrew/vendor/<repo>` holds the owner's released tags. Nix reads it at evaluation. The owner and agents read it for context. | Owner; [PV-16](results/PV-16.md) | `STORE-008`; `STORE-006` stays | A fetch from `framework` over the tailnet |
| Read transport | A read-only `git daemon` serves `git://` to the tailnet. The tailnet is the access boundary, and the owner accepts that every tailnet device can read. An idle daemon used 0 CPU ticks in 20 seconds. | Owner; PV-16 | `STORE-008` | Build it on `server` (Step 6.3) |
| Release push | The owner's CI, through devenv, pushes release tags over SSH. Unreleased work stays out. | Owner | `STORE-011` | SSH key login; the release task |
| Pinning | Every `[inputs]` entry pins a tag. There is no `latest` ref. Following a release means editing the tag and running `nix flake update`; a script can do that later. | Owner | `REG-017` | None |
| Registry shape | A `[forge]` table names the collection. An entry without `url` resolves to it. `repo` names a repository whose name has a dot. | [PV-17](results/PV-17.md) | `REG-016`; `REG-021` supersedes `REG-015` | None |
| Third-party code | Optional per entry. `mirror = true` keeps a reading copy in the collection and leaves the input URL alone. nixpkgs and devenv are never copied. | Owner | `REG-018` | The store step |
| Reading on other machines | `vendomat path <name>` prints the locked tree as a store path. `keep = true` keeps a persistent clone. | Owner | `REG-019`; `CLI-007` stays | The store step |
| Backup URL | An optional `backup` per entry. Vendomat uses it only when the owner asks, because Nix cannot fail over between two URLs. | Owner | `REG-020` | An explicit command |
| Store rules | `STORE-002` becomes `STORE-009`, and `STORE-004` becomes `STORE-010`, because the collection is the owner's source and not a cache. A working tree shows the newest release (`STORE-013`). | Owner | `STORE-009` to `STORE-013` | The store step |
| Tag-only pushes | Git refuses only a push to the checked-out branch, so each repository carries a `pre-receive` hook: new tags only, and a tag never moves. | [PV-18](results/PV-18.md) | `STORE-014` supersedes `STORE-011` | None |
| Per-repository export | The daemon serves a repository only when it has `.git/git-daemon-export-ok`. `/home/andrew/vendor` already holds other clones. Port 9418 opens on `tailscale0` only. | PV-18 | `STORE-015` | Switch `server` (the owner) |
| `nix-meta` change | The daemon settings and `scripts/collection-add` sit in a `nix-meta` lane, `source-collection`. Described, not landed, not switched. | PV-18 | None | The owner lands the lane and runs `sudo nixos-rebuild switch` |
| `sync` | `vendomat sync` is V5-only. The knowledge installer is gone from it, because the library is being rewritten from scratch. | Owner | None | The old `vendor-sync` script in `modules/devenv.nix` now fails |

## Decisions of 2026-10-08, fourth session: the store step

The owner set these rules in the task. The design choices below them follow from the code and the
fixtures in [PV-20](results/PV-20.md). No existing ID is superseded.

| Topic | Decision | Evidence | Requirement changes | Remaining work |
| --- | --- | --- | --- | --- |
| `sync` order | Write `flake.nix` first, then do the store work. A store failure leaves the flake written. Exit 1 for a refused entry, 2 for a Git failure. | Owner; PV-20 | Add `STORE-016` | None |
| Clone rules | Directory is `$VENDOMAT_SOURCE_ROOT` or `~/vendor`, then the repo name. A directory with an `origin` gets a tag fetch. A directory with no `origin` is the collection's own repository and is skipped. A directory that is not a Git repository is refused. | Owner; PV-20 | Add `STORE-017`. `STORE-009` stays and now has a Verify | None |
| Mirror | `mirror` acts only with `sync --collection`. It gets no marker and no hook. | Owner; PV-20 | Add `STORE-018` | A `mirror` run on `server` |
| Pinned tag in the tree | A `keep` or `mirror` clone shows its pinned tag as a detached checkout when clean. Two projects with different tags share one clone; the last `sync` wins; `path` stays exact. | Owner; PV-20 | Add `STORE-019` | None |
| Git calls | Subprocess, explicit arguments, `GIT_TERMINAL_PROMPT=0`, a timeout. A URL scheme outside git, http(s), ssh, and file is refused, so an `ext::` URL cannot run a command. A password in a URL never reaches a message. | Design choice; PV-20 | Add `STORE-020` | None |
| Dry run | `--dry-run` writes nothing, including `flake.nix`. It still reads Git state, so it reports a dirty tree. | Owner; PV-20 | Add `STORE-021` | None |
| Newest release | `sync --collection` checks out the newest tag by version order in each repository with the hook or the marker. The checkout is detached, so a clean tree is possible on an unborn branch. A side effect is that the daemon now advertises `HEAD` for `devman`. Tags are unchanged. | Owner; PV-20 | Add `STORE-022`. `STORE-013` stays; a push-time hook is not built | Decide whether a push-time hook is wanted |
| `path` | Ask Nix with `nix flake archive --json --no-write-lock-file`. Do not read the lock. `--dry-run` still prints paths, so it is not used. A `path:` input inside the project has no path and is an error. | Owner; PV-20 | Add `CLI-016`. `CLI-007` stays | None |
| Push-time hook | `hooks/collection-post-receive` refreshes the tree after a tag push, with the `STORE-022` rules. It needs only Git and never fails a push. It is a file in this repository. The owner approved adding it to `collection-add` and copying it into `devman`. `devman` has it. The `collection-add` lane is not landed: unbookmarked work in the main `nix-meta` checkout blocks `gitman land`. | Owner ("do the hook", "Yes, please proceed"); [PV-21](results/PV-21.md), [PV-22](results/PV-22.md) | Add `STORE-023`. `STORE-013` stays | The owner resolves the `nix-meta` checkout; the lane lands |
| Owner-reported checks | The owner reports that `nix flake lock` plus a build against the collection, and `ssh server true`, passed from `framework`. They are recorded as owner-reported. Nobody verified where the outputs came from. | Owner; [PV-19](results/PV-19.md) | None | Observed evidence from `framework` |

## Open owner choices (recommendation first)

1. ~~Private source host.~~ Closed above: `server`, over `git://`.
2. **Installer credential delivery** (blocks Step 10, [PV-09 addendum](results/PV-09.md)). Recommend a root-only, pull-only, short-lived credential file copied from the installer medium to `/run` and passed with `--option netrc-file`. Consequence: the medium holds a secret.
3. **Drive scan** (blocks Step 0, [PV-02 addendum](results/PV-02.md)). Recommend that the owner runs the read-only `wipefs --no-act`, `sfdisk --dump`, and `blkid -p` with their own sudo, and saves the output.
4. **Land and switch the `nix-meta` lane** (Step 6.3). Needs your `sudo`.
5. **SSH key login from `framework` to `server`** (release pushes). SSH from `server` to itself failed on 2026-10-08; `framework` was not tested.
