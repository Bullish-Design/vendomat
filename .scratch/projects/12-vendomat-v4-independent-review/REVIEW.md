# Vendomat V4 independent design review

**Date:** 2026-10-06. **Status:** Proposal for owner review. No V4 document changed.
**Scope rule:** This review assessed no pre-V4 code, module, fixture, consumer, or command. It
treats V4 as a ground-up design. Migration is a separate later task and is not an input here.
**Evidence rule:** Native behaviour below comes from official documentation and upstream source,
read on 2026-10-06. A documented upstream fact is evidence about the upstream tool. It is not a
passed Vendomat gate.

## 1. Verdict in brief

Build the **minimal Vendomat layer**: two operations and one record.

1. `publish` — freeze one selection, run the declared check set, realize the output, push the
   output and its closure, then verify every closure path from the cache. Write one receipt.
2. `retain` — fetch every locked input source into the store, root it, push those paths to the
   same cache, and record their identity in the same receipt.

Everything else in the current contract is either native behaviour, a restatement of a native
rule, or a precaution with no observed failure behind it.

The research for this review found that **seven of the current contract's open experiments already
have documented upstream answers**. Several contract rules exist to solve problems the native
tools do not have. The largest single discovery is that **retained source can travel through
Attic as ordinary store paths**. That removes the source host, the remote read layer, the local
replica question, the capture list, and the two capture graphs in one step.

I recommend **60 active requirement IDs**, not 88. The reason is not more aggressive cutting. It
is a different classification: about a quarter of the current IDs test devenv, Nix, NixOS, Home
Manager, or Attic rather than Vendomat. Those belong in a pin record that is observed once. They
are not perpetual V4 gates.

I also recommend removing the monolithic P0 gate. Replace it with a pin record plus per-phase
entry conditions. The current P0 blocks the whole programme on `sudo` access, one SSH key, and a
conflicted lane in another repository. None of those facts affect the first Neovim module.

## 2. Proposed V4 concept (one page)

> **Vendomat V4**
>
> **Purpose.** One owner composes personal machines, projects, and reusable applications from
> native devenv, NixOS, and Home Manager modules. Vendomat adds exactly two things that no native
> tool provides: a durable record binding declared checks to exact output bytes, and retained
> source for the software a selection chose.
>
> **Authority.** Native declarations and locks are the only selection authority. Nix owns
> evaluation, derivations, store identity, and substitution. devenv owns composition, tasks, and
> machine operations. NixOS and Home Manager own activation. Attic owns cached objects and
> signing. Vendomat owns no selection, no plan, no lock, no runtime, and no daemon.
>
> **The two operations.**
>
> - `retain` runs `nix flake archive`, adds a garbage-collection root, pushes the archived input
>   source paths to Attic, and records each input's locked revision and NAR hash.
> - `publish` freezes one immutable selection, runs the declared required check set, realizes the
>   requested output, pushes the output and its runtime closure to Attic, queries every closure
>   path back from Attic, and writes one receipt.
>
> **The receipt.** One immutable file. It stores four native JSON documents verbatim
> (`nix flake metadata --json`, `nix build --json`, `nix path-info --json --recursive`, and the
> archived-source index) plus six Vendomat fields: the required check list with each check's
> owner, result, and log reference; the upload result; the closure verification result and its
> time; a coverage statement; and an optional machine plan identifier. It records the Nix version
> and JSON format of every stored document. It stores no credential and no environment dump.
>
> **Separate facts.** These never imply one another: source retained, source correspondence
> established, rebuild from source proved, declared checks passed, output available in Attic now,
> dependency change accepted, configuration activated.
>
> **Purity invariant.** A publishable selection evaluates purely from its recorded revision and
> locks. A selection whose evaluation reads undeclared host state cannot be published. This
> replaces any drift-detection mechanism: Nix is the drift detector.
>
> **Identity invariant.** An input-addressed store path follows its derivation. Its NAR hash
> identifies its bytes. The receipt records both. Attic re-hashes every upload and rejects a
> mismatch. Nix re-hashes every import and rejects a mismatch. Vendomat compares the recorded
> hash with the served hash once, in the cold-consumer proof.
>
> **Source scope.** V4 retains the source of every locked native input. It does not map a built
> package back to its upstream source. `pkgs.srcOnly` is the native mechanism for that later
> capability, and it needs its own evidence. Until then a package's source status is `unresolved`,
> stated plainly.
>
> **First proof.** One Neovim review application: one shared command, one plugin contribution for
> the normal editor, and one dedicated configured editor. The command is reached by absolute store
> path, never by `PATH` lookup. P1–P6 prove the application, inspection, publication, and
> recovery path. P7 separately proves any machine claim.
>
> **Machine claim.** devenv Machines copies plan outputs directly to the target with
> `nix copy --to ssh://…`. It does not substitute through Attic. Vendomat therefore makes no
> machine transfer or machine-cache claim. It records the plan identifier beside the receipt and
> nothing more.
>
> **Boundaries.** No resolver, second lock, daemon, runtime, action registry, deployment engine,
> context server, index, UI schema, release engine, retention engine, or cache protocol.

## 3. Design comparison

| Dimension | Native-only | Minimal Vendomat (**recommended**) | Current V4 contract |
| --- | --- | --- | --- |
| New Vendomat operations | 0 | 2 (`retain`, `publish`) | Composition inspection, source lookup and capture, publication, reports, diagnostics, upgrade proposals, release tasks, scaffolds, scheduled sweeps |
| New file formats | 0 | 1 (the receipt) | Receipt, source identity records, capture policy list, coverage report, correspondence labels, storage report |
| New state objects | 0 | 1 (receipt store) + GC roots | Source archive, identity records, read views, indexes, derived summaries, receipt store, failure logs, capture list, holds |
| Active requirement IDs | 0 | 60 | 184 |
| Phases | 0 | 7 + a pin record | 11 (P0–P10) |
| Reaches goal 1, compose modules | Yes | Yes | Yes |
| Reaches goal 2, local overrides | Yes (`--override-input`, `path:` input) | Yes | Yes |
| Reaches goal 3, inspect source | Partly: identity yes, retention yes, but no durable inventory and no honest correspondence label | Yes, for locked inputs; package source stated as unresolved | Claims both graphs; neither graph is proved |
| Reaches goal 4, check and build exact output | Partly: runs the checks, keeps no durable result | Yes | Yes |
| Reaches goal 5, publish full closure | Yes (`attic push` includes the closure) | Yes, plus a verified availability record | Yes |
| Reaches goal 6, consume elsewhere | Yes | Yes | Yes |
| Reaches goal 7, Neovim proof | Yes | Yes | Yes |
| Reaches goal 8, separate machine claim | Yes | Yes | Yes |
| What is missing | A durable, structured record that these checks passed for these bytes, and that every closure path was present at time T. A source inventory separate from the store. An honest correspondence label. | An automatic package-to-source map. Upgrade and release helpers. | Nothing is missing. Much is unproved. |
| Main cost | Every claim is a shell transcript. Nothing survives the terminal. | One command, one format, one store of receipts. | 2,075 contract lines, 184 IDs, 63 guide steps, 11 proposed names, 25 decision and experiment rows. |

**Native-only reaches all eight owner goals.** That is the important result, and it sets the bar.
The three gaps above are real but small, and each is a *record-keeping* gap, not a capability gap.
A minimal Vendomat layer closes exactly those three gaps and nothing else.

The current V4 contract does not reach more goals than the minimal layer. It specifies more
mechanism for the same goals, and most of that mechanism has no fixture.

## 4. Native facts that close current open experiments

These were researched from upstream documentation and source for this review. Each one removes an
experiment row or a requirement from the current contract.

