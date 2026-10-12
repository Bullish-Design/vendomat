#!/usr/bin/env python3
# S5 fixture, NON-PRODUCTION. Test harness for the three pass-through wrappers.
# Usage: run-passthrough.py   (prints one line per case)
import os, pty, signal, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
FAKE = os.path.join(HERE, "fake-devenv")
WRAPPERS = ["passthrough-exec.py", "passthrough-subprocess.py", "passthrough-forward.py"]
env = dict(os.environ, VENDOMAT_DEVENV=FAKE)

def run(w, args, stdin=None):
    p = subprocess.run([os.path.join(HERE, w), *args], input=stdin, env=env,
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def sig_case(w, sig, group):
    p = subprocess.Popen([os.path.join(HERE, w), "up"], env=env, stdout=subprocess.PIPE, text=True,
                         start_new_session=True)
    while "UP-READY" not in p.stdout.readline():
        pass
    time.sleep(0.3)
    child_pid = None
    if group:
        os.killpg(p.pid, sig)
    else:
        os.kill(p.pid, sig)
    try:
        rc = p.wait(timeout=5)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True; rc = None
    left = subprocess.run(["pgrep", "-s", str(p.pid), "-f", "fake-devenv"], capture_output=True, text=True).stdout.split()
    for pid in left:
        try: os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError: pass
    out = ""
    try:
        out = p.stdout.read() if rc is not None else ""
    except Exception:
        pass
    if timed_out:
        try: os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        p.wait()
    return rc, timed_out, out.strip().replace("\n", " | "), len(left)

def pty_case(w):
    master, slave = pty.openpty()
    p = subprocess.Popen([os.path.join(HERE, w), "tty"], env=env, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    p.wait()
    data = b""
    try:
        os.set_blocking(master, False)
        data = os.read(master, 4096)
    except OSError:
        pass
    return p.returncode, data.decode().strip()

for w in WRAPPERS:
    print("=== %s" % w)
    for code in (0, 1, 3, 77):
        rc, out, _ = run(w, ["exit", str(code)])
        print("exit %-3d -> wrapper rc=%d" % (code, rc))
    rc, out, _ = run(w, ["segv"])
    print("child SIGSEGV -> wrapper rc=%d" % rc)
    rc, out, _ = run(w, ["cat"], stdin="hello stdin\n")
    print("stdin pipe -> rc=%d out=%r" % (rc, out.splitlines()[-1]))
    rc, out, _ = run(w, ["exit", "0", "a b", "--flag=x y", "--", "-z", ""])
    print("argv -> %s" % out.splitlines()[0].split("argv=")[1].split(" stdin_tty")[0])
    rc, line = pty_case(w)
    print("pty -> rc=%d %s" % (rc, line.split("\n")[0].split("argv=")[-1][-60:]))
    for name, sig, group in (("SIGINT to process group (Ctrl-C)", signal.SIGINT, True),
                             ("SIGINT to wrapper pid only", signal.SIGINT, False),
                             ("SIGTERM to wrapper pid only", signal.SIGTERM, False)):
        rc, to, out, left = sig_case(w, sig, group)
        print("%s -> wrapper rc=%s timed_out=%s child_got=[%s] orphan_child_processes=%d" % (name, rc, to, out, left))
