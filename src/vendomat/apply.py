"""``vendomat apply``: a machine activates its own configuration, with no SSH (R15, ``VMT-075``).

The command runs on the machine. It does the steps that devenv's deploy worker does over SSH:

1. read the machine name from ``/etc/devenv/machine-facts.json`` (the catalog sets
   ``networking.hostName`` to the machine name, R21);
2. read the watched files: the four fixed ones and the paths of the option ``vendomat.watch`` (R62,
   ``VMT-280``), with ``devenv eval vendomat.watch``;
3. refuse ignored watched files unless they are explicitly force-added, and refuse every other
   uncommitted change under the workspace root (R55, ``VMT-182``), unless ``--dirty``;
4. ``devenv build machines.NAME.build.nixos``;
5. commit the watched files, unless ``--dirty``;
6. ``sudo nix-env --profile /nix/var/nix/profiles/system --set TOP``;
7. ``sudo TOP/bin/switch-to-configuration switch``;
8. append one line to the generation record (see ``record.py``), as root.

A name that is not this machine passes through to ``devenv machines deploy NAME``. The workspace
commit is never written into the system (``VMT-110``).
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import workspace
from .errortrim import save_log, trim
from .record import RECORD_PATH, Entry, RecordError, now

FACTS_PATH = Path("/etc/devenv/machine-facts.json")
PROFILE = Path("/nix/var/nix/profiles/system")
#: The setuid sudo. The copy first on PATH may not be setuid.
SUDO = "/run/wrappers/bin/sudo"
#: A build can fetch a kernel. The limit stops a hung command, not a slow one.
BUILD_TIMEOUT = 7200
#: The public key of the machine's cache, made at first boot by the sharing module.
CACHE_KEY_PATH = Path("/var/lib/vendomat/cache-key.pub")


@dataclass
class Result:
    returncode: int
    stdout: str = ""
    stderr: str = ""


#: ``run(argv, cwd=..., input=..., capture=...)``. Tests replace it with a fake.
Runner = Callable[..., Result]
Emit = Callable[[str], None]


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    input: str | None = None,
    capture: bool = True,
    timeout: float | None = None,
) -> Result:
    """Run one command. With ``capture=False`` the command writes to the terminal."""

    try:
        proc = subprocess.run(
            list(argv),
            cwd=cwd,
            input=input,
            text=True,
            capture_output=capture,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return Result(127, "", str(exc))
    except subprocess.TimeoutExpired:
        return Result(124, "", f"timed out after {timeout} s: {' '.join(argv)}")
    return Result(proc.returncode, proc.stdout or "", proc.stderr or "")


@dataclass
class Applied:
    generation: int
    toplevel: str
    commit: str
    dirty: bool
    failed_units: list[str]


def machine_name(facts: Path | None = None) -> str:
    """The machine name, from the facts file that devenv writes on every machine."""

    facts = facts or FACTS_PATH
    try:
        data = json.loads(facts.read_text())
    except FileNotFoundError as exc:
        raise RecordError(f"no facts file at {facts}: this host is not a devenv machine", 2) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordError(f"cannot read {facts}: {exc}", 2) from exc
    name = data.get("hostname") if isinstance(data, dict) else None
    if not isinstance(name, str) or not name:
        raise RecordError(f"{facts} names no hostname", 2)
    return name


def devenv_binary() -> str:
    """The devenv to run: ``$VENDOMAT_DEVENV``, else ``devenv`` on PATH."""

    return os.environ.get("VENDOMAT_DEVENV") or "devenv"


def deploy_argv(name: str) -> list[str]:
    """The command for a machine that is not this one: devenv's own deploy over SSH."""

    return [devenv_binary(), "machines", "deploy", name]


