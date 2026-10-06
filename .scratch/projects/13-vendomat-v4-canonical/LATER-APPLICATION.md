# Later application: Jujutsu, btrfs, and bubblewrap

**Date:** 2026-10-06. **Status:** Canonical record of a later reusable module. **Outside V4.**
**Decision:** `D-APP-SCOPE`, accepted 2026-10-04.

This file holds the design case and the 31 conditional requirement IDs `V4-APP-001`–`031`. None of
them gates a V4 phase. None is reused or renumbered. The case shows what native composition can
express. It does not change Vendomat's core and it does not create a Vendomat runtime, image cache,
or deployment engine.

Opening this module needs its own review. Its results never retroactively gate the V4 P1–P6
application proof.

## Move map

| Moved from | Moved to | Change |
| --- | --- | --- |
| Project-10 `V4-SPEC.md` §9, "Conditional Jujutsu–btrfs–bubblewrap composition case" | §2–§6 of this file | Text preserved. Illustrative option names remain marked proposed. |
| Project-10 `V4-REQUIREMENTS.md`, conditional table, `V4-APP-001`–`031` | §7 of this file | ID strings and observable results preserved. The `Source` column collapses to `Owner case; D-APP-SCOPE`, which it already was for every row. |
| Project-10 `V4-SPEC.md` §10 rows `Q-QUEUE`, `Q-APP-STATE`, `Q-APP-NET`, `P-IMAGE`, `P-SANDBOX` | §8 of this file | Preserved as this module's open questions. |

The core V4 contract keeps one sentence of boundary, in
[CONCEPT-V4.md](./CONCEPT-V4.md) under "Boundaries".

## 2. Purpose and ownership

A reusable application module composes three focused contributions: Jujutsu selects a commit, a btrfs
adapter materializes its files, and bubblewrap runs those files with a matching Nix runtime. The
application contract states admission, instance identity, and mutable state behaviour. A devenv
contribution supplies project tools, checks, and a local run. A NixOS contribution supplies the
persistent host service, storage, permissions, and supervision. A Home Manager contribution is
optional, for a user launcher or user service.

Vendomat inspects source, gates selected Nix outputs, publishes their runtime closures, and records
evidence. It does not own the application's runtime state and does not schedule arbitrary
applications.

The following configuration is **proposed and illustrative**. A prototype must establish the actual
options and paths. No name here is an established devenv, NixOS, or Vendomat interface.

```nix
# devenv.nix — proposed local project consumer
{ ... }: {
  imports = [ ./modules/revision-app/devenv.nix ];

  revisionApp = {
    enable = true;
    repository = ./.;
    runtime.output = "revision-runtime";
    limits.running = 3;
    limits.queued = 5;
  };
}
```

```nix
# devenv.nix — proposed host composition with native Machines syntax
{ ... }: {
  machines.workstation = {
    system = "x86_64-linux";
    target.host = "root@workstation.example";
    nixos = {
      imports = [ ./modules/revision-app/nixos.nix ];
      services.revisionApp = {
        enable = true;
        stateRoot = "/var/lib/revision-app";
        limits.running = 3;
        limits.queued = 5;
      };
    };
  };
}
```

The requested revision is an operation input, not a mutable Nix option. The operation resolves it to
one full commit identifier before admission. The machine example deliberately uses native `machines`
and a proposed NixOS service option. It introduces no `vendomat.*` option and no new deployment plan.

Jujutsu documents that a change identifier may refer to several commit versions after rewriting or
divergence. A commit identifier names one commit. The application resolves the requested revset to
**exactly one full commit identifier** before any materialization or queue admission. An empty or
multi-commit result fails. A later change-identifier movement cannot change an accepted request.

## 3. Materialization contract

The adapter reads the exact commit tree from Jujutsu and materializes a verified read-only btrfs
image for execution. Readers cannot see an incomplete image. A writable staging subvolume followed by
a read-only snapshot is one possible implementation, subject to the later fixture.

A Jujutsu commit is **not** a btrfs snapshot: a btrfs snapshot copies another btrfs subvolume's
initial contents.

The mapping record binds repository identity, full commit identifier, tree or file manifest identity,
materialization format version, btrfs filesystem and subvolume identity, read-only status, creation
result, and verification result. The commit identifier names selected source. The btrfs identifier
names one materialized storage object. Neither substitutes for the other. A second materialization of
the same commit may have a different btrfs identifier.

The adapter must handle regular files, paths, executable bits, and symlinks consistently. It must
reject unsupported entries, path escapes, and unresolved conflicts rather than claim exact
correspondence. Jujutsu can record conflicts inside commits and materialize markers in a working
copy.

Publication of the image is atomic for readers: a failed or incomplete stage never becomes runnable.
A reused image must pass its mapping and read-only checks. Retain the Jujutsu commit object or an
independently verified source representation for any claimed rematerialization. An image alone proves
neither that its commit remains fetchable nor that it can be regenerated. A running instance pins its
image against cleanup. A snapshot is local storage and needs its own backup or transfer plan.

