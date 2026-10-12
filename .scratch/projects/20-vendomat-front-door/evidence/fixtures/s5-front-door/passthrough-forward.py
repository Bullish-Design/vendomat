#!/usr/bin/env python3
# S5 fixture, NON-PRODUCTION. Pass-through by subprocess.Popen, with signal forwarding
# and the shell convention 128+n for a child that died by signal n.
import os, signal, subprocess, sys
DEVENV = os.environ.get("VENDOMAT_DEVENV", "devenv")
p = subprocess.Popen([DEVENV, *sys.argv[1:]])
def fwd(sig, frm):
    try: p.send_signal(sig)
    except ProcessLookupError: pass
for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
    signal.signal(s, fwd)
while True:
    try:
        rc = p.wait(); break
    except KeyboardInterrupt:
        pass
sys.exit(128 - rc if rc < 0 else rc)
