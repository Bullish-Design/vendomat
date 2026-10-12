# NON-PRODUCTION spike fixture (project 20, spike S1).
# How do plain loaders read risky plain scalars? Shows why the subset rejects them.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand
import yaml
from ruamel.yaml import YAML

ry = YAML(typ="safe")
VALUES = ["no", "No", "NO", "yes", "on", "off", "y", "n", "true", "True", "TRUE", "null", "Null", "~", "", "3.10", "3.1", "1e3", "1E3", ".inf", ".nan",
          "0o12", "012", "0x1F", "0b11", "+1", "-0", "1_000", "1:30", "2024-01-01", "12:30:45", "9223372036854775808", "ripgrep", "a: b", "- x", "# c"]
print(f"{'plain value':22} | {'PyYAML 6 (YAML 1.1)':32} | {'ruamel 0.19 (YAML 1.2)':32} | hand parser")
for v in VALUES:
    doc = f"k: {v}\n"
    try:
        py = repr(yaml.safe_load(doc)["k"]) if yaml.safe_load(doc) else "(no map)"
    except Exception as e:  # noqa: BLE001
        py = "ERROR"
    try:
        d = ry.load(doc)
        ru = repr(d["k"]) if d else "(no map)"
    except Exception as e:  # noqa: BLE001
        ru = "ERROR"
    try:
        t, _ = hand.load(doc.encode())
        h = "accept " + repr(t["k"])
    except hand.LintError as e:
        h = "reject " + e.code
    print(f"{v!r:22} | {py:32} | {ru:32} | {h}")
