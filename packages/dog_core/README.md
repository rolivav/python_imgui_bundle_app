# dog-core

The native (C++) **image procurement** core of the *Dog* panel, packaged as its
own distribution so the application depends on it like on any other library.

It performs, in C++:

1. the HTTP request to `https://dog.ceo/api/breeds/image/random`;
2. the JSON parsing that yields the URL of a random picture;
3. the HTTP download of that picture;
4. the breed name derived from the URL.

The GIL is released while the network I/O is in flight, so the panel can call it
from a worker thread without stalling the GUI. Decoding the returned bytes into
pixels is left to the caller (Pillow).

```python
from dog_core import fetch_random_dog

image = fetch_random_dog()   # DogImage(data=..., breed="Afghan Hound", url=...)
```

## Why it is a separate wheel

It is the piece that may be optimized heavily (or reimplemented in Rust) and
that should **not** be rebuilt when the application's Python code changes. It is
therefore a distribution of its own, consumed as a prebuilt wheel by default and
built locally only while developing it (see the repository README).

## Build requirements

Building the wheel needs [Bazel](https://bazel.build/) — install
[bazelisk](https://github.com/bazelbuild/bazelisk) and put it on `PATH`; it uses
the version pinned in `.bazelversion` — plus a C++17 compiler. Everything else
comes from the [Bazel Central Registry](https://registry.bazel.build/): nanobind
(the binding layer) and `nlohmann/json`. The extension is compiled against the
CPython 3.13 toolchain pinned in `MODULE.bazel`, so it only loads into Python
3.13 (the build hook rejects other versions); the repository keeps that
interpreter in `.python-version`.

The HTTP client invokes the `curl` command line tool at runtime instead of
linking a library: `curl` ships with Windows 10+ and with macOS; on Linux install
it with your package manager if it is missing.

```bash
uv build     # from this folder: writes dist/dog_core-0.1.0-...whl
```

`uv build` runs Bazel through a hatchling build hook (`hatch_build.py`), so the
wheel workflow is the same as for the pure-Python panels. Bazel's caches are the
reason for using it instead of CMake: rebuilding after editing one file only
recompiles that file. To compile without packaging:

```bash
bazel build //:_dog_core      # -> bazel-bin/_dog_core.pyd
```

On Windows that needs CPython's import library on the linker's search path, since
`pyconfig.h` asks MSVC for `python3xx.lib` by name:

```powershell
bazel build //:_dog_core --linkopt="/LIBPATH:<python>\libs"
```

(`uv build` adds that automatically, for the interpreter building the wheel.)

## Installing

```bash
uv add dog-core                                  # from a package index
uv add dog-core --path ../dog_core --editable    # from a local folder
```
