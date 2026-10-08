# V5 preliminary spikes

**State:** Planned. No row is a passed requirement. `PV-*` names a spike, not a V5 requirement.

Run these before V5 implementation. Use the current concept, specification, guide, and storage
refinement as inputs. A result must state the exact pinned tools and actual fixture output.
Treat every new command and interface as proposed until the fixture runs.

## Priority and completion

`P0` blocks the part of implementation named in its result. `P1` settles a scope limit before
the affected feature starts. Record a failure or infrastructure gap as blocked. Do not call it
passed because an upstream document describes the mechanism.

| Spike | Priority | Main question | Related requirements |
| --- | --- | --- | --- |
| PV-01 | P0 | Which active claims disagree? | All active IDs; `RES-*`, `EMIT-*`, `PROJ-*` |
| PV-02 | P0 | Does disk preflight reject every unsafe target? | `DISK-001` to `DISK-007`, `BOOT-021` to `BOOT-024` |
| PV-03 | P0 | Can another host evaluate a lock with local source URLs? | `STORE-*`, `GEN-001`, `GEN-008`, `BOOT-019` |
| PV-04 | P0 | What does the flake graph really share? | `GEN-002`, `GEN-003`, `GEN-008`, `CORE-007` |
| PV-05 | P0 | Can a consumer work without Vendomat? | `GEN-004`, `GEN-009` to `GEN-012`, `DEL-002`, `DEL-005` |
| PV-06 | P0 | Can host TOML preserve option types and conflict policy? | `SYS-001` to `SYS-007` |
| PV-07 | P0 | Does `mkModules` merge additions and activate only on enable? | `MOD-001` to `MOD-009`, `INP-002`, `INP-006` |
| PV-08 | P0 | Can `set → diff → apply` reach a defined state? | `CLI-009` to `CLI-013` |
| PV-09 | P0 | Can a fresh installer reach every needed cache path? | `CACHE-001`, `CACHE-007`, `BOOT-002`, `BOOT-019` |
| PV-10 | P1 | What can the cache and retention policy promise? | `CACHE-004` to `CACHE-008`, `BUILD-001` to `BUILD-008` |
| PV-11 | P0 | Does the Nix-only machine core stand without the CLI? | `BOOT-001`, `BOOT-006`, `BOOT-009`, `DEL-001` |
| PV-12 | P0 | Are the final documents and launch conditions consistent? | Every changed ID |

## PV-01 — active claim audit

**Question.** Can one implementer follow all active documents without choosing between
contradictory instructions?

**Work.** Make a claim table with file, line, requirement ID, current status, and replacement.
Search all active documents for `devenv.yaml`, `fromManifest`, `mkProject`, resolver, version
selection, generated lock, `nixpkgs` count, `PREFLIGHT PASS`, and implementation step numbers.
Check the specification's top-level authority statement against its withdrawn resolution section.
Check `GUIDE-V5.md`'s superseded header and acceptance checklist. Count requirement IDs and
record duplicates, including superseded IDs. Do not reuse or renumber one.

**Minimum result.** Give every contradiction one proposed resolution and affected document list.
Distinguish a stale example from a normative requirement. The resulting design must have one
dependency declaration and one owner for `flake.lock`.

**Stop condition.** Do not start generator or source-store implementation while the input
contract still requires both a flake and `devenv.yaml` to name the same dependencies.

## PV-02 — read-only drive identity and preflight

**Question.** Does the proposed preflight prove the declared drive and reject every stated
unsafe condition?

**Fixture.** On `server`, use `/dev/disk/by-id/` to inspect all four declared drives. Capture
model, serial, exact byte size, filesystem UUIDs, parent drive for each UUID, mounts, root and
boot ancestry, partition table, and signatures. Use read-only tools such as `lsblk`, `findmnt`,
`blkid`, and `wipefs -n`. Keep the command transcript. Do not select a target by kernel name.

Build a disposable checker fixture with explicit inventory values. Inject a missing hardware
ID, wrong model, wrong serial, wrong size, wrong UUID owner, mounted target, running-root
target, running-boot target, partition table, and stray signature. Each mismatch must exit
non-zero before any write command is reachable. A matching fixture must pass. Run the checker
against the real inventory read-only. Re-resolve the target immediately before the future
write step; document that required check in the install procedure.

**Minimum result.** State each injection, exit status, and reason. Record whether every real
UUID belongs to the declared hardware ID. A printed model or an existing UUID alone is not a
comparison. A passing checker is still not permission to partition a physical disk.

**Stop condition.** Do not use Step 7's partition commands until this checker and a reviewed
install procedure satisfy `DISK-001` to `DISK-006` on the observed host.

## PV-03 — source URL portability and restore

**Question.** What must exist on a second machine for `git+file:///home/andrew/vendor/<name>`
and its lock entry to evaluate?

