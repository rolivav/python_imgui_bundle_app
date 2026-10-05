#!/usr/bin/env python3
"""Serve `tools/local_index/packages` as a throwaway PEP 503 package index.

Starts pypiserver - run through `uvx`, so nothing is installed globally - on
http://127.0.0.1:8080. The simple index lives at /simple.

The server is deliberately permissive for local testing:

  -i 127.0.0.1   bound to the local machine only
  -a . -P .      no authentication (uploads accepted anonymously)
  -o             allow overwriting an existing version on upload

Press Ctrl+C to stop it.

The script is plain Python so it runs on Windows, macOS and Linux alike. Run it
without touching the project environment with:

    uv run --no-project python tools/local_index/serve.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SERVED_DIR = SCRIPT_DIR / "packages"
HOST = "127.0.0.1"
PORT = 8080


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def uvx():
    """The command that runs a tool ephemerally: `uvx`, or `uv tool run`."""
    executable = shutil.which("uvx")
    if executable is not None:
        return [executable]
    uv_executable = shutil.which("uv")
    if uv_executable is not None:
        return [uv_executable, "tool", "run"]
    fail("uv was not found on PATH; install it from https://docs.astral.sh/uv/")


def main() -> int:
    SERVED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Serving            {SERVED_DIR}")
    print(f"  simple index:    http://{HOST}:{PORT}/simple")
    print(f"  upload endpoint: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")

    command = [
        *uvx(),
        "--from",
        "pypiserver",
        "pypi-server",
        "run",
        "-p",
        str(PORT),
        "-i",
        HOST,
        "-a",
        ".",
        "-P",
        ".",
        "-o",
        str(SERVED_DIR),
    ]
    return subprocess.run(command).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
