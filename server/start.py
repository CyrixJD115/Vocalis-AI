#!/usr/bin/env python
"""
Voice changer launcher.

Creates a virtual environment (.venv), installs the dependencies for the
selected backend (preferring uv when available), and starts the server.

Examples:
    python start.py                          # auto-detect backend, defaults
    python start.py --backend cuda           # force a backend
    python start.py --host 0.0.0.0 --https   # expose to the local network
    python start.py --dev-ui                 # backend + Svelte/Vite dev server (all-in-one)
    python start.py --reinstall              # rebuild .venv from scratch
    python start.py -- --log-level info      # flags after -- go to main.py

Backends: cuda | dml (Windows) | rocm (Linux) | cpu. When --backend is not
given, the launcher picks one: macOS -> cpu, Nvidia GPU present -> cuda,
otherwise Windows -> dml, Linux -> cpu (pass --backend rocm for AMD GPUs).
"""
import argparse
import os
import queue
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SERVER_DIR)
UI_DIR = os.path.join(REPO_ROOT, "client", "demo")
LIB_DIR = os.path.join(REPO_ROOT, "client", "lib")
VENV_DIR = os.path.join(SERVER_DIR, ".venv")
# Backends whose dependency wheels are published for Python 3.10 only.
PY310_ONLY = {"rocm"}

BACKEND_REQUIREMENTS = {
    "cuda": ["requirements-cuda.txt"],
    "dml": ["requirements-dml.txt"],
    "rocm": ["requirements-rocm.txt"],
    "cpu": ["requirements-cpu.txt"],
}
COMMON_REQUIREMENTS = ["requirements-common.txt"]


def log(msg: str) -> None:
    print(f"[start] {msg}", flush=True)


def venv_python() -> str:
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def find_uv() -> str | None:
    return shutil.which("uv")


def detect_backend() -> str:
    if sys.platform == "darwin":
        return "cpu"
    if shutil.which("nvidia-smi") or shutil.which("nvidia-smi.exe"):
        return "cuda"
    if sys.platform == "win32":
        return "dml"
    # AMD ROCm heuristics on Linux
    if os.path.exists("/dev/kfd") or shutil.which("rocm-smi") or os.path.isdir("/opt/rocm"):
        return "rocm"
    return "cpu"


def pinned_torch(backend: str) -> str | None:
    """The exact torch build (including the +cu128/+cpu local version) pinned
    in the backend's requirements file, if any."""
    for req in BACKEND_REQUIREMENTS[backend]:
        path = os.path.join(SERVER_DIR, req)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*torch==([^\s;]+)", line)
                if m:
                    return m.group(1)
    return None


def deps_ok(backend: str) -> bool:
    """Check that the venv has the dependencies for THIS backend installed
    (a venv built for another backend, e.g. CPU-only or wrong-CUDA torch,
    must not pass)."""
    build_probe = {
        "cuda": "import torch; assert torch.version.cuda is not None, 'CPU-only torch build'",
        "rocm": "import torch; assert torch.version.hip is not None, 'non-ROCm torch build'",
        "dml": "import torch, torch_directml",
        "cpu": "import torch",
    }[backend]
    checks = [f"import numpy, fastapi, onnxruntime; {build_probe}"]
    pin = pinned_torch(backend)
    if pin:
        # Verify the exact pinned build is installed (e.g. 2.9.1+cu128), so a
        # torch from a different backend or CUDA generation is replaced.
        checks.append(
            f"from importlib.metadata import version; assert version('torch') == {pin!r}, "
            f"version('torch')"
        )
    if backend == "cuda" and sys.platform == "linux":
        # Without the cudnn upgrade, onnxruntime fails on the HuBERT position
        # convolution with HEURISTIC_QUERY_FAILED (see CUDNN_UPGRADE).
        checks.append(
            "assert tuple(int(x) for x in version('nvidia-cudnn-cu12').split('.')[:2]) >= (9, 27), "
            "version('nvidia-cudnn-cu12')"
        )
    probe = "; ".join(checks)
    try:
        check = subprocess.run(
            [venv_python(), "-c", probe],
            cwd=SERVER_DIR,
            capture_output=True,
            timeout=120,
        )
        return check.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def ensure_venv(uv: str | None, base_python: str) -> None:
    if os.path.exists(venv_python()):
        return
    if uv:
        log(f"Creating virtual environment with uv ({VENV_DIR})")
        # --clear replaces a broken or half-built venv without the interactive
        # "Do you want to replace it?" prompt, which hangs non-attended runs.
        run([uv, "venv", VENV_DIR, "--python", base_python, "--clear"])
    else:
        log("uv not found, falling back to pip. Tip: install uv for a much faster setup (https://docs.astral.sh/uv/)")
        log(f"Creating virtual environment ({VENV_DIR})")
        run([base_python, "-m", "venv", VENV_DIR])