| Current open item | Native answer found | Consequence |
| --- | --- | --- |
| `P-ATTIC`: how to prove a complete closure despite the upstream filter | `attic push` pushes the closure **by default**; `--no-closure` disables it. The filter drops only paths signed by the cache's `upstream_cache_key_names`, whose default is the single entry `cache.nixos.org-1`. `--ignore-upstream-cache-filter` disables it, and `attic cache configure --upstream-cache-key-name` sets the list. | One flag, not a subsystem. `V4-CACHE-004` becomes a recorded setting. |
| `P-NAR-IDENTITY`: do checked bytes equal served bytes | Attic's upload handler re-hashes the stream and rejects a mismatch with "Bad NAR Hash or Size". Nix's `addToStore` re-hashes every import and fails with "hash mismatch importing path". Attic serves a signature generated **at read time** from the per-cache server key. | Both ends verify natively. Vendomat records the hash so one end-to-end comparison is possible. The drift-rejection machinery shrinks to one comparison. |
| `P-MACHINES`: does Machines transfer substitute through Attic | No. devenv `apply` runs `nix copy --to ssh://<target>` directly. There is no `--substitute-on-destination` and no cache step. Substituters appear only with `--use-machines-as-builders`. | `V4-MACH-008` is answered without a fixture. V4 makes **no** machine transfer claim. The rationale for caching whole machine generations disappears. |
| `P-DELIVERY`, plain-repository half | devenv merges an imported `devenv.yaml` only for local relative or absolute paths inside the git root. "Remote inputs are not yet supported for `devenv.yaml` imports." `--from` for a non-path source states "Its devenv.yaml is not merged". | `V4-MOD-013` is a documented upstream fact. A plain consumer must declare the module's inputs itself. |
| `P-EDITOR`: how two editor forms share one implementation | `wrapNeovimUnstable` with `wrapRc = true` sets `VIMINIT` to `lua dofile('<store path>')` through `--set-default`. That isolates the dedicated editor's configuration. Plugins are ordinary `buildVimPlugin` derivations and can be listed in both forms. `neovimRequireCheckHook` is a native plugin check. | `P-EDITOR` is answered. Keep the fixture as a scenario, not an open design question. |
| `P-SOURCE`, locked-input half | `nix flake metadata --json` returns `locks`, the whole lock file, with `rev` and `narHash` per input. `nix flake archive [--to <store>] [--json]` walks the lock recursively and copies every input's source tree as a store path. A `/nix/var/nix/gcroots` symlink pins a path and its closure. | The identity record and the retained bytes are both native. No Vendomat source format is needed for locked inputs. |
| `P-CAPTURE-LIST`: a reviewable capture list that does not duplicate locks | Not needed. `nix flake archive` already covers every locked input. The list existed to bound a cost that the archive makes negligible, and to reach a graph this review defers. | `V4-SRC-019`–`023` and the whole capture-policy design retire. |
| `P-SOURCE`, package half | `pkgs.srcOnly` produces the unpacked and patched source tree as a store path. It runs `unpackPhase` and `patchPhase` only. It is undocumented in the Nixpkgs manual and requires evaluating the package. | The later capability has a named native mechanism. Defer it with a trigger instead of specifying it now. |

Two **negative** findings matter as much:

- **`nix flake archive --to <attic url>` will not work.** Attic's binary-cache router serves only
  `GET` for `nix-cache-info`, narinfo, and NAR. Uploads use a separate `PUT /_api/v1/upload-path`.
  So source distribution is two native steps: `nix flake archive` into the local store, then
  `attic push <cache> <archived paths>`.
- **`attic push` produces no machine-readable output.** All output is emoji-prefixed lines on
  standard error. The exit status is nonzero if any path failed, and successful uploads remain on
  the server. This is the single strongest argument for a Vendomat layer. The native way to verify
  availability is to query the cache as a store:
  `nix path-info --store https://<host>/<cache> --json --json-format 2 <paths>`.

Two **traps** worth recording in the contract:

- A `devenv:enterShell` task failure does **not** block shell entry. Upstream source states
  "Shell entry proceeds even if some tasks fail". Never use an `enterShell` task as a gate.
- `devenv tasks run` exits 0 or 1 only, and prints its JSON output on success only. A missing
  declared check is therefore not distinguishable from a failed one by exit status. Vendomat must
  check existence with `devenv tasks list --json` before running. That justifies keeping
  `V4-CHK-011` as a real obligation with a real mechanism.

## 5. Ranked findings

Rank follows the size of the simplification against the risk it carries. "Evidence basis" states
whether an observed failure requires the current rule, or whether the rule is precautionary.

### F01 — Retained source can travel through Attic. The source host, read layer, and replica question all disappear.

- **Location:** Concept §§11–12, 19; Spec §5; guide P3 steps 2, 4, 6; `V4-SRC-002`, `011`–`018`,
  `024`–`025`; `D-OFFLINE-SOURCE`; `V4-REC-008`.
- **Owner need:** Read the source that this selection chose, later, from any of my machines.
- **Native alternative:** `nix flake archive` fetches every locked input's source tree into the
  store as ordinary store paths. A `/nix/var/nix/gcroots` symlink pins them. `attic push` sends
  those paths to the same cache that already carries the binaries. Any machine fetches them back
  with the same substituter it already trusts.
- **Evidence basis:** Precautionary. The contract designs a durable store on the build host, a
  read-only tree exposed over the private network, derived read views, a regeneration path, an
  unavailable-lookup result, and a deferred local replica. No observed failure requires any of it.
  The store **is** the durable store. The store path **is** the read-only tree. Attic **is** the
  distribution.
- **Simplification:** Delete the source host, the read views, the regeneration path, the remote
  read contract, the disconnected-lookup result, and the local replica question. Source retention
  becomes: archive, root, push, record. Source reading becomes: substitute the path.
- **Affected IDs:** Retire `V4-SRC-012`, `014`, `016`–`018`, `025`, `V4-REC-008`. Restate
  `V4-SRC-002` and `011` against store paths. `D-OFFLINE-SOURCE` becomes moot.
- **Savings:** About 90–130 contract lines, 7 IDs, 3 guide steps, 1 decision, 1 state class.
- **Risk:** Low to medium. Two real costs. First, archived nixpkgs source trees are large; measure
  before adopting this for every consumer. Second, Attic garbage collection refreshes
  `last_accessed_at` on pull, so rarely-read source needs retention period 0 on its cache. Both
  are native settings, not design problems. Use a separate Attic cache for source if the retention
  policies must differ.

### F02 — About a quarter of the requirement IDs test upstream tools, not Vendomat.

- **Location:** `V4-OWN-006`; `V4-MOD-003`, `006`, `007`, `013`; `V4-SRC-005`, `010`, `012`,
  `016`, `017`; `V4-CACHE-004`, `007`, `010`–`012`; `V4-REC-006`, `012`; `V4-MACH-003`, `005`,
  `006`, `008`, `010`, `012`, `014`.
- **Owner need:** Know that the pinned tools behave as the design assumes.
- **Native alternative:** Observe each fact once on the pinned versions and record it. These are
  properties of Nix, devenv, NixOS, Home Manager, and Attic. Vendomat cannot make them true or
  false.
- **Evidence basis:** Precautionary, and misclassified. "Evaluating a devenv module does not start
  processes" is Nix semantics. "Input-addressed Attic substitutions follow the configured signature
  trust policy" is the `require-sigs` and `trusted-public-keys` contract. "Machines rejects a stale
  plan" is devenv behaviour, and this review already found it holds only for the NixOS role and
  only against target generations and SSH access facts.
- **Simplification:** Split the ledger into two classes. Class A is a **native baseline record**:
  24 facts, observed once on the pin, no gate, no fixture to maintain. Class B is **Vendomat
  obligations**: the only IDs that gate a phase.
- **Affected IDs:** 24 move to the baseline record and keep their ID strings as history.
- **Savings:** 24 active IDs, about 60–80 requirement lines, and an unbounded amount of future
  fixture maintenance.
- **Risk:** Low. The facts are still recorded and still cited. They stop being gates that a
  Vendomat change can fail.

### F03 — The monolithic P0 gate couples the application proof to P5 and P7 infrastructure.

- **Location:** Guide P0 (5 steps) and its gate; Concept §22; `V4-OWN-009`, `V4-OWN-012`,
  `V4-MACH-001`, `V4-REC-009`.
- **Owner need:** Do not claim a proof that the environment cannot support.
- **Native alternative:** State each phase's entry condition at that phase. P1 needs a pinned
  devenv and Nix and nothing else. P5 needs a reachable Attic with a push token and a pull token.
  P7 needs a reachable NixOS target and the Machines pin.
- **Evidence basis:** Observed, and it is the current failure. P0 is blocked on an inactive Attic
  endpoint, an unproved second host, absent `sudo`, a rejected SSH key, and a conflicted lane in
  another repository. None of those affect one Neovim module with a command and two editor forms.
  The design's own `D-PROOF-GATE` already separates the application from the machine claim. P0
  then re-couples them.
