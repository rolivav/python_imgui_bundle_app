#!/usr/bin/env python3
"""Rebuild the packages you changed, then run the app.

`uv run zoo-app` always runs the published wheels. This wrapper rebuilds the
wheel of every package under `packages/` whose sources are newer than the wheel
built for it, installs every package that has a current local build into the
project environment, and then starts the command without syncing, so those
builds stay in place.

Nothing is uploaded and no index is involved: the wheels are written to `dist/`
and installed from there, and `uv.lock` is not modified. Only a package you
edited is rebuilt, so only a changed C++ core costs compile time; packages with
no local build keep their published wheel.

The environment is not synced on every run - dependencies are `uv sync`'s
business. If the environment has never been set up (or is missing the app), the
first run syncs it, keeping the locally built packages out of that sync so they
can be installed from `dist/`. Going back to the published wheels is
`uv run zoo-app`, which syncs. Pass --verbose to see uv's own output for the
install.

The script is plain Python so it runs on Windows, macOS and Linux alike. Run it
without touching the project environment with:

    uv run --no-project python tools/dev.py
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BUILD_DIR = REPO_ROOT / "dist"
PACKAGES_DIR = REPO_ROOT / "packages"
DEFAULT_COMMAND = "zoo-app"

# Directories that never hold sources: build outputs and caches. A package is
# stale when its newest source file is newer than the wheel built for it (or
# when it has never been built). That is the rule a build system uses, and
# unlike `git status` it does not care whether the work has been committed.
IGNORED_DIRS = re.compile(
    r"^(build|dist|target|bazel-.*|__pycache__|\.pytest_cache|\.mypy_cache)$"
)

EXAMPLES = """\
examples:
  uv run --no-project python tools/dev.py
  uv run --no-project python tools/dev.py --all
  uv run --no-project python tools/dev.py --none
  uv run --no-project python tools/dev.py --command python
"""


def uv() -> str:
    """Path to the uv executable, or a clear error if it is missing."""
    executable = shutil.which("uv")
    if executable is None:
        fail("uv was not found on PATH; install it from https://docs.astral.sh/uv/")
    return executable


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def run_uv(args, **kwargs):
    """Run `uv` from the repository root, so the `.venv` there is found."""
    return subprocess.run([uv(), *args], cwd=REPO_ROOT, **kwargs)


def all_packages():
    """Every distribution under `packages/`, sorted by folder name."""
    if not PACKAGES_DIR.is_dir():
        return []
    return sorted(
        entry.name
        for entry in PACKAGES_DIR.iterdir()
        if entry.is_dir() and (entry / "pyproject.toml").is_file()
    )


def iter_source_files(root: Path):
    """Source files under `root`, skipping build outputs and caches."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if not IGNORED_DIRS.match(name) and not name.endswith(".egg-info")
        ]
        for name in filenames:
            yield Path(dirpath) / name


def newest_source(root: Path):
    """The newest source file under `root`, as (path, mtime), or None."""
    newest = None
    for path in iter_source_files(root):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if newest is None or mtime > newest[1]:
            newest = (path, mtime)
    return newest


def local_wheel(folder: str):
    """The most recently built wheel for `folder` in `dist/`, or None."""
    if not BUILD_DIR.is_dir():
        return None
    wheels = [path for path in BUILD_DIR.glob(f"{folder}-*.whl") if path.is_file()]
    if not wheels:
        return None
    return max(wheels, key=lambda path: path.stat().st_mtime)


def stale_reason(folder: str):
    """Why `folder` must be rebuilt, or None when its local build is current."""
    wheel = local_wheel(folder)
    if wheel is None:
        return "nothing built for it yet"
    newest = newest_source(PACKAGES_DIR / folder)
    if newest is not None and newest[1] > wheel.stat().st_mtime:
        return f"sources newer than {os.path.join('dist', wheel.name)}"
    return None


