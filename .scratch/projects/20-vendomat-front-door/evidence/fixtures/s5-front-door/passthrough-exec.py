#!/usr/bin/env python3
# S5 fixture, NON-PRODUCTION. Pass-through by os.execvp: the wrapper becomes devenv.
import os, sys
DEVENV = os.environ.get("VENDOMAT_DEVENV", "devenv")
# (the prep step runs here, before exec)
os.execvp(DEVENV, [DEVENV, *sys.argv[1:]])
