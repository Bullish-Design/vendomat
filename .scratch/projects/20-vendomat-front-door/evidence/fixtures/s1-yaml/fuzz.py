# NON-PRODUCTION spike fixture (project 20, spike S1).
# Differential fuzz. Oracle: PyYAML safe_load (YAML 1.1) and ruamel.yaml safe load (YAML 1.2).
# Part 1: random trees rendered as subset YAML must parse back to the same tree in all three.
# Part 2: random mutations of corpus files. When the hand parser accepts a mutant, both oracles
#         must accept it and return the same tree. The hand parser must never raise anything
#         except LintError.
# usage: python -I fuzz.py LOGDIR N_TREES N_MUTANTS SEED
import io
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import corpus
import hand
import yaml
from ruamel.yaml import YAML

LOG, N_TREES, N_MUT, SEED = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
os.makedirs(LOG, exist_ok=True)
rnd = random.Random(SEED)
ry = YAML(typ="safe")


def canon(t):
    return json.dumps(t, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


ALPHA = "abcxyz_-"
WORDS = ["a", "bb", "k-1", "_p", "Key", "x_y", "nixpkgs-python", "enterShell", "yes_", "nope", "on1"]
TEXT_CHARS = list("abc xyz#:-'\"\\{}[]&*!|>%@`,?=$/.~") + ["é", "日", "\U0001F600"]


def rnd_text(lines=False):
    n = rnd.randint(0, 12)
    s = "".join(rnd.choice(TEXT_CHARS) for _ in range(n))
    return s


def rnd_block_text():
    ls = []
    for _ in range(rnd.randint(1, 5)):
        kind = rnd.random()
        if kind < 0.2:
            ls.append("")
        else:
            ind = " " * rnd.choice([0, 0, 0, 1, 2, 4])
            tab = "\t" if rnd.random() < 0.1 else ""
            ls.append(ind + tab + rnd_text())
    # first text line must not start with a space-only difference that makes indentation ambiguous
    first = next((i for i, l in enumerate(ls) if l != ""), None)
    if first is None:
        return "x"
    ls[first] = ls[first].lstrip(" ") or "z"
    ls[first] = "z" + ls[first] if ls[first].startswith("\t") else ls[first]
    ls = [l if l.strip(" ") != "" else "" for l in ls]
    while ls and ls[-1] == "":
        ls.pop()
    return "\n".join(ls)


def dq(s):
    out = []
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20 or ch in "\u2028\u2029\ufeff":
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def key_text(k):
    if hand.IDENT.fullmatch(k) and k.lower() not in hand.RESERVED_KEYS and rnd.random() < 0.7:
        return k
    return dq(k)


def gen_tree(depth=0):
    r = rnd.random()
    if depth >= 4 or r < 0.35:
        return gen_scalar()
    if r < 0.7:
        n = rnd.randint(0, 4)
        keys = rnd.sample(WORDS + ["a.b", "with space", "7"], n)
        return {k: gen_tree(depth + 1) for k in keys}
    return [gen_tree(depth + 1) for _ in range(rnd.randint(0, 4))]


def gen_scalar():
    r = rnd.random()
    if r < 0.15:
        return rnd.choice([True, False, None])
    if r < 0.35:
        return rnd.choice([0, 1, -1, 42, 9223372036854775807, -9223372036854775808, rnd.randint(-1000, 1000)])
    if r < 0.55:
        return rnd_block_text() + rnd.choice(["", "\n"])
    return rnd_text() if rnd.random() < 0.9 else rnd.choice(["yes", "NO", "3.10", "~", "null", "", "true", "0o12", "1e3"])


def scalar_inline(v, style_ok=True):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, int):
        return str(v)
    if rnd.random() < 0.25 and "'" not in v and all(ord(c) >= 0x20 for c in v) and "\\" not in v or (rnd.random() < 0.1 and all(ord(c) >= 0x20 and c not in "\u2028\u2029\ufeff" for c in v)):
        if all(ord(c) >= 0x20 for c in v):
            return "'" + v.replace("'", "''") + "'"
    return dq(v)


