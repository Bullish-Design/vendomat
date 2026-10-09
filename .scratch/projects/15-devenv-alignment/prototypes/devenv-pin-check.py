#!/usr/bin/env python3
"""Read-only. Report devenv module pins that differ from the system pin.

Usage: devenv-pin-check.py --expect REV [--expect REV ...]
         [--cli-version 2.4.0 --repo DEVENV_CLONE] ROOT_DIR
Scans ROOT_DIR/*/devenv.lock (root.inputs.devenv -> locked.rev) and the
top-level require_version key of ROOT_DIR/*/devenv.yaml. With --repo it reads
src/modules/latest-version at each rev (git show) and flags an expected rev
whose modules version differs from --cli-version. Exit 1 on any problem.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path


def lock_rev(path):
    try:
        nodes = json.loads(path.read_text()).get("nodes", {})
    except (OSError, ValueError) as err:
        return None, f"unreadable lock: {err}"
    ref = nodes.get("root", {}).get("inputs", {}).get("devenv")
    if not isinstance(ref, str):
        return None, "no devenv input (or follows path)"
    return nodes.get(ref, {}).get("locked", {}).get("rev"), ""


def require_version(path):
    if not path.exists():
        return "NO-YAML"
    for line in path.read_text().splitlines():
        m = re.match(r"^require_version:\s*(.*?)\s*(#.*)?$", line)
        if m:
            return m.group(1).strip("\"'")
    return None


def modules_version(repo, rev):
    cmd = ["git", "-C", repo, "show", f"{rev}:src/modules/latest-version"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--expect", action="append", required=True)
    ap.add_argument("--cli-version")
    ap.add_argument("--repo")
    a = ap.parse_args()
    ver, rows, bad = {}, [], 0
    for lock in sorted(Path(a.root).glob("*/devenv.lock")):
        rev, note = lock_rev(lock)
        rv = require_version(lock.parent / "devenv.yaml")
        issues = []
        if rev is None:
            issues.append(f"NO-REV({note})")
        elif rev not in a.expect:
            issues.append("REV-MISMATCH")
        if rv is None:
            issues.append("NO-require_version")
        if a.repo and rev and rev not in ver:
            ver[rev] = modules_version(a.repo, rev)
        if rev in a.expect and a.cli_version and ver.get(rev) != a.cli_version:
            issues.append(f"EXPECTED-REV-MODULES-VERSION-{ver.get(rev)}")
        bad += bool(issues)
        rows.append((lock.parent.name, (rev or "-")[:12], ver.get(rev, "-"), rv or "-", ",".join(issues) or "ok", rev or "-"))
    w = max((len(r[0]) for r in rows), default=7)
    print(f"{'project':<{w}}  {'lock-rev':<12}  {'mod-ver':<7}  {'require_version':<15}  status")
    for r in rows:
        print(f"{r[0]:<{w}}  {r[1]:<12}  {r[2]:<7}  {r[3]:<15}  {r[4]}")
    counts = {}
    for r in rows:
        counts[r[5]] = counts.get(r[5], 0) + 1
    print(f"\n{len(rows)} projects, {bad} with problems, {len(counts)} distinct revs (incl. '-' = none)")
    for rev, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {rev[:12]}  x{n}  modules-version={ver.get(rev, '-')}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