- **Simplification:** Replace P0 with (a) a **pin record** — a document, not a gate, naming the
  tool versions, the hosts, each durable state class and its owner, and the native cache policy;
  and (b) a one-line entry condition on each phase. Keep `V4-OWN-009` and `V4-REC-009` as record
  obligations. Move `V4-MACH-001` to P7 entry.
- **Affected IDs:** `V4-MACH-001` moves to P7 entry. `V4-OWN-012` leaves V4 entirely (see F06).
  `V4-OWN-009` and `V4-REC-009` become record obligations, not gates.
- **Savings:** 1 phase label, 5 guide steps, and the current total block on all work.
- **Risk:** Medium. A single early gate does surface absent infrastructure before effort is spent.
  Counter: the P5 entry condition surfaces it, and P1–P4 effort produces the application, which is
  valuable whether or not Attic ever runs.

### F04 — The receipt should store native JSON documents verbatim instead of defining its own schema.

- **Location:** Concept §§14–15; Spec §§4, 8; `V4-SEL-004`–`006`, `V4-EVD-001`, `V4-EVD-007`,
  `V4-EVD-010`, `V4-REC-010`–`011`, `V4-MACH-015`.
- **Owner need:** Explain later which checks passed, for which exact bytes, and whether the cache
  held every path at that time.
- **Native alternative:** Nix already emits every identity fact as JSON. `nix flake metadata
  --json` gives the complete locked input graph with `rev` and `narHash` per input. `nix build
  --json` gives `drvPath` and every output path. `nix path-info --json --recursive` gives
  `narHash`, `narSize`, `references`, `deriver`, `signatures`, and `ca` for the whole closure.
- **Evidence basis:** Precautionary. The contract names eleven receipt items and seven claims. Six
  of the eleven are fields Nix already produces. Re-specifying them creates a schema to design, a
  mapping to maintain, and a way to disagree with Nix.
- **Simplification:** The receipt is a thin envelope. It stores four native documents verbatim and
  adds six fields that no native tool knows: the required check list with owner, result, and log
  reference; the upload result; the closure verification result and time; a coverage statement; and
  an optional machine plan identifier. It also records the Nix version and `--json-format` of every
  stored document, because `nix path-info` and `nix derivation show` changed shape across releases.
- **Affected IDs:** Merge `V4-SEL-004`, `005` into `006`. Merge `V4-EVD-007` into `V4-CACHE-014`.
  Merge `V4-EVD-010` into `V4-SRC-015`. Merge `V4-REC-010`, `011` into `V4-REC-001`/`002`. Add one
  new ID `V4-EVD-012` for the version-and-format record.
- **Savings:** About 40–60 lines, 6 IDs, and one schema design problem.
- **Risk:** Low. The receipt becomes larger in bytes and harder to read by eye. Mitigation: the
  six Vendomat fields are the summary; the native blobs are the proof.

### F05 — The capture list and the two capture graphs retire completely.

- **Location:** Concept §12; Spec §5; guide P3 step 1; `V4-SRC-001`, `003`, `019`–`023`;
  `D-CAPTURE`; `D-CAPTURE-GRAPH`; `P-CAPTURE-LIST`.
- **Owner need:** Inspect the source of the things I selected, without retaining the world.
- **Native alternative:** `nix flake archive` retains every locked input. No list is needed,
  because no selection is needed. For the package-dependency graph, `pkgs.srcOnly` is the native
  mechanism and it requires evaluating each package.
- **Evidence basis:** Precautionary, and the design is unsound as written. The contract requires
  each list entry to name one of two graphs and resolve in it. Those graphs are not symmetric. A
  locked input's source is free and exact. A built package's source is reachable only by
  evaluating the package set that selected it, and the result is "selected source with packaging
  changes", never "exact selected source", because patches apply during the build and not to `src`.
  The contract asks P3 to prove both, and states that failing either fails P3. That makes the
  cheap half hostage to the hard half.
- **Simplification:** Retain every locked input unconditionally. State a package's source status as
  `unresolved` until a later capability proves otherwise. Delete the list, the policy gap report,
  the stale-entry diagnostic, and the graph-naming rule.
- **Affected IDs:** Retire `V4-SRC-001`, `019`–`023`. Restate `V4-SRC-003` as "every locked input
  is retained". `D-CAPTURE-GRAPH` is withdrawn. `D-CAPTURE` is replaced.
- **Savings:** About 70–100 lines, 6 IDs, 1 guide step, 2 decisions, 1 experiment row.
- **Risk:** Medium, and this is the honest cost. V4 stops claiming it can show the source of a
  packaged dependency. That was a stated owner goal. The mitigation is that the claim was never
  proved and the contract's own review (F07 in project 10) already found the graph unstable. State
  the gap plainly rather than specifying an unproved mechanism for it.
- **This is a stronger cut than project 11 proposed.** Project 11 kept "owned module plus one named
  selected third-party source". The archive makes that narrowing unnecessary: all inputs cost one
  command.

### F06 — The host-state drift rules exist to work around a pre-V4 defect. Replace them with a purity invariant.

- **Location:** Spec §4; `V4-SEL-009`; Concept §14; project-10 finding F03.
- **Owner need:** The bytes I checked are the bytes I published.
- **Native alternative:** Evaluate purely. If a selection's evaluation reads only its recorded
  revision and locks, re-evaluation reproduces the derivation. Nix is then the drift detector.
- **Evidence basis:** Observed, but the observation is about the pre-V4 module, which reads a host
  manifest during evaluation. `V4-SEL-009` cites "current machine manifest" as its source. Under a
  ground-up V4 that defect does not exist, so the requirement to "freeze or reject effective
  non-lock inputs" has nothing to guard.
- **Simplification:** State one invariant: a publishable selection evaluates purely. Enforce it
  with one check — evaluate in a sandbox or with impure access denied, and refuse to publish if it
  fails. This is strictly stronger than drift rejection, because it prevents the class rather than
  detecting one instance of it. Keep the ID string `V4-SEL-009` and restate its result.
- **Affected IDs:** Restate `V4-SEL-009`. Retire `V4-OWN-012` from V4 entirely: a preserve, migrate,
  or retire outcome for each pre-V4 delivery path is migration work, not a V4 architecture gate.
- **Savings:** About 20–30 lines, 1 ID retired from V4, and one subsystem replaced by one check.
- **Risk:** Low for the architecture. Medium for scheduling: pure evaluation is not devenv's
  default. The flake delivery form needs `--no-pure-eval` and the docs call it "impure by default".
  So "pure" here means "reads no undeclared host state", proved by denying such access in a fixture,
  not by Nix's `pure-eval` flag. Name that distinction in the spec.

### F07 — The publication form is undecided, and it is the one architectural choice that must be made before P1.

- **Location:** Concept §8; Spec §3 "Flake-backed exports"; `P-DELIVERY`; `V4-MOD-012`.
- **Owner need:** Freeze, build, archive, and publish one exact named output.
- **Native alternative:** The two delivery forms are not interchangeable for publication.
  - The **flake form** (`devenv.lib.mkShell` or `inputs.devenv.flakeModule`) gives real flake
    output attributes. `nix build --json`, `nix flake metadata --json`, and `nix flake archive` all
    work on it directly. Entry needs `nix develop --no-pure-eval`.
  - The **devenv CLI form** gives `devenv build outputs.<name>`, which prints a JSON map of output
    name to store path, plus `devenv.lock`. There is no documented `nix build .#devenv.outputs.<n>`
    route. `devenv.lock` is flake-lock JSON format version 7, so `nix flake metadata` has no
    handle on it, but the lock is readable.
  - The devenv docs state the flake route loses containers, garbage-collection protection,
    lazy-tree evaluation, evaluation caching, pure evaluation, and secretspec.
- **Evidence basis:** Precautionary in the current contract — it defers the question to P2 — but
  the question gates the design of `publish` and `retain`, which both take a flake reference in the
  recommended design.
- **Simplification:** Decide it explicitly: **develop with the devenv CLI, publish through a flake
  output attribute.** One lock format serves both. Make this a stated V4 decision, not a P2
  experiment, and let the P2 fixture confirm it rather than discover it.
