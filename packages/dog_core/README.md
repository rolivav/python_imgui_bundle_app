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

Building the wheel needs CMake, a C++17 compiler and pybind11 (installed
automatically in the build environment) — and nothing else: the HTTP client
invokes the `curl` command line tool at runtime instead of linking a library.
`curl` ships with Windows 10+ and with macOS; on Linux install it with your
package manager if it is missing. `nlohmann/json` is used if already installed,
otherwise it is fetched during the build.

```bash
uv build     # from this folder: writes dist/dog_core-0.1.0-...whl
```

## Installing

```bash
uv add dog-core                                  # from a package index
uv add dog-core --path ../dog_core --editable    # from a local folder
```
