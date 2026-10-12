# NON-PRODUCTION spike fixture (project 20, S3). Schema cache: key, lookup, export, store.
# Usage: python3 -I schema_cache.py WS DEVENV_BIN CACHE_DIR [--keys a,b] [--force-miss]
# Prints one line: "HIT <path> key=<hex>" or "MISS exported <path> key=<hex>".
# A hit starts no process. The key excludes .vendomat/config.json (the data).
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

SKIP_DIRS = {".devenv", ".git", ".jj", ".direnv", "node_modules"}
# Files in .vendomat that are generated data, not module source.
SKIP_FILES = {".vendomat/config.json"}

def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def workspace_sources(ws: Path):
    """Every .nix, .yaml, and lock file that can change an option declaration."""
    for p in sorted(ws.rglob("*")):
        rel = p.relative_to(ws)
        if any(part in SKIP_DIRS for part in rel.parts) or not p.is_file():
            continue
        if rel.as_posix() in SKIP_FILES:
            continue
        if p.suffix in (".nix", ".yaml", ".yml") or p.name == "devenv.lock":
            yield rel.as_posix(), h(p.read_bytes())

def compute_key(ws: Path, devenv_bin: str, keys: list[str], system: str = "x86_64-linux") -> str:
    parts = {
        # Identity of the CLI without starting it: the store path names its content.
        "devenv_cli": os.path.realpath(os.environ.get("REAL_DEVENV", devenv_bin)),
        "system": system,
        "export_flags": ["_module.check=false", "vendomat.neutral=true", "maxDepth=8"],
        "sources": dict(workspace_sources(ws)),
    }
    return h(json.dumps(parts, sort_keys=True).encode())[:32]

def main():
    ws, devenv_bin, cache = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    keys = []
    if "--keys" in sys.argv:
        keys = sys.argv[sys.argv.index("--keys") + 1].split(",")
    pin = compute_key(ws, devenv_bin, [])
    out = cache / pin
    out.mkdir(parents=True, exist_ok=True)
    # One file per top-level option key. "ALL" is the full tree.
    wanted = keys or ["ALL"]
    missing = [k for k in wanted if "--force-miss" in sys.argv or not (out / f"{k}.json").is_file()]
    if not missing:
        print(f"HIT {out} key={pin}")
        return 0
    if "ALL" in missing:
        request = "[]"
    else:
        request = json.dumps(missing)
    done = subprocess.run(
        [devenv_bin, "eval", "-O", "_module.check:bool", "false", "-O", "vendomat.neutral:bool", "true",
         "-O", "vendomat.schema.keys:string", request, "vendomat.schema.json"],
        cwd=ws, capture_output=True, text=True,
    )
    if done.returncode != 0:
        tail = "\n".join(done.stderr.replace("\x1b", "").splitlines()[-6:])
        sys.stderr.write(
            f"vendomat: no option schema for pin {pin} and the export failed (exit {done.returncode}).\n"
            "  The schema cache has no entry, and Nix could not read the locked sources.\n"
            "  Connect to the network, or restore the sources, then run the command again.\n"
            f"  Nix said:\n{tail}\n")
        return 2
    records = json.loads(next(iter(json.loads(done.stdout).values())))
    if "ALL" in missing:
        groups = {"ALL": records}
    else:
        groups = {k: [r for r in records if r["loc"][0] == k] for k in missing}
    for k, recs in groups.items():
        text = json.dumps(recs, sort_keys=True, separators=(",", ":"))
        fd, tmp = tempfile.mkstemp(dir=out)
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, out / f"{k}.json")
    print(f"MISS exported {','.join(groups)} -> {out} key={pin}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
