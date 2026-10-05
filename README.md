# Zoo App

A small [Dear ImGui Bundle](https://imgui-bundle.pages.dev/) application whose
frontend is ImGui. It ships with three panels:

- **Cat**, which displays a random animated cat GIF fetched from
  [cataas.com](https://cataas.com/);
- **Dog**, which displays a random dog picture fetched from
  [dog.ceo](https://dog.ceo/dog-api/);
- **Bird**, which displays a random bird picture fetched from
  [Ornithophile](https://github.com/tustoz/ornithophile) — no API key, but note
  its academic licence (see "Requirements").

When a panel is first shown it fetches a random picture; its **Get Cat** /
**Get Dog** / **Get Bird** button fetches a new one.

Panels are dockable windows inside a full screen dock space, so the panel fills
the whole window on its own, and upcoming panels will share that space (tabs,
splits, freely rearranged by the user).

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs the pinned Python — 3.13, see
  `.python-version` — automatically if needed)

Building the native core (`dog-core`) needs a C++17 compiler and
[Bazel](https://bazel.build/) (easiest through
[bazelisk](https://github.com/bazelbuild/bazelisk), which follows the pinned
`.bazelversion`); nanobind and `nlohmann/json` come from the Bazel Central
Registry. The extension is compiled against the CPython 3.13 toolchain pinned in
`packages/dog_core/MODULE.bazel`; loading it into another minor version of Python
crashes, so the repository pins 3.13 in `.python-version` and the build hook
rejects any other interpreter. The HTTP client shells out to the `curl` command
line tool, so no HTTP library has to be linked or installed on Windows (curl
ships with Windows 10+) or macOS; on Linux, install `curl` if it is missing.
Consuming the prebuilt wheels instead (see "Testing the wheel workflow with a
local index") needs none of that.

Its sibling `bird-core` is written in Rust and built with
[maturin](https://www.maturin.rs/), so it needs a [Rust](https://rustup.rs/)
toolchain; it reads its bird data from the free
[Ornithophile](https://github.com/tustoz/ornithophile) API, which needs no key.
Note its licence: free for academic, research and educational use only, with
credit to *Maxi Aditya Kusuma Winarjo*, and no commercial use without permission.

## Run

```bash
uv run zoo-app
```

`uv` creates the virtual environment, installs the dependencies and runs the
app in one step. The panels and the native core are resolved as described under
"Panels and the native core are separate distributions" below. Equivalent
invocations:

```bash
uv run python -m zoo_app
uv sync && uv run zoo-app
```

## Project layout

Two .python-version                   # pins CPython 3.13 (the native core's ABI)
├── kinds of projects: the application, and the distributions it consumes — the
panels and the native cores, each one its own project (see below).

```
.
├── pyproject.toml                    # the app: depends on the panels + the native core
├── tools/                            # ./tools/dev.py and the local test index
├── src/zoo_app/
│   ├── app.py                        # window + main loop, draws every registered panel
│   └── panels/
│       └── __init__.py               # panel contract + registry (add new panels here)
└── packages/
    ├── cat_panel/                    # the "Cat" panel, as its own project
    │   ├── pyproject.toml            # distribution `cat-panel`
    │   └── src/cat_panel/
    │       ├── __init__.py           # public API of the panel
    │       ├── cat_gif.py            # model
    │       └── cat_panel.py          # logic + UI
    ├── dog_panel/                    # the "Dog" panel, as its own project
    │   ├── pyproject.toml            # distribution `dog-panel`
    │   └── src/dog_panel/
    │       ├── __init__.py           # public API of the panel
    │       ├── dog.py                # model (decode + call the native core)
    │       └── dog_panel.py          # logic + UI
    ├── dog_core/                     # the native (C++) image-procurement core
        ├── pyproject.toml            # distribution `dog-core` (hatchling + Bazel hook)
        ├── BUILD.bazel               # one C++ library + the Python extension
        ├── MODULE.bazel              # Bazel deps (nanobind, nlohmann/json)
        ├── hatch_build.py            # compiles the extension with Bazel
        ├── cpp/dog_core.cpp          # HTTP + JSON in C++
        └── src/dog_core/__init__.py  # Python wrapper
    ├── bird_panel/                   # the "Bird" panel, as its own project
    │   ├── pyproject.toml            # distribution `bird-panel`
    │   └── src/bird_panel/
    │       ├── __init__.py           # public API of the panel
    │       ├── bird.py               # model (decode + call the native core)
    │       └── bird_panel.py         # logic + UI
    └── bird_core/                    # the native (Rust) image-procurement core
        ├── pyproject.toml            # distribution `bird-core` (maturin)
        ├── Cargo.toml                # the Rust crate (PyO3, stable ABI)
        ├── src/lib.rs                # HTTP + JSON in Rust
        └── src/bird_core/__init__.py # Python wrapper (resolves the API key)
```

### Panels are self-contained

Every panel owns its model, its logic and its UI, and is packaged as its own
distribution — the app depends on it like on any other library:

| Part  | File           | Contents                                                                                      |
|-------|----------------|-----------------------------------------------------------------------------------------------|
| model | `cat_gif.py`   | `CatGif` — the animation decoded into RGBA frames, plus `decode_gif()` / `fetch_random_cat_gif()` |
| logic | `cat_panel.py` | `CatPanel` — downloads in a background thread, uploads the frames to the GPU, advances the current frame on a timer |
| ui    | `cat_panel.py` | `CatPanel.draw()` — the panel content: the **Get Cat** button and the picture                     |

A panel exposes just `label` (the title of its dockable window) and `draw()`
(its content). Panels never open an ImGui window themselves: `app.py` wraps each
one in a `hello_imgui.DockableWindow`, and hello_imgui calls
`imgui.begin()`/`imgui.end()` around it. That is what makes them dockable.

### Panels and the native core are separate distributions

`cat-panel`, `dog-panel`, `bird-panel`, `dog-core` and `bird-core` (the native
cores that procure the pictures) are declared in the app's dependencies and
resolve like any other dependency — as wheels from the package index — so
`uv run zoo-app` downloads them and compiles nothing.

There is deliberately no "install the workspace folder instead" source for them:
uv needs a single source per package version, and because these packages are also
plain dependencies, a `[tool.uv.sources]` path source — even one gated behind an
`extra` — also wins for the default install, which would compile the C++ core on
every machine. Working on a package therefore means rebuilding its wheel, which
`tools/dev.py` does for the packages you changed (see below).

To build and upload a wheel yourself:

```bash
uv build --out-dir dist packages/dog_core   # wheel + sdist
uv publish --index internal dist/*          # upload it to the package index
```
CPython 3.13,
the version the Bazel toolchain compiles against (see
`packages/dog_core/MODULE.bazel`), so uv needs the sdist to resolve the project
on other interpreters. The native core can only be built for 3.13 — the build
hook fails on any other version instead of emitting an ABI-incompatible
extension — and `.python-version` keeps the project on italling on the matching interpreter still uses
the wheel, so nothing is compiled).

To add another panel, copy `packages/dog_panel/` (it needs `imgui_bundle`,
`numpy` and `Pillow`, plus the native core if its work is heavy), give the new
class a unique `label`, add the distribution to the app's dependencies, and
register the class in `src/zoo_app/panels/__init__.py` (`PANEL_TYPES`).

### Developing a wheel locally

Nothing is compiled by `uv run zoo-app`. When you edit a package under
`packages/`, rebuild its wheel and let uv pick it up:

```bash
uv run --no-project python tools/dev.py                    # rebuild the packages whose sources changed
uv run --no-project python tools/dev.py --all              # rebuild all of them
uv run --no-project python tools/dev.py --none             # rebuild nothing, just run
uv run --no-project python tools/dev.py --command python   # same, for another uv-run command
```

`dev.py` builds the wheel of each stale package into `dist/` and installs every
package that has a current local build into the project environment with
`uv pip install --no-deps --reinstall`. Nothing is uploaded and no index is
involved: a package's build requirements come from PyPI, the built wheels never
leave the machine and `uv.lock` is untouched. The app is then started with
`uv run --no-sync`, which keeps those local wheels in place. If the environment
has never been set up (the app is missing), `dev.py` syncs it first, holding the
locally built packages back from that sync and installing them from `dist/`
afterwards, so the index's published wheel hashes do not matter. Installation is
cheap, idempotent and quiet (`--verbose` shows uv's output), and dependencies are
not dev.py's business: run `uv sync` after changing them. If you have no local
builds at all, `dev.py` is just `uv run`.

A package is stale when its sources are newer than the wheel built for it, so the
decision does not depend on your git state; a package with no local build yet
counts as stale (the first run therefore builds all three, once). Every package
that has a current local build is then (re)installed, so working on two packages
at the same time does not put either of them back on its published wheel.
Untouched packages have no local build, so editing `cat_panel` never recompiles
`dog_core` — the C++ core is only built when its own sources change.

Going back to the published wheels is just `uv run zoo-app`: it syncs the
environment back to `uv.lock`. The scripts in `tools/local_index/` answer a
different question — what a *consumer* sees when your wheel is published to and
installed from an index.

### Testing the wheel workflow with a local index

`tools/local_index/` runs a throwaway [pypiserver](https://github.com/pypiserver/pypiserver)
so the "publish a wheel, then install it from an index" loop can be exercised
without a real server:

The package index in `pyproject.toml` points at this server
(`http://127.0.0.1:8080/simple`), so once it is running, `uv run zoo-app` gets
the wheels from it:

```bash
# 1. build the panels and the native core into the served folder
uv run --no-project python tools/local_index/publish.py

# 2. serve them on http://127.0.0.1:8080 (leave running; Ctrl+C to stop)
uv run --no-project python tools/local_index/serve.py

# 3. in another terminal: a rebuilt wheel keeps its version but changes its
#    hash, so refresh the lock before syncing. For edits under packages/ use
#    tools/dev.py instead - it builds and installs them locally without the
#    index, so the lock stays untouched.
uv lock --refresh
uv sync
uv run zoo-app
```

The scripts are plain Python, so they run on Windows, macOS and Linux alike.
`publish.py` builds each distribution with `uv build` (a wheel and a sdist) into
`dist/` and copies the artifacts into the directory the server serves, so a
rebuilt artifact replaces the published one on the next request (the server is
started with `-o`, which allows overwriting the same version), and publishing
also counts as a local build for `tools/dev.py`. Building resolves each
distribution's build requirements from PyPI instead of the local index, so the
index does not have to be up to build a package. The server is bound to
`127.0.0.1` and runs without authentication: it is a local test aid only. See
`tools/local_index/README.md`.

### Docking

`app.py` requests a full screen dock space
(`DefaultImGuiWindowType.provide_full_screen_dock_space`) and places every panel
in `MainDockSpace`:

- with one panel, that space is the whole window, so the panel takes all the
  available space;
- with several, they share it — drag a tab to split the space — and the layout,
  including which panels are visible, is remembered between runs;
- the **View** menu of the menu bar (`show_menu_bar`) lists the panels and can
  restore the default layout, the escape hatch if a panel is closed or lost;
- the window geometry, the dock layout and the panel visibility are stored by
  hello_imgui in `zoo_app_settings.ini` (see `runner_params.ini_filename`; it is
  written in the working directory by default), which is why `.gitignore` ignores
  `*.ini`. Delete it to fall back to the default layout.

Multi-viewports are enabled (`enable_viewports`), so a panel can be detached
into its own native window and moved to another monitor: drag its tab out of the
main window (Shift + drag on the tab undocks it into a floating window first).
Its position is stored in the settings file like any other window.

Detached panels get real OS window decorations (title bar, borders, buttons):
ImGui disables them by default (`io.ConfigViewportsNoDecoration` defaults to
true), so `app.py` clears that flag in its `setup_imgui_config` callback.

## Notes on the implementation

- The download runs on a worker thread so the GUI never blocks; the result is
  handed back to the GUI thread on the next frame (textures must be created on
  the GUI thread, while the renderer is alive).
- Frames are decoded with Pillow and uploaded once with
  `hello_imgui.create_texture_gpu_from_rgba_data()`; animating a GIF is then
  just a matter of picking the right texture every frame.
- Idling is disabled (`fps_idling.enable_idling = False`) so the GIF keeps
  animating when the mouse is not moving.
- The window keeps drawing while the user drags a window border. Windows
  normally runs that drag in a *modal* loop inside the window procedure: the
  render loop stops until the mouse is released, and the last frame is stretched
  over the new size. `REPAINT_DURING_RESIZE` deals with it by asking hello_imgui
  to render from inside that loop
  (`app_window_params.repaint_during_resize_gotcha_reentrant_repaint`). It
  repaints on `WM_SIZE`, i.e. before the step has settled, and it renders a frame
  from inside an event handler, so panel `draw()` code is called re-entrantly and
  must not assume "exactly once per frame". Upstream considers this
  advanced/unsupported API
  ([hello_imgui#112](https://github.com/pthom/hello_imgui/issues/112)).
- A *decorated* window can only redraw *after* a resize step, so the frame
  presented during a drag is briefly scaled to the new size. Resizing a borderless
  window is smooth instead, because hello_imgui then resizes within ImGui's own
  frame. hello_imgui#112 suggests repainting from `WM_PAINT` (the GLFW *window
  refresh* callback) to close that gap - a change on the library side.
