# NON-PRODUCTION spike fixture (project 20, spike S1).
# Run every corpus case through each candidate. Print tables. Write JSON results to the log dir.
# usage: python -I run_s1.py LOGDIR   (needs PyYAML, ruamel.yaml, strictyaml; reads src/vendomat/yamlsubset.py)
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.environ["YAMLSUBSET_DIR"])  # src/vendomat in the research workspace, read only

import corpus
import evlint
import hand
from hand import LintError

LOG = sys.argv[1]
os.makedirs(LOG, exist_ok=True)


def to_bytes(x):
    return x if isinstance(x, bytes) else x.encode("utf-8")


def canon(tree):
    return json.dumps(tree, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=repr)


# ---- candidate adapters: return ("ok", tree) or ("err", code, line, col, msg)
def run_hand(data):
    try:
        tree, p = hand.load(data)
        sec = hand.find_secrets(tree, p)
        if sec:
            raise sec[0]
        return ("ok", tree)
    except LintError as e:
        return ("err", e.code, e.line, e.col, e.format())


def _ev(backend):
    def f(data):
        try:
            tree = evlint.load(data, backend)

            class P:
                vlocs = {}
                keylocs = {}

            sec = hand.find_secrets(tree, P())
            if sec:
                raise sec[0]
            return ("ok", tree)
        except LintError as e:
            return ("err", e.code, e.line, e.col, e.format())

    return f


def run_strictyaml(data):
    import strictyaml

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        return ("err", "not-utf8", 0, 0, str(e))
    try:
        y = strictyaml.dirty_load(text, schema=strictyaml.Any(), allow_flow_style=False)
        return ("ok", y.data)
    except Exception as e:  # noqa: BLE001
        line = getattr(getattr(e, "problem_mark", None), "line", -1) + 1
        col = getattr(getattr(e, "problem_mark", None), "column", -1) + 1
        return ("err", type(e).__name__, line, col, str(e).splitlines()[0] if str(e) else "")


def run_yamlsubset(data):
    import yamlsubset

    try:
        return ("ok", yamlsubset.parse(data.decode("utf-8"), "vendomat.yaml"))
    except yamlsubset.YamlError as e:
        return ("err", "YamlError", 0, 0, str(e))
    except UnicodeDecodeError as e:
        return ("err", "not-utf8", 0, 0, str(e))
    except Exception as e:  # noqa: BLE001
        return ("crash", type(e).__name__, 0, 0, str(e))


def run_pyyaml_plain(data):
    import yaml

    try:
        return ("ok", yaml.safe_load(data))
    except Exception as e:  # noqa: BLE001
        return ("err", type(e).__name__, 0, 0, str(e).splitlines()[0])


def run_ruamel_plain(data):
    from ruamel.yaml import YAML

    try:
        v = YAML(typ="safe").load(data)
        return ("ok", {} if v is None else v)
    except Exception as e:  # noqa: BLE001
        return ("err", type(e).__name__, 0, 0, str(e).splitlines()[0])


IMPLS = {
    "hand (d)": run_hand,
    "pyyaml events (b1)": _ev("pyyaml"),
    "ruamel events (b2)": _ev("ruamel"),
    "strictyaml (c)": run_strictyaml,
    "yamlsubset.py today (a)": run_yamlsubset,
    "pyyaml safe_load (no lint)": run_pyyaml_plain,
    "ruamel safe load (no lint)": run_ruamel_plain,
}


def same(a, b):
    try:
        return canon(a) == canon(b)
    except TypeError:
        return False