def remove_built_artifacts(folder: str) -> None:
    """Drop old artifacts for `folder`: an installed wheel can still be held open."""
    if not BUILD_DIR.is_dir():
        return
    for path in BUILD_DIR.glob(f"{folder}-*"):
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                pass


def environment_ready() -> bool:
    """Whether the project environment exists and has the app installed.

    A venv is only usable once it has been synced; the app's entry point is used
    as the marker for that, since a successful sync installs it along with its
    dependencies.
    """
    venv = REPO_ROOT / ".venv"
    if not venv.is_dir():
        return False
    scripts = venv / ("Scripts" if os.name == "nt" else "bin")
    return any(
        (scripts / name).exists()
        for name in (DEFAULT_COMMAND, f"{DEFAULT_COMMAND}.exe")
    )


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="dev.py",
        description="Rebuild the packages you changed, then run the app.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--all", action="store_true", help="rebuild every package, changed or not"
    )
    parser.add_argument(
        "--none",
        action="store_true",
        help="rebuild nothing - just run what is installed",
    )
    parser.add_argument(
        "-c",
        "--command",
        default=DEFAULT_COMMAND,
        help=f"the command to run (default: {DEFAULT_COMMAND})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show uv's output for the install",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    folders = all_packages()

    rebuild = []
    for folder in folders:
        if args.all:
            rebuild.append((folder, "--all"))
            continue
        reason = stale_reason(folder)
        if reason:
            rebuild.append((folder, reason))

    local = []
    if args.none:
        print("dev: --none, leaving the environment as it is")
    else:
        for folder, reason in rebuild:
            print(f"dev: rebuilding {folder} - {reason}")
            remove_built_artifacts(folder)
            # --no-config keeps the project's local package index out of the
            # build: a package's build requirements (hatchling, maturin, ...)
            # come from PyPI, so building never needs the index to be up.
            result = run_uv(
                [
                    "build",
                    "--no-config",
                    "--wheel",
                    "--out-dir",
                    str(BUILD_DIR),
                    str(PACKAGES_DIR / folder),
                ]
            )
            if result.returncode != 0:
                fail(f"uv build failed for {folder}")
        if not rebuild:
            print("dev: nothing to rebuild")

        # Every package whose local build matches its sources runs from that
        # build. Installing is cheap, and since a rebuild keeps the version, uv
        # cannot tell a local build from the published one - so the local builds
        # are simply put back on every run instead of guessing what is installed.
        for folder in folders:
            wheel = local_wheel(folder)
            if wheel is None:
                continue
            newest = newest_source(PACKAGES_DIR / folder)
            if newest is None or newest[1] <= wheel.stat().st_mtime:
                local.append((folder, wheel))

        if not local:
            print("dev: no local builds - using the published wheels")
        else:
            print("dev: local builds: " + ", ".join(folder for folder, _ in local))

            if not environment_ready():
                # Install the app and its third-party dependencies, but keep the
                # locally built packages out of the sync: they are installed
                # from dist/ right below, so uv must not fetch them from the
                # index (whose published wheel hashes may not match uv.lock).
                sync_args = ["sync"]
                for folder, _ in local:
                    sync_args += ["--no-install-package", folder.replace("_", "-")]
                if run_uv(sync_args).returncode != 0:
                    fail("uv sync failed")

            result = run_uv(
                [
                    "pip",
                    "install",
                    "--no-deps",
                    "--reinstall",
                    *[str(path) for _, path in local],
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if result.returncode != 0:
                sys.stdout.write(result.stdout)
                fail("uv pip install failed")
            if args.verbose:
                sys.stdout.write(result.stdout)

    # --no-sync keeps whatever is installed in place. A plain `uv run zoo-app`
    # syncs the environment back to the published wheels.
    run_args = ["run"]
    if args.none or local:
        run_args.append("--no-sync")
    run_args.append(args.command)
    return run_uv(run_args).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
