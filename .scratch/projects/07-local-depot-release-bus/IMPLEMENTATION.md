# Implementation guide: the local depot and the release bus

**Status:** IN PROGRESS — Phase A execution started on 2026-09-29.
**Filed:** 2026-09-28
**Area:** machine layout (`nix-meta`), `devman` workflows, every repo's `gitman.toml`
**Host:** `server` (Dell Precision 5820, Xeon W-2125, 128 GB RAM)

## 0. Decision

Replace the GitHub-only development loop with a **machine-local depot** and a
**release bus** that propagates version bumps through the flake dependency graph.

> A 2 TB SATA SSD holds bare git repositories, a Nix binary cache, and an offline
> install source. A `post-receive` hook turns every landed push into a Dagu job.
> The job bumps each dependent's pin, relocks, verifies, lands, and pushes — which
> fires the next hook. GitHub becomes an offsite mirror.

**No forge service.** No Forgejo, no Gitea, no database, no listening port. The
depot is a directory. The trigger is a shell script. Dagu already runs.

**Locked decisions:**

1. **No forge software.** Dagu already owns scheduling, queues, retries, history,
   and a web UI. A forge would add a second scheduler competing for 4 cores.
2. **Flake inputs resolve from the depot**, not GitHub:
   `git+file:///srv/git/<repo>.git?ref=refs/tags/vN`.
3. **The depot lives on a different physical drive than the system.** This is what
   makes decision 2 safe. The namespace that names your inputs must survive the
   loss of the drive it installs.
4. **`nix-meta` never auto-lands.** The bus prepares and verifies its lane, then
   stops. A human lands the machine configuration.
5. **Verify gates come before automation.** A propagation engine with no gate is a
   breakage amplifier.

---

## 1. What already exists

Do not rebuild these. The design depends on them being present.

| Component | Where | Owns |
|---|---|---|
| **Dagu control plane** | `nix-meta/profiles/devman.nix`, `services.devman-dagu` | run order, queues, retries, history, web UI |
| **devman** | flake input, v0.7.0 | workflow registration, projection, cross-repo contract |
| **repoman** | per repo | conducts copyroom / gitman / testee / docman |
| **gitman** | per repo | lanes, verify gate, land, tag, push (jj + colocated git) |
| **testee** | per repo | pytest / ruff / ty |
| **vendomat** | flake input, v0.4.4 | the shared `*man` toolchain closure, artifact publishing |

devman's own trigger model already names the missing piece:

```
a save             -> watchexec -+
a commit / a push  -> git hook  -+-> devman run -> dagu enqueue -> Dagu -> devenv tasks
a developer        -> a prompt  -+
a cron expression  -> the daemon-+
```

The `push` arm fires from a **client-side** hook in a working copy. It is
skippable and it means "intent to push", not "landed on trunk". The depot supplies
a **server-side** `post-receive`, which is neither.

---

## 2. Verified mechanics

These were tested on this host on 2026-09-28. Do not re-derive them; do re-run
them if anything behaves unexpectedly.

**A `post-receive` hook fires on a plain filesystem-path push.** No daemon, no
port, no ssh.

```bash
git init --bare /tmp/t/bare.git
printf '#!/bin/sh\nwhile read o n r; do echo "$r -> $n" >> /tmp/t/fired.log; done\n' \
  > /tmp/t/bare.git/hooks/post-receive
chmod +x /tmp/t/bare.git/hooks/post-receive
git -C /tmp/t/work push /tmp/t/bare.git main
# observed: refs/heads/main -> b3ad0230717c6a58e700d77fb3f5691eb4e94d9c
```

**Nix resolves a bare repo by tag.**

```bash
nix flake metadata --json 'git+file:///tmp/t/bare.git?ref=refs/tags/v0.0.2'
# observed: locked.type=git  locked.rev=cf9643bb07bb  url=file:///tmp/t/bare.git
```

**A file:// binary cache round-trips.**

```bash
nix copy --to 'file:///tmp/nixcache?compression=zstd' /nix/store/<path>
# observed: 84 NARs + .narinfo written
```

**Sizes.** `/run/current-system` closure = **15.6 GB**. All 72 `.git` directories
= **4.2 GB**. The depot needs roughly 60-100 GB in total.

