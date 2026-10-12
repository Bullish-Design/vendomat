# NON-PRODUCTION spike fixture (project 20, spike S1).
# Canonical JSON byte stability. For each accepted case, run `hand.py` as a fresh process under
# three PYTHONHASHSEED values and compare sha256. Then compare reformatted equivalents.
# usage: python -I determinism.py LOGDIR
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import corpus

LOG = sys.argv[1]
os.makedirs(os.path.join(LOG, "cases"), exist_ok=True)


def run(path, seed):
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": str(seed)}
    p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "hand.py"), path], capture_output=True, env=env)
    return p.returncode, p.stdout


same = 0
for id_, desc, text, tree in corpus.ACCEPT:
    path = os.path.join(LOG, "cases", f"{id_}.yaml")
    open(path, "wb").write(text if isinstance(text, bytes) else text.encode())
    hashes = set()
    for seed in (0, 12345, "random"):
        rc, out = run(path, seed)
        assert rc == 0, (id_, rc)
        hashes.add(hashlib.sha256(out).hexdigest())
    same += len(hashes) == 1
print(f"{same} of {len(corpus.ACCEPT)} accepted cases give one sha256 across 3 hash seeds and 3 processes")

A = """\
inputs:
  tools:
    url: "git://collection.example/tools?ref=refs/tags/v1.0.0"
packages:
  - "ripgrep"
  - "fd"
basix:
  machines:
    laptop:
      mode: "adopt-existing"
      swapGiB: 8
"""
# same data: keys reordered, indent changed, comments added, quote style changed, blank lines
B = """\
# a leading comment
basix:
    machines:
        laptop:
            swapGiB: 8   # eight
            mode: 'adopt-existing'

packages:
- 'ripgrep'
- "fd"
inputs:
    tools:
        url: 'git://collection.example/tools?ref=refs/tags/v1.0.0'
"""
C = A.replace('"fd"', '"fd-find"')  # different data
D = A.replace('"ripgrep"\n  - "fd"', '"fd"\n  - "ripgrep"')  # list order differs
hs = {}
for name, txt in (("A", A), ("B-equivalent", B), ("C-different-value", C), ("D-list-reordered", D)):
    path = os.path.join(LOG, "cases", f"det-{name}.yaml")
    open(path, "w").write(txt)
    rc, out = run(path, 0)
    assert rc == 0
    hs[name] = hashlib.sha256(out).hexdigest()
    print(f"{name:20} {hs[name]}")
print("A == B-equivalent (reordered keys, indent, comments, quote style):", hs["A"] == hs["B-equivalent"])
print("A != C (value change):", hs["A"] != hs["C-different-value"])
print("A != D (list order is data):", hs["A"] != hs["D-list-reordered"])
