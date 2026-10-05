# Local package index

A throwaway [pypiserver](https://github.com/pypiserver/pypiserver) for testing
the application's wheel workflow: build the panels/core as wheels, publish them
to a local index, then run the app resolving those wheels instead of the
workspace folders.

## Usage

The package index declared in `pyproject.toml` points at this server
(`http://127.0.0.1:8080/simple`), so once it is running the app resolves the
wheels from it.

```bash
# 1. Build the panels and the native core into the served folder.
uv run --no-project python tools/local_index/publish.py

# 2. Serve them (leave this running; Ctrl+C to stop).
uv run --no-project python tools/local_index/serve.py

# 3. In another terminal, fetch the wheels from the index.
uv sync
uv run zoo-app
```

The scripts are plain Python, so they run on Windows, macOS and Linux alike. Run
them with `uv run --no-project python <script>`, which keeps the project
environment untouched, or with any Python 3 on your PATH.

`serve.py` runs pypiserver through `uvx` (nothing is installed globally) bound
to `127.0.0.1:8080`, with authentication disabled and overwriting allowed, so
rebuilding the same version during development works.

`publish.py` doesn't upload over HTTP: it builds each distribution with
`uv build --no-config` (wheel and sdist) into `dist/` and copies the artifacts
into `tools/local_index/packages/`, which is the directory the server serves.
`--no-config` keeps the project's local index out of the build, so a
distribution's build requirements come from PyPI and the index does not have to
be up to build it. The sdist is what lets uv resolve `dog-core` for the Python
versions this machine did not build a wheel for; the wheel is still what gets
installed here. Since the wheels also land in `dist/`, publishing counts as a
local build for `tools/dev.py` — publish and edit nothing, and there is nothing
to rebuild. If you prefer to exercise the upload path, pypiserver also accepts
anonymous uploads:

```bash
uv publish --index internal packages/*
```

## This folder is for the publish/consume path

Day-to-day editing does not need a server: `tools/dev.py` builds the changed
wheels into `dist/` and installs them straight into the project environment, so
nothing is uploaded and `uv.lock` stays untouched. Use the scripts here to check
what a *consumer* of your wheel sees - build, publish to an index, install from
that index:

```bash
uv run --no-project python tools/local_index/publish.py    # build wheel + sdist into packages/
uv run --no-project python tools/local_index/serve.py      # serve them on 127.0.0.1:8080
uv lock --refresh-package cat_panel
uv run --reinstall-package cat_panel zoo-app
```

The last two commands are needed because a rebuilt artifact keeps its version but
changes its hash: uv has to re-read the index metadata (`--refresh-package`) and
reinstall (`--reinstall-package`). Against a real server the steps are the same,
with `uv publish` for the upload.

## Layout

| Path             | Purpose                                                        |
|------------------|----------------------------------------------------------------|
| `serve.py`       | Start pypiserver on `http://127.0.0.1:8080`                     |
| `publish.py`     | Build the wheel and sdist of each package into `packages/`      |
| `packages/`      | The served directory (git-ignored)                             |

The server is unauthenticated and bound to the local machine; treat it as a
local test aid only.