**Caveat, not yet solved:** a `file://` cache written by `nix copy` is unsigned.
Either pass `--option require-sigs false` at install time, or generate a local
signing key and add its public half to `nix.settings.trusted-public-keys`. The
second is correct. Decide in Phase C.

---

## 3. Current-state inventory

Measured 2026-09-28. Re-measure before acting; these age.

| Fact | Value |
|---|---|
| Repos under `~/Documents/Projects` | 72 |
| Repos with unpushed commits or a dirty tree | **28** |
| Repos carrying `v*` tags | 41 |
| Repos in the flake DAG | ~25 |
| DAG repos | **26** — all already have a `gitman.toml` |
| DAG repos whose `gitman.toml` declares `verify` | **2** (`gitman`, `repoman`) |
| Cross-repo flake edges | 31 |
| Local-path (`git+file:///home/...`) inputs in `nix-meta` | 7 |

Drives:

```
nvme0n1  3.6T  WD Blue SN5100 4TB   EMPTY, new         (Gen4 silicon on Gen3 x4)
nvme1n1  477G  NX-512 2280          holds everything, 91% full, no-name
sdb      1.9T  TEAM TM8PS7002T      SATA 6.0 Gbps, 130G used (7%), NTFS "SHARED"
sda      1.8T  WDC WD20EADS         5400rpm, ~2009, empty, ext4, /mnt/wd_green1
```

Both NVMe sit behind Intel VMD (`0000:b2:05.5`). An installer without the `vmd`
module does not see them. SATA enumerates normally.

`sdb` is **not a Windows install** — no ESP on the drive, no `Microsoft` directory
in the live ESP. Its 130 GB is `flora/training_data` (119 GB), an old
`structured-agents-v2` copy (11 GB), and a pre-flake `configuration.nix`. Nothing
symlinks to it. **Do not delete any of it without an explicit decision.**

---

## 4. Target architecture

```
workstation (4TB)             depot (2TB SATA)              offsite
~/Documents/Projects  ------> /srv/git/*.git     --mirror--> GitHub
  gitman land / push           post-receive hook
                                     |
                                     v
                            devman run release-bus
                                     |
                                     v
                            Dagu queue "release" (concurrency 1)
                                     |
                                     v
                     bump pin -> nix flake lock -> verify -> land -> push
                                     |
                                     v
                            nix copy --to file:///srv/cache
```

Drive roles, reliability matched to job:

| Drive | Mount | Role |
|---|---|---|
| 4 TB WD Blue NVMe | `/` | system, `/nix`, `/home` |
| 2 TB Team SATA | `/srv` | **depot**: bare repos, cache, install source |
| 512 GB NX NVMe | `/scratch` | Dagu runners, nix build dir — disposable |
| 1.8 TB WD Green | `/mnt/wd_green1` | restic repository |

Depot layout:

```
/srv/git/<repo>.git    72 bare repos       4.2 GB
/srv/cache/            nix binary cache   ~40 GB
/srv/installer/        flake + closure    15.6 GB
```

---

## 5. The dependency graph

Measured on 2026-09-29. Strip Nix comments before reading flake.nix. The
current graph has **24 repos and 28 edges**. Phase D must derive the edges from
the flakes. Do not copy an old hand-written edge list.

The current DAG roster is:

    agentman  argentic  atuout  copyroom  devman  docman  fornix  gitman
    inferference  loci-core  loci.nvim  nixbuild  nix-meta  nix-nvim  nix-paseo
    nix-secrets  nix-terminal  nixos-core  pyjutsu  pytuin  repoman
    silverbullet-server  templateer_v2  vendomat

Fornix is consumed at nix-meta/flake.nix:167 as
path:/home/andrew/Documents/Projects/fornix/nix/fornix-host. Its consumed
flake is a subdirectory; the repo has no root flake.nix.

The earlier 2026-09-28 inventory was wrong. Shellij and
structured-agents-v2 are commented out in nix-meta. Zelligate is
commented out in both nix-meta and nix-terminal. Nixvim appears only in a
retirement comment. Nix-meta has 13 direct Bullish-Design edges.
Nix-terminal has 4.

**Every repo in the 24-repo graph is inside nix-meta's transitive closure.**
That is why decision 3 in section 0 applies to all of them.

Reference chain, done by hand on 2026-09-28 and usable as the Phase D answer
key: agentman v0.0.2 -> vendomat v0.4.4 -> nix-meta 93fadde.

