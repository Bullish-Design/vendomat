# NON-PRODUCTION spike fixture (project 20, spike S1).
# Startup cost of each candidate: wall time of `python -I -c <snippet>` in a fresh process.
# usage: python -I timing.py FIXTURE_DIR YAML_FILE RUNS [EXTRA_PYTHON_FOR_TYPER]
import resource
import statistics
import subprocess
import sys
import time

d, yfile, runs = sys.argv[1], sys.argv[2], int(sys.argv[3])
py = sys.executable
snips = {
    "python -I (bare interpreter)": "pass",
    "hand: import + parse + canonical": f"import sys;sys.path.insert(0,{d!r});import hand;t,p=hand.load(open({yfile!r},'rb').read());hand.find_secrets(t,p);hand.canonical(t)",
    "pyyaml: import yaml": "import yaml",
    "pyyaml: import + events lint + canonical": f"import sys;sys.path.insert(0,{d!r});import evlint,hand;t=evlint.load(open({yfile!r},'rb').read(),'pyyaml');hand.canonical(t)",
    "ruamel: import ruamel.yaml": "from ruamel.yaml import YAML",
    "ruamel: import + events lint + canonical": f"import sys;sys.path.insert(0,{d!r});import evlint,hand;t=evlint.load(open({yfile!r},'rb').read(),'ruamel');hand.canonical(t)",
    "strictyaml: import strictyaml": "import strictyaml",
}
rows = []
for name, code in snips.items():
    times = []
    for _ in range(3):
        subprocess.run([py, "-I", "-c", code], check=True, capture_output=True)
    cpus = []
    for _ in range(runs):
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.perf_counter()
        subprocess.run([py, "-I", "-c", code], check=True, capture_output=True)
        times.append((time.perf_counter() - t0) * 1000)
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpus.append((r1.ru_utime + r1.ru_stime - r0.ru_utime - r0.ru_stime) * 1000)
    rows.append((name, statistics.median(times), min(times), statistics.median(cpus)))
if len(sys.argv) > 4:
    py2 = sys.argv[4]
    times = []
    cpus = []
    for _ in range(runs):
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.perf_counter()
        subprocess.run([py2, "-I", "-c", "import typer"], check=True, capture_output=True)
        times.append((time.perf_counter() - t0) * 1000)
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpus.append((r1.ru_utime + r1.ru_stime - r0.ru_utime - r0.ru_stime) * 1000)
    rows.append(("(reference) import typer, current CLI dependency", statistics.median(times), min(times), statistics.median(cpus)))
print(f"{'case':58} | median wall ms | min wall ms | median CPU ms   ({runs} runs)")
for name, med, lo, cpu in rows:
    print(f"{name:58} | {med:14.1f} | {lo:12.1f} | {cpu:13.1f}")
