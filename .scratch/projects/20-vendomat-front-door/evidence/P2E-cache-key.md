# E: where the cache signing key comes from

Date: 2026-10-12. Project 20. No repository file changed. No sudo, no uv, no garbage collection.

## 1. Question

Must an administrator place the Harmonia signing key (DOOR-061, DOOR-068)? Or can the cache host make
its own key, so that only a public key moves?

## 2. Hypotheses

- H1: a oneshot unit runs `nix key generate-secret` when the key file is absent. Harmonia starts after it.
- H2: keep manual key placement (current proposal).
- H3: no signing. Use an `ssh-ng://` substituter or a trusted user.

## 3. Reading (what the records say)

- Project 19 decision 10: "Generate and deliver the Harmonia signing key before enabling the cache
  server." The word "deliver" comes from project 19's SecretSpec design (concept section on secrets).
  Project 18 open decision 7 chose a new key stored with sops-nix, because the old design stored
  `attic-signing-key` that way.
- No record gives a reason that kills H1. No record tests it. The only reasons for placement are
  inherited: a secret store existed, and the key had to survive a reinstall. Both are deferred now
  (SIMPLIFY-REVIEW, rows on the secret receiver and SecretSpec).
- S6 step 1b found that the stock module degrades the system on the first request when the key is
  absent. S6 used a path unit and `ConditionPathExists` to fix that. H1 removes the cause.
- S6 step 4b: a path signed by another key is ignored. A build from the `.drv` then builds locally.
  Only a direct request for the output path fails.
- Project 18 experiment C (`exp-C-ssh-ng.md`): a cold copy over `ssh-ng` failed with "lacks a signature
  by a trusted key" for unsigned paths. The client daemon also needs an SSH private key.

## 4. Inputs

| Item | Value |
| --- | --- |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`, narHash `sha256-H83yz/do+hjOO0uujHyH8RgtIQP2v7Mw+cLwcZK/xKc=` (the S6 pin) |
| Host Nix | 2.34.7 (`nix-store --version`) |
| Test driver | `pkgs.testers.runNixOSTest`, one node `cachehost`, KVM, systemd 261.3 |
| Harmonia | stock `services.harmonia.cache` at the pin (3.3.0 in S6) |
| Fixture | `fixture/test.nix` (VM test), `fixture/derive.nix` (pure eval) in this directory |
| Disk guard before | `btrfs filesystem usage /`: unallocated 37.09 GiB, metadata 71.44 % (`logs/disk-before.txt`) |
| Disk guard after | unallocated 36.09 GiB, metadata 71.60 % (`logs/disk-after.txt`); a watcher logged every 10 s (`logs/disk-watch.txt`) |

Module shape under test (H1):

```nix
systemd.services.harmonia-keygen = {
  before = [ "harmonia.service" ];
  serviceConfig = { Type = "oneshot"; RemainAfterExit = true;
    StateDirectory = "vendomat-cache"; StateDirectoryMode = "0700"; UMask = "0077"; };
  script = ''
    if [ ! -s KEY ]; then
      nix key generate-secret --key-name <hostName>-cache-1 > KEY.tmp
      nix key convert-secret-to-public < KEY.tmp > PUB.tmp ; chmod 0644 PUB.tmp
      mv PUB.tmp PUB ; mv KEY.tmp KEY
    fi '';
};
systemd.services.harmonia = { requires = [ "harmonia-keygen.service" ]; after = [ "harmonia-keygen.service" ]; };
services.harmonia.cache = { enable = true; signKeyPaths = [ KEY ]; };
```

The stock socket activation stays. No path unit. No `ConditionPathExists`.

## 5. Command

```text
nix build -L --file fixture/test.nix --out-link result > logs/run1.log      # one VM build, exit 0
nix eval --json --file fixture/derive.nix                                   # pure eval
```

## 6. Expected

Boot is `running` with no key and no failed unit. The first request makes the key (0600 root) and
Harmonia answers. The narinfo carries one `Sig:` line named after the host key. The public key
verifies it. A wrong trusted key refuses it. A restart keeps the key. An unsigned path from a
substituter is refused unless `require-sigs = false`.

## 7. Actual

Log: `logs/run1.log` (raw), `logs/run1.clean` (prefix removed). Run time: 22.06 s test script. One run, pass.

| Step | Result (quoted) |
| --- | --- |
| T1 boot, no request | `running`; `systemctl --failed` empty; `KEY-ABSENT-BEFORE-FIRST-REQUEST`; port 5000 listening (socket) |
| T2 first `curl http://localhost:5000/nix-cache-info` | `StoreDir: /nix/store`; key mode `600 root:root`; keygen `ActiveState=active Result=success`; harmonia `active/running`; system still `running`; no failed unit |
| Public key line | `cachehost-cache-1:HtSXqKlqprV/KjsY26fmsFa19K//Jp43nnyRE6NqZtI=` (test only) |
| T3 narinfo of a host-built path | one line: `Sig: cachehost-cache-1:VPEEcyIM...` (the local path itself had no cache signature) |
| T4 client chroot store, trusted key = the public line | `copying path ... from 'http://localhost:5000'`; rc 0; `nix path-info --sigs` shows `cachehost-cache-1:VPEE...`; `nix store verify --sigs-needed 1 --trusted-public-keys <pub>` rc 0 |
| T4 wrong trusted key | rc 1: `warning: ignoring substitute ... as it's not signed by any of the keys in 'trusted-public-keys'` then `is required, but there is no substituter that can build it` |
| T5 restart keygen and harmonia | sha256 of the key file unchanged ("RESULT key unchanged after restart"); cache answers; system `running` |
| T6 unsigned path in a `file://` cache, default `require-sigs` | rc 1: `warning: ignoring substitute ... from 'file:///tmp/ucache', as it's not signed by any of the keys in 'trusted-public-keys'` |
| T6 same, `--option require-sigs false` | rc 0: `copying path ... from 'file:///tmp/ucache'...` |
| T6 the same unsigned path through Harmonia | narinfo carries `Sig: cachehost-cache-1:WLD22Fc4...` (Harmonia signs on the fly) |
| derive.nix | client: `substituters=["http://server:5000"]`, `trusted-public-keys=["server-cache-1:..."]`, `fallback=true`, `connect-timeout=3`. Host itself: `{}`. No cache data: `{}`. `nameMatches: true` |