**Fixture.** Inspect one real generated or hand-written local flake reference, its lock entry,
and the source path it names. Use disposable path-backed flakes for relocation tests. If a
`git+file` fixture is necessary, create and change its temporary repository through Gitman.
Test an unchanged flake and lock under a second absolute checkout path. Test a missing source
clone in an environment without that source already present in its store. Test whether changing
`VENDOMAT_SOURCE_ROOT` changes the generated URL, the lock, or neither. Repeat the source fetch
test with the cache available and unavailable.

**Minimum result.** State the required path, clone, store content, and network access for each
case. Name any assumption shared by `server`, `framework`, a virtual machine, and a restored
machine. Decide whether the fleet uses one fixed absolute path or remote URLs with explicit
local overrides. Do not claim portability from a warm store.

**Stop condition.** Do not adopt generated local URLs fleet-wide until a fresh consumer can
obtain every input through the chosen route.

## PV-04 — transitive graph and `nixpkgs.follows`

**Question.** Do direct `follows` lines give the promised one-node graph at three levels?

**Fixture.** Build local, disposable flakes `consumer → A → B → C`. Give A, B, and C explicit
inputs. Run one case with only the consumer's direct `follows`, and one with each authored flake
following its parent `nixpkgs`. Add a `flake = false` source case. Capture `flake.lock` and
`nix flake metadata --json`. Count distinct `nixpkgs` nodes and record the lock edges. Build
the same small output under both graphs and compare closure paths. Use exact pinned Nix.

**Minimum result.** State which graph has one node, what contract each authored input must
follow, and whether forcing one revision breaks any tested input. Decide whether one node is
a universal requirement or a controlled-graph goal. Nix documents transitive input overrides;
that upstream fact does not replace this fixture.

**Stop condition.** Do not claim `GEN-002` proves a single transitive node from direct inputs
alone. Do not add a Vendomat graph resolver to repair this.

## PV-05 — generated consumer independence

**Question.** Can an ordinary consumer evaluate, enter its shell, and build with no Vendomat
input or package?

**Fixture.** Hand-write the proposed generated `flake.nix` in a disposable consumer. Include
one module-bearing input, one input without `devenvModules.default`, and one non-flake source.
Check that automatic imports define options but activate nothing until `enable` is true.
Check `flake.lock` for transitive inputs and the generated source for only direct inputs.
Remove Vendomat from the fixture's flake inputs and command path. Evaluate, enter, and build.
Use a cold store where required to prove that cached Vendomat artifacts did not hide a
dependency. Test a stale or hand-written `flake.nix` only after a generator exists.

**Minimum result.** Record source, lock, evaluation, shell entry, build, and absence of
Vendomat as a declared input. A static fixture proves feasibility; it does not pass the later
`vendomat sync` acceptance test.

**Stop condition.** Do not make a consumer depend on `mkProject` or another Vendomat flake
function. The inline output must stand alone.

## PV-06 — typed host TOML and native merge behavior

**Question.** Can a short converter handle real option types without changing string lists?

**Fixture.** Evaluate a host TOML with a boolean, integer, ordinary string list, package list,
and a user group list containing `docker`. Compare each evaluated value with its declared
NixOS or Home Manager option type. Try an unknown package name. Define the same scalar in
TOML and Nix with equal and unequal values. Define the same list in both. Record each native
merge or conflict. Test a malformed dotted path and a setting that needs a Nix function.

**Minimum result.** Select a type-aware package rule with an explicit scope. Specify whether
the converter rejects, preserves, or resolves each value. State the real conflict policy:
Nix option types decide how definitions merge. If strict cross-file duplicate rejection is
still required, specify a separate check and prove it.

**Stop condition.** Do not use the guide's `pkgs.${n} or n` rule for every string list. Do not
claim that `lib.mkMerge` rejects every duplicate.

## PV-07 — module faces, list merge, and activation

**Question.** Can the proposed helper safely produce devenv, NixOS, and Home Manager modules?

**Fixture.** Use one small authored input. Evaluate each face alone with `enable = false`,
then with `enable = true`. Give `packages` one derivation. Give `extra.nixos` another entry
under `environment.systemPackages`, and give `extra.homeManager` another under
`home.packages`. Compare the exact lists. Repeat with native `lib.mkMerge` instead of
`lib.recursiveUpdate`. Check target-specific options never reach another face. Inspect real
candidate inputs and count which actually need one, two, or three faces.

**Minimum result.** Select a merge rule that preserves both package lists. Decide whether
unused faces may be omitted. Record the cost of any required no-op face. Keep `enable = false`
as the default for an imported face.

**Stop condition.** Do not implement the helper with a list-replacing merge. Do not promote a
three-face requirement without a real need for all three.

## PV-08 — host edit, diff, and apply state

**Question.** How does the documented `set → diff → apply` sequence pass the dirty-file rule?

