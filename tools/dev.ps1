<#
.SYNOPSIS
Rebuild the packages you changed, then run the app.

.DESCRIPTION
`uv run cat-gifs` always runs the published wheels. This wrapper builds the wheel
of every package under `packages/` whose sources are newer than the wheel built
for it, installs those wheels into the project environment on top of a synced
`uv.lock`, and then starts the command with the environment left untouched.

Nothing is uploaded and no index is involved: the artifacts stay in `dist/`, the
local environment gets them directly, and `uv.lock` is not modified. Everything
you did not edit keeps its published wheel, so only a changed C++ core costs
compile time.

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
$packages = @(
    [pscustomobject]@{ Folder = "cat_panel"; Distribution = "cat-panel" }
    [pscustomobject]@{ Folder = "dog_panel"; Distribution = "dog-panel" }
    [pscustomobject]@{ Folder = "dog_core"; Distribution = "dog-core" }
)

$buildDir = Join-Path $repoRoot "dist"

# A package is stale when its newest source file is newer than the wheel built
# for it (or when it has never been built). That is the rule a build system uses,
# and unlike `git status` it does not care whether the work has been committed.
$ignoredPaths = '[\\/](build|dist|__pycache__|\.pytest_cache|\.mypy_cache)[\\/]|\.egg-info'

function Get-NewestSourceFile {
    param([string]$Path)
    Get-ChildItem -LiteralPath $Path -Recurse -File -Force |
        Where-Object { $_.FullName -notmatch $ignoredPaths } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

$rebuild = @()
if (-not $None) {
    foreach ($package in $packages) {
        if ($All) {
            $rebuild += $package
            continue
        }
        $source = Join-Path $repoRoot "packages/$($package.Folder)"
        if (-not (Test-Path -LiteralPath $source)) { continue }

        $newestArtifact = Get-ChildItem -LiteralPath $buildDir -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "$($package.Folder)-*" } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        $newestSource = Get-NewestSourceFile -Path $source

        if (-not $newestArtifact -or ($newestSource -and $newestSource.LastWriteTime -gt $newestArtifact.LastWriteTime)) {
            $rebuild += $package
        }
    }
}

if ($rebuild.Count -eq 0) {
    Write-Host "dev: nothing to rebuild - running what is installed" -ForegroundColor DarkGray
} else {
    $names = ($rebuild | ForEach-Object { $_.Distribution }) -join ", "
    Write-Host "dev: rebuilding $names" -ForegroundColor DarkGray

    $wheels = @()
    foreach ($package in $rebuild) {
        $source = Join-Path $repoRoot "packages/$($package.Folder)"
        & uv build --wheel --out-dir $buildDir $source
        if ($LASTEXITCODE -ne 0) { throw "uv build failed for $($package.Folder)" }

        $wheel = Get-ChildItem -LiteralPath $buildDir -File -Filter "$($package.Folder)-*.whl" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if (-not $wheel) { throw "uv build produced no wheel for $($package.Folder)" }
        $wheels += $wheel.FullName
    }

    # Bring the rest of the environment in line with uv.lock, then overlay the
    # wheels built from the working copy. No index, no upload, no lock change.
    & uv sync
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

    & uv pip install --no-deps --reinstall @wheels
    if ($LASTEXITCODE -ne 0) { throw "uv pip install failed" }
}

# --no-sync keeps the locally built wheels in place. A plain `uv run cat-gifs`
# syncs the environment back to the published ones.
& uv run --no-sync $Command
exit $LASTEXITCODE