## 8. What this proves

- H1 works in a VM. The oneshot makes the key on the first request, Harmonia starts after it, the
  system stays `running`, the key stays 0600 root, and a restart keeps the key.
- The cache signature verifies with only the public line. A client with another key refuses it.
- Plain `Requires=`/`After=` ordering gives a clean first boot and a clean first request. The path
  unit, the socket removal, and `ConditionPathExists` from S6 are not needed. This also removes the
  S6 degraded state, because the key always exists when the service starts.
- Nix refuses an unsigned substituted path under default settings (local-store path, `file://`
  substituter). H3 needs `require-sigs = false` or a signature.
- Harmonia signs every path it serves, including paths that carry no signature on the host.
- The client settings follow from a host name and a public key line (pure eval).

## 9. Inference (not run)

- A real `ssh-ng://` substituter fails the same way: project 18 exp C saw "lacks a signature by a
  trusted key" for unsigned paths. H3 also moves a secret: an SSH private key on every client daemon
  (root), plus a pinned host key. So H3 swaps one public key line for a private key per client.
  `require-sigs = false` would remove the signature check for every substituter, including
  cache.nixos.org. Do not use it.
- A trusted user skips the check only for an explicit `nix copy --no-check-sigs`. A daemon
  substitution still checks signatures. This follows from Nix behaviour; not run here.
- Reinstall of the cache host gives a new key. Clients ignore the cache with a warning and build
  from the `.drv` locally (S6 step 4b); a direct output-path request fails. The fix is to copy one new
  public line. A backup of `/var/lib/vendomat-cache` keeps the old key.
- On a full-disk reinstall of Basix, `/var/lib` is wiped, so the key changes. If a user wants to keep
  the key, one backup step restores it. This is optional and outside the first release.
- `substituters` must append to the default list (`extra-substituters`), or the client loses
  cache.nixos.org. `derive.nix` shows the replace form only for brevity.

## 10. Not proved

- A second machine, a real network, a firewall limited to the client, or a tailnet name.
- `fallback = true` together with `connect-timeout = 3` (already open in S6).
- A reboot of the VM. T5 restarted the units only. The rule "file present means skip" is plain shell.
- Key generation on first boot with `nix key` when `nix-command` is off (the fixture turns it on).
- A daemon-side substitution of an unsigned path; a real `ssh-ng://` run.
- Interrupted keygen: the temp-then-rename order means a partial file never has the final name.
  The `-s` test covers an empty file. Not forced here.
- Whether `StateDirectory` fits the Basix impermanence or backup layout.

## 11. Two further questions

Build shared outputs on the cache host: a rule or not?
- Harmonia serves any valid path in the host store and signs it on the fly (T6; S6 step 6). So the
  host can serve whatever it holds. The rule is not needed for the cache to work.
- With no rule: a client builds what the host lacks. A 404 falls back to a local build (S6 step 5a).
  Nothing breaks. The cost: client builds never reach other machines, and host GC may drop unrooted
  paths (S6 step 3), which only makes a later 404.
- With the rule: every shared output needs a build step on the host (SSH, remote build, or a command).
  That is a workflow Vendomat would have to own. It also needs a root per output to keep it. This adds
  the "collection builder" the simplify review wants to defer.
- Recommendation: state it as advice, not a MUST. "The host serves its store. Build on the host if you
  want a client to reuse an output. Add a native GC root to keep it."

Derive client settings from one host name plus one public key line?
- Yes for URL (`http://<host>:5000`), trust, `fallback = true`, and a fixed bounded `connect-timeout`.
  The host name must resolve on the client (DNS, tailnet, or `networking.hosts`). The cache host
  itself sets none.
- One concept stays outside the pair: who may reach port 5000. The host must open it to the client
  only (firewall or bind address). The host knows its clients if the data lists the machines; no new
  user field is needed beyond the machine list already in the data.
- The module can check that the key name starts with the host name, to catch a wrong paste.

## 12. Verdicts

- H1: viable, best. Passes the VM test. Removes key placement, the key-exists start condition, the path
  unit, the delivery route, and any secret in transit. Loses key survival across reinstall unless backed up.
- H2: works (S6) but adds an administrator step and a start condition. No reason in the records
  requires it.
- H3: does not remove the key problem. Nix refuses unsigned substitutes (T6; project 18 exp C). The
  workaround is `require-sigs = false` (unsafe) or an SSH private key on each client. Reject.