def other_changes(
    root: Path, name: str, cache_key: Path | None = None, watched: Sequence[str] = workspace.WATCHED
) -> list[workspace.Change]:
    """Uncommitted changes under ``root`` that are not a watched file (R55).

    Two kinds of path do not count: a file that Git ignores, and the cache key file that an earlier
    apply wrote for this machine (``VMT-161``). Apply must not block on its own output.
    """

    key = workspace.written_key_file(root, name, cache_key or CACHE_KEY_PATH)
    skip = (*watched, *([key] if key else []))
    return workspace.uncommitted_changes(root, skip=skip)


def dirty_apply(
    root: Path,
    name: str,
    *,
    allow: bool,
    emit: Emit,
    cache_key: Path | None = None,
    watched: Sequence[str] = workspace.WATCHED,
) -> bool:
    """Return whether this apply skips its commit.

    Ignored watched files always need an explicit force-add. Without ``--dirty``, any other uncommitted
    change stops the apply before the build, because a record is a whole commit (R55). With ``--dirty``,
    watched and other changes are allowed, and the record marks the generation dirty.
    """

    changes = [change for change in workspace.watched_changes(root, watched) if change.status != "!!"]
    workspace.refuse_ignored_watched(root, watched)
    other = other_changes(root, name, cache_key, watched)
    if other and not allow:
        listing = "\n".join(f"  {change.text()}" for change in other)
        raise workspace.WorkspaceError(
            f"uncommitted changes outside the watched files ({', '.join(watched)}):\n"
            f"{listing}\n"
            "A record names one whole commit. Commit these paths or remove them, then apply again. "
            "Or run `vendomat apply --dirty` to apply them without a commit. Nothing was built."
        )
    if not (changes or other) or not allow:
        return False
    listing = "; ".join(change.text() for change in [*changes, *other])
    emit(f"warning: applying uncommitted changes ({listing}); the record marks this generation dirty")
    return True


def refuse_changed_during_build(
    root: Path, before: tuple[str, dict[str, str | None]], watched: Sequence[str] = workspace.WATCHED
) -> None:
    """Refuse when a file of the tree under the root or HEAD changed during the build.

    The system was built from the earlier content. A commit now would record files that nobody built.
    """

    after = workspace.fingerprint(root, watched)
    if after == before:
        return
    names = sorted(name for name in {*before[1], *after[1]} if before[1].get(name) != after[1].get(name))
    if after[0] != before[0]:
        names.append("HEAD")
    shown = ", ".join(names[:10]) + (f", and {len(names) - 10} more" if len(names) > 10 else "")
    raise RecordError(
        f"{shown} changed during the build, so the built system does not match the files. "
        "Nothing was committed or activated, and no record line was written. Apply again.",
        1,
    )


#: The longest trimmed failure text that a command prints. The full text goes to the log file.
FAILURE_LINES = 40
WATCH_ATTRIBUTE = "vendomat.watch"


def failure_text(kind: str, argv: Sequence[str], result: Result) -> str:
    """The text of a failed ``devenv`` command, trimmed as ``VMT-117`` says (R62, ``VMT-281``).

    The lines ``FILE.yaml:LINE:COL: reason`` come first, then the text after the last ``error:`` line, then
    one line that names the command and the file of the full trace. A failure with no ``error:`` line keeps
    its last lines.
    """

    raw = (result.stderr or result.stdout).strip()
    body = trim(raw).splitlines()
    if len(body) > FAILURE_LINES:
        body = [*body[:FAILURE_LINES], f"... ({len(body) - FAILURE_LINES} more lines)"]
    log = save_log(kind, f"$ {' '.join(argv)}\n(exit {result.returncode})\n{result.stderr}\n{result.stdout}")
    where = f"; the full trace is in {log}" if log else ""
    return "\n".join([*body, f"devenv {' '.join(argv[1:])} failed (exit {result.returncode}){where}"])