### Two simplifications that remove the hard parts

1. **The bus recurses through the hook.** When the bus lands vendomat and pushes
   it to /srv/git/vendomat.git, that push fires vendomat's own post-receive,
   which enqueues vendomat's dependents. You need a one-hop "who depends on X"
   lookup, **not a topological sort**. Correct order emerges from hook plus a
   concurrency-1 queue.
2. **The bump is idempotent.** Devman reaches nix-meta by three paths, so
   nix-meta gets enqueued three times. If the pin already reads the target
   version, exit 0 and do nothing. Diamonds resolve themselves with no scheduler
   logic.

## PHASE 0 — restic (no downtime, no risk, do first)

There are currently **no backups of anything**. Every later phase is a disk
operation. Do this before any of them.

1. In the `nix-secrets` repo, provision a `restic-password` secret in
   `secrets.yaml`. `profiles/secrets.nix` only enables names that already have
   encrypted material, so this must land first.
2. Add `profiles/backup.nix` to `nix-meta` — a profile, not a machine file,
   because backups are not machine specific. Export it in `profiles/default.nix`.

```
repository:  /mnt/wd_green1/restic
paths:       /home/andrew, /etc, /var/lib
excludes:    ~/.cache, .devenv, target, .venv, node_modules, .worktrees
schedule:    daily
retention:   --keep-daily 7 --keep-weekly 4 --keep-monthly 6
plus:        a weekly `restic check` timer
```

The excludes drop roughly 150 GB of rebuildable data.

**Gate:** `restic snapshots` lists a snapshot, **and** a test restore into `/tmp`
returns real files. An unverified backup is a guess. Do not proceed until a
restore has actually been performed.

---

## PHASE A — verify gates (independent of every drive decision)

**This is the highest-value work on the list and it blocks Phase D.** The bus
must never propagate a change that has not passed a gate.

**Measured scope (2026-09-29).** The DAG has 24 repos. All 24 already carry a
gitman.toml. Eleven files have an inert top-level verify; move those keys
under [publish]. Eleven repos already have a working gate. Fornix has no
gate. The owner chose to keep the nix-secrets omission for Phase A.

The DAG repos are:

    agentman  argentic  atuout  copyroom  devman  docman  fornix  gitman
    inferference  loci-core  loci.nvim  nixbuild  nix-meta  nix-nvim  nix-paseo
    nix-secrets  nix-terminal  nixos-core  pyjutsu  pytuin  repoman
    silverbullet-server  templateer_v2  vendomat

Pyjutsu is lowercase on disk; the flake input uses Pyjutsu.
Nix-meta, nix-terminal, nixos-core, and silverbullet-server have no
devenv.nix, so they take the Nix gate below.

**Nix-secrets decision (2026-09-29).** Keep its gate omitted for Phase A.
Inspection showed that its module declares SOPS settings and that decryption
happens at activation. nix flake check --no-build evaluates the flake and
does not decrypt secrets/. The omission is a scope decision, not a safety
limit. Revisit it before Phase D.

**Fornix gate.** Use the Testee gate below. The flake consumed by nix-meta
is nix/fornix-host. Consider a second gate for that subdirectory. Phase A
does not add it.

Python repos (agentman, copyroom, devman, docman, fornix,
templateer_v2, vendomat, pyjutsu, atuout, pytuin, ...):

    verify = ["devenv", "shell", "testee", "verify", "--mode", "ci"]
    verify_timeout = 1800

Nix repos (nixos-core, nix-terminal, nix-nvim, nixbuild, nix-paseo):

    verify = ["nix", "flake", "check", "--no-build"]
    verify_timeout = 1800

Nix-meta — the gate is evaluation of the real machine, which is the check that
was run by hand before landing 93fadde:

    verify = ["bash", "-c", "nix flake check --no-build && nix eval --raw .#nixosConfigurations.server.config.system.build.toplevel.drvPath > /dev/null"]
    verify_timeout = 3600

**Also in this phase:** land and push the 28 repos with dirty or unpushed work.
That list is the gate for Phase B and for the Phase E migration.

**Gate:** every DAG repo has a gitman.toml; every DAG repo except the
intentional nix-secrets omission has a working publish.verify; gitman
status is CANONICAL with zero dirty trees across all 71 Gitman-managed repos.

### Phase A gate evidence

