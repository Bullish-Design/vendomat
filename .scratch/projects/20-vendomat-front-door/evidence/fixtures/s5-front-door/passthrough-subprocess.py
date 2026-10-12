#!/usr/bin/env python3
# S5 fixture, NON-PRODUCTION. Pass-through by subprocess.run, with no signal handling.
import os, subprocess, sys
DEVENV = os.environ.get("VENDOMAT_DEVENV", "devenv")
try:
    rc = subprocess.run([DEVENV, *sys.argv[1:]]).returncode
except KeyboardInterrupt:
    print("WRAPPER-KeyboardInterrupt", flush=True); rc = 130
sys.exit(rc)   # a negative returncode (death by signal) becomes exit code 256-n here
