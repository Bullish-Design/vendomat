# NON-PRODUCTION spike fixture (project 20, spike S1).
# Parse time on a large generated file. usage: python -I bigfile.py N
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evlint
import hand

n = int(sys.argv[1])
text = "".join(f"svc{i}:\n  enable: true\n  port: {i}\n  name: \"service number {i}\"\n  tags:\n    - \"a\"\n    - \"b\"\n" for i in range(n))
data = text.encode()
print(f"input: {len(data)} bytes, {text.count(chr(10))} lines")
for name, fn in (("hand", lambda: hand.load(data)), ("pyyaml events", lambda: evlint.load(data, "pyyaml")), ("ruamel events", lambda: evlint.load(data, "ruamel"))):
    t0 = time.perf_counter()
    fn()
    print(f"{name:14} {1000*(time.perf_counter()-t0):9.1f} ms")
