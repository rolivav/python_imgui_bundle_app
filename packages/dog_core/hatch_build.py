"""Build hook that compiles the native extension with Bazel.

hatchling is the PEP 517 backend (so ``uv build``, ``uv publish`` and the rest of
the workflow keep working), but it knows nothing about C++. This hook shells out
to Bazel and drops the resulting extension module into the wheel.

Bazel is used rather than CMake because of its caches: a rebuild after editing one
``.cpp`` file only recompiles that file, even though a wheel build happens in a
fresh, temporary copy of the project.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class BazelBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version, build_data):
        root = Path(self.root).resolve()

        if self.target_name == "sdist":
            self._include_sources(root, build_data)
            return

        extension = self._build_extension(root)

        # A wheel with a compiled extension is not "none-any": tag it for the
        # interpreter and platform it was built against (cp313-cp313-win_amd64,
        # cp313-cp313-linux_x86_64, ...).
        interpreter = f"cp{sysconfig.get_config_var('py_version_nodot')}"
        platform = sysconfig.get_platform().replace("-", "_").replace(".", "_")
        build_data["infer_tag"] = False
        build_data["tag"] = f"{interpreter}-{interpreter}-{platform}"
        build_data.setdefault("force_include", {})[str(extension)] = (
            f"dog_core/{extension.name}"
        )

    @staticmethod
    def _include_sources(root: Path, build_data) -> None:
        """Pack everything Bazel needs into the source distribution.

        A consumer without a wheel for their Python version builds the extension
        from the sdist, so the C++ sources and the Bazel files have to be in it -
        hatchling's own selection does not know about them.
        """
        force_include = build_data.setdefault("force_include", {})
        patterns = [
            "cpp/**/*",
            "src/**/*",
            "BUILD.bazel",
            "MODULE.bazel",
            "MODULE.bazel.lock",
            ".bazelversion",
            "hatch_build.py",
        ]
        for pattern in patterns:
            for path in sorted(root.glob(pattern)):
                if path.is_file() and "__pycache__" not in path.parts:
                    force_include[str(path)] = str(path.relative_to(root))

    def _build_extension(self, root: Path) -> Path:
        bazel = _find_bazel()
        command = [bazel, "build", "//:_dog_core", *_bazel_flags()]
        try:
            subprocess.run(command, cwd=root, check=True)
            bazel_bin = subprocess.run(
                [bazel, "info", "bazel-bin"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip().splitlines()[-1]
        finally:
            # The wheel is built in a temporary directory that disappears right
            # after this, and Bazel's server would keep pointing at it.
            subprocess.run([bazel, "shutdown"], cwd=root, check=False)

        for candidate in Path(bazel_bin).glob("_dog_core.*"):
            if candidate.suffix in {".pyd", ".so"}:
                return candidate
        raise RuntimeError(f"Bazel produced no extension module in {bazel_bin}")


def _find_bazel() -> str:
    """Locate bazelisk (or bazel) even when it is not on PATH."""
    for name in ("bazelisk", "bazel"):
        found = shutil.which(name)
        if found:
            return found

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        link = Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "bazelisk.exe"
        if link.is_file():
            return str(link)
        for candidate in (
            Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        ).glob("Bazel.Bazelisk*/bazelisk.exe"):
            return str(candidate)

    raise RuntimeError(
        "Neither bazel nor bazelisk is on PATH. Install bazelisk (which manages "
        "the Bazel version in .bazelversion) and try again."
    )


def _bazel_flags() -> list[str]:
    """Flags that make a build in a throwaway directory cheap.

    The disk cache is keyed on the actions themselves, so a fresh workspace still
    gets the compiled objects from a previous build.
    """
    cache_root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "dog-core-bazel"
    flags = [f"--disk_cache={cache_root / 'disk'}"]
    flags.extend(_python_link_flags())
    return flags


def _python_link_flags() -> list[str]:
    """Point the linker at CPython's import library on Windows.

    CPython's ``pyconfig.h`` asks MSVC for ``python3xx.lib`` through
    ``#pragma comment(lib, ...)``, and that file is not part of the headers, so
    the linker needs the directory holding it.
    """
    if sys.platform != "win32":
        return []

    libs = Path(sys.base_prefix) / "libs"
    name = f"python{sysconfig.get_config_var('py_version_nodot')}.lib"
    if (libs / name).is_file():
        # Quoted: the path may contain spaces (e.g. "C:\Program Files\Python313").
        return [f'--linkopt=/LIBPATH:"{libs}"']
    return []
