# bird-core

The native (Rust) core of the "Bird" panel: it asks the
[Ornithophile API](https://github.com/tustoz/ornithophile) for a bird and
downloads its picture. The Python side only decodes the returned bytes into
pixels (Pillow) and uploads them to the GPU.

It is the piece that may be optimized heavily (or swapped for another
implementation) and that should **not** be rebuilt when the application's Python
code changes. It is therefore a distribution of its own, consumed as a prebuilt
wheel by default and built locally only while developing it (see the repository
README).

## Data source and licence

The data comes from [Ornithophile](https://github.com/tustoz/ornithophile), a free
API that needs no key and no sign-up. It has no "random" endpoint, so the core
fetches the species list of a random letter (`/api/birds/alpha/<letter>`, about a
megabyte for ~500 birds), keeps it in memory for the lifetime of the process, and
picks a bird from it. The pictures are Wikimedia thumbnails: the protocol-relative
URLs the API returns are completed to `https:`, and the 250 px thumbnails are
rewritten to 1000 px ones, since the URL encodes the size. Wikimedia answers 400
when that width is larger than the original file (common for the smaller species
photos), so the 250 px URL the API gave is then used as it is; the file itself is
never downloaded, some of them are scans of tens of megabytes.

**Licence:** Ornithophile is under the *Academic Non-Commercial License* — free
for academic, research and educational use only, with credit to *Maxi Aditya
Kusuma Winarjo*, and no commercial use without prior written permission. The
pictures come from Wikimedia Commons and carry their own licences.

## Build requirements

Building the wheel needs a [Rust](https://rustup.rs/) toolchain (`cargo`);
`maturin`, the build backend, is installed automatically in the build
environment. The HTTP client invokes the `curl` command line tool at runtime
instead of linking an HTTP/TLS library, so `curl` has to be on `PATH` — it ships
with Windows 10+ and with macOS; on Linux install it with your package manager if
it is missing.

```bash
uv build     # from this folder: writes dist/bird_core-0.1.0-...whl
```

The extension is built against the stable ABI (`abi3-py310`), so a single wheel
works on every Python ≥ 3.10 rather than one wheel per interpreter version.

## Installing

```bash
uv add bird-core                                  # from a package index
uv add bird-core --path ../bird_core --editable   # from a local folder
```
