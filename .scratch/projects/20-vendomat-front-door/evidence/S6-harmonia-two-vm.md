# S6: signed Harmonia cache across two virtual machines

**Date:** 2026-10-11. **Result:** PASS on all six steps in VMs. Two project 19 claims need a change
(section 7). Fixture: [fixtures/s6-harmonia/test.nix](fixtures/s6-harmonia/test.nix)
(NON-PRODUCTION; test-only keys).

## 1. Questions and hypotheses

| # | Question | Hypothesis |
| --- | --- | --- |
| Q1 | Does the stock `services.harmonia` module give a clean boot when the signing key is absent? | Socket activation hides the fault until the first request. |
| Q2 | Which form gives zero failed units: plain module, `ConditionPathExists` on the service, or a path unit that starts the socket? | The path unit. |
| Q3 | Does Harmonia serve and sign after a key arrives post-boot? | Yes. |
| Q4 | Does a symlink in `/nix/var/nix/gcroots/` keep a release output through `nix-collect-garbage`? | Yes. |
| Q5 | Does a second VM substitute a rooted path, verify the signature, and refuse a path signed by another key? | Yes. |
| Q6 | Does the client fall back to a local build when the path is absent, or the cache is down or silent? | Project 19 claims yes ("a missing cache never blocks a build"). |
| Q7 | Does Harmonia serve a path that was never a release output? | Yes (project 18 saw it on loopback). |

## 2. Exact inputs

| Item | Value |
| --- | --- |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`, the pin of `nix-systems` (`vendomat.toml`, `[passthrough]`). narHash `sha256-H83yz/do+hjOO0uujHyH8RgtIQP2v7Mw+cLwcZK/xKc=`. |
| Harmonia | 3.3.0 (`curl /version` answered `harmonia-cache 3.3.0`) |
| Nix in the VMs | 2.34.8. The host has 2.34.7. |
| Test driver | `pkgs.testers.runNixOSTest`, KVM, four nodes |
| Nodes | `cachehost` (path-unit form), `condhost` (`ConditionPathExists` on the service), `plainhost` (stock module), `client` |
| Module options at this pin | `services.harmonia.cache.{enable,signKeyPaths,settings}`. `services.harmonia.{enable,signKeyPath,signKeyPaths,settings}` are renamed aliases. `signKeyPath` (singular) is deprecated and warns. |
| Module behavior (source) | `harmonia.socket` is wanted by `sockets.target`. `harmonia.service` has `LoadCredential=sign-key-N:<path>`, `Restart=on-failure`, `DynamicUser`, `PrivateNetwork=true`. |
| Keys | Two test-only keys, `vendomat-s6-good-1` and `vendomat-s6-bad-1`, made with `nix key generate-secret`. The run embedded them; the committed fixture is redacted (see "Fixture redaction" below). |
| Key path | `/var/lib/vendomat/keys/harmonia.secret`, mode 0400, `root:root`, directory 0700 from `systemd.tmpfiles` |
| Client Nix settings | `substituters = http://cachehost:5000 http://plainhost:5000`; `trusted-public-keys` = the good public key only. No cache.nixos.org. |
| Test command | `nix build -L --file .scratch/projects/20-vendomat-front-door/evidence/fixtures/s6-harmonia/test.nix --out-link <path>` |
| Upstream docs | Harmonia README (master): lists `sign_key_paths`, `bind`, `priority`. It does not say a missing key file is an error. It does not mention socket activation or credentials. This is evidence about upstream only. |

Form (b2), the recommended form, in full:

```nix
systemd.tmpfiles.rules = [ "d /var/lib/vendomat/keys 0700 root root -" ];
services.harmonia.cache = {
  enable = true;
  signKeyPaths = [ "/var/lib/vendomat/keys/harmonia.secret" ];
};
systemd.sockets.harmonia = {
  wantedBy = lib.mkForce [ ];
  unitConfig.ConditionPathExists = "/var/lib/vendomat/keys/harmonia.secret";
};
systemd.paths.harmonia-key = {
  wantedBy = [ "multi-user.target" ];
  pathConfig = {
    PathExists = "/var/lib/vendomat/keys/harmonia.secret";
    Unit = "harmonia.socket";
  };
};
```

## 3. Expected

Each hypothesis in section 1 holds, except Q6, where project 19 expects a fallback for every
cache fault.

## 4. Actual, per step

Timings come from the final run (run 6). Runs 1 to 3 gave the same results for steps 1 to 4b.

### Step 1: keyless boot — PASS