## 4. Matching Nix runtime and sandbox

The runtime selection evaluates the native Nix declarations and lock at the pinned commit, or uses a
previously verified output mapped to that exact selection. The record binds full commit identifier,
relevant native lock contents, target system, derivation, and output paths. It never silently uses
the current branch's runtime for an older commit. Missing or incompatible runtime inputs fail the
request. Local realization can use the local Nix store and native build policy with no Attic and no
Vendomat. Attic may distribute the runtime output closure. It must not claim to distribute the btrfs
image or writable state.

Bubblewrap runs one application's selected process tree. Its mount policy exposes the read-only
image, the required Nix runtime paths, and one instance's writable state. It hides unrelated host
homes, source archives, credentials, and other instance state. The module declares network, device,
process, and interprocess communication access explicitly. The wrapper validates the image and
runtime identities before launch and records what it actually mounted. The chosen host must support
the required namespace setup, and it must fail closed if the required isolation cannot be
established.

Bubblewrap provides bind mounts and namespaces for a process. It does not build or activate a NixOS
system.

Each instance receives a unique durable instance identifier and a distinct writable state directory.
Several commits and several instances of one commit can run at once. State survives or expires under
the application's declared policy, independently of image, source, Nix output, and system generation
retention. A NixOS rollback does not undo writes in an instance directory. The process supervisor may
use systemd instance units and resource controls. Those units do not by themselves define an
application-wide running and queued admission limit.

## 5. Admission and concurrent runs

The application contract exposes a configurable positive running limit and a nonnegative queued
limit. `limits.running` and `limits.queued` above are **proposed names**. The counts apply across all
revisions of this application on one host.

Admission atomically starts a request when a running slot exists, queues it when only a queue slot
exists, or rejects it with a capacity result. A queued record pins the full commit identifier and the
runtime selection. It never resolves a mutable revset again. Cancellation, process exit, failed
preparation, and supervisor restart must not double launch and must not exceed the limits.

Queue durability, ordering, and count ownership belong to this module's design and prototype. Do not
infer them from systemd's unit job queue.

The application declares whether each instance is a user or a system service. NixOS supplies its host
storage and service policy. Home Manager may supply a user-facing launcher. The devenv contribution
permits a local run with native inputs and a writable local state path. The same exact commit,
runtime, and image checks apply. No local run contacts a Vendomat process and none requires an Attic
push.

## 6. Conditional fixture

An application fixture must run two different commits and two instances of one commit concurrently.
It must show the same pinned commit and runtime in each instance report, distinct writable state, and
a read-only image. It must fill running and queued capacity, reject the next request, and show a
queued request start after a slot opens. It must reject ambiguous revisions, conflicted or
unsupported trees, altered image mappings, missing runtime closure paths, and sandbox setup failure.
It must restart the host supervisor during queued work with no duplicate execution. It must restore
source, image, Nix output, and instance state as separate results.

These gates apply only if the owner brings this application into scope.

## 7. Conditional requirements

All rows have owner source `Owner case; D-APP-SCOPE`. They do **not** gate V4.