The Phase A config lanes proved their gate values with Gitman's config loader.
The gates were installed, not exercised. The lanes used gitman land and gitman
push. Neither command runs verify. Phase A did not run gitman publish.

Argentic's recorded failure is in
argentic/.scratch/projects/017-argentic-ci-gate-failures/issue.md.
Vendomat's failure is in
.scratch/projects/08-vendomat-ci-gate-failures/issue.md.
Loci Core's failure is in
loci-core/.scratch/projects/001-loci-core-ci-gate-failures/issue.md.

No artifact exists on disk for shellij, templateer_v2, or
structured-agents-v2. Their reported failures are unconfirmed. Do not call
these gates green.

## PHASE B — the depot, initially on the 512 GB NVMe

The depot starts on `nvme1n1` **on purpose**. `sdb` holds 130 GB that has not been
adjudicated, and relocating it is not a prerequisite for anything here. The depot
is ~60 GB and moving it later is an rsync (Phase F).

1. Create `/srv/git` and one bare repo per project:

```bash
sudo install -d -o andrew -g users /srv/git
cd ~/Documents/Projects
for d in */; do
  n="${d%/}"
  [ -d "$d/.git" ] || continue
  git init --bare --initial-branch=main "/srv/git/$n.git"
done
```

2. Add the depot as `origin` and demote GitHub. gitman's `pick_remote` selects
   `origin` and refuses when several remotes exist with no `origin`, so this
   naming is forced and is also correct.

```bash
for d in */; do
  n="${d%/}"
  [ -d "$d/.git" ] || continue
  git -C "$d" remote rename origin github 2>/dev/null
  git -C "$d" remote add origin "/srv/git/$n.git"
  git -C "$d" push --all origin && git -C "$d" push --tags origin
done
```

3. Re-point `nix-meta`'s 7 `git+file:///home/andrew/Documents/Projects/<x>` inputs
   at `git+file:///srv/git/<x>.git?ref=refs/tags/vN`. These are currently broken
   for a fresh install because they name **working copies on the system drive**.
   The depot form fixes both defects: bare repos have immutable tags, and the
   drive survives the system drive being wiped.

**Gate:** `git -C <repo> ls-remote origin` succeeds for all 72.
`nix flake metadata 'git+file:///srv/git/vendomat.git?ref=refs/tags/v0.4.4'`
resolves. `nix flake check` still passes in `nix-meta`.

---

## PHASE C — binary cache and install source

1. Decide the signing question from section 2. Preferred: generate a key, store
   the secret half through sops-nix, add the public half to
   `nix.settings.trusted-public-keys`, and sign on copy.

2. Populate the cache and the installer tree:

```bash
sudo install -d -o andrew -g users /srv/cache /srv/installer
nix copy --to 'file:///srv/cache?compression=zstd' /run/current-system
nix copy --to 'file:///srv/cache?compression=zstd' \
  "$(nix eval --raw ~/Documents/Projects/nix-meta#nixosConfigurations.server.config.system.build.toplevel)"
```

3. Add the cache as a substituter in `nix-meta`:

```nix
nix.settings.substituters = [ "file:///srv/cache" ];
```

4. **Prove the offline install in a VM before trusting it.** Do not discover this
   works or does not work during Phase E.

```bash
nixos-install --root /mnt/new \
  --flake 'git+file:///srv/git/nix-meta.git?ref=refs/tags/vN#server' \
  --option substituters 'file:///srv/cache' \
  --option require-sigs false
```

**Gate:** a VM installs from `/srv` **with networking disabled** and boots.

This phase also deletes the `nix-secrets` bootstrap problem: a depot input needs
no GitHub SSH credentials for root at install time.

---

## PHASE D — the release bus

Home: **devman**. It already owns cross-repo workflows and the
`DEVMAN_PROJECT_DIR` contract, and it adds no node to the graph the bus walks.
(This guide is filed under `vendomat/.scratch` for storage only. If the bus is
instead built in vendomat, note that vendomat is itself an L1 node in the DAG and
would then be modifying a graph it belongs to.)

Five pieces. Only two contain real logic.

**D1 — the `post-receive` hook** (~15 lines of `sh`, templated into all 72 bare
repos). It reads refs from stdin, ignores everything that is not a tag on trunk,
and calls `devman run release-bus --repo <name> --tag <vN>`. It must exit 0
always; a failing hook must never block a push.

