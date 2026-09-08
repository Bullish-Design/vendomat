## Next, in order

Nothing, once the rebuild is switched. See "Sub-phase 5" below for the one command
left, which needs a sudo password this session could not supply.

### Sub-phase 6 — templateer joins the roster

templateer is the fifth command in the closure. It belongs there because devman's
changelog group calls `templateer generate` as a COMMAND, never as an import. It was
the one roster tool still coming from the mutable shelf venv, so a login shell got
four commands from the store and this one from nowhere.

It cannot use the shared `pkgs.python313`. templateer requires
`pydantic-ai-slim>=2,<3`, and this nixpkgs carries pydantic-ai 1.107.0 — a major
version apart. So `pkgs/templateer-deps.nix` pins the 2.x line and the parts of its
tree that moved with it: `idna`, `httpcore2`, `httpx2`, `jiter`, `genai-prices`,
`pydantic-graph`, `openai`, `pydantic-ai-slim`. `minijinja` is there for the other
reason — nixpkgs carries no such package at all. Every entry states which of the two
it is, so the next reader can tell an entry that is still needed from one nixpkgs has
since caught up with.

`lib/mkPypiWheel.nix` is the builder for those entries: it installs the PUBLISHED
wheel rather than building from source, for the same reason `pyjutsu-package` does —
the wheel is the artifact of record and a nix build cannot reach the network to repeat
the build. It derives the PyPI legacy download URL from the wheel filename, so no
field is restated by hand.

**Three things this cost, each worth keeping.**

**It is an overlay, not a set of standalone derivations.** A standalone pin produces
two copies of a distribution the moment anything else in the closure still resolves
the nixpkgs one, and `buildPythonPackage` refuses that closure. Measured here on
`idna`. Overriding the package set rebuilds every dependent against the pin instead,
so there is only ever one.

**It is a separate interpreter, not a global override.** `pythonTemplateer =
pkgs.python313.override { self = pythonTemplateer; packageOverrides = ...; }`. A
global override would rebuild every other roster tool and every consumer of
`pkgs.python313` for no reason. The roster is a closure of independent applications,
so one tool may sit on a different package set — what the closure joins on is command
names, not a shared site-packages.

**The `[openai]` extra is folded into the `pydantic-ai-slim` entry itself.**
`mkPythonCli` resolves a PEP 508 head and drops the extra, so an extra's dependencies
must be named by the derivation that stands for the head. `openai` and `tiktoken` are
therefore ordinary dependencies of that entry.

The closure hash moved when templateer joined it, so nix-meta's vendomat input must be
bumped before the new roster is what a login shell actually gets.

### Sub-phase 5 — Home Manager (nix-meta)

`profiles/developer.nix` no longer puts `~/.local/share/repoman/venv/bin` on the login
shell's PATH. It puts the closure there:

    export PATH="$PATH${PATH:+:}/nix/store/...-repoman-toolchain-core/bin"

Still appended, not prepended, keeping the profile's rule that developer tooling never
shadows a Nix-managed binary — though the original reason is gone, because the closure
holds only the five manager commands and no python.

**No `inputs.nixpkgs.follows` on the vendomat input.** Making it follow the system
nixpkgs forked the closure in two: same source, same version, different build. The
whole design is one build shared everywhere, so the input keeps vendomat's own pin.
Verified: nix-meta, vendomat's flake and the published tag all resolve to the same
`repoman-toolchain-core` store path.

`scripts/repoman-toolchain-test` is the live test, 13 checks against the real evaluated
configuration and the real file a login shell sources — not the source text that
produced them. It was proven to FAIL when the venv line is restored (exit 1) and pass
otherwise (exit 0).

**Left to do:** `sudo nixos-rebuild switch --flake .#server`. The configuration builds
and every check passes against the built generation; only the activation is pending.

### Sub-phase 1's fixture — done, and it earned its keep

`tests/fixtures/store-consumer` is a real devenv consumer that declares NO manager
anywhere: no repoman.lock, no `uv add`, nothing in pyproject.toml. Opt-in, because it
builds a closure and needs the network: `VENDOMAT_E2E=1`.

Proven directly rather than inferred (CONCEPT 03 §7):

- `REPOMAN_CLI_PROVIDER=store`, and `repoman`/`copyroom` resolve into `/nix/store`.
- The consumer venv's `bin` holds only activation scripts and python; its
  site-packages holds three entries and no manager distribution.
- An impostor `copyroom` placed in the venv — exactly where a stale pre-migration copy
  would sit — does NOT shadow the shared command. The real one runs.

**It found a bug on its first run.** The store bin expression carried a quoted
`"store"` and an apostrophe in `vendomat's`. Interpolated inside double quotes in every
manager task exec, the quote closed the string early and the apostrophe opened an
unterminated one, so every store-mode task died with `unexpected EOF while looking for
matching`. The expression was correct Nix and read correctly; it was only wrong once
bash parsed it, so no grep-level test could see it. Fixed in repoman v0.7.4, with a
guard that unescapes before checking — the buggy version spelled the quote as `\"`, and
a naive check would have passed on the very bug it exists to catch.

### A note on this file

This file was once 235,087 lines: the same 53-line document appended 4,435 times, each
copy glued onto the previous one's last character. Every unique line outside the first
copy was a `<char>## Next, in order` seam, so nothing was lost by truncating it. If it
grows that way again, the writer that appends to it is duplicating rather than
replacing.