def watch_paths(root: Path, run: Runner) -> tuple[str, ...]:
    """The files to watch: the four fixed files and the paths of ``vendomat.watch`` (R62).

    The command evaluates the workspace, so a fault in a workspace file stops here, with its first line first.
    """

    argv = [devenv_binary(), "eval", WATCH_ATTRIBUTE]
    result = run(argv, cwd=root, timeout=BUILD_TIMEOUT)
    if result.returncode != 0:
        raise RecordError(failure_text("watch", argv, result), 2)
    text = result.stdout.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("\n{")
        try:
            data = json.loads(text[start + 1 :] if start >= 0 else text)
        except json.JSONDecodeError as exc:
            raise RecordError(f"devenv eval {WATCH_ATTRIBUTE} printed no JSON: {text[:200]!r}", 2) from exc
    paths = data.get(WATCH_ATTRIBUTE) if isinstance(data, dict) else None
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        raise RecordError(f"devenv eval {WATCH_ATTRIBUTE} printed no list of paths: {text[:200]!r}", 2)
    return workspace.extend_watched(root, paths)


def build_toplevel(root: Path, name: str, run: Runner) -> str:
    """Build ``machines.NAME.build.nixos`` and return the system path."""

    attr = f"machines.{name}.build.nixos"
    argv = [devenv_binary(), "build", attr]
    result = run(argv, cwd=root, timeout=BUILD_TIMEOUT)
    if result.returncode != 0:
        raise RecordError(failure_text("build", argv, result), 2)
    top = ""
    try:
        parsed = json.loads(result.stdout)
        if isinstance(parsed, dict) and isinstance(parsed.get(attr), str):
            top = parsed[attr]
    except json.JSONDecodeError:
        pass
    if not top:
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("/nix/store/")]
        top = lines[-1] if lines else ""
    if not top.startswith("/nix/store/"):
        raise RecordError(f"devenv build {attr} printed no system path:\n{result.stdout.strip()[-400:]}", 2)
    return top


def profile_generation(profile: Path | None = None) -> int:
    """The number of the generation that the profile points at."""

    profile = profile or PROFILE
    try:
        target = os.readlink(profile)
    except OSError as exc:
        raise RecordError(f"cannot read the profile link {profile}: {exc}", 2) from exc
    stem = profile.name + "-"
    if not (target.startswith(stem) and target.endswith("-link")):
        raise RecordError(f"{profile} points at {target}, which is not a generation link", 2)
    number = target[len(stem) : -len("-link")]
    if not number.isdigit():
        raise RecordError(f"{profile} points at {target}, which is not a generation link", 2)
    return int(number)


def current_toplevel(profile: Path | None = None) -> str:
    """The system path that the profile points at."""

    return str((profile or PROFILE).resolve())


def sudo(run: Runner, *argv: str, input: str | None = None) -> Result:
    return run([SUDO, *argv], input=input, capture=False if input is None else True)


#: switch-to-configuration exits 4 when the new system is active but some units failed to start or
#: restart. That is a warning: the profile moved and the system runs the new configuration.
SWITCH_UNITS_FAILED = 4


def switch(
    run: Runner,
    top: str,
    *,
    set_profile: bool,
    profile: Path | None = None,
    generation: int | None = None,
) -> int:
    """Point the profile at ``top`` (or at a generation), then run ``switch-to-configuration switch``.

    The profile moves first, as in devenv's own deploy worker, so that the boot entry the switch writes
    is the new default. Return the exit status of the switch: 0, or 4 for "active, but some units failed".
    """

    profile = profile or PROFILE
    if set_profile:
        step = sudo(run, "nix-env", "--profile", str(profile), "--set", top)
        label = f"nix-env --set {top}"
    else:
        step = sudo(run, "nix-env", "--profile", str(profile), "--switch-generation", str(generation))
        label = f"nix-env --switch-generation {generation}"
    if step.returncode != 0:
        raise RecordError(f"{label} failed (exit {step.returncode}); the running system did not change", 2)
    activated = sudo(run, f"{top}/bin/switch-to-configuration", "switch")
    if activated.returncode not in (0, SWITCH_UNITS_FAILED):
        raise RecordError(
            f"switch-to-configuration failed (exit {activated.returncode}). The profile already points at the new "
            "generation. Run `vendomat rollback --fast` to return, or fix the fault and run apply again. "
            "The configuration commit stays; apply again to retry. No record line was written.",
            2,
        )
    return activated.returncode