**D2 — reverse-dependency lookup** (~100 lines). "Who depends on X." Derive it
from `nix flake metadata --json` over the DAG repos. **Derive, never declare** — a
declared graph drifts from the flakes, a derived one cannot. This also supplies
the closure check that enforces decision 3.

**D3 — the pin bump** (~100 lines). Rewrite one input's `?ref=refs/tags/...` in a
`flake.nix`. Must be **idempotent** (already-correct pin exits 0) and must
**refuse** on an unexpected URL shape rather than guess. This replaces the
`sed 's|vendomat?ref=refs/tags/v0.4.3|...v0.4.4|'` that was used by hand.

**D4 — the Dagu release workflow.** Queue `release`, **concurrency 1**. Topological
order along a path is inherently serial, so the queue matches the problem. The
host is a 4-core Xeon W-2125 shared with `inferference-router`, SilverBullet,
Atuin, and `argentic`; the runner slice needs a `CPUQuota` and an `IOWeight`.
Per dependent: bump -> `nix flake lock` -> verify gate -> land -> tag -> push.

**D5 — the mirror drift workflow.** Weekly cron. Diff each repo's `/srv/git` trunk
against `github/main`. Fail loudly on drift.

> This closes the one real regression in this design. Because inputs resolve from
> the depot, the GitHub mirror is never exercised by the pipeline and can rot
> silently. The depot covers **drive** failure; GitHub covers **machine** failure.
> Neither is optional.

**Build order: D2 and D3 first, read-only, tested against the real 31 edges.**
Then a dry-run mode that prints the plan and changes nothing. Then D1 and D4.

**Gate:** dry-run the `agentman v0.0.2 -> vendomat v0.4.4 -> nix-meta` chain and
diff the proposed result against what was landed by hand on 2026-09-28. That
commit is the answer key. Report-only for the first month; enable landing after
the dry-run diffs come back clean.

### Bus policy

| Situation | Action |
|---|---|
| Patch or minor bump, verify passes | land, tag, push |
| Major bump | stop, open a lane, notify |
| Verify fails | stop, leave the lane with the failing output attached |
| Conflict during relock | stop, never auto-resolve |
| Target is **`nix-meta`** | **never auto-land** — prepare and verify the lane, then stop |

This mirrors the standing rule in the user's global `CLAUDE.md`: land once verify
passes, stop when something is unusual. `nix-meta` is exempt because it is the
machine.

---

## PHASE E — migrate the system to the 4 TB drive

Now an **offline** install from `/srv`. No network, no GitHub round trip, no
17-input fetch, no rate limits.

**The one thing that breaks the system if missed:** `profiles/secrets.nix`
decrypts with `ageKeySource = /etc/ssh/ssh_host_ed25519_key`. A fresh install
generates a **new** host key and sops-nix then fails to decrypt
`tailscale-auth-key` and `subconscious-api-key`. Preserve these two files and
restore them **before first activation**:

```
/etc/ssh/ssh_host_ed25519_key
/etc/ssh/ssh_host_ed25519_key.pub
```

Steps:

1. Fresh restic backup, verified.
2. Record current UUIDs:
   `root e6b180fa-534a-4b71-aff8-f9fe2e6d0834` (btrfs),
   `boot 0086-EC69` (vfat),
   `swap 5445f100-dc12-4d50-b7b2-24f7d4d3b9a9` (to be dropped).
3. Partition `nvme0n1` from the running system. No installer USB is needed — the
   512 GB is never modified, so it stays bootable and rollback is a BIOS boot-order
   change. Keep a USB on a stick as insurance only.

```bash
# p1 = 2 GB ESP, p2 = remainder
mkfs.vfat -F32 -n BOOT /dev/nvme0n1p1
mkfs.ext4 -m 1 -L nixos  /dev/nvme0n1p2
```

   `-m 1` instead of the default 5% reserve reclaims about 145 GB on 3.6 TB.
   2 GB ESP because space on a 4 TB drive is free and kernels only grow.

4. Update `machines/hardware/server.nix`: new UUIDs, remove every `subvol=`
   option, remove the `/.snapshots` entry, empty `swapDevices`. The 32 GB swap
   partition is dropped — 128 GB RAM plus 62.7 GB zram, headless, 0 B in use.
