# NON-PRODUCTION spike fixture (project 20, S3). Minimal data validator over the exported schema.
# Usage: python3 -I validate.py SCHEMA_OUT.json DATA.json
# Reads the raw `devenv eval` output (a dict whose one value is the schema JSON string).
# Exit 0 if valid, 1 with one line per fault. Covers: str int bool enum nullOr listOf attrsOf
# submodule freeform. Other type names pass as "unchecked" and are listed.
import json, sys

raw = json.load(open(sys.argv[1]))
records = json.loads(next(iter(raw.values())))
data = json.load(open(sys.argv[2]))

# Index: top-level option path -> record. Sub-options of a submodule live in type.options.
index = {tuple(r["loc"]): r for r in records}
faults, unchecked = [], set()

def ty_check(t, v, path):
    n = t["name"]
    nested = t.get("nested", {})
    if n == "str" or n == "nonEmptyStr" or n == "singleLineStr":
        ok = isinstance(v, str)
    elif n == "int":
        ok = isinstance(v, int) and not isinstance(v, bool)
    elif n == "bool":
        ok = isinstance(v, bool)
    elif n == "enum":
        vals = t["payload"]["values"]
        ok = v in vals
        if not ok:
            return faults.append(f"{path}: {v!r} is not one of {vals}")
    elif n == "nullOr":
        return None if v is None else ty_check(nested["elemType"], v, path)
    elif n == "listOf":
        if not isinstance(v, list):
            return faults.append(f"{path}: expected a list")
        for i, x in enumerate(v):
            ty_check(nested["elemType"], x, f"{path}[{i}]")
        return None
    elif n == "attrsOf":
        if not isinstance(v, dict):
            return faults.append(f"{path}: expected an attribute set")
        for k, x in v.items():
            ty_check(nested["elemType"], x, f"{path}.{k}")
        return None
    elif n == "submodule":
        return sub_check(t, v, path)
    else:
        unchecked.add(f"{path} ({n})")
        return None
    if not ok:
        faults.append(f"{path}: expected {n}, got {type(v).__name__}")

def sub_check(t, v, path):
    if not isinstance(v, dict):
        return faults.append(f"{path}: expected an attribute set")
    opts = {o["loc"][-1]: o for o in (t.get("options") or [])}
    free = t.get("nested", {}).get("freeformType")
    for k, x in v.items():
        if k in opts:
            ty_check(opts[k]["type"], x, f"{path}.{k}")
        elif free:
            ty_check(free.get("nested", {}).get("elemType", free), x, f"{path}.{k}")
        else:
            faults.append(f"{path}.{k}: no such option")

def walk(prefix, obj):
    for k, v in obj.items():
        p = prefix + (k,)
        if p in index:
            ty_check(index[p]["type"], v, ".".join(p))
        elif any(loc[: len(p)] == p for loc in index):
            if isinstance(v, dict):
                walk(p, v)
            else:
                faults.append(f"{'.'.join(p)}: expected an attribute set")
        else:
            faults.append(f"{'.'.join(p)}: no such option")

walk((), data)
for f in faults:
    print("FAULT", f)
for u in sorted(unchecked):
    print("UNCHECKED", u)
sys.exit(1 if faults else 0)