# onnxruntime's CUDA provider plans convolutions through the cuDNN frontend,
# whose heuristic has no fp16 engine for HuBERT's grouped position convolution
# at realtime chunk sizes on cuDNN <= 9.10 (HEURISTIC_QUERY_FAILED); >= 9.27
# covers it. torch 2.9.1+cu128 pins nvidia-cudnn-cu12==9.10.2.21 exactly, so
# this cannot go into requirements-cuda.txt; it is installed as a separate
# step right after the requirements.
CUDNN_UPGRADE = "nvidia-cudnn-cu12~=9.27.0"


def install_backend(backend: str, uv: str | None) -> None:
    # The requirements files are the single source of truth: they carry the
    # per-backend PyTorch index URLs and AMD's direct wheel link, which the
    # pyproject lockfile cannot express.
    reqs = COMMON_REQUIREMENTS + BACKEND_REQUIREMENTS[backend]
    if uv:
        run([uv, "pip", "install", "--python", venv_python()] + [x for r in reqs for x in ("-r", r)])
    else:
        run([venv_python(), "-m", "pip", "install", "--upgrade", "pip"])
        run([venv_python(), "-m", "pip", "install"] + [x for r in reqs for x in ("-r", r)])
    if backend == "cuda" and sys.platform == "linux":
        # A standalone resolution: the requirements install above would reject
        # it because of torch's exact cudnn pin.
        if uv:
            run([uv, "pip", "install", "--python", venv_python(), CUDNN_UPGRADE])
        else:
            run([venv_python(), "-m", "pip", "install", CUDNN_UPGRADE])


def run(cmd: list[str], cwd: str | None = None, **kwargs) -> None:
    log(f"$ {' '.join(cmd)}" + (f"  (in {cwd})" if cwd else ""))
    if os.name == "nt":
        # npm is a .cmd batch file on Windows; CreateProcess cannot launch it
        # directly, so go through the shell with properly quoted arguments.
        subprocess.run(subprocess.list2cmdline(cmd), cwd=cwd or SERVER_DIR, check=True, shell=True, **kwargs)
    else:
        subprocess.run(cmd, cwd=cwd or SERVER_DIR, check=True, **kwargs)


# ///////////////////////////////////////////////////////////
# Web UI (client/demo, Svelte + Vite)
# ///////////////////////////////////////////////////////////

def ui_dist_index() -> str:
    return os.path.join(UI_DIR, "dist", "index.html")


def ensure_ui_deps(npm: str, directory: str) -> None:
    if not os.path.isdir(os.path.join(directory, "node_modules")):
        log(f"Installing web UI dependencies ({os.path.relpath(directory, REPO_ROOT)})")
        run([npm, "install"], cwd=directory)


def build_ui(npm: str) -> None:
    """Install UI dependencies (client/lib needs its own for module resolution)
    and produce the production build served by the backend."""
    ensure_ui_deps(npm, LIB_DIR)
    ensure_ui_deps(npm, UI_DIR)
    log("Building the web UI")
    run([npm, "run", "build"], cwd=UI_DIR)


def spawn_proc(cmd: list[str], cwd: str, env: dict) -> subprocess.Popen:
    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        # Own process group so the cleanup can kill the whole npm -> vite tree.
        kwargs["start_new_session"] = True
    if os.name == "nt":
        return subprocess.Popen(subprocess.list2cmdline(cmd), cwd=cwd, env=env, shell=True, **kwargs)
    return subprocess.Popen(cmd, cwd=cwd, env=env, **kwargs)


def terminate_tree(proc: subprocess.Popen | None, group: bool = True) -> None:
    if proc is None or proc.poll() is not None:
        return
    # Mask our SIGTERM-to-KeyboardInterrupt bridge while killing: terminating a
    # process group that includes ourselves (the backend inherits our group)
    # would otherwise interrupt the cleanup with a second exception.
    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGTERM, signal.SIG_IGN)
    except (ValueError, OSError):
        pass
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)
        elif group:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
    except (OSError, ProcessLookupError):
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    finally:
        if old_handler is not None:
            try:
                signal.signal(signal.SIGTERM, old_handler)
            except (ValueError, OSError):
                pass