5. Restore the host key into `/mnt/new/etc/ssh/` with mode 0600.
6. `nixos-install` from `/srv` as proven in Phase C.
7. Reboot, set BIOS boot order to the 4 TB, verify `inferference-router`,
   `silverbulletServer`, the Atuin server, `argentic`, and the tailnet identity.

**Leave `nvme1n1` untouched through this phase.** It is the rollback, and it is
also holding the depot.

**Do not reformat the 512 GB for at least a month** after a successful boot. It is
the only record of host-local state configured by hand over the years.

---

## PHASE F — final drive allocation

Only after Phase E has been stable for several weeks.

1. Adjudicate the 130 GB on `sdb` (`flora/training_data` 119 GB, an old
   `structured-agents-v2` 11 GB, a pre-flake `configuration.nix`). If it is still
   wanted, move it to the 4 TB — which now has ~3.2 TB free — and give it a restic
   policy. **Nothing here is deleted without an explicit decision.**
2. Reformat `sdb` to ext4, rsync `/srv` across (~60 GB, minutes), update the mount
   in `machines/server.nix`. `sdb` is currently declared at `server.nix:620` as an
   `ntfs3` automount at `/mnt/shared`.
3. Repoint the depot input URLs if the path changes. Keep the path `/srv` so that
   nothing has to change.
4. The 512 GB becomes `/scratch`: Dagu runners, the nix build directory, CI caches.
   Write-heavy and disposable, which is the correct job for the least trustworthy
   drive in the machine.

Why `sdb` and not the 512 for the depot:

- **Wear.** The Team SSD is at 7% used and near-idle. The NX-512 ran at 91% full
  for the life of the machine, which is its worst operating point.
- **VMD.** Both NVMe sit behind `0000:b2:05.5`. A recovery medium belongs on the
  bus that needs no special installer module.
- **Removability.** A 2.5" SATA SSD plus a USB adapter plugs into anything. An M.2
  2280 needs an enclosure.
- Speed is irrelevant here: 6.0 Gbps reads the 15.6 GB closure in ~30 seconds.

---

## 6. Open decisions

1. **Does the framework laptop need to resolve these inputs?** `git+file:///srv/...`
   is local only. Git over SSH needs no new software — sshd already runs key-only
   on `tailscale0:22` — so `git+ssh://andrew@server.tail770f47.ts.net/srv/git/<x>.git`
   covers the tailnet. But `file://` is simpler at install time. Pick one form for
   all inputs, or accept two.
2. **Do the ~47 non-DAG repos move to the depot too?** Only the ~25 in `nix-meta`'s
   closure need to. Uniformity argues for all of them and the drive has room for
   100x the data.
3. **Cache signing** (section 2): local signing key, or `require-sigs false`.
4. **`/mnt/flex` (`FLEX_252`) and the two WD Re 2 TB bays** are declared in
   `server.nix` but not connected. The WD Re are 7200 rpm enterprise drives and
   would make a better restic target than the 2009 WD Green. Asked three times,
   not yet answered.
5. **Is `flora`'s 119 GB of training data still wanted?** It sits on one drive with
   no backup.

---

## 7. Working rules for the implementing session

**Version control.** Route everything through gitman. Never run raw `jj` or `git`
for mutations. gitman runs from its own pinned repository environment:

```bash
cd ~/Documents/Projects/gitman && devenv shell -- bash -c 'cd <target-repo> && gitman status'
```

**Never run `devenv` from inside the target repo.** It overwrites that repo's
`devenv.lock` with gitman's own input closure and drops the repo's real inputs.
This has already happened twice in this repository and produced a lane
(`preserve-devenv-lock`) that captured the corruption rather than reverting it.
`devenv --dir` was removed in devenv 2.2.2, and `--from path:` is not a
replacement — it loads gitman's config but evaluates it against the current
directory.

**Do not trust a raw `git status` in a colocated repo.** jj's record of git's
`HEAD` goes stale and reports committed-and-pushed files as modified. Check
against trunk before building a plan on it.

**Commits carry no AI attribution.**

**Land and push a lane once its verify passes.** Stop and ask when verify fails or
is skipped, when the lane touches shared or risky files (secrets, CI config,
release branches), or when a merge conflict appears.

**Writing style.** Simplified Technical English: one idea per sentence, active
voice, one word per meaning, no filler.
