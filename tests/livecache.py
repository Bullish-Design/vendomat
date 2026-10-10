"""The live cache check: push to the host Attic, then pull cold through the pull credential.

This module holds the whole procedure. `tests/test_live_cache.py` runs it with fakes in every
`testee verify` and against the real cache in `testee check live-cache`.

The procedure:

1. Read the push and pull credentials from the Attic client configuration.
2. Add one unique file to the store, so each run makes a real upload, not a cache hit.
3. Build the Vendomat package from this checkout as the fixed medium path.
4. Push both closures with `attic push`, retrying a bounded number of times.
5. Ask the cache for each closure path with the pull credential (an HTTP `narinfo` request).
6. Copy both roots into an empty root store with signature checking on, and compare content.

A credential never reaches an argument list, a log, or the report. Infrastructure that is
missing raises `Blocked`, and the report names it. A blocker is a failure, not a pass.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Run a command: argv, timeout in seconds, extra environment.
Runner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]
#: Return the HTTP status of a GET. The token is None for an anonymous request.
Fetcher = Callable[[str, str | None], int]


class Blocked(Exception):
    """Infrastructure the check needs is unavailable. The message names it."""


@dataclass(frozen=True)
class Server:
    name: str
    endpoint: str
    token: str

    @property
    def host(self) -> str:
        return urllib.parse.urlsplit(self.endpoint).hostname or ""

    def __repr__(self) -> str:  # keep the token out of any traceback or log
        return f"Server(name={self.name!r}, endpoint={self.endpoint!r})"


@dataclass(frozen=True)
class Settings:
    config: Path
    push_server: str = "vendomat-server"
    pull_server: str = "vendomat-pull-check"
    cache: str = "vendomat"
    attic: str | None = None
    fixed_path: str | None = None
    flake: str | None = None
    size: int = 1 << 20
    attempts: int = 3
    pause: float = 20.0
    jobs: int = 1
    push_timeout: float = 1800.0
    logs: Path = Path("live-cache")

    @classmethod
    def from_env(cls, env: Mapping[str, str], *, flake: str | None = None) -> Settings:
        home = Path(env.get("HOME") or Path.home())
        base = Path(env["XDG_CONFIG_HOME"]) if env.get("XDG_CONFIG_HOME") else home / ".config"
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        state = home / ".local/state/vendomat/v6/live-cache"
        return cls(
            config=base / "attic/config.toml",
            push_server=env.get("VENDOMAT_ATTIC_PUSH_SERVER", cls.push_server),
            pull_server=env.get("VENDOMAT_ATTIC_PULL_SERVER", cls.pull_server),
            cache=env.get("VENDOMAT_ATTIC_CACHE", cls.cache),
            attic=env.get("VENDOMAT_ATTIC") or None,
            fixed_path=env.get("VENDOMAT_LIVE_CACHE_FIXED_PATH") or None,
            flake=flake,
            size=int(env.get("VENDOMAT_LIVE_CACHE_SIZE", cls.size)),
            attempts=int(env.get("VENDOMAT_LIVE_CACHE_ATTEMPTS", cls.attempts)),
            pause=float(env.get("VENDOMAT_LIVE_CACHE_PAUSE", cls.pause)),
            jobs=int(env.get("VENDOMAT_LIVE_CACHE_JOBS", cls.jobs)),
            logs=Path(env.get("VENDOMAT_LIVE_CACHE_LOGS") or state / stamp),
        )


#: Stop a narinfo survey after this many server errors. Each can cost the server's 30 s timeout.
MAX_SURVEY_ERRORS = 3


@dataclass
class Survey:
    checked: int = 0
    absent: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.absent and not self.errors


@dataclass
class Step:
    name: str
    ok: bool
    seconds: float
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Report:
    result: str = "fail"  # pass | fail | blocked
    blocker: str | None = None
    started: str = ""
    finished: str = ""
    endpoint: str = ""
    cache: str = ""
    push_server: str = ""
    pull_server: str = ""
    versions: dict[str, str] = field(default_factory=dict)
    paths: dict[str, str] = field(default_factory=dict)
    push_attempts: list[dict[str, Any]] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)

    def as_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


# --- pure helpers ---------------------------------------------------------------------------


def load_server(config: Path, name: str) -> Server:
    """Read one server entry from the Attic client configuration."""
    try:
        data = tomllib.loads(config.read_text())
    except FileNotFoundError:
        raise Blocked(f"attic client configuration missing: {config}") from None
    except tomllib.TOMLDecodeError as error:
        raise Blocked(f"attic client configuration is not valid TOML: {config}: {error}") from None
    entry = data.get("servers", {}).get(name)
    if not isinstance(entry, dict):
        raise Blocked(f"attic server entry {name!r} missing in {config}")
    endpoint, token = entry.get("endpoint"), entry.get("token")
    if not endpoint or not token:
        raise Blocked(f"attic server entry {name!r} needs an endpoint and a token")
    return Server(name=name, endpoint=str(endpoint).rstrip("/"), token=str(token))


def netrc_text(server: Server) -> str:
    """The netrc text Nix and curl use for a private cache. The login name is not checked."""
    return f"machine {server.host}\nlogin vendomat\npassword {server.token}\n"


def narinfo_url(server: Server, cache: str, store_path: str) -> str:
    return f"{server.endpoint}/{cache}/{Path(store_path).name[:32]}.narinfo"


def public_key(cache_info: str) -> str | None:
    found = re.search(r"Public Key:\s*(\S+)", cache_info)
    return found.group(1) if found else None


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tail(text: str, lines: int = 12) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def force_remove(path: Path) -> None:
    """Delete a tree that a Nix store root made read-only."""
    if not path.exists():
        return
    for root, directories, _files in os.walk(path):
        for name in [".", *directories]:
            target = Path(root) / name
            if not target.is_symlink():
                target.chmod(target.stat().st_mode | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRUSR)
    shutil.rmtree(path)


def real_runner(env: Mapping[str, str] | None = None) -> Runner:
    def run(argv: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                list(argv), capture_output=True, text=True, timeout=timeout, env=dict(env) if env else None
            )
        except FileNotFoundError as error:
            return subprocess.CompletedProcess(list(argv), 127, "", str(error))
        except subprocess.TimeoutExpired as error:
            out = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
            return subprocess.CompletedProcess(list(argv), 124, out, f"timed out after {timeout} s")

    return run


def real_fetcher(timeout: float = 30.0) -> Fetcher:
    def fetch(url: str, token: str | None) -> int:
        request = urllib.request.Request(url)  # noqa: S310 (the URL is the configured endpoint)
        if token is not None:
            request.add_header("Authorization", "Basic " + base64.b64encode(f"vendomat:{token}".encode()).decode())
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return int(response.status)
        except urllib.error.HTTPError as error:
            return int(error.code)
        except urllib.error.URLError as error:
            if isinstance(error.reason, ConnectionRefusedError):
                raise Blocked(f"cache endpoint refused the connection: {url}") from None
            return 599  # a stalled server: transient, like an HTTP 5xx
        except (TimeoutError, OSError):
            return 599

    return fetch


# --- the check ------------------------------------------------------------------------------


class LiveCache:
    def __init__(
        self,
        settings: Settings,
        run: Runner,
        fetch: Fetcher,
        *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.run = run
        self.fetch = fetch
        self.sleep = sleep
        self.clock = clock
        self.report = Report(cache=settings.cache, push_server=settings.push_server, pull_server=settings.pull_server)
        self._attic: str | None = None

    # step bookkeeping
    def _step(self, name: str, started: float, ok: bool, **detail: Any) -> bool:
        self.report.steps.append(Step(name, ok, round(self.clock() - started, 3), detail))
        return ok

    def _must(self, argv: Sequence[str], timeout: float, what: str, *, both: bool = False) -> str:
        """Run a command that must succeed. `both` adds stderr: the Attic client prints info there."""
        done = self.run(argv, timeout)
        if done.returncode != 0:
            raise Blocked(f"{what} failed (exit {done.returncode}): {tail(done.stderr)}")
        return done.stdout + done.stderr if both else done.stdout

    # procedure
    def execute(self, work: Path) -> Report:
        self.report.started = datetime.now(UTC).isoformat(timespec="seconds")
        try:
            self._execute(work)
        except Blocked as blocker:
            self.report.result = "blocked"
            self.report.blocker = str(blocker)
        finally:
            self.report.finished = datetime.now(UTC).isoformat(timespec="seconds")
        return self.report

    def _execute(self, work: Path) -> None:
        s = self.settings
        t = self.clock()
        push = load_server(s.config, s.push_server)
        pull = load_server(s.config, s.pull_server)
        self.report.endpoint = push.endpoint
        self._step("credentials", t, True, push=push.name, pull=pull.name, endpoint=push.endpoint)

        t = self.clock()
        attic = self._attic = self._resolve_attic()
        self.report.versions["attic"] = self._must([attic, "--version"], 60, "attic --version").strip()
        self.report.versions["nix"] = self._must(["nix", "--version"], 60, "nix --version").strip()
        self._step("tools", t, True, **self.report.versions)

        t = self.clock()
        anonymous = self.fetch(f"{pull.endpoint}/{s.cache}/nix-cache-info", None)
        authed = self.fetch(f"{pull.endpoint}/{s.cache}/nix-cache-info", pull.token)
        if authed != 200:
            raise Blocked(f"pull credential {pull.name!r} gets HTTP {authed} from {pull.endpoint}/{s.cache}")
        self._step("reach", t, True, anonymous_status=anonymous, pull_status=authed)

        t = self.clock()
        info = self._must([attic, "cache", "info", f"{pull.name}:{s.cache}"], 120, "attic cache info", both=True)
        key = public_key(info)
        if key is None:
            raise Blocked("attic cache info printed no public key")
        self._step("cache-info", t, True, public_key=key)

        t = self.clock()
        unique = self._add_unique(work)
        fixed = self._fixed_path()
        self.report.paths = {"unique": unique, "fixed": fixed}
        closure = self._closure([unique, fixed])
        self._step("paths", t, True, unique=unique, fixed=fixed, closure_paths=len(closure), unique_bytes=s.size)

        pushed = self._push_with_retries(push, pull, closure, [unique, fixed])
        if not pushed:
            return

        t = self.clock()
        survey = self._survey(pull, closure)
        detail = {"checked": survey.checked, "absent": survey.absent, "errors": survey.errors}
        if not self._step("narinfo", t, survey.complete, **detail):
            return

        t = self.clock()
        self._cold_copy(pull, key, work, [unique, fixed], unique, t)

    # tools and paths
    def _resolve_attic(self) -> str:
        if self.settings.attic:
            return self.settings.attic
        found = shutil.which("attic")
        if found:
            return found
        out = self._must(
            ["nix", "build", "--no-link", "--print-out-paths", "nixpkgs#attic-client"], 900, "nix build attic-client"
        )
        return out.strip().splitlines()[-1] + "/bin/attic"

    def _add_unique(self, work: Path) -> str:
        nonce = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        directory = work / "unique"
        directory.mkdir(parents=True)
        file = directory / f"vendomat-live-cache-{stamp}-{nonce}"
        # Random bytes do not compress and do not deduplicate, so the push uploads every chunk.
        file.write_bytes(os.urandom(self.settings.size))
        out = self._must(["nix-store", "--add", str(file)], 300, "nix-store --add")
        return out.strip().splitlines()[-1]

    def _fixed_path(self) -> str:
        if self.settings.fixed_path:
            return self.settings.fixed_path
        if not self.settings.flake:
            raise Blocked("no fixed path: set VENDOMAT_LIVE_CACHE_FIXED_PATH or give a flake")
        out = self._must(
            ["nix", "build", "--no-link", "--print-out-paths", f"{self.settings.flake}#vendomat"],
            1800,
            "nix build vendomat",
        )
        return out.strip().splitlines()[-1]

    def _closure(self, roots: Sequence[str]) -> list[str]:
        out = self._must(["nix-store", "--query", "--requisites", *roots], 300, "nix-store --query")
        return sorted({line for line in out.splitlines() if line.startswith("/")})

    # push and pull
    def _survey(self, pull: Server, closure: Sequence[str]) -> Survey:
        """Ask for each path. A 404 is absent. A 5xx or a timeout is an error, not a blocker."""
        survey = Survey()
        for path in closure:
            status = self.fetch(narinfo_url(pull, self.settings.cache, path), pull.token)
            survey.checked += 1
            if status == 200:
                continue
            if status == 404:
                survey.absent.append(path)
            elif status >= 500:
                survey.errors.append({"path": path, "status": status})
                if len(survey.errors) >= MAX_SURVEY_ERRORS:
                    break  # each error can cost the server's 30 s timeout; stop asking
            else:
                raise Blocked(f"narinfo for {path} returned HTTP {status} for the pull credential")
        return survey

    def _push_with_retries(self, push: Server, pull: Server, closure: Sequence[str], roots: Sequence[str]) -> bool:
        s = self.settings
        target = f"{push.name}:{s.cache}"
        started = self.clock()
        survey = Survey()
        for attempt in range(1, max(s.attempts, 1) + 1):
            t = self.clock()
            done = self.run([self._attic or "attic", "push", "-j", str(s.jobs), target, *roots], s.push_timeout)
            survey = self._survey(pull, closure)
            self.report.push_attempts.append(
                {
                    "attempt": attempt,
                    "exit": done.returncode,
                    "seconds": round(self.clock() - t, 3),
                    "absent_after": len(survey.absent),
                    "narinfo_errors": survey.errors,
                    "errors": [line for line in done.stdout.splitlines() + done.stderr.splitlines() if "❌" in line][
                        :10
                    ],
                    "stderr_tail": tail(done.stderr, 6),
                }
            )
            if survey.complete:
                self._step("push", started, True, attempts=attempt, closure_paths=len(closure))
                return True
            if attempt < s.attempts:
                self.sleep(s.pause)
        detail = {"absent_after": len(survey.absent), "narinfo_errors": len(survey.errors)}
        self._step("push", started, False, attempts=s.attempts, closure_paths=len(closure), **detail)
        return False

    def _cold_copy(self, pull: Server, key: str, work: Path, roots: Sequence[str], unique: str, t: float) -> None:
        s = self.settings
        store = work / "cold-store"
        netrc = work / "netrc"
        fd = os.open(netrc, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(netrc_text(pull))
        argv = [
            "nix", "copy",
            "--from", f"{pull.endpoint}/{s.cache}",
            "--to", f"local?root={store}",
            "--option", "netrc-file", str(netrc),
            "--option", "trusted-public-keys", key,
            "--option", "substituters", "",
            *roots,
        ]  # fmt: skip
        done = self.run(argv, 1800)
        copied = store / "nix/store" / Path(unique).name
        original = Path(unique)
        ok = done.returncode == 0 and copied.is_file()
        same = ok and _digest(copied) == _digest(original)
        self._step(
            "cold-substitution",
            t,
            bool(same),
            exit=done.returncode,
            copied_paths=len(list((store / "nix/store").iterdir())) if (store / "nix/store").is_dir() else 0,
            content_matches=bool(same),
            stderr_tail=tail(done.stderr, 6),
            signature_checking="on",
        )
        if same:
            self.report.result = "pass"


def run_check(
    settings: Settings,
    run: Runner | None = None,
    fetch: Fetcher | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Report:
    """Run the check in a scratch directory under the log directory, then write the report."""
    settings.logs.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="work-", dir=settings.logs))
    check = LiveCache(settings, run or real_runner(os.environ), fetch or real_fetcher(), sleep=sleep)
    try:
        report = check.execute(work)
    finally:
        force_remove(work)
    (settings.logs / "report.json").write_text(report.as_json())
    return report
