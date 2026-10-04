<#
.SYNOPSIS
Rebuild the packages you changed, then run the app.

.DESCRIPTION
`uv run cat-gifs` always runs the published wheels. This wrapper rebuilds the
wheel of every package under `packages/` whose sources are newer than the wheel
built for it, installs every package that has a current local build into the
project environment, and then starts the command without syncing, so those builds
stay in place.

Nothing is uploaded and no index is involved: the wheels are written to `dist/`
and installed from there, and `uv.lock` is not modified. Only a package you
edited is rebuilt, so only a changed C++ core costs compile time; packages with
no local build keep their published wheel.

The environment is not synced - dependencies are `uv sync`'s business. Going back
to the published wheels is `uv run cat-gifs`, which syncs. Use -Verbose to see
uv's own output for the install.

Going back to the published wheels is just `uv run cat-gifs`: it syncs the
environment back to `uv.lock`.

Parameters:
  -All       rebuild every package, changed or not
  -None      rebuild nothing - just run what is installed
  -Command   the command to run (default: cat-gifs)

Examples:
  .\tools\dev.cmd
  .\tools\dev.cmd -All
  .\tools\dev.cmd -None
  .\tools\dev.cmd -Command python
#>
[CmdletBinding()]
param(
    [switch]$All,
    [switch]$None,
    [string]$Command = "cat-gifs"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$buildDir = Join-Path $repoRoot "dist"

# Every distribution under `packages/` (its folder name is its distribution name
# with dashes) is built from its own folder - but only while it is stale.
$packages = Get-ChildItem -LiteralPath (Join-Path $repoRoot "packages") -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "pyproject.toml") } |
    Sort-Object -Property Name |
    Select-Object -ExpandProperty Name

# A package is stale when its newest source file is newer than the wheel built
# for it (or when it has never been built). That is the rule a build system uses,
# and unlike `git status` it does not care whether the work has been committed.
$ignoredPaths = '[\\/](build|dist|target|bazel-[^\\/]+|__pycache__|\.pytest_cache|\.mypy_cache)[\\/]|\.egg-info'

function Get-NewestSourceFile {
    param([string]$Path)
    Get-ChildItem -LiteralPath $Path -Recurse -File -Force |
        Where-Object { $_.FullName -notmatch $ignoredPaths } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Get-LocalWheel {
    param([string]$Folder)
    Get-ChildItem -LiteralPath $buildDir -File -Filter "$Folder-*.whl" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

# Returns why a package has to be rebuilt, or $null when its local build is
# current.
function Get-StaleReason {
    param([string]$Folder)
    $wheel = Get-LocalWheel -Folder $Folder
    if (-not $wheel) { return "nothing built for it yet" }
    $newestSource = Get-NewestSourceFile -Path (Join-Path $repoRoot "packages/$Folder")
    if ($newestSource -and $newestSource.LastWriteTime -gt $wheel.LastWriteTime) {
        return "sources newer than $(Join-Path 'dist' $wheel.Name)"
    }
    return $null
}

$rebuild = @()
foreach ($folder in $packages) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "packages/$folder"))) { continue }
    if ($All) {
        $rebuild += [pscustomobject]@{ Folder = $folder; Reason = "-All" }
        continue
    }
    $reason = Get-StaleReason -Folder $folder
    if ($reason) { $rebuild += [pscustomobject]@{ Folder = $folder; Reason = $reason } }
}

$local = @()
if ($None) {
    Write-Host "dev: -None, leaving the environment as it is" -ForegroundColor DarkGray
} else {
    foreach ($item in $rebuild) {
        Write-Host "dev: rebuilding $($item.Folder) - $($item.Reason)" -ForegroundColor DarkGray
        # A wheel that was just installed from here can briefly be held open by
        # the OS, which would make the build fail while writing it.
        Get-ChildItem -LiteralPath $buildDir -File -Filter "$($item.Folder)-*" -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
        & uv build --wheel --out-dir $buildDir (Join-Path $repoRoot "packages/$($item.Folder)")
        if ($LASTEXITCODE -ne 0) { throw "uv build failed for $($item.Folder)" }
    }
    if ($rebuild.Count -eq 0) {
        Write-Host "dev: nothing to rebuild" -ForegroundColor DarkGray
    }

    # Every package whose local build matches its sources runs from that build.
    # Installing is cheap, and since a rebuild keeps the version, uv cannot tell
    # a local build from the published one - so the local builds are simply put
    # back on every run instead of trying to guess what is installed.
    foreach ($folder in $packages) {
        $wheel = Get-LocalWheel -Folder $folder
        if (-not $wheel) { continue }
        $newestSource = Get-NewestSourceFile -Path (Join-Path $repoRoot "packages/$folder")
        if (-not $newestSource -or $newestSource.LastWriteTime -le $wheel.LastWriteTime) {
            $local += [pscustomobject]@{ Folder = $folder; Path = $wheel.FullName }
        }
    }

    if ($local.Count -eq 0) {
        Write-Host "dev: no local builds - using the published wheels" -ForegroundColor DarkGray
    } else {
        Write-Host "dev: local builds: $(($local.Folder) -join ', ')" -ForegroundColor DarkGray

        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ".venv"))) {
            & uv sync
            if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }
        }

        $output = @()
        $code = 1
        # uv reports progress on stderr, which PowerShell 5.1 turns into an error
        # record; relax the preference while we capture it.
        $previousErrorAction = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $output = & uv pip install --no-deps --reinstall @($local.Path) 2>&1
            $code = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorAction
        }
        if ($code -ne 0) {
            $output | ForEach-Object { Write-Host "$_" }
            throw "uv pip install failed"
        }
        if ($VerbosePreference -ne "SilentlyContinue") {
            $output | ForEach-Object { Write-Host "$_" }
        }
    }
}

# --no-sync keeps whatever is installed in place. A plain `uv run cat-gifs`
# syncs the environment back to the published wheels.
$runArgs = @()
if ($None -or $local.Count -gt 0) { $runArgs += "--no-sync" }
$runArgs += $Command
& uv run @runArgs
exit $LASTEXITCODE
