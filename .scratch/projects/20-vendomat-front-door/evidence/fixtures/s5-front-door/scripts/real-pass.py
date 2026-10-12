#!/usr/bin/env python3
# S5 fixture, NON-PRODUCTION. Real devenv through the exec wrapper: exit codes and SIGINT on `up`.
import os, signal, subprocess, sys, time
S5 = os.path.expanduser("~/.local/state/vendomat/p20/2026-10-11/S5")
W = "/home/andrew/Documents/Projects/gitman-workspaces/p20-research/.scratch/projects/20-vendomat-front-door/evidence/fixtures/s5-front-door/passthrough-%s.py"
env = {k: v for k, v in os.environ.items() if not k.startswith(("DEVENV_", "DIRENV_")) and k not in ("IN_NIX_SHELL", "VIRTUAL_ENV", "NIX_PYTHONPATH", "PYTHONPATH")}
env["VENDOMAT_DEVENV"] = "/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv"
def run(kind, args, cwd):
    t = time.time()
    p = subprocess.run([W % kind, *args], cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, round(time.time() - t, 2)
for kind in ("exec", "forward"):
    for label, args in (("shell -- sh -c 'exit 7'", ["shell", "--", "sh", "-c", "exit 7"]),
                        ("shell -- true", ["shell", "--", "true"]),
                        ("tasks run no:such", ["tasks", "run", "no:such"]),
                        ("unknown subcommand", ["frobnicate"]),
                        ("eval env.S5_B1", ["eval", "env.S5_B1"])):
        print(kind, label, "->", run(kind, args, S5 + "/fx"))
# SIGINT to the process group during `devenv up`
for kind in ("exec", "forward"):
    p = subprocess.Popen([W % kind, "--no-tui", "up"], cwd=S5 + "/fx", env=env, stdin=subprocess.DEVNULL,
                         stdout=open(S5 + "/logs/real-up-%s.log" % kind, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    time.sleep(12)
    os.killpg(p.pid, signal.SIGINT)
    try: rc = p.wait(timeout=30)
    except subprocess.TimeoutExpired:
        rc = "TIMEOUT"; os.killpg(p.pid, signal.SIGKILL)
    left = subprocess.run(["pgrep", "-s", str(p.pid)], capture_output=True, text=True).stdout.split()
    print(kind, "up + SIGINT to group ->", rc, "processes left in session:", len(left))
    for pid in left:
        try: os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError: pass