| Node | Reaches multi-user | `is-system-running` | Failed units | Socket | Service |
| --- | --- | --- | --- | --- | --- |
| `plainhost` (stock) | yes | `running` | none | listening on `*:5000` | inactive (dead) |
| `condhost` | yes | `running` | none | listening on `*:5000` | inactive; condition not yet checked |
| `cachehost` (path unit) | yes | `running` | none | inactive, no listener | inactive; `harmonia-key.path` waiting |

All four nodes reached `multi-user.target` in 52 s in run 6 (23 to 28 s in runs 1 to 3). Userspace
boot took 13.6 to 14.9 s on every node.

Step 1b: the first request before the key exists breaks the two guard-less forms.

- `plainhost`: the service ran five times in 1.3 s. Each run ended with
  `Failed at step CREDENTIALS ... No such file or directory` (status 243). Then
  `harmonia.service: Failed with result 'start-limit-hit'` and
  `harmonia.socket: Failed with result 'service-start-limit-hit'`. The client got
  `Connection reset by peer`. State: `degraded`, two failed units.
- `condhost`: the service start was skipped 20 times
  (`unmet condition check ConditionPathExists=...`). Then
  `harmonia.socket: Trigger limit hit, refusing further activation`. Result: `trigger-limit-hit`.
  State: `degraded`, one failed unit (the socket).
- `cachehost`: curl got `Connection refused` (exit 7) at once. State: `running`, zero failed units.

### Step 2: key delivery after boot — PASS

Delivery method: stage as `key.in`, `install -m 0400 -o root -g root` to `harmonia.secret.tmp`, then
`mv` into place (an atomic rename).

| Node | Serves without help | Time to first 200 | Recovery needed |
| --- | --- | --- | --- |
| `cachehost` | yes | 0.5 s | none |
| `plainhost` | no | still failing at 18 s | `systemctl reset-failed; systemctl restart harmonia.socket` |
| `condhost` | no | still failing at 16 s | the same |

After delivery, `/nix-cache-info` answered `StoreDir: /nix/store`, `WantMassQuery: 1`,
`Priority: 50`. A narinfo carried `Sig: vendomat-s6-good-1:...`. The service ran as user `harmonia`
(`DynamicUser`), with `LoadCredential=sign-key-0:/var/lib/vendomat/keys/harmonia.secret` and
`PrivateNetwork=true`. The key file stayed `400 root:root`. A user other than root never reads the
file; systemd passes it as a credential.

Reboot of `cachehost` with the key present: `running`, zero failed units, socket listening,
serving 200. Time to multi-user 18 to 32 s.

Key rotation: after `plainhost` got the bad key at the same path, the old key kept signing. After
`systemctl restart harmonia.service`, narinfo carried `Sig: vendomat-s6-bad-1:...`. The service reads
the key only when it starts.

### Step 3: release root and garbage collection — PASS

- `nix-store --add-root /nix/var/nix/gcroots/vendomat/release-1 -r <drv>` built the output and made
  a symlink root. `nix-store --gc --print-roots` listed
  `"/nix/var/nix/gcroots/vendomat/release-1" -> /nix/store/...-s6-release`.
- `nix-collect-garbage` (6.5 s, 166 paths deleted): the release output stayed, the unrooted output
  and its `.drv` were deleted.
- The narinfo for the release path stayed 200. The narinfo for the unrooted path went from 200 to
  404. The cache retains exactly what the host GC retains.
- Step 3b (the `cachehost` store layer on disk, then reboot): the release root and output survived
  the reboot. A second `nix-collect-garbage` deleted the never-rooted `private` path (narinfo
  200 to 404) and kept the release path (narinfo 200).

### Step 4: cold substitution — PASS

- Client store lacked the path (`ABSENT-COLD`). `nix-store -r <path>` printed
  `copying path ... from 'http://cachehost:5000'` and took 0.2 s.
- `nix path-info --sigs` on the client: `vendomat-s6-good-1:c4FV...` (the cache signature).
  `nix store verify --sigs-needed 1` exited 0.
- Path signed by another key (step 4b): `plainhost` served a path signed with `vendomat-s6-bad-1`.
  - `nix-store -r <path>` on the client exited 1:
    `warning: ignoring substitute ... from 'http://plainhost:5000', as it's not signed by any of the keys in 'trusted-public-keys'`
    then `error: path ... is required, but there is no substituter that can build it`.
  - `nix-store -r <drv>` ignored the substitute with the same warning, built locally (0.4 s), and
    `nix path-info --sigs` showed `ultimate` (a local build, no cache signature).

### Step 5: missing path and cache faults — PARTIAL PASS

