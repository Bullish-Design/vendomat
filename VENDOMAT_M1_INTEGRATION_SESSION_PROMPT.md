# Vendomat M1 cross-repository integration prompt

```text
Work across these local repositories:

- `/home/andrew/Documents/Projects/vendomat`
- `/home/andrew/Documents/Projects/repoman`

Your task is to complete the final integration proof for Milestone M1: a RepoMan consumer must
install pyjutsu through Vendomat's prebuilt wheelhouse using a `wheel:` source, with
`repoman.nativeBuild = false` and no native Rust build.

This is an integration-validation session first, not a rewrite. M1a is complete in vendomat;
M1b is already committed in repoman as:

    c5b4071 gitman: default pyjutsu to a prebuilt wheel; Rust is opt-in via repoman.nativeBuild

Vendomat Face B through M4 is also complete in:

    ea57542 M4: shared constraints and review-on-bump

Start by reading these files in full:

- `vendomat/VENDOMAT_M4_SESSION_PROMPT.md` for project conventions and preserved-worktree rules
- `vendomat/docs/IMPLEMENTATION_PLAN.md`, especially M1/M1b/M1c and cross-cutting risks
- `vendomat/docs/DESIGN.md`, especially the wheel-source and abi3 sections
- `vendomat/flake.nix`
- `vendomat/modules/devenv.nix`
- `repoman/modules/scripts/repoman-sync.sh`
- `repoman/modules/managers/gitman.nix`
- `repoman/flake.nix`
- `repoman/tests/test_repoman_sync.py`
- `repoman/tests/consumer-example/devenv.yaml`
- `repoman/tests/consumer-example/devenv.nix`
- `repoman/tests/consumer-example/repoman.lock`

Current intended contract

1. Vendomat builds a CPython-3.13 abi3 pyjutsu wheel and exposes it as a `wheelhouse` package.
2. The Vendomat devenv module sets `UV_FIND_LINKS` to that wheelhouse and prevents source builds
   for `vendor.libs` through `UV_NO_BUILD_PACKAGE`.
3. RepoMan resolves a generic `wheel:<requirement>` source to the bare requirement passed to uv.
4. RepoMan fails before invoking uv if a selected `wheel:` source has no `UV_FIND_LINKS`, with an
   actionable instruction to import and enable Vendomat's module.
5. `repoman.nativeBuild = false` must mean gitman contributes neither Rust nor maturin. It is true
   only for a repository deliberately compiling pyjutsu locally.

The consumer fixture is already intended to exercise this:

- it imports `vendomat/modules`;
- it sets `vendor.enable = true` and `vendor.libs = [ "pyjutsu" ]`;
- it selects Python 3.13;
- it sets `repoman.nativeBuild = false`;
- its `git-pyjutsu` pseudo-entry uses `source = "wheel:pyjutsu>=0.8"`.

What to prove

From `repoman/tests/consumer-example`, establish all of the following with command output or
other concrete inspection evidence:

1. The devenv evaluation succeeds and `UV_FIND_LINKS` points at Vendomat's wheelhouse.
2. `UV_NO_BUILD_PACKAGE` includes `pyjutsu`.
3. `repoman-sync` resolves the pseudo-entry to `pyjutsu>=0.8`, not `wheel:pyjutsu>=0.8`, and
   completes successfully.
4. The consumer venv can execute `python -c "import pyjutsu; print(pyjutsu.__file__)"`.
5. The installed pyjutsu came from the Vendomat wheelhouse rather than a source/native build.
   Use uv's verbose install output, wheel/install metadata, and/or the evaluated configuration as
   appropriate; do not infer this solely from import success.
6. No Rust or maturin package is contributed by the consumer configuration while
   `repoman.nativeBuild = false`. Distinguish a host-global `cargo` on PATH from a package
   contributed by devenv. The existing `repoman` `gitman-rust-gate` check is supporting evidence,
   but the consumer evaluation is the integration proof.
7. No Cargo build was invoked during the installation. Capture the relevant install output; do not
   claim this merely because `cargo` is absent from PATH.
8. Run `repoman doctor` after the sync and report whether its checks are healthy. If other
   pre-existing managers in the full-roster consumer fixture fail for unrelated reasons, separate
   those failures clearly from the wheel-path evidence.

Suggested verification sequence

Use the intended commands before inventing alternatives:

```sh
cd /home/andrew/Documents/Projects/vendomat
nix build .#wheelhouse

cd /home/andrew/Documents/Projects/repoman
nix build .#checks.x86_64-linux.gitman-rust-gate

cd /home/andrew/Documents/Projects/repoman/tests/consumer-example
devenv shell -- bash -lc 'printf "UV_FIND_LINKS=%s\\nUV_NO_BUILD_PACKAGE=%s\\n" "$UV_FIND_LINKS" "$UV_NO_BUILD_PACKAGE"'
devenv shell -- repoman-sync
devenv shell -- python -c 'import pyjutsu; print(pyjutsu.__file__)'
devenv shell -- repoman doctor
```

Adapt the system attribute in the Nix check if the host is not `x86_64-linux`. Use verbose uv
output when needed to establish wheel provenance. Do not delete a pre-existing `.devenv`, venv,
or other consumer state without first determining whether it is generated and safe to recreate;
preserve unrelated worktree changes in both repositories.

If the proof fails

- Diagnose the first failing boundary: Vendomat wheel build, consumer devenv evaluation,
  `UV_FIND_LINKS` wiring, source resolution/guard, uv selection, ABI compatibility, or import.
- Make only the smallest change needed to repair a genuine M1 cross-repo contract bug.
- Keep each fix within the repository that owns that behavior. Do not broaden into M4 knowledge
  work, repoman manager redesign, more artifact builders, registries, or fleet orchestration.
- Add or update a focused regression test for every code fix.
- If fixing the issue requires a material product choice, a private credential, a remote publish,
  or an unsafe destructive reset, stop and report the blocker rather than guessing.

Verification and commit rules

- For vendomat changes, run `devenv shell -- testee verify`.
- For repoman changes, first discover and run its established verification path, then run focused
  pytest/Nix checks relevant to the change.
- If Nix/devenv is unavailable because of sandbox daemon access, request the normal approved
  escalation for the exact verification command. If it remains unavailable, report the precise
  failure and run the strongest safe fallback; never claim an integration test passed when it did
  not run.
- Do not commit merely because the integration proof passes. Commit only if you made a focused,
  verified code/test fix and the user explicitly authorizes a commit.

Finish criteria

- A concise evidence-backed result for each of the eight proof points above.
- Clear separation between M1 wheel-path status and unrelated consumer/full-roster issues.
- Any changed files and tests listed exactly.
- No unrelated changes staged, discarded, or modified.
```