def can_block(v, ind):
    return isinstance(v, str) and v != "" and "\n" in v.strip("\n") + "x" and all((ord(c) >= 0x20 or c in "\n\t") and c not in "\u2028\u2029\ufeff" for c in v) \
        and not v.startswith((" ", "\n", "\t")) and v.split("\n")[0].strip(" ") != "" and not any(l != l.rstrip("\n") and False for l in v.split("\n"))


def block_form(v, indent, parent_indent):
    # choose chomp; v must end with exactly one newline for "|" or none for "|-"
    if v.endswith("\n\n") or v == "" or v.startswith(("\n", " ", "\t")):
        return None
    chomp = "" if v.endswith("\n") else "-"
    body = v[:-1] if v.endswith("\n") else v
    lines = body.split("\n")
    if lines[0].strip(" ") == "" or lines[0][0] in " \t":
        return None
    if any(c in v for c in "\u2028\u2029\ufeff\r") or any(ord(c) < 0x20 and c not in "\n\t" for c in v):
        return None
    pad = " " * (parent_indent + rnd.choice([1, 2, 4]))
    head = "|" + chomp + (" # note" if rnd.random() < 0.2 else "")
    return head, [(pad + l) if l != "" else rnd.choice(["", ""]) for l in lines]


def render(tree):
    out = []
    unit = rnd.choice([2, 2, 4])

    def put(v, indent, prefix, parent_indent, in_list_item=False):
        """Render value v after `prefix` (e.g. 'key:' or '-'), appended to out."""
        if isinstance(v, dict) and v:
            if prefix is None:
                body_map(v, indent)
                return
            out.append(prefix)
            body_map(v, indent + unit)
        elif isinstance(v, list) and v:
            out.append(prefix)
            body_list(v, indent + (0 if prefix.endswith(":") and rnd.random() < 0.3 else unit))
        elif isinstance(v, dict):
            out.append(prefix + " {}" + rnd.choice(["", "  # c"]))
        elif isinstance(v, list):
            out.append(prefix + " []" + rnd.choice(["", "  # c"]))
        else:
            if isinstance(v, str) and rnd.random() < 0.6:
                bf = block_form(v, indent, parent_indent)
                if bf:
                    out.append(prefix + " " + bf[0])
                    out.extend(bf[1])
                    return
            out.append(prefix + " " + scalar_inline(v) + rnd.choice(["", "", "  # c"]))

    def body_map(d, indent):
        for k, v in d.items():
            if rnd.random() < 0.15:
                out.append(" " * indent + "# comment")
            if rnd.random() < 0.1:
                out.append("")
            start = len(out)
            put(v, indent, " " * indent + key_text(k) + ":", indent)

    def body_list(items, indent):
        for v in items:
            if isinstance(v, dict) and v and rnd.random() < 0.8:
                # compact map in list item: first key on the dash line
                first = True
                sub = []
                saved = out[:]
                out.clear()
                body_map(v, indent + 2)
                lines = out[:]
                out.clear()
                out.extend(saved)
                lines[0] = " " * indent + "- " + lines[0][indent + 2 :]
                out.extend(lines)
            elif isinstance(v, list) and v and rnd.random() < 0.8:
                saved = out[:]
                out.clear()
                body_list(v, indent + 2)
                lines = out[:]
                out.clear()
                out.extend(saved)
                lines[0] = " " * indent + "- " + lines[0][indent + 2 :]
                out.extend(lines)
            else:
                put(v, indent, " " * indent + "-", indent)

    if not tree:
        return rnd.choice(["", "# nothing\n"])
    body_map(tree, rnd.choice([0, 0, 0, 2]))
    return "\n".join(out) + "\n"