results = {}
summary = []
for name, fn in IMPLS.items():
    acc_ok = acc_wrongval = acc_rejected = 0
    rej_rejected = rej_code = rej_line = rej_col = rej_accepted = crashes = 0
    detail = {"accept": {}, "reject": {}}
    for id_, desc, text, tree in corpus.ACCEPT:
        res = fn(to_bytes(text))
        if res[0] == "ok":
            if same(res[1], tree):
                acc_ok += 1
                detail["accept"][id_] = "ok"
            else:
                acc_wrongval += 1
                detail["accept"][id_] = f"WRONG VALUE {canon(res[1])[:100]}"
        elif res[0] == "crash":
            crashes += 1
            detail["accept"][id_] = f"CRASH {res[1:]}"
        else:
            acc_rejected += 1
            detail["accept"][id_] = f"REJECTED {res[1]} {res[2]}:{res[3]} {res[4][:80]}"
    for id_, desc, text, code, line, col in corpus.REJECT:
        res = fn(to_bytes(text))
        if res[0] == "ok":
            rej_accepted += 1
            detail["reject"][id_] = f"ACCEPTED {canon(res[1])[:80]}"
        elif res[0] == "crash":
            crashes += 1
            detail["reject"][id_] = f"CRASH {res[1:]}"
        else:
            rej_rejected += 1
            c = res[1] == code
            l = res[2] == line
            k = res[3] == col
            rej_code += c
            rej_line += c and l
            rej_col += c and l and k
            detail["reject"][id_] = f"rejected code={'ok' if c else res[1]} line={'ok' if l else res[2]} col={'ok' if k else res[3]}"
    results[name] = detail
    summary.append((name, acc_ok, acc_wrongval, acc_rejected, rej_rejected, rej_code, rej_line, rej_col, rej_accepted, crashes))

na, nr = len(corpus.ACCEPT), len(corpus.REJECT)
print(f"corpus: {na} accepted cases, {nr} rejected cases\n")
hdr = f"{'implementation':28} | acc ok | acc wrong value | acc wrongly rejected | rej rejected | rej code ok | +line ok | +col ok | rej wrongly ACCEPTED | crashes"
print(hdr)
print("-" * len(hdr))
for row in summary:
    print(f"{row[0]:28} | {row[1]:6} | {row[2]:15} | {row[3]:20} | {row[4]:12} | {row[5]:11} | {row[6]:8} | {row[7]:7} | {row[8]:20} | {row[9]}")

json.dump(results, open(os.path.join(LOG, "results.json"), "w"), indent=1, sort_keys=True)

# ---- failures of the chosen candidates
print("\n== hand (d) mismatches ==")
for kind in ("accept", "reject"):
    for id_, v in results["hand (d)"][kind].items():
        if v != "ok" and not (v.startswith("rejected") and "code=ok line=ok col=ok" in v):
            print(id_, v)

for impl in ("pyyaml events (b1)", "ruamel events (b2)"):
    print(f"\n== {impl} mismatches ==")
    for kind in ("accept", "reject"):
        for id_, v in results[impl][kind].items():
            if v != "ok" and not (v.startswith("rejected") and "code=ok line=ok col=ok" in v):
                print(id_, v)

# ---- diagnostics gallery
with open(os.path.join(LOG, "diagnostics.txt"), "w") as out:
    for id_, desc, text, code, line, col in corpus.REJECT:
        res = run_hand(to_bytes(text))
        src = to_bytes(text).decode("utf-8", "replace").split("\n")
        out.write(f"[{id_}] {desc}\n  {res[4] if res[0]=='err' else 'ACCEPTED'}\n")
        if res[0] == "err" and 1 <= res[2] <= len(src):
            out.write(f"    {src[res[2]-1]!r}\n")
        out.write("\n")
print("\nwrote", os.path.join(LOG, "diagnostics.txt"))

# ---- canonical JSON: determinism and cross-implementation equality
os.makedirs(os.path.join(LOG, "canon"), exist_ok=True)
rows = []
for id_, desc, text, tree in corpus.ACCEPT:
    data = to_bytes(text)
    t, _ = hand.load(data)
    b = hand.canonical(t)
    open(os.path.join(LOG, "canon", f"{id_}.json"), "wb").write(b)
    h = hashlib.sha256(b).hexdigest()
    b2 = evlint.load(data, "pyyaml")
    b3 = evlint.load(data, "ruamel")
    eq = hand.canonical(b2) == b and hand.canonical(b3) == b
    rows.append((id_, h, eq))
with open(os.path.join(LOG, "canon-sha256.txt"), "w") as f:
    for id_, h, eq in rows:
        f.write(f"{h}  {id_}.json  cross-impl-equal={eq}\n")
print("canonical cross-implementation equal:", sum(1 for r in rows if r[2]), "of", len(rows))
