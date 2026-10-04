# Local package index

A throwaway [pypiserver](https://github.com/pypiserver/pypiserver) for testing
the application's wheel workflow: build the panels/core as wheels, publish them
to a local index, then run the app resolving those wheels instead of the
workspace folders.

## Usage

The package index declared in `pyproject.toml` points at this server
(`http://127.0.0.1:8080/simple`), so once it is running the app resolves the
wheels from it.

```powershell
# 1. Build the panels and the native core into the served folder.
./tools/local_index/publish.cmd

# 2. Serve them (leave this running; Ctrl+C to stop).
./tools/local_index/serve.cmd

# 3. In another terminal, fetch the wheels from the index.
uv sync
uv run cat-gifs
```

The `.cmd` files are thin wrappers that run the `.ps1` scripts with
`-ExecutionPolicy Bypass`, so Windows' default policy (which blocks unsigned
scripts) does not get in the way. Run the `.ps1` files directly if your policy
already allows unsigned scripts.

`serve.ps1` runs pypiserver through `uvx` (nothing is installed globally) bound
to `127.0.0.1:8080`, with authentication disabled and overwriting allowed, so
rebuilding the same version during development works.

`publish.ps1` doesn't upload over HTTP: it builds each distribution with
`uv build` (wheel and sdist) directly into `tools/local_index/packages/`, which
is the directory the server serves. The sdist is what lets uv resolve `dog-core`
for the Python versions this machine did not build a wheel for; the wheel is
still what gets installed here. If you prefer to exercise the upload path,
pypiserver also accepts anonymous uploads:

```powershell
uv publish --index internal packages/*
```

## This folder is for the publish/consume path

Day-to-day editing does not need a server: `./tools/dev.cmd` builds the changed
wheels into `dist/` and installs them straight into the project environment, so
nothing is uploaded and `uv.lock` stays untouched. Use the scripts here to check
what a *consumer* of your wheel sees - build, publish to an index, install from
that index:

```powershell
./tools/local_index/publish.cmd    # build wheel + sdist into packages/
./tools/local_index/serve.cmd      # serve them on 127.0.0.1:8080
uv lock --refresh-package cat_panel
uv run --reinstall-package cat_panel cat-gifs
```

The last two commands are needed because a rebuilt artifact keeps its version but
changes its hash: uv has to re-read the index metadata (`--refresh-package`) and
reinstall (`--reinstall-package`). Against a real server the steps are the same,
with `uv publish` for the upload.

## Layout

| Path             | Purpose                                                        |
|------------------|----------------------------------------------------------------|
| `serve.cmd`      | Start pypiserver on `http://127.0.0.1:8080` (wraps `serve.ps1`)  |
| `publish.cmd`    | Build the wheel and sdist of each package into `packages/` (wraps `publish.ps1`) |
| `serve.ps1`      | The server script itself                                       |
| `publish.ps1`    | The build script itself                                        |
| `packages/`      | The served directory (git-ignored)                             |

The server is unauthenticated and bound to the local machine; treat it as a
local test aid only.
