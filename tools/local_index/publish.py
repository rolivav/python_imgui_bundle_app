#!/usr/bin/env python3
"""Build the distributions under `packages/` into the local index's package folder.

Runs `uv build` for each distribution into `dist/` and copies the artifacts
(wheel and sdist) into `tools/local_index/packages/`, the directory served by
serve.py. That is enough to "publish": pypiserver picks the new files up on the
next request. A rebuilt artifact replaces the previous one of the same version
(serve.py runs the server with `-o`, which allows overwriting).

Because the wheels land in `dist/`, publishing also counts as a local build for
`tools/dev.py`: publish, then edit nothing, and there is nothing to rebuild.

Both a wheel and a source distribution are built. The sdist matters for
`dog-core`: its wheel only matches one Python version, so uv needs the sdist to
be able to resolve the project for the other Python versions allowed by
`requires-python`. Installing on the matching interpreter still uses the wheel -
nothing is compiled for it.

The script is plain Python so it runs on Windows, macOS and Linux alike. Run it
without touching the project environment with:

    uv run --no-project python tools/local_index/publish.py
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
BUILD_DIR = REPO_ROOT / "dist"
PACKAGES_SOURCE = REPO_ROOT / "packages"
SERVED_DIR = SCRIPT_DIR / "packages"

EXAMPLES = """\
examples:
  uv run --no-project python tools/local_index/publish.py
  uv run --no-project python tools/local_index/publish.py cat_panel
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
    if not PACKAGES_SOURCE.is_dir():
        return []
    return sorted(
        entry.name
        for entry in PACKAGES_SOURCE.iterdir()
        if entry.is_dir() and (entry / "pyproject.toml").is_file()
    )


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


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="publish.py",
        description=(
            "Build the distributions under `packages/` into the local index's "
            "package folder."
        ),
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "packages",
        nargs="*",
        metavar="PACKAGE",
        help="distribution folders to build (default: all of them)",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    SERVED_DIR.mkdir(parents=True, exist_ok=True)

    projects = args.packages or all_packages()
    for project in projects:
        source = PACKAGES_SOURCE / project
        if not source.is_dir():
            fail(f"No such package folder: {source}")
        print(f"Building {project}")
        # A wheel that was installed from here can briefly be held open by the
        # OS, which would make the build fail while writing it.
        remove_built_artifacts(project)
        # --no-config keeps the project's local package index out of the build: a
        # package's build requirements (hatchling, maturin, ...) come from PyPI,
        # so building never needs the index to be up.
        if (
            run_uv(
                ["build", "--no-config", "--out-dir", str(BUILD_DIR), str(source)]
            ).returncode
            != 0
        ):
            fail(f"uv build failed for {project}")

        artifacts = (
            [path for path in BUILD_DIR.glob(f"{project}-*") if path.is_file()]
            if BUILD_DIR.is_dir()
            else []
        )
        if not artifacts:
            fail(f"uv build produced no artifacts for {project}")
        # Mirror the build directory: drop this project's previous artifacts
        # first, so rebuilding under a different Python tag does not leave a
        # stale wheel (say an old cp314 next to the new cp313) on the index.
        for stale in SERVED_DIR.glob(f"{project}-*"):
            if stale.is_file():
                stale.unlink()
        for artifact in artifacts:
            shutil.copy2(artifact, SERVED_DIR)

    print()
    print(f"Published from {BUILD_DIR} into {SERVED_DIR}:")
    for artifact in sorted(SERVED_DIR.iterdir()):
        if artifact.is_file() and artifact.name.endswith((".whl", ".tar.gz")):
            print(f"  {artifact.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