| Case | Result | Time |
| --- | --- | --- |
| 5a. Path absent from the cache, cache up (404) | Local build, exit 0 | 0.3 s |
| 5b. Cache down, connection refused, default settings, `nix-store -r` | **Exit 1, no build.** `error: unable to download '.../<hash>.narinfo': Could not connect to server (7)` after 5 attempts | 5.0 s |
| 5b. The same, `nix-build` | Exit 1, no build | 4.8 s |
| 5b. The same, `nix build` | Exit 1, no build | 5.0 s |
| 5b. The same, `--option fallback true` | Exit 0, local build | 4.4 s |
| 5c. Cache VM frozen (no packets answered), defaults | **Exit 1, no build** | 44.3 s |
| 5c. The same, `--option fallback true` | Exit 0, local build | 20.6 s |
| 5c. The same, `--option connect-timeout 3` (no fallback) | Exit 1, no build | 20.1 s |
| 5c. The same, `nix build`, defaults | Exit 1, no build | 21.3 s |

- The effective `connect-timeout` is 15 s. It is a Nix 2.34.8 default; `/etc/nix/nix.conf` does not
  set it. `download-attempts` is 5. `fallback` is `false`.
- A frozen host and a stopped service both fail without `fallback = true`. With `fallback = true`
  the client builds locally and exits 0.
- The 44 s and 20 s timings vary with the ARP state of the client. One attempt timed out at 15 s,
  and others failed at 3.3 s with `Could not connect to server`.
- Not tested: `fallback = true` together with a short `connect-timeout`.
- An earlier attempt to simulate silence with an `iptables` DROP rule did not block the client
  (the build finished in 0.4 s). That result is discarded. The freeze method replaced it.

### Step 6: whole-store visibility — PASS

A path built on `cachehost`, never rooted and never released (`s6-private`, content
`PRIVATE-CANARY-1`), returned narinfo 200. Its `.drv` also returned 200. The client substituted it
in 0.3 s and read the canary text. Harmonia has no allow-list.

## 5. Side findings

- `systemctl stop harmonia.socket` on `cachehost` does not stop the cache. The active
  `harmonia-key.path` unit starts the socket again within 20 ms (systemd printed
  `Stopping 'harmonia.socket', but its triggering units are still active`). An operator stops
  `harmonia-key.path` first.
- Harmonia reads the key once per service start. Replacing the file needs
  `systemctl restart harmonia.service`.
- Non-atomic delivery (a plain `cp` that creates the file, then writes) can start the socket before
  the content is complete. The first request would then read a short key. Not tested; the fixture
  delivers atomically. Inference from how the path unit fires.
- The VM test store layer sits on tmpfs by default. Without `virtualisation.writableStoreUseTmpfs =
  false`, a reboot deletes the built paths and roots (run 3 showed `release root still there: False`).
  This is a test harness fact, not a Harmonia fact.
- The stock module has no `ConditionPathExists`, no path unit, and no `signKeyPaths` assertion.
  A missing key file is not a build or activation error. `nixos-rebuild switch` succeeds and the
  fault appears at the first request.

## 6. Logs

All under `~/.local/state/vendomat/p20/2026-10-11/S6/`:

| File | Content |
| --- | --- |
| `run6.log`, `run6.clean`, `final-run6.clean` | Final passing run (raw and filtered) |
| `run1.log` ... `run5.log` | Earlier runs (fixture errors: `nix-command` disabled; `--add-root` output misread; stopped socket restarted by the path unit; 5c iptables rule ineffective) |
| `run4.log` | Run stopped when host btrfs unallocated space fell to 1 MiB (see section 8) |
| `keys/` | Test-only key pair |
| `result-run6` | Build output of the final run |

## 7. Proves, infers, does not prove

**Proves (VM level, NixOS module at the nix-systems pin, second machine):**

- The stock module boots clean without a key and fails at the first request, with a degraded system.
- A path unit that starts the socket gives zero failed units before and after the key, and a
  refused connection (not a reset) in between.
- After an atomic key delivery the socket starts in 0.5 s, the narinfo carries the cache signature,
  and the key is not readable by the service user.
- A direct symlink under `/nix/var/nix/gcroots/vendomat/` survives `nix-collect-garbage`, including
  after a reboot. The cache serves what the GC retains.
- Cold substitution works across two VMs, verifies against one trusted key, and refuses a path
  signed by another key.
- A down or silent cache blocks `nix-store -r`, `nix-build`, and `nix build` under default
  settings. `fallback = true` removes the block.
- The cache serves a never-released path and its `.drv`.

**Infers:**

- Rotation by file replace needs a restart (observed on `plainhost`); a `PathChanged` unit could
  automate it (not tested).
- A client with `fallback = true` and a low `connect-timeout` has a bounded delay (not tested as a
  pair).