- **Affected IDs:** Keep `V4-MOD-011` and `V4-MOD-012`. Add one new ID `V4-SEL-010`: a publishable
  selection resolves to a flake output attribute.
- **Savings:** None in lines. It removes one open architectural question from the critical path.
- **Risk:** Medium. If the flake form cannot express the Neovim outputs the owner needs, the whole
  `retain`/`publish` interface changes. Prove it in P2 step 1, before P3.

### F08 — Coverage-gap discovery is unfalsifiable. Delete it and keep the honesty statement.

- **Location:** Spec §6; `V4-CHK-005`, `012`, `015`; `D-CHECK-GAP`; `P-CHECK-COVERAGE`.
- **Owner need:** Do not read "published" as "fully tested".
- **Native alternative:** None, and none is possible. No tool can enumerate "documented behaviour
  that lacks a check".
- **Evidence basis:** Precautionary. `V4-CHK-015` asks Vendomat to "name documented behavior that
  lacks a nonrequired relevant check". There is no closed set to compare against, so the
  requirement cannot fail and therefore cannot pass. `V4-CHK-012` ("an absent nonrequired check
  does not block publication") is a tautology once the required set is a declared list. The
  project-10 review's own F04 found that the contract's example of a nonrequired gap is the same
  removal that `V4-CHK-013` makes a missing required check.
- **Simplification:** The receipt carries one coverage field with a fixed value, such as
  `coverage: declared-required-only`. That is the whole of `D-CHECK-GAP`. Delete the discovery
  requirement.
- **Affected IDs:** Retire `V4-CHK-005`, `012`, `015`. Retire the `P-CHECK-COVERAGE` experiment.
- **Savings:** About 25–40 lines, 3 IDs, 1 experiment row.
- **Risk:** Low. The owner loses a report that was never implementable. The honest non-claim stays.

### F09 — The machine requirements mostly test devenv and NixOS. Vendomat's machine obligation is one field.

- **Location:** Spec §7; `V4-MACH-002`–`015`; `V4-OWN-011`; `V4-REC-013`; guide P7 (6 steps).
- **Owner need:** Know whether my machine actually received and activated the configuration.
- **Native alternative:** `devenv machines plan` writes `plan.json` with a `plan-<24 chars>`
  identifier and a garbage-collection root per output. `apply` re-observes the target, rejects a
  stale NixOS plan, copies with `nix copy --to ssh://…`, and activates. A systemd watchdog on the
  target rolls back NixOS with a 300-second default deadline. Home Manager and nix-darwin roles
  have no staleness check and no automatic rollback. Home Manager activates after NixOS and a
  Home Manager failure leaves NixOS applied.
- **Evidence basis:** Precautionary. Thirteen of the fifteen MACH requirements assert devenv,
  NixOS, or Home Manager behaviour. This review found the answer to `V4-MACH-008` in upstream
  source: transfer is always a direct copy, never an Attic substitution. So the requirement to
  "distinguish Attic substitution from direct build-host copy" has only one possible outcome.
- **Simplification:** Keep four MACH IDs. `001` becomes the P7 entry condition. `004` is the only
  real obligation: the receipt records the native plan identifier and the checked paths, and
  Vendomat creates no second plan. `009` keeps system, user, and application outcomes separate in
  the report. `015` keeps the non-claim that an application output in the cache implies a cached
  machine generation. Everything else goes to the native baseline record. Also record the plan's
  two upstream weaknesses as design limits: the plan identifier is random, not content-addressed,
  and staleness is not checked against the lock or a re-evaluation.
- **Affected IDs:** Retire `V4-MACH-002`, `007`, `011`, `013`; move `003`, `005`, `006`, `008`,
  `010`, `012`, `014` to the native baseline record; retire `V4-OWN-011` and `V4-REC-013` into
  `V4-MACH-004` and `009`.
- **Savings:** About 50–70 lines, 11 IDs, 2 guide steps.
- **Risk:** Medium. Driver-specific Home Manager recovery still needs a real observation, and it
  stays in the P7 scenario. The cut is to the ledger, not to the fixture.

### F10 — The later application and P8–P10 leave the contract.

- **Location:** Spec §9 (about 60 lines); `V4-APP-001`–`031`; `V4-UPG-001`–`009`;
  `V4-OPT-001`–`004`; Concept §§16–18, 23; guide P8–P10.
- **Owner need:** Run pinned revisions with isolated state, later. Review dependency updates.
- **Native alternative:** Jujutsu, btrfs, bubblewrap, Nix, and systemd own the later application.
  `devenv update`, an isolated checkout, a devenv task, and a systemd timer cover reviewed updates
  and release work.
- **Evidence basis:** Precautionary. No first-proof failure requires either. The contract itself
  makes both conditional, then specifies them in normative text.
- **Simplification:** Two short notes outside the contract. One later-module note holds Spec §9 and
  the 31 `APP` IDs with a move map. One future-work note holds the 13 `UPG`/`OPT` IDs and the
  trigger that would open their design.
- **Affected IDs:** 44 IDs move out of the active ledger and keep their strings as history.
- **Savings:** About 200–280 lines, 44 IDs, 3 phase labels, 12 guide steps.
- **Risk:** Low for V4. Each note needs its own review when its trigger fires.
- Both this review and project 11 reach the same conclusion here. I found no reason to differ.

### F11 — Four documents state one contract.

- **Location:** Concept §§2–3, 8–25; Spec §§1–8, 10; Requirements traceability and decision tables;
  guide P0–P10.
- **Owner need:** Find one rule and the one test for it.
- **Native alternative:** Not applicable; this is a documentation defect.
- **Evidence basis:** Observed. 2,075 active contract lines state the selection, check, source,
  cache, and phase rules four times. The traceability map repeats the ID groups. The decision table
  repeats the decisions already stated in the concept and the specification.
- **Simplification:** One normative document. The concept states goals in one page. The
  specification holds every rule once. Each requirement row points at a rule and names one
  observable check. Each guide step cites requirement IDs and gives one command.
- **Affected IDs:** None. All ID strings stay traceable.
- **Savings:** About 600–800 lines, no behaviour lost.
- **Risk:** Low. Cross-references must stay valid; check them in the same edit.

### F12 — Eleven proposed names sit inside a normative contract that says names are unproved.

- **Location:** Spec §3 examples (`review.enable`, `review.command.enable`, `review.editor.enable`,
  `programs.review.enable`, `services.review.enable`); Spec §9 (six later-application names);
  Concept §25; `D-NAMES`.
- **Owner need:** Configure the first module.
- **Native alternative:** devenv `imports` and typed Nix options already have real syntax. The
  first fixture produces the real names.
- **Evidence basis:** Precautionary, and self-contradictory. `D-NAMES` says every new name stays
  proposed. The specification then shows eleven of them in copyable code blocks.
- **Simplification:** Keep one schematic consumer example with placeholder names marked as such, or
  link the fixture once it exists. Fix a name only after its fixture passes.
- **Affected IDs:** None. `D-NAMES` stays.
- **Savings:** About 30–50 lines. Zero fixed new names before P1.
- **Risk:** Low. Readers get less copyable syntax until the fixture exists.

## 6. Decision recommendation for every `D-*` decision

| Decision | Recommendation | Reason, and what changes |
| --- | --- | --- |
| `D-APP-SCOPE` | **Keep, and move the whole case out of the contract.** | Its 31 IDs and 60 specification lines serve no first-proof gate. Preserve the design and the ID strings in one later-module note with a move map. (F10) |
| `D-NAMES` | **Keep, and enforce it.** | Remove the eleven proposed names from normative text. The decision already says they are unproved; the documents must stop showing them as syntax. (F12) |
| `D-CHECK-OWNER` | **Keep, as one declared list with an owner tag per entry.** | The union of module defaults and consumer additions is right. Collapse the five requirements that split it into one. Add the mechanism: check existence with `devenv tasks list --json` before running, because `devenv tasks run` exits 0 or 1 only and cannot distinguish missing from failed. (F02, §4 traps) |
| `D-CHECK-GAP` | **Keep as a receipt non-claim. Delete the gap-discovery requirement.** | "Published" must not read as "fully tested". That is one receipt field. Naming documented behaviour that lacks a check is unfalsifiable, and the contract's own example contradicts `V4-CHK-013`. (F08) |
| `D-CAPTURE` | **Replace.** Retain every locked input unconditionally. | `nix flake archive` makes selective capture pointless for locked inputs. The consumer-maintained list, its stale-entry diagnostic, and its policy-gap report all retire. Measure archive size before adopting it for every consumer. (F05) |
| `D-CAPTURE-GRAPH` | **Withdraw.** | The two graphs are not symmetric. Locked-input source is free and exact. Package source needs `pkgs.srcOnly` and per-package evaluation, and can never be labelled "exact selected source". The current rule makes the cheap half hostage to the hard half. Defer the package graph with a named trigger and the named native mechanism. (F05) |
| `D-PROOF-GATE` | **Keep, and finish the job.** | Separating the application proof from the machine proof is correct. P0 then re-couples them by requiring a remote Machines plan before P1. Move the Machines pin to P7 entry and replace P0 with a pin record plus per-phase entry conditions. (F03) |
| `D-OFFLINE-SOURCE` | **Withdraw as moot.** | It exists because retained source was designed to live on a build host behind the private network. If source is a store path in Attic, there is no remote tree to be disconnected from, no unavailable-lookup result to define, and no local replica to defer. (F01) |
| `D-REPO-BACKUP` | **Keep as project policy. Remove it from normative V4 text.** | It creates no Vendomat feature and no requirement names it. It belongs in the project record, not the contract. Attic objects stay unbacked and are rebuilt from retained source, which F01 now also places in Attic — so record that source and binaries share one cache and therefore one loss domain. |
| **New: publication form** | **Decide now:** develop with the devenv CLI, publish through a flake output attribute. | `nix build --json`, `nix flake metadata --json`, and `nix flake archive` all need a flake reference. `devenv build outputs.<n>` has no documented `nix build` route. One lock format serves both. Confirm in P2 step 1. (F07) |
| **New: source distribution** | **Decide now:** source travels through Attic as store paths. | Two native steps: `nix flake archive`, then `attic push`. `nix flake archive --to <attic>` cannot work, because Attic's binary-cache router is `GET`-only. (F01, §4) |

## 7. Before and after counts

Counts for "before" come from the repository files as read on 2026-10-06. Counts for "after" are
edit targets, not measured results.

| Measure | Before | After | Change |
| --- | ---: | ---: | --- |
| Concept lines | 1,031 | 70 | One page of goals and boundary. |
| Specification lines | 330 | 210 | The one normative contract. |
| Requirements lines | 331 | 180 | Active ledger plus compact ID history. |
| Guide lines | 383 | 200 | Ordered fixtures and gates. |
| **Active contract lines** | **2,075** | **660** | **1,415 fewer.** |
| Later-module note | 0 | 120 | New file, outside the contract. |
| Future-work note | 0 | 40 | New file, outside the contract. |
| Native baseline record | 0 | 90 | New file; 24 observed facts, no gates. |
| Adversarial review (project 10) | 163 | 163 | History; unchanged. |
| Requirement audit (project 10) | 260 | 260 | History; unchanged. |
| P0 evidence record | 226 | 226 | Observed record; retain and supersede by the pin record. |
| **Total ID strings** | **184** | **186** | Two new IDs: `V4-SEL-010`, `V4-EVD-012`. |
| **Active requirement IDs** | **184** | **60** | 126 existing IDs leave the active ledger. |
| Phases | 11 (P0–P10) | 7 (P1–P7) | P0 becomes a pin record. P8–P10 become triggers. |
| Numbered guide steps | 63 | 33 | 5 common + 55 phase + 3 release → 4 common + 29 phase. |
| Receipt items | 18 (11 fields + 7 claims) | 10 (4 native documents + 6 fields) | The native documents replace six invented fields. |
| Proposed new names in normative text | 11 | 0 | Names come from the P1 and P2 fixtures. |
| Decision and experiment rows | 25 (9 `D-*`, 16 `P-`/`Q-`) | 13 (8 `D-*`, 5 `P-`) | Seven experiments are answered by upstream evidence; four move to notes. |
| Vendomat-defined file formats | 6 | 1 | Only the receipt. |
| Durable state classes Vendomat owns | 8 | 2 (receipts, garbage-collection roots) | Source objects become ordinary store paths in Attic. |

Active IDs by group:

| Group | Now | Proposed active | What leaves |
| --- | ---: | ---: | --- |
| OWN | 13 | 5 | 4 merged, 2 to baseline, 2 retired (one out of V4 scope). |
| MOD | 14 | 8 | 2 merged, 4 to baseline. |
| SEL | 9 | 7 (6 existing + 1 new) | 2 merged, 1 retired. |
| CHK | 16 | 7 | 4 merged, 3 retired, 2 to guide scenarios. |
| SRC | 25 | 9 | 9 retired, 5 to baseline, 2 deferred by trigger. |
| CACHE | 15 | 9 | 1 merged, 5 to baseline. |
| EVD | 11 | 7 (6 existing + 1 new) | 4 merged, 1 to future work. |
| REC | 13 | 4 | 5 merged, 1 retired, 1 to baseline, 1 measurement, 1 future work. |
| MACH | 15 | 4 | 4 merged, 7 to baseline. |
| PROOF | 9 | 0 | 7 to guide scenarios; 2 already retired. |
| UPG, OPT | 13 | 0 | All to the future-work note. |
| APP | 31 | 0 | All to the later-module note. |
| **Total** | **184** | **60** | — |

## 8. ID disposition map

Every ID string survives as history. No ID is reused and none is renumbered. The project-10 audit
already records one disposition for each of the 172 baseline IDs and names the 12 added IDs
(`V4-OWN-012`, `V4-OWN-013`, `V4-SEL-009`, `V4-CHK-016`, `V4-SRC-024`, `V4-SRC-025`,
`V4-CACHE-015`, `V4-EVD-011`, `V4-REC-013`, `V4-MACH-014`, `V4-MACH-015`, `V4-PROOF-009`). That
audit stays unchanged as provenance. This map layers on top of it.

Dispositions used: **Active** gates a phase. **Merged** retires into a named active ID that keeps
the observable result. **Baseline** moves to the native-tool record, observed once on the pin, no
gate. **Retired** has no successor and no gate; the reason is recorded. **Scenario** becomes a
combined acceptance scenario in a guide phase. **Trigger** waits for a named condition.
**Measurement** is recorded, not gated. **Note** moves to the later-module or future-work note.

| Group | Active | Merged into | Baseline | Retired (reason) | Other |
| --- | --- | --- | --- | --- | --- |
| OWN | `002`, `003`, `007`, `009`, `013` | `001`→`002`; `004`→`003`; `008`→`002`; `011`→`MACH-004` | `005`, `006` | `010` (no user-visible claim); `012` (pre-V4 migration, out of V4 scope) | — |
| MOD | `001`, `002`, `005`, `008`, `009`, `010`, `011`, `012` | `004`→`005`; `014`→`SEL-001` | `003`, `006`, `007`, `013` | — | — |
| SEL | `001`, `002`, `003`, `006`, `007`, `009`, **`010` (new)** | `004`→`006`; `005`→`006` | — | `008` (trivially true) | — |
| CHK | `001`, `002`, `004`, `006`, `007`, `010`, `011` | `008`→`010`; `009`→`010`; `014`→`010`; `016`→`011` | — | `005`, `015` (unfalsifiable: no closed set of documented behaviour); `012` (tautology once the required set is a declared list) | Scenario: `003` (P4), `013` (P1) |
| SRC | `002`, `003`, `004`, `006`, `008`, `009`, `011`, `015`, `024` | — | `005`, `010`, `012`, `016`, `017` | `001` (graph policy withdrawn); `014`, `018`, `025` (moot: source is a store path); `019`–`023` (capture list withdrawn) | Trigger: `007` (package source via `pkgs.srcOnly`), `013` (index) |
| CACHE | `001`, `002`, `003`, `005`, `006`, `009`, `013`, `014`, `015` | `008`→`OWN-002` | `004`, `007`, `010`, `011`, `012` | — | — |
| EVD | `001`, `002`, `003`, `005`, `006`, `009`, **`012` (new)** | `004`→`SRC-008`; `007`→`CACHE-014`; `010`→`SRC-015`; `011`→`002` | — | — | Note: `008` (future work) |
| REC | `001`, `002`, `005`, `009` | `003`→`001`; `004`→`002`; `010`→`001`; `011`→`002`; `013`→`MACH-009` | `012` | `008` (moot: no derived views) | Measurement: `006`. Note: `007` (future work) |
| MACH | `001` (P7 entry), `004`, `009`, `015` | `002`→`MOD-001`; `007`→`CHK-007`; `011`→`009`; `013`→`009` | `003`, `005`, `006`, `008`, `010`, `012`, `014` | — | — |
| PROOF | — | — | — | `007`, `008` already retired in project 10 | Scenario: `001`–`006` (P1–P5), `009` (P7) |
| UPG | — | — | — | — | Note: `001`–`009` |
| OPT | — | — | — | — | Note: `001`–`004` |
| APP | — | — | — | — | Note: `001`–`031` |

Arithmetic check: 58 active existing + 24 baseline + 26 merged + 16 retired + 9 scenario
+ 3 trigger + 1 measurement + 14 future-work note + 31 later-module note + 2 already retired
= **184**. Plus 2 new IDs = 186 ID strings, of which 60 are active.

The two new IDs:

| New ID | Phase | Required behaviour | Why it is new |
| --- | --- | --- | --- |
| `V4-SEL-010` | P2 | A publishable selection resolves to a flake output attribute whose evaluation reads no undeclared host state. | No existing ID states the publication form. F07 shows the choice gates the design of both Vendomat operations. |
| `V4-EVD-012` | P4 | The receipt records the tool version and JSON format of every stored native document. | `nix path-info --json` takes `--json-format 1|2|3` and `nix derivation show` changed shape across releases. A stored blob without its format is not readable later. |

## 9. Proof plan

### Common steps (4)

1. Open one Gitman lane per phase and record its base revision. **Verify:** `devenv shell -- gitman
   status` shows the intended lane and no unrelated work.
2. Before implementing, write the fixture inputs and the expected pass, fail, and gap results.
   **Verify:** Another reader can run each check without guessing a version, host, or selection.
3. Record the command, exit status, relevant output, selected revisions, and observed identities in
   a dated record. Keep raw logs outside the repository. **Verify:** The record separates
   observation from inference and links its preserved logs.
4. Run the repository gate after every change. Do not advance past a failed gate; fix the
   implementation or revise the contract with a recorded decision. **Verify:** The next phase cites
   a passing prior gate and the exact fixture.

### Pin record (a document, not a phase)

Record the devenv version, Nix version, target systems, publisher host, cold consumer host, Attic
endpoint, each durable state class with its owner and restore route, and the native cache policy.
Record the 24 native baseline facts. **No gate.** `V4-OWN-009` and `V4-REC-009` are satisfied by
the record itself. A missing host is a named blocker on the phase that needs it, not on the
programme.

**Entry conditions per phase:** P1 and P2 need devenv and Nix. P3 needs P2 plus a writable store.
P4 needs P3. P5 needs P4 plus a reachable Attic with a push token and a separate pull token, plus a
second machine with an empty store. P6 needs P5. P7 needs a reachable NixOS target and the Machines
pin (`V4-MACH-001`).

### P1 — one focused native module (4 steps)

**IDs:** `V4-OWN-002`, `003`, `007`; `V4-MOD-001`, `002`, `005`, `008`, `009`, `010`.
**Scenarios:** `V4-PROOF-001`, `V4-PROOF-002`, `V4-CHK-013`.

1. Put one review implementation and one command with a documented result format in one repository.
   Export a devenv module, a NixOS module, and a Home Manager module as distinct native targets.
   **Verify:** Run the command on known input and parse the expected result. Evaluate each target
   alone. Importing the project target activates no system or user configuration.
2. Export the plugin contribution as a `buildVimPlugin` derivation and the dedicated editor as
   `wrapNeovimUnstable` with `wrapRc = true`. Substitute the command's absolute store path into the
   Lua at build time. **Verify:** Both forms invoke the same packaged implementation. Place a
   conflicting binary first on `PATH`; both forms still invoke the selected store path. Record that
   the Nixpkgs and Home Manager wrappers default to `--suffix PATH`, so a `PATH` lookup would have
   been shadowed.
3. Enable the module with no overrides, then disable the editor while keeping the command, then
   change one supported option. **Verify:** Defaults evaluate as declared. The command still runs
   without the editor. The override changes only its intended output.
4. Run the module with no Vendomat process and no Attic. Keep a normal editor profile active beside
   the dedicated output. **Verify:** Both editors keep their own settings. The command produces its
   expected result. Declare the module's required check set and confirm it evaluates.

**Gate:** One implementation serves the command and both editor forms, and the editor reaches the
command by absolute store path. This gate makes no publication or machine claim.

### P2 — delivery, overrides, and the publication form (4 steps)

**IDs:** `V4-MOD-011`, `012`; `V4-SEL-001`, `002`, `010`; `V4-OWN-013`. **Scenario:**
`V4-PROOF-003`.

1. Resolve the publication form. Build the same named output through a flake attribute and through
   `devenv build outputs.<name>`. **Verify:** `nix build --json` returns `drvPath` and the output
   path for the flake attribute. `nix flake metadata --json` returns the complete `locks` graph.
   Record whether `devenv build` can supply an equivalent handle. If the flake form cannot express
   the P1 outputs, stop and revise the contract before P3.
2. Build two clean consumers: a plain devenv repository and a flake-backed repository. Export only
   the focused module. **Verify:** Neither consumer inherits an author-only tool or process. Remove
   one required input from the plain consumer; the diagnostic identifies it. Add an extra input to
   the author's `devenv.yaml`; the remote consumer does not receive it, matching the documented
   limit that remote `devenv.yaml` imports are not merged.
3. Test a reversible local checkout override through both paths, with two independent consumers.
   **Verify:** The effective selection report names each path, profile, and override. Reverting
   restores the prior result. Consumer B's accepted lock does not change.
4. Deny Vendomat and Attic to a fresh local consumer. Permit only the native sources and public
   caches the pin record allows. **Verify:** The consumer realizes its inputs and runs the command.
   Record every external source used. Do not call this an offline rebuild.

**Gate:** One publication form is chosen and proved. Both delivery forms and a fresh local
realization pass. The tested syntax replaces every proposed name in the specification.

### P3 — retain selected source (3 steps)

**IDs:** `V4-SRC-002`, `003`, `004`, `006`, `008`, `009`, `011`, `015`, `024`. **Scenario:**
`V4-PROOF-004`.

1. Run `nix flake archive --json` on the chosen selection and add a garbage-collection root for
   each archived path. **Verify:** Every locked input has one store path. `nix flake metadata
   --json` supplies each input's `rev` and `narHash`. Run local garbage collection; every archived
   path survives. Measure total archived bytes and record them.
2. Record one identity entry per retained input: locator, locked revision, NAR hash, store path,
   and the consumer selection that chose it. Label correspondence. **Verify:** A locked input
   labels as exact selected source. A package dependency labels as unresolved, with
   `pkgs.srcOnly` named as the later mechanism. Corrupt one retained path and confirm it loses its
   exact-correspondence claim. Capture a dirty local tree with `nix store add` and confirm the
   content-addressed identity still names the captured bytes after the working tree changes.
3. Read one retained file through its store path from the project. Leave one selected package
   uncaptured. **Verify:** Reading returns the file and its provenance without changing any lock or
   output path. The uncaptured package reports a coverage gap, and the artifact checks still pass.
   A capture-only record sets no rebuild-proof field.

**Gate:** Every locked input is retained, rooted, identified, and readable. Package source is
reported as unresolved, not guessed. Source retention changes no selection.

### P4 — bind declared checks to exact bytes (5 steps)

**IDs:** `V4-SEL-003`, `006`, `007`, `009`; `V4-CHK-001`, `002`, `004`, `006`, `007`, `010`,
`011`; `V4-EVD-001`, `002`, `005`, `006`, `012`; `V4-SRC-008`. **Scenario:** `V4-PROOF-005`,
`V4-CHK-003`.

1. Freeze one immutable consumer revision. Evaluate the selection with undeclared host access
   denied. **Verify:** Evaluation succeeds under denial and reproduces the same derivation path on
   re-evaluation. A selection that needs host state cannot be published, and the failure names the
   cause.
2. Assemble the required check set as a declared list of native check names, each tagged with its
   owner. Check existence with `devenv tasks list --json` before running any check. **Verify:** The
   effective set changes when a component is enabled or disabled, and when the consumer adds a
   check. Remove a declared check's implementation; the result is `missing-required`, distinct from
   `failed-required`. Never use a `devenv:enterShell` task as a gate, because shell entry proceeds
   after such a failure.
3. Run the declared pre-build checks, realize the output, then run the artifact and integration
   checks against that output. **Verify:** Instrument the stage order. A failed pre-build check
   prevents any build success. An artifact check given a different output path fails identity
   validation.
4. Store the four native documents and the six Vendomat fields in one receipt. Record the tool
   version and JSON format of each document. **Verify:** Compare each stored document with a fresh
   native query. Inject a canary secret into the environment; neither the receipt nor the preserved
   logs contain it. Break the derivation and confirm the failure record names the stage and no
   success result exists.
5. Retry the same selection after partial work, then change one check input and retry again.
   **Verify:** Reuse requires matching recorded inputs. A changed input reruns its affected check.
   An existing output path alone is never success.

**Gate:** A failed required check and a missing required check both block success, with different
reasons. The exact checked bytes and their selection are reconstructible from the receipt.

### P5 — publish and prove Attic consumption (5 steps)

**IDs:** `V4-CACHE-001`, `002`, `003`, `005`, `006`, `009`, `013`, `014`, `015`; `V4-EVD-003`.
**Scenario:** `V4-PROOF-006`.

1. Configure the cache, a push token, a separate pull-only token, and the consumer's trusted public
   key. Create the pull token with `atticadm make-token --pull` only. **Verify:** The pull token
   cannot push. Secrets stay outside tracked files and store paths. Record the effective substituter
   order and the accepted key on the cold machine. Set the source cache's retention period to zero.
2. Seed one runtime dependency from a public cache, then push the output with its closure.
   `attic push` includes the closure by default. Clear the cache's
   `upstream_cache_key_names` list or pass `--ignore-upstream-cache-filter`, because its default
   entry `cache.nixos.org-1` would otherwise drop the seeded path. **Verify:** The seeded path
   appears in `nix-store -qR` before the push and in the cache afterwards.
3. Query every closure path back from the cache as a store:
   `nix path-info --store <cache> --json --json-format 2`. **Verify:** Every path is present. Record
   the result and its time in the receipt. A successful push with one absent path is a failure, not
   a success. Interrupt an upload and retry; partial progress is recorded and no false prior success
   appears.
4. In an isolated store with other substituters and local builds disabled, substitute the whole
   closure from the cache alone. **Verify:** Every path substitutes. The served selected output's
   NAR hash equals the checked hash. Record each closure member's metadata. Note that Attic
   re-hashed the upload and Nix re-hashes the import, so this step confirms the end-to-end result
   rather than creating the guarantee.
5. On the cold machine, select the same immutable output and run the command and both editor forms.
   **Verify:** The machine starts without the output, obtains it from the cache, performs no build,
   and runs both interfaces. Remove one published object afterwards; the fresh availability report
   changes while the historical check result does not.

**Gate:** The cache alone serves every required runtime path with the checked bytes, and the cold
machine runs the application. This gate makes no machine-generation claim.

### P6 — evidence and recovery (4 steps)

**IDs:** `V4-REC-001`, `002`, `005`, `009`; `V4-EVD-009`. **Measurement:** `V4-REC-006`.

1. Back up three state classes separately: retained source store paths with their identity records,
   the Attic server signing state, and receipts with failure logs. Attic objects are not backed up.
   **Verify:** Record the time, owner, restore target, and identity for each class. Note that source
   and binaries now share one cache and therefore one loss domain.
2. Restore retained source into a clean location and read one input again. **Verify:** Restored
   bytes match their recorded NAR hashes and the provenance stays readable. A damaged source backup
   fails only the source restore claim.
3. Restore the Attic signing state, rebuild the selected output from a clean checkout of the
   retained source, publish it, and substitute it with an existing trusted consumer. **Verify:** The
   output path and NAR hash match P4. The consumer accepts it under its existing trust policy.
   Record that Attic signs at read time with its per-cache key, so regenerating that key invalidates
   every consumer's trust setting. A missing signing state fails only the cache-trust claim.
4. Restore receipts and logs, then recreate the P4 and P5 reports. **Verify:** Prior check and
   upload outcomes stay explainable. A signature sets no rebuild-proof field. Measure archived
   source bytes, closure size, and transfer bytes and record them; these are measurements, not
   gates.

**Gate:** Source, cache trust, and evidence restore as three separate results. Do not claim machine
readiness from this gate.

### P7 — the separate machine claim (4 steps)

**IDs:** `V4-MACH-001` (entry), `004`, `009`, `015`. **Scenario:** `V4-PROOF-009`.

1. Compose a native machine fixture with one persistent NixOS service and a separate Home Manager
   role on the pinned Machines version. **Verify:** Each contribution evaluates. The NixOS input
   requirement `disko` is present, as the Machines documentation requires even for an existing host.
2. Create a native plan and record its identifier and selected output paths beside the receipt.
   **Verify:** Every recorded path matches `plan.json`. Vendomat creates no second plan. Record two
   upstream limits: the identifier is random rather than content-addressed, and staleness is not
   checked against the lock or a re-evaluation.
3. Apply the saved plan. **Verify:** Apply uses the saved outputs. Observe that transfer is a direct
   `nix copy --to ssh://<target>` and record that no Attic substitution occurs, which is the
   documented upstream behaviour. Confirm the target accepts the copied paths through
   `nix.settings.trusted-users` or a trusted signature.
4. Fail the NixOS health check after an application write, then separately fail Home Manager
   activation after NixOS succeeds. **Verify:** System, user, and application outcomes report
   separately. A NixOS rollback claims nothing about user files or application data. Record that the
   Home Manager role has no staleness check and no automatic rollback, and name its activation
   driver. An application output in the cache sets no machine-generation field.

**Gate:** The pinned fixture proves plan, transfer, activation, and recovery limits. Only now may
V4 text make a machine claim.

## 10. Project-11 recommendations that relied on pre-V4 facts

The brief asked me to find the project-11 recommendations that rested on pre-V4 consumer or
implementation facts, and to reassess each from V4 goals and native tool boundaries alone.

| Project-11 item | Pre-V4 fact it used | Reassessment from V4 goals and native boundaries | Change in conclusion |
| --- | --- | --- | --- |
| Finding 2: "Move active consumer transition tests to cutover." | "21 overlay transitions", taken from the P0 record's inventory of 11 installed-module overlays and 10 local-checkout overlays. | Those overlays consume the pre-V4 module. A ground-up V4 has no obligation to any of them. Consumer cutover is a **migration project**, not a V4 phase, not a V4 gate, and not a V4 requirement. | **Stronger.** Do not move `V4-OWN-012` to a cutover phase. Retire it from V4 entirely and open migration as separate work after P6. |
| ID map: "Move `012` to cutover." | Same inventory. | Same as above. | **Stronger.** Retire from V4 scope. |
| Finding 2's other half: "The current P0 gate requires a remote Machines plan." | Partly pre-V4 (consumer transitions), partly native (an SSH failure to an unreachable host). | The native half stands: a remote NixOS plan proves nothing about one Neovim module. The recommendation is right but incomplete. The deeper defect is the monolithic gate itself, not which steps sit in it. | **Extended.** Abolish P0; use a pin record plus per-phase entry conditions (F03). |
| Finding 4: "Capture the owned module and one named selected native input." | Not pre-V4, but it under-uses native capability. Its native claim — "Nix locks and source paths already identify selected inputs" — is correct and sufficient. | `nix flake archive` retains **every** locked input in one command. Narrowing to one named input bounds a cost that the archive makes negligible, and it keeps a capture list that is then unnecessary. | **Stronger.** Retain all locked inputs; delete the list entirely (F05). |
| Finding 4: "Retain a Git object, archive, or rooted Nix source path with one manifest." | None. | Three retention forms plus a manifest is still three mechanisms. One form is enough: a rooted store path. The "manifest" is `nix flake metadata --json`, already native. | **Stronger.** One form, no new format for locked-input identity. |
| Finding 6: "devenv tasks already supplies order and check exit status." | None; native. | Correct about order. Incomplete about status: `devenv tasks run` exits 0 or 1 only, so exit status cannot distinguish a missing declared check from a failed one. Vendomat must check existence first. | **Corrected.** The mechanism for `V4-CHK-011` is `devenv tasks list --json`, not the exit code. |
| Finding 6: "Keep `CHK-010`–`014` as applicable." | None. | `CHK-012` is a tautology once the required set is a declared list. `CHK-005` and `CHK-015` cannot fail, so they cannot pass. | **Stronger.** Retire `005`, `012`, `015`; merge `014` into `010`. |
| Finding 7: "Store one immutable run manifest" with a listed field set. | "No V4 receipt exists yet" — an absence of implementation, which is valid evidence of no observed failure. | Right direction, wrong level. Six of the listed fields are already native JSON. Define an envelope that stores native documents verbatim rather than a field schema that can disagree with Nix. | **Extended.** Add `V4-EVD-012` for the version-and-format record (F04). |
| Finding 8: "Make P7 one native plan/apply fixture." | None; native. | Correct, and the native research strengthens it: transfer is always a direct `nix copy` over SSH, so `V4-MACH-008` has one possible outcome and needs no experiment. | **Extended.** MACH falls to 4 active IDs, not 10 (F09). |
| Finding 9: storage report as optional evidence. | None. | Agreed without change. The archive makes measurement more important, not less, because archived nixpkgs trees are large. Keep it as a measurement in P3 and P6. | **Unchanged in substance.** |
| Finding 10: names before fixtures. | None. | Agreed without change. | **Unchanged.** |
| `D-REPO-BACKUP` row: "Remove this decision from normative V4 text." | None. | Agreed. Add one consequence the earlier reviews could not see: once retained source also lives in Attic, source and binaries share one loss domain. Record that in the pin record. | **Extended.** |
| "Current host audit" section (devenv 2.4.0, Nix 2.34.7, `atticd` active, `/attic` route, `fallback=false`, `require-sigs=true`). | Environment facts, not pre-V4 implementation facts. | Valid and useful. They belong in the pin record. | **Unchanged; relocate.** |
| Proposed total of **88 active IDs**. | Derived by merging within the existing classification. | The classification is the problem. 24 IDs assert upstream behaviour and cannot be made true or false by Vendomat. Separating them, plus the deeper source and receipt cuts, gives 60. | **Stronger.** 60 active IDs plus a 24-fact baseline record (F02). |
| Proposed concept budget of **220 lines**. | None. | The brief asks for a one-page concept. 70 lines meets that; 220 does not. | **Stronger.** |

Nothing in project 11 was wrong on native grounds. Its recommendations were consistently in the
right direction and consistently short of the native capability, because it treated the existing
consumer inventory as a constraint and did not research `nix flake archive`, Attic's upload
verification, or the Machines transfer path.

## 11. Edit plan

Do not start any phase during these edits. Do not claim a gate passed. Each step is one reviewable
change. Run the edits in this order, because later files cite earlier ones.

| Order | File | Change | Acceptance check |
| --- | --- | --- | --- |
| 1 | `.scratch/projects/12-.../LATER-APPLICATION.md` (new) | Move Spec §9 verbatim and the 31 `APP` IDs here. Add the ID move map. | The 31 ID strings appear exactly once here and nowhere in the contract. No `APP` ID has a V4 phase. |
| 2 | `.scratch/projects/12-.../FUTURE-WORK.md` (new) | Move the 13 `UPG` and `OPT` IDs and `V4-EVD-008`, `V4-REC-007`, `V4-SRC-013` here. State each trigger. | Each moved ID names its trigger condition. No moved ID has a V4 phase. |
| 3 | `.scratch/projects/12-.../NATIVE-BASELINE.md` (new) | Record the 24 baseline facts with their ID strings, the observed command, and the pinned version. Include the seven answered experiments from §4 and the two traps. | Each of the 24 IDs appears once with a command and a version. No row states a gate. |
| 4 | `.scratch/projects/10-.../CONCEPT-V4.md` | Replace with the one-page concept from §2 of this review, plus a short boundary list and a pointer to the three notes. | 70 lines or fewer. No procedure, no later feature, no proposed option name, no requirement table. |
| 5 | `.scratch/projects/10-.../V4-SPEC.md` | Make it the only normative contract. Apply every accepted decision from §6. Delete §9. Remove the eleven proposed names. Add the purity invariant, the identity invariant, the publication form, and the source-distribution decision. | 210 lines or fewer. Every rule appears once. Zero fixed new names. The decision table has 8 `D-*` and 5 `P-` rows. |
| 6 | `.scratch/projects/10-.../V4-REQUIREMENTS.md` | Rebuild as the 60-ID active ledger plus the compact history map from §8. Add `V4-SEL-010` and `V4-EVD-012`. | 60 active rows. 186 ID strings traceable. The arithmetic in §8 reproduces from the file. No ID reused or renumbered. |
| 7 | `docs/V4_IMPLEMENTATION_GUIDE.md` | Rebuild in phase order: 4 common steps, a pin record, P1–P7 with 29 steps, and the per-phase entry conditions. Delete P0, P8, P9, P10 as phases. | 200 lines or fewer. 33 numbered steps. Every step cites requirement IDs and one command. Every scenario ID from §8 appears in a phase. |
| 8 | `docs/V4_P0_PROOF.md` | Do not rewrite. Add one header note: the pin record supersedes its gate framing, and its observed facts remain valid evidence. | The observed results and preserved log references are unchanged. |
| 9 | `AGENTS.md` | Update the authority list and gate order only. Point to the pin record and the three new notes. Remove the "P0 is blocked, do not start P1" line and state the new entry conditions. | No pre-V4 claim is used to justify a V4 rule. The file still describes the preserved pre-V4 surface as a separate concern. |
| 10 | All of the above | Check cross-references, ID counts, phase labels, and decision text together. Run `devenv shell -- testee verify --mode quick`. Review the whole change through Gitman as one lane. | Every link resolves. The gate passes. Gitman reports the lane and no unrelated work. |

**Acceptance checks for the whole edit:**

- Active ID count is 60 and the §8 arithmetic closes to 184 plus 2.
- Every one of the 184 original ID strings is findable in exactly one of: the active ledger, the
  history map, the native baseline record, the later-application note, or the future-work note.
- No V4 rule cites a pre-V4 module, consumer, overlay, or command as its reason.
- No proposed option or command name appears as syntax in normative text.
- Each of the 8 decisions and 5 experiments appears once, in the specification only.
- The guide's 33 steps cover all 60 active IDs and all 9 scenario IDs.
- `devenv shell -- testee verify --mode quick` passes.

## 12. The strongest argument against this recommendation

**The minimal layer may not be worth building at all.**

Native-only reaches all eight owner goals. The three gaps the minimal layer closes are
record-keeping gaps: a durable structured record, a source inventory separate from the store, and an
honest correspondence label. A disciplined owner with a shell script and a dated directory closes
all three for a fraction of the cost. The whole justification for Vendomat V4 rests on one
observation — that `attic push` emits no machine-readable output — plus a preference for a
structured receipt over a transcript. That is a thin foundation for a tool, 60 requirement IDs, and
seven proof phases.

**And the deferral has a real cost.** The source store's original purpose was to answer "which
retained source corresponds to the software this machine runs, and where can I read it?" My
recommendation answers that for locked inputs and declines to answer it for packaged dependencies —
which is most of what a machine runs. The owner may judge that the locked-input half alone is not
worth a source store, because `nix flake metadata --json` and a garbage-collection root already
provide it without Vendomat. If so, the honest conclusion is that V4 should be **one operation**
(`publish`) and `retain` should wait for the package-source mechanism to be proved.

**Two further risks against the recommendation:**

- Putting retained source in Attic couples two retention policies to one service and one disk. A
  disk loss takes both. The current design's separate source store, whatever its complexity cost,
  does not have that property.
- Choosing the flake form for publication gives up devenv's garbage-collection protection,
  evaluation caching, and containers, which the devenv documentation lists explicitly. If the
  owner's daily workflow depends on those, the publication path and the development path diverge
  more than this review assumes, and P2 step 1 will show it.

I still recommend the minimal layer. The receipt is the artefact that makes every other claim
checkable a year later, and no native tool writes it. But the owner should decide this on the value
of the receipt alone, not on the source store, because the source store's strongest half is now
native.