**Fixture.** Trace a disposable tracked host TOML through clean, `set`, `diff`, commit, apply,
and rollback states. Use Gitman for every version-control action. Define the exact baseline
for `diff`: previous commit, active generation, or another recorded state. Evaluate a small
NixOS option before and after the edit. Test a package option and a derived option whose
effective value changes indirectly. Write down what `diff` can report accurately and what it
cannot serialize to JSON. No live `nixos-rebuild switch` is needed for this feasibility test.

**Minimum result.** State one sequence that satisfies both `CLI-009` and `CLI-012`. Define
what `apply` refuses, what force bypasses, and how the owner sees the exact evaluated delta.
The later CLI acceptance test remains open until the command exists.

**Stop condition.** Do not publish a kickoff example where `set` creates the condition that
causes `apply` to refuse.

## PV-09 — private cache and installer bootstrap

**Question.** Can a fresh installer obtain the prebuilt closure before the installed system
starts Tailscale and loads a pull credential?

**Fixture.** First confirm the current substituter URL, public key, route, and read credential
on `server` without printing a secret. Check a known path through the intended URL. Then use
a disposable virtual machine or installer image with a genuinely cold store. Attempt to fetch
one prebuilt output with `--max-jobs 0`. Record how the installer joins the tailnet or receives
the closure. Record the target Nix configuration seen by the installer and by first boot.
If the chosen path is a prebuilt closure copy, verify the copy and install using only a
disposable disk image. Do not write a physical disk.

**Minimum result.** The cold target must obtain the exact closure without compilation. Save
the store path, NAR hash, route, exit status, and log. State where the installer gets the
source flake, pull credential, and trust key. A warm `server` store is not this proof.

**Stop condition.** Do not call the laptop install a download until its actual installer
route is specified and a cold fixture has passed. Mark inaccessible infrastructure blocked.

## PV-10 — publication, collection, and the “build once” claim

**Question.** What happens after Attic retention or Nix garbage collection removes a path?

**Fixture.** Read the actual Attic and Nix collection settings. Use a disposable Attic cache
or safe test namespace to build and push a small path. Check a locally built path and an
upstream-substituted path; the latter tests the known push filter. Check `watch-store` output
and presence through `nix path-info --store`. In the disposable namespace, expire or remove
one path, then ask a cold consumer for it. Record whether the builder can recreate and
re-push it. Do not change production retention or delete production cache objects.

**Minimum result.** State the exact period and conditions for reuse. Decide whether selected
closures need explicit roots or retention. Rewrite “nothing builds twice” if collection
allows a later rebuild. A cache absence must never appear as success.

**Stop condition.** Do not treat `watch-store` activity as proof that each closure is present.
Verify each target path through the cache API.

## PV-11 — machine core and CLI dependency

**Question.** Can the shared Nix core boot and stay reachable before the Vendomat command
exists or when its package fails?

**Fixture.** Build a minimal, disposable NixOS virtual machine that contains the proposed
shared boot, user, network, Secure Shell, and cache settings. Omit Vendomat Python and CLI
packages. Boot it and verify login and the trusted cache configuration. Separately evaluate
the guide's core with the Vendomat package present and with that package unavailable. Record
which failure prevents a new system build or switch. Do not change `server`.

**Minimum result.** State whether `DEL-001` belongs in the shared core or in a later host
delta. Keep the Nix-only bootstrap claim precise. The virtual machine proof does not replace
the later real `server` boot proof.

**Stop condition.** Do not say a broken Vendomat package cannot affect machine builds if the
machine flake evaluates or builds that package unconditionally.

## PV-12 — reconciliation and readiness

**Question.** Is there one implementable V5 design after the spikes?

**Work.** Build a result index. For every failed claim, preserve its old requirement ID and
add a new ID with a Verify command. Search the active documents for duplicate statements.
Update examples, guide commands, acceptance conditions, and kickoff prompts together. Remove
stale resolver, manifest, package-list, lock, and disk safety claims from current direction.
Keep observations and inferences separate. Do not promote a documented upstream fact to a
passed gate.

**Minimum result.** Each P0 spike has a passed result or a named blocker. Every proposed
interface has a fixture or remains marked proposed. The concept, specification, guide,
refinement, current-state file, and kickoff agree. Run the repository's Testee gate for the
document and fixture changes. Publish the final readiness result and pending owner choices.

**Stop condition.** Do not start V5 Step 0 while the disk checker can report a false pass.
Do not start a dependent implementation step while its P0 spike is blocked.

## Upstream references

These references explain native mechanisms. They do not pass a Vendomat requirement.

- [Nix flakes and transitive inputs](https://nix.dev/concepts/flakes).
- [Nix flake references and local Git URLs](https://nix.dev/manual/nix/2.24/command-ref/new-cli/nix3-flake.html).
- [Nix module types and merge behavior](https://nix.dev/tutorials/module-system/deep-dive).
- [devenv shells with flakes](https://devenv.sh/guides/using-with-flakes/).
- [NixOS installation](https://nixos.org/manual/nixos/stable/).
- [Tailscale Serve and tailnet access](https://tailscale.com/docs/features/tailscale-serve).