bad = []
ok_trees = 0
for n in range(N_TREES):
    tree = {k: gen_tree(1) for k in rnd.sample(WORDS, rnd.randint(0, 5))}
    # PyYAML/ruamel return None for an empty document; compare with {}
    text = render(tree)
    try:
        got, _ = hand.load(text.encode())
    except hand.LintError as e:
        bad.append(("hand-rejected-own-render", text, e.format()))
        continue
    except Exception as e:  # noqa: BLE001
        bad.append(("hand-crash", text, repr(e)))
        continue
    py = yaml.safe_load(text) or {}
    ru = ry.load(text) or {}
    if canon(got) != canon(tree):
        bad.append(("hand-wrong", text, canon(got)[:200] + " vs " + canon(tree)[:200]))
    elif canon(py) != canon(tree):
        bad.append(("pyyaml-differs", text, canon(py)[:200]))
    elif canon(ru) != canon(tree):
        bad.append(("ruamel-differs", text, canon(ru)[:200]))
    else:
        ok_trees += 1
print(f"part 1: {N_TREES} random trees; all three agree and match the source tree: {ok_trees}; problems: {len(bad)}")

# ---- part 2 mutation
seeds = [t if isinstance(t, bytes) else t.encode() for _, _, t, _ in corpus.ACCEPT]
seeds += [t if isinstance(t, bytes) else t.encode() for _, _, t, *_ in corpus.REJECT]
CHARS = list(": -#\"'\\\n\t|>[]{}&*!%@`,?~.0189aZ_") + ["\u00e9", "\u2028", "\x00", "\r", "\ufeff", "é"]


def mutate(b):
    s = b.decode("utf-8", "surrogateescape")
    for _ in range(rnd.randint(1, 3)):
        if not s:
            s = rnd.choice(CHARS)
            continue
        op = rnd.randrange(7)
        i = rnd.randrange(len(s))
        if op == 0:
            s = s[:i] + s[i + 1 :]
        elif op == 1:
            s = s[:i] + rnd.choice(CHARS) + s[i:]
        elif op == 2:
            s = s[:i] + rnd.choice(CHARS) + s[i + 1 :]
        elif op == 3:
            ls = s.split("\n")
            j = rnd.randrange(len(ls))
            ls.insert(j, ls[rnd.randrange(len(ls))])
            s = "\n".join(ls)
        elif op == 4:
            ls = s.split("\n")
            j = rnd.randrange(len(ls))
            ls[j] = rnd.choice(["", " ", "  ", "    "]) + ls[j].lstrip(" ")
            s = "\n".join(ls)
        elif op == 5:
            s = s[:i]
        else:
            ls = s.split("\n")
            if len(ls) > 1:
                j = rnd.randrange(len(ls) - 1)
                ls[j], ls[j + 1] = ls[j + 1], ls[j]
            s = "\n".join(ls)
    return s.encode("utf-8", "surrogateescape")


acc = rej = crash = 0
diverge = []
overreject = 0
for n in range(N_MUT):
    m = mutate(rnd.choice(seeds))
    try:
        tree, p = hand.load(m)
        found = hand.find_secrets(tree, p)
        res = ("ok", tree) if not found else ("err",)
    except hand.LintError:
        res = ("err",)
    except Exception as e:  # noqa: BLE001
        crash += 1
        diverge.append(("crash", m, repr(e)))
        continue
    if res[0] == "ok":
        acc += 1
        text = m.decode("utf-8")
        try:
            py = yaml.safe_load(text)
            ru = ry.load(text)
        except Exception as e:  # noqa: BLE001
            diverge.append(("oracle-rejects-hand-accepted", m, repr(e)[:150]))
            continue
        py = {} if py is None else py
        ru = {} if ru is None else ru
        if canon(py) != canon(res[1]) or canon(ru) != canon(res[1]):
            diverge.append(("tree-differs", m, f"hand={canon(res[1])[:120]} py={canon(py)[:120]} ru={canon(ru)[:120]}"))
    else:
        rej += 1
print(f"part 2: {N_MUT} mutants; hand accepted {acc}, rejected {rej}, crashed {crash}; divergences {len(diverge)}")

with open(os.path.join(LOG, "fuzz-problems.txt"), "w") as f:
    for kind, text, info in bad[:50]:
        f.write(f"## {kind}: {info}\n{text}\n-----\n")
    for kind, m, info in diverge[:80]:
        f.write(f"## {kind}: {info}\n{m!r}\n-----\n")
print("details:", os.path.join(LOG, "fuzz-problems.txt"))
