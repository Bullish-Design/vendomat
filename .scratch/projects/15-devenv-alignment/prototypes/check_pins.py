#!/usr/bin/env python3
"""Read-only tag-pin check for devenv.yaml and devenv.lock.

Usage:  python -I check_pins.py DIR [--collection HOST ...]

Fails (exit 1) when:
  * a git input in devenv.yaml has no ref=refs/tags/... in its URL;
  * a git node in devenv.lock (direct or transitive) has no original ref
    under refs/tags/, or no 40-hex locked rev;
  * a git input in devenv.yaml has no matching node in devenv.lock.

An input is a git input when its URL scheme is git, git+*, or when its
host matches a --collection HOST. Exit 2 means the check could not run
(unreadable file or YAML outside the supported subset). The script only
reads files. It uses the standard library only.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


class Unsupported(Exception):
    pass


def _strip_comment(line):
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"" and (i == 0 or line[i - 1] in " :-"):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text):
    text = text.strip()
    if text[:1] in "{[&*|>!%@`" and text != "[]":
        raise Unsupported(f"unsupported YAML value: {text!r}")
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    if text == "[]":
        return []
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text in ("", "~", "null"):
        return None
    return text


def parse_yaml(text):
    """Parse the block-style YAML subset that devenv.yaml uses."""
    rows = []
    for no, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise Unsupported(f"line {no}: tab indentation")
        line = _strip_comment(raw)
        if not line.strip() or line.strip() == "---":
            continue
        rows.append((no, len(line) - len(line.lstrip(" ")), line.strip()))

    def block(i, indent):
        if i >= len(rows):
            return None, i
        if rows[i][2].startswith("- "):
            items = []
            while i < len(rows) and rows[i][1] == indent and rows[i][2].startswith("- "):
                items.append(_scalar(rows[i][2][2:]))
                i += 1
            return items, i
        mapping = {}
        while i < len(rows) and rows[i][1] == indent:
            no, _, body = rows[i]
            if body.startswith("- "):
                raise Unsupported(f"line {no}: list item inside mapping")
            key, sep, rest = body.partition(":")
            if not sep or (rest and not rest.startswith(" ")):
                raise Unsupported(f"line {no}: expected 'key: value'")
            key = _scalar(key)
            i += 1
            if rest.strip():
                mapping[key] = _scalar(rest)
            elif i < len(rows) and rows[i][1] > indent:
                mapping[key], i = block(i, rows[i][1])
            elif i < len(rows) and rows[i][1] == indent and rows[i][2].startswith("- "):
                mapping[key], i = block(i, indent)
            else:
                mapping[key] = None
        if i < len(rows) and rows[i][1] > indent:
            raise Unsupported(f"line {rows[i][0]}: bad indentation")
        return mapping, i

    if not rows:
        return {}
    value, end = block(0, rows[0][1])
    if end != len(rows):
        raise Unsupported(f"line {rows[end][0]}: trailing content")
    return value


def is_git_url(url, hosts):
    parts = urlsplit(url)
    return (
        parts.scheme == "git"
        or parts.scheme.startswith("git+")
        or (parts.hostname or "") in hosts
    )


def url_ref(url):
    values = parse_qs(urlsplit(url).query).get("ref", [])
    return values[0] if values else None


def check(directory, hosts):
    problems = []
    root = Path(directory)
    config = parse_yaml((root / "devenv.yaml").read_text())
    lock = json.loads((root / "devenv.lock").read_text())
    nodes = lock["nodes"]
    root_inputs = nodes[lock["root"]].get("inputs", {})

    def walk(inputs, trail):
        for name, spec in (inputs or {}).items():
            if not isinstance(spec, dict):
                continue
            url = spec.get("url")
            path = "/".join(trail + [name])
            if url and is_git_url(url, hosts):
                ref = url_ref(url)
                if not (ref or "").startswith("refs/tags/"):
                    problems.append(f"devenv.yaml: {path}: ref is {ref!r}, need refs/tags/...: {url}")
                if not trail:
                    key = root_inputs.get(name)
                    node = nodes.get(key) if isinstance(key, str) else None
                    if node is None:
                        problems.append(f"devenv.lock: {path}: no locked node (run devenv update)")
                    elif (node.get("original") or {}).get("ref") != ref:
                        problems.append(
                            f"devenv.lock: {path}: locked original ref "
                            f"{(node.get('original') or {}).get('ref')!r} differs from yaml ref {ref!r}"
                        )
            walk(spec.get("inputs"), trail + [name])

    walk(config.get("inputs"), [])

    for key, node in nodes.items():
        locked, original = node.get("locked") or {}, node.get("original") or {}
        if locked.get("type") != "git":
            continue
        ref = original.get("ref") or ""
        if not ref.startswith("refs/tags/"):
            problems.append(f"devenv.lock: node {key}: original ref is {ref!r}, need refs/tags/... ({original.get('url')})")
        if not re.fullmatch(r"[0-9a-f]{40}", locked.get("rev", "")):
            problems.append(f"devenv.lock: node {key}: locked rev is not 40 hex characters")
    return problems


def main(argv):
    args, hosts, directory = argv[1:], set(), None
    while args:
        arg = args.pop(0)
        if arg == "--collection" and args:
            hosts.add(args.pop(0))
        elif directory is None and not arg.startswith("-"):
            directory = arg
        else:
            print(__doc__, file=sys.stderr)
            return 2
    if directory is None:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        problems = check(directory, hosts)
    except (OSError, KeyError, ValueError, Unsupported) as error:
        print(f"check_pins: cannot check: {error}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        return 1
    print("ok: every git input is pinned to refs/tags/...")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