| ID | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- |
| `V4-APP-001` | The reusable application module composes Jujutsu selection, btrfs image, and bubblewrap execution behaviour. | Application module | Import the module. Exercise each operation through its documented boundary. |
| `V4-APP-002` | The application exports a local devenv contribution. | Application module | Enter the project shell. Exercise a local run with no persistent machine activation. |
| `V4-APP-003` | The application exports a NixOS contribution for persistent host needs. | Application module | Evaluate the NixOS fixture. Inspect service, storage, and permissions. |
| `V4-APP-004` | A requested revset resolves to exactly one full Jujutsu commit identifier before admission. | Jujutsu adapter | Request zero, one, and several revisions. Only the single result proceeds. |
| `V4-APP-005` | A queued or running request keeps its full commit identifier when its change identifier later moves. | Application module | Admit a request, rewrite the change, then compare the executed commit identifier. |
| `V4-APP-006` | The adapter materializes the pinned commit's file tree into a verified btrfs image. | btrfs adapter | Materialize a commit. Compare file contents, paths, modes, and symlinks. |
| `V4-APP-007` | The adapter publishes only a fully verified read-only subvolume. | btrfs adapter | Interrupt materialization. Confirm the incomplete image cannot launch. |
| `V4-APP-008` | A mapping record binds full commit identifier, source manifest, and btrfs subvolume identity. | btrfs adapter | Materialize the same commit twice. Inspect the equal source identity and the distinct physical identities. |
| `V4-APP-009` | Unsupported or conflicted commit tree entries fail materialization explicitly. | btrfs adapter | Use conflicted, path-escape, and unsupported entry fixtures. Inspect the rejection. |
| `V4-APP-010` | Reusing an image rechecks its mapping and read-only state. | btrfs adapter | Alter the mapping or the image mode. Confirm the launch fails. |
| `V4-APP-011` | The selected Nix runtime derives from native files and locks at the pinned commit, or from an exact verified mapping. | Application module | Run an old commit after a head runtime update. Inspect the old commit's runtime path. |
| `V4-APP-012` | A missing or incompatible runtime selection fails before process launch. | Application module | Remove a required runtime path. Inspect the failure and the absence of a process. |
| `V4-APP-013` | Bubblewrap mounts the image read-only and one instance's state writable. | Bubblewrap contribution | Attempt writes to the image and the state from inside. Only the state write succeeds. |
| `V4-APP-014` | An instance cannot read another instance's writable state by default. | Bubblewrap contribution | Start two instances. Attempt a cross-instance read from each sandbox. |
| `V4-APP-015` | An instance cannot read host source archives or cache credentials by default. | Bubblewrap contribution | Probe denied host paths from inside the sandbox. |
| `V4-APP-016` | Required sandbox setup failure prevents an unsandboxed launch. | Bubblewrap contribution | Deny the namespace setup. Confirm no application process starts. |
| `V4-APP-017` | Each admitted instance has a unique identifier and separate writable state. | Application module | Run two instances of one commit. Compare identifiers and independent writes. |
| `V4-APP-018` | Two distinct commits can run concurrently on one host. | Application module | Start both. Inspect the simultaneous processes and pinned images. |
| `V4-APP-019` | Two instances of one commit can run concurrently on one host. | Application module | Start both. Inspect the simultaneous processes and distinct state. |
| `V4-APP-020` | Configured running and queued limits apply across all revisions of one application on a host. | Application module | Fill the slots with mixed commits. Inspect the running and queued counts. |
| `V4-APP-021` | A request beyond both limits receives an explicit capacity result and does not start. | Application module | Submit one excess request. Inspect the result and the process list. |
| `V4-APP-022` | A queued request retains its pinned commit and runtime selections until it starts or fails. | Application module | Queue a request, change the branch and lock, release a slot, then inspect the executed identifiers. |
| `V4-APP-023` | Concurrent admission never exceeds the configured running or queued limits. | Application module | Race parallel requests against small limits. Count the accepted states. |
| `V4-APP-024` | Supervisor restart cannot launch one accepted request twice. | Application module | Restart during queued and running work. Compare durable instance identifiers and processes. |
| `V4-APP-025` | Instance state retention is independent of source, image, Nix output, and NixOS generation retention. | Application module | Change or roll back each domain. Inspect the retained instance data. |
| `V4-APP-026` | A local run succeeds with no live Vendomat process and no Attic publication. | Application module | Stop Vendomat, deny Attic, realize native inputs locally, and run the pinned commit. |
| `V4-APP-027` | Attic publication covers the selected Nix runtime outputs and makes no btrfs-image or mutable-state distribution claim. | Vendomat | Publish the runtime. Inspect the receipt, the remote cache, the image, and the state separately. |
| `V4-APP-028` | A whole-system candidate uses native NixOS build and activation, or a virtual-machine test. | NixOS | Change the system module. Perform a native build or VM test, not only a bubblewrap run. |
| `V4-APP-029` | Invalid running or queued limit values fail configuration. | Application module | Set a zero running limit and a negative queued limit. Inspect the evaluation error. |
| `V4-APP-030` | A running instance keeps its image available until it exits. | Application module | Attempt image cleanup during a run. Confirm the image remains readable. |
| `V4-APP-031` | A claimed rematerialization retains the exact commit object, or a separately verified source copy. | Jujutsu adapter | Remove the commit and the image. Confirm the rematerialization claim fails unless a verified copy restores it. |

## 8. Open questions for this module

| ID | Question | Evidence or decision needed |
| --- | --- | --- |
| `Q-QUEUE` | How does the module implement its limits, queue ordering, and restart behaviour? | Owner decision and a concurrent fixture. Do not infer from systemd's job queue. |
| `Q-APP-STATE` | How long must stopped instance state and queued requests remain? | Owner retention policy and a restore fixture. |
| `Q-APP-NET` | Which network, device, and interprocess communication access does the application need? | An application threat model and a bubblewrap host probe. |
| `P-IMAGE` | How does the adapter preserve tree entries and reject conflicts safely? | A btrfs fixture with files, modes, symlinks, conflicts, and failure injection. |
| `P-SANDBOX` | Which bubblewrap mount and namespace policy works on the selected hosts? | A host test, including denied host access and setup failure. |

## 9. Recovery domains

These remain separate results if this module enters scope.

| Domain | Native rollback or restore | Protected state |
| --- | --- | --- |
| btrfs source image | Re-select a retained, verified image, or rematerialize the pinned commit | Commit objects, image and mapping record |
| Instance state | Application-defined migration and backup | Per-instance mutable data |
| Nix runtime | Rebuild from the pinned selection | Derivation and output paths |

A btrfs snapshot is not a backup by itself. A NixOS rollback does not undo instance writes.
