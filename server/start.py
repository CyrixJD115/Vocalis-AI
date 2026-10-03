#!/usr/bin/env python
"""
Voice changer launcher.

Creates a virtual environment (.venv), installs the dependencies for the
selected backend (preferring uv when available), and starts the server.

Examples:
    python start.py                          # auto-detect backend, defaults
    python start.py --backend cuda           # force a backend
    python start.py --host 0.0.0.0 --https   # expose to the local network
    python start.py --reinstall              # rebuild .venv from scratch
    python start.py -- --log-level info      # flags after -- go to main.py

Backends: cuda | dml (Windows) | rocm (Linux) | cpu. When --backend is not
given, the launcher picks one: macOS -> cpu, Nvidia GPU present -> cuda,
otherwise Windows -> dml, Linux -> cpu (pass --backend rocm for AMD GPUs).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
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
    return os.path.join(VENV_DIR, "Scripts", "python.exe" if os.name == "nt" else "python")


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
        run([uv, "venv", VENV_DIR, "--python", base_python])
    else:
        log("uv not found, falling back to pip. Tip: install uv for a much faster setup (https://docs.astral.sh/uv/)")
        log(f"Creating virtual environment ({VENV_DIR})")
        run([base_python, "-m", "venv", VENV_DIR])


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


def run(cmd: list[str], **kwargs) -> None:
    log(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=SERVER_DIR, check=True, **kwargs)


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
    args, forwarded = parser.parse_known_args()

    backend = args.backend
    if backend == "auto":
        backend = detect_backend()
        log(f"Auto-detected backend: {backend} (override with --backend)")

    under_uv = bool(os.environ.get("UV"))

    base_python = args.python or sys.executable
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

    cmd = [venv_python(), "main.py",
           "--https", "true" if https else "false",
           "--browser", "true" if args.browser else "false"] + forwarded
    log(f"Starting server on {host}:{env.get('PORT', '18888')} ({'https' if https else 'http'})")
    try:
        proc = subprocess.run(cmd, cwd=SERVER_DIR, env=env)
        return proc.returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