def append_record(run: Runner, entry: Entry, path: Path | None = None) -> None:
    """Append one line to the record, as root. Create the directory when it is missing."""

    path = path or RECORD_PATH
    made = sudo(run, "install", "-d", "-m", "755", str(path.parent))
    if made.returncode != 0:
        raise RecordError(f"cannot create {path.parent} (exit {made.returncode})", 2)
    wrote = run([SUDO, "tee", "-a", str(path)], input=entry.line() + "\n", capture=True)
    if wrote.returncode != 0:
        raise RecordError(f"cannot append to {path} (exit {wrote.returncode}): {wrote.stderr.strip()}", 2)


def failed_units(run: Runner) -> list[str]:
    """The units that ``systemctl --failed`` lists."""

    result = run(["systemctl", "--failed", "--no-legend", "--plain"])
    return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]


def activate(
    run: Runner,
    top: str,
    commit: str,
    dirty: bool,
    emit: Emit,
    *,
    profile: Path | None = None,
    record: Path | None = None,
    generation: int | None = None,
) -> Applied:
    """Switch to ``top`` and write the record line. With ``generation``, move to that existing generation."""

    status = switch(run, top, set_profile=generation is None, profile=profile, generation=generation)
    if status == SWITCH_UNITS_FAILED:
        emit("warning: switch-to-configuration exited 4: the new system is active, but some units failed")
    number = profile_generation(profile)
    append_record(run, Entry(number, top, commit, dirty, now()), record)
    failed = failed_units(run)
    emit(f"generation {number} is active: {top}")
    emit(f"commit {commit[:12]}{' (uncommitted changes applied)' if dirty else ''}")
    emit("failed units: " + (", ".join(failed) if failed else "none"))
    return Applied(number, top, commit, dirty, failed)


def publish_cache_key(root: Path, name: str, emit: Emit, source: Path | None = None) -> bool:
    """Copy the machine's public cache key to ``.machines/NAME/cache-key.pub`` in the workspace.

    The other machines read that committed file to trust this machine's cache. Copy it only when the
    file is missing or differs, and tell the user to commit it. Never commit it. A machine with no
    key (``serve: false``) has no source file, and nothing happens. Return whether the file changed.
    """

    source = source or CACHE_KEY_PATH
    try:
        key = source.read_text()
    except OSError:
        return False
    target = root / workspace.cache_key_path(name)
    try:
        if target.read_text() == key:
            return False
    except OSError:
        pass
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(key)
    emit(f"wrote .machines/{name}/cache-key.pub; commit it so that your other machines trust this one")
    return True


def apply(
    root: Path,
    *,
    dirty_ok: bool = False,
    run: Runner = run_command,
    emit: Emit = print,
    facts: Path | None = None,
    profile: Path | None = None,
    record: Path | None = None,
    cache_key: Path | None = None,
) -> Applied:
    """Activate this machine's configuration from the workspace at ``root``."""

    name = machine_name(facts)
    watched = watch_paths(root, run)
    dirty = dirty_apply(root, name, allow=dirty_ok, emit=emit, cache_key=cache_key, watched=watched)
    # Precondition: the workspace has a commit. A dirty apply records this commit.
    commit = workspace.head(root)
    if not dirty and workspace.watched_changes(root, watched):
        # Apply commits after the build. Find out now that the commit can be made (no build is wasted).
        workspace.require_commit_identity(root)
    before = workspace.fingerprint(root, watched)
    emit(f"machine {name}: building machines.{name}.build.nixos")
    top = build_toplevel(root, name, run)
    emit(f"built {top}")
    refuse_changed_during_build(root, before, watched)
    if not dirty:
        commit = workspace.commit_watched(root, watched=watched)
    applied = activate(run, top, commit, dirty, emit, profile=profile, record=record)
    publish_cache_key(root, name, emit, cache_key)
    return applied