def start_vite_dev_server(ui_port: int, backend_url: str, expose: bool) -> tuple[subprocess.Popen, "queue.Queue[str | None]"]:
    """Start the Svelte/Vite dev server. Returns (process, queue). The queue
    yields the printed "Local:" URL once the server is up, or None on exit."""
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    env = os.environ.copy()
    env["VC_SERVER_URL"] = backend_url
    cmd = [npm, "run", "dev", "--", "--port", str(ui_port)]
    if expose:
        cmd += ["--host"]
    log(f"$ {' '.join(cmd)}  (in {UI_DIR}, proxying to {backend_url})")
    proc = spawn_proc(cmd, UI_DIR, env)
    urls: "queue.Queue[str | None]" = queue.Queue()

    def reader() -> None:
        url_re = re.compile(r"Local:\s+(\S+)")
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                line = line.rstrip()
                print(f"[ui] {line}", flush=True)
                m = url_re.search(line)
                if m:
                    urls.put(m.group(1))
        finally:
            urls.put(None)

    threading.Thread(target=reader, daemon=True).start()
    return proc, urls


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set up the environment and start the voice changer server.",
        epilog="Any arguments after -- are forwarded to main.py (e.g. -- --log-level info).",
    )
    parser.add_argument("--backend", choices=["auto", "cuda", "dml", "rocm", "cpu"], default="auto",
                        help="compute backend to install (default: auto-detect)")
    parser.add_argument("--host", default=None, help="bind address (default: 127.0.0.1; set 0.0.0.0 to expose)")
    parser.add_argument("--port", type=int, default=None, help="port (default: 18888)")
    parser.add_argument("--https", dest="https", action="store_true", default=None,
                        help="serve over self-signed HTTPS (auto-enabled when host is not localhost)")
    parser.add_argument("--no-https", dest="https", action="store_false",
                        help="force plain HTTP even for non-localhost hosts")
    parser.add_argument("--browser", dest="browser", action="store_true", default=True,
                        help="open the UI in the default browser (default)")
    parser.add_argument("--no-browser", dest="browser", action="store_false",
                        help="do not open the browser")
    parser.add_argument("--skip-deps", action="store_true",
                        help="do not create/check the virtual environment")
    parser.add_argument("--reinstall", action="store_true",
                        help="delete .venv and reinstall dependencies")
    parser.add_argument("--no-start", action="store_true",
                        help="set up the environment only, do not start the server")
    parser.add_argument("--python", default=None,
                        help="base Python interpreter for the virtual environment (default: this Python)")
    parser.add_argument("--dev-ui", action="store_true",
                        help="start the Svelte/Vite dev server (hot reload) alongside the backend "
                             "and open the browser at the dev server; requires Node.js")
    parser.add_argument("--ui-port", type=int, default=5173,
                        help="port for the --dev-ui Vite server (default: 5173)")
    parser.add_argument("--build-ui", action="store_true",
                        help="build the web UI into client/demo/dist before starting (also done "
                             "automatically when dist is missing and Node.js is available)")
    args, forwarded = parser.parse_known_args()

    backend = args.backend
    if backend == "auto":
        backend = detect_backend()
        log(f"Auto-detected backend: {backend} (override with --backend)")

    under_uv = bool(os.environ.get("UV"))

    base_python = args.python or sys.executable
    if args.python is None and os.path.abspath(sys.executable).startswith(os.path.abspath(VENV_DIR) + os.sep):
        # 'uv run' executes us with the project venv's own interpreter, which
        # cannot seed a replacement of the very venv it lives in.
        base_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    uv = find_uv()
    if backend in PY310_ONLY:
        version = sys.version_info[:2]
        # onnxruntime-rocm / faiss-gpu wheels are cp310 only
        if uv:
            base_python = "3.10"  # uv downloads CPython 3.10 automatically
            log(f"{backend} backend requires Python 3.10 wheels; uv will fetch 3.10 if needed")
        elif version != (3, 10):
            log(f"WARNING: {backend} backend needs Python 3.10 (onnxruntime-rocm/faiss-gpu wheels), "
                f"but you are running {version[0]}.{version[1]}. Install uv or use Python 3.10.")

    if args.reinstall and os.path.isdir(VENV_DIR):
        log(f"Removing {VENV_DIR}")
        shutil.rmtree(VENV_DIR)

    if not args.skip_deps:
        if os.path.isdir(VENV_DIR) and deps_ok(backend):
            log(f"Virtual environment is up to date for the {backend} backend, skipping dependency installation (--reinstall to force)")
        else:
            if under_uv:
                log("Note: 'uv run' re-synced the environment to the base dependencies; reinstalling"
                    " the backend packages (use 'uv run --no-sync' to avoid this).")
            ensure_venv(uv, base_python)
            install_backend(backend, uv)
            if not deps_ok(backend):
                log(f"Dependency check for the {backend} backend failed after installation; see the output above")
                return 1

    if args.no_start:
        log("Environment is ready (--no-start was given)")
        return 0

    node = shutil.which("node")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    dev_ui = args.dev_ui
    if dev_ui:
        if not (node and npm):
            log("ERROR: --dev-ui requires Node.js (https://nodejs.org, LTS recommended). "
                "Install it, or drop the flag to serve the pre-built UI from client/demo/dist.")
            return 1
        ensure_ui_deps(npm, LIB_DIR)
        ensure_ui_deps(npm, UI_DIR)

    if args.build_ui:
        if not (node and npm):
            log("ERROR: --build-ui requires Node.js (https://nodejs.org).")
            return 1
        build_ui(npm)
    elif not dev_ui and not os.path.isfile(ui_dist_index()):
        # First run on a fresh checkout without a committed build.
        if node and npm:
            log("client/demo/dist is missing; building the web UI once (use --dev-ui to develop instead)")
            build_ui(npm)
        else:
            log("WARNING: client/demo/dist is missing and Node.js is not installed, "
                "so the web UI will be unavailable. Install Node.js, or run with --dev-ui.")

    env = os.environ.copy()
    if args.host is not None:
        env["HOST"] = args.host
    if args.port is not None:
        env["PORT"] = str(args.port)

    host = args.host or "127.0.0.1"
    https = args.https
    if https is None:
        # Browsers only grant microphone access to secure contexts, so
        # automatically use self-signed HTTPS when exposing the server.
        https = host not in ("127.0.0.1", "localhost", "::1")
    backend_port = args.port if args.port is not None else int(os.environ.get("PORT", "18888"))

    cmd = [venv_python(), "main.py",
           "--https", "true" if https else "false",
           "--browser", "false" if dev_ui else ("true" if args.browser else "false")] + forwarded

    vite_proc: subprocess.Popen | None = None
    vite_url: str | None = None
    if dev_ui:
        target = f"{'https' if https else 'http'}://127.0.0.1:{backend_port}"
        vite_proc, vite_urls = start_vite_dev_server(args.ui_port, target, expose=https)
        log("Waiting for the web UI dev server...")
        try:
            vite_url = vite_urls.get(timeout=90)
        except queue.Empty:
            vite_url = None
        if not vite_url:
            log("ERROR: the web UI dev server did not start; see the [ui] output above")
            terminate_tree(vite_proc)
            return 1
        log(f"Web UI dev server ready at {vite_url}")

    log(f"Starting server on {host}:{backend_port} ({'https' if https else 'http'})")

    # SIGTERM (e.g. `kill`, process managers) should trigger the same graceful
    # cleanup as Ctrl+C.
    def _sigterm_to_keyboardinterrupt(signum, frame):
        raise KeyboardInterrupt

    if dev_ui:
        try:
            signal.signal(signal.SIGTERM, _sigterm_to_keyboardinterrupt)
        except (ValueError, OSError):
            pass

    proc: subprocess.Popen | None = None
    try:
        proc = subprocess.Popen(cmd, cwd=SERVER_DIR, env=env)
        if dev_ui and vite_url:
            # Wait for the backend port (or its death) before opening the UI.
            deadline = time.time() + 180
            backend_up = False
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                try:
                    with socket.create_connection(("127.0.0.1", backend_port), timeout=1):
                        backend_up = True
                        break
                except OSError:
                    time.sleep(0.5)
            if backend_up:
                if args.browser:
                    webbrowser.open(vite_url)
                log(f"All-in-one mode: UI at {vite_url} (API proxied to {target})")
            else:
                log("WARNING: the backend did not open its port in time; the UI will show a connection error until it is up")
        while True:
            ret = proc.poll()
            if ret is not None:
                return ret
            if vite_proc is not None and vite_proc.poll() is not None:
                log("WARNING: the web UI dev server exited; the backend keeps running")
                vite_proc = None
            time.sleep(0.5)
    except KeyboardInterrupt:
        log("Shutting down")
        return 0
    finally:
        terminate_tree(vite_proc)
        if proc is not None and proc.poll() is None:
            # The backend shares our process group, so kill it by PID to avoid
            # signaling ourselves.
            terminate_tree(proc, group=False)


if __name__ == "__main__":
    sys.exit(main())