- The same module shape works on `server` (not tested on its hardware or its Tailscale Serve).

**Does not prove:** real hardware; a real network or a tailnet; the real key delivery route
(controller copy over SSH, SecretSpec, sops-nix); `harmonia.gc` or `nix.gc` under disk pressure
(`min-free` and `max-free`); more than one release root at scale; cache.nixos.org in the client
substituter list ahead of or behind the shared cache; a firewall that restricts port 5000 to one
interface; TLS; the Basix core role on these VMs (the nodes use an ordinary test configuration, not
the Basix role).

## 8. Disk guard note

Run 4 set `writableStoreUseTmpfs = false` on all four nodes. During that run host btrfs
unallocated space fell from 5.09 GiB to 1 MiB. The rule is to stop below 2 GiB, so the run stopped
at once and I killed my build. The space came back to 5.09 GiB (btrfs freed the chunks). Other
spikes ran VM tests at the same time, so the cause is not certain. The setting now applies to
`cachehost` only. Unallocated space stayed above 4 GiB for runs 5 and 6, with a watcher that killed
the build below 1 GiB. Metadata use stayed between 84.5 and 86.4%.

## 9. Recommended NixOS module shape

1. Use form (b2): a path unit that starts `harmonia.socket` when the key file exists, with
   `harmonia.socket` not wanted by `sockets.target`, and `ConditionPathExists` on the socket as a
   guard. Do not use the plain form or the service-condition form: both go `degraded` on the first
   probe.
2. Create the key directory with `systemd.tmpfiles` (0700, root). The delivery route writes into it.
3. Deliver the key atomically: write a temporary name in the same directory, set mode 0400 and owner
   root, then rename.
4. Restart `harmonia.service` after a key rotation. Stop `harmonia-key.path` before the socket when
   an operator wants the cache off.
5. On every client set `nix.settings.fallback = true`. Consider `connect-timeout = 3`; test the pair
   first.
6. Keep the public key in the client `trusted-public-keys` and keep upstream caches first, as
   project 19 says.

## 10. `NEW:` claims (no IDs allocated)

- NEW: The stock `services.harmonia` module (nixpkgs `e7439b6b`) boots without a key with zero failed
  units, but the first request before the key exists puts `harmonia.service` and `harmonia.socket`
  in `failed` (status 243/CREDENTIALS, `start-limit-hit`) and the system in `degraded`.
- NEW: A `harmonia-key.path` unit with `Unit=harmonia.socket` and the socket removed from
  `sockets.target` gives a clean keyless boot, a refused connection before the key, and service
  within 0.5 s after an atomic key delivery.
- NEW: A direct symlink in `/nix/var/nix/gcroots/vendomat/<tag>` is a valid release root for
  `nix-collect-garbage`, and Harmonia stops serving a path when GC deletes it.
- NEW: With Nix 2.34.8 defaults (`fallback = false`, `connect-timeout = 15`, `download-attempts = 5`),
  a refused or silent cache makes `nix-store -r`, `nix-build`, and `nix build` fail. The delay is 5 s
  (refused) or 20 to 44 s (silent). `fallback = true` restores the local build.
- NEW: Harmonia serves a path and its `.drv` even when no release root names them.
- NEW: Harmonia reads the signing key at service start only.

## 11. Concept changes

1. Project 19 section 5 ("A missing cache or a missing path never blocks a build") and the project 20
   concept section 5 ("keep normal cache fallback") are false under default Nix settings for a down
   cache. Add `fallback = true` to the client wiring, and change `DOOR-017` proof text from "cache
   failure fixture" to include it. A missing path (404) already falls back.
2. Project 19 decision 10 and `DOOR-016` hold at VM level: the key can follow boot. Add the path-unit
   form to the module shape so that keyless boot and first probe stay clean. The Basix core role
   must not enable the plain module with a missing key.
3. Section 5 of the project 20 concept says Harmonia is "socket-activated". Add that this hides the
   key fault until the first request, so a guard is part of the supported shape.
4. State the release root route: a symlink under a Vendomat directory in
   `/nix/var/nix/gcroots/`. `harmonia.gc.gcRootsDirs` is needed only for roots outside that tree
   (not tested).
5. The visibility statement stands: the cache serves the whole host store, `.drv` files included.

## Fixture redaction (orchestrator, 2026-10-11)

The run used two inline test-only Nix signing keys. The orchestrator redacted them before commit.
`fixtures/s6-harmonia/test.nix` now reads `./s6-good.secret` and `./s6-bad.secret`. Neither file is
committed. To rerun the fixture, regenerate both with `nix key generate-secret` and update `goodPub`.
