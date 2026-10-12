#!/usr/bin/env python3
# S5 fixture, NON-PRODUCTION. Prototype front door: prep, then become devenv (os.execvp).
# Exit codes: 0 ok; 64 usage; 65 lint fault; 66 schema fault; 69 pinned build missing;
#             70 launcher protocol mismatch; 71 no host release; 72 lock unreadable (the launcher exits 69..72);
#             any other code is devenv's or the user command's own (passed through by exec).
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
if not args:
    print("vendomat: usage: vendomat <command> [args]", file=sys.stderr); sys.exit(64)
rc = subprocess.run([sys.executable, "-I", os.path.join(HERE, "prep.py"), os.getcwd()]).returncode
if rc != 0:
    sys.exit(rc)
print("vendomat: release=%s" % os.environ.get("VENDOMAT_RELEASE_KIND", "direct"), file=sys.stderr)
dev = os.environ.get("VENDOMAT_DEVENV", "devenv")
os.execvp(dev, [dev, *args])
