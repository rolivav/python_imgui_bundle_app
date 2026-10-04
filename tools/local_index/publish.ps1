<#
.SYNOPSIS
Build the panels and the native core into the local index's package folder.

.DESCRIPTION
Runs `uv build` for each distribution and writes the artifacts into
`tools/local_index/packages/`, the directory served by serve.ps1. That is enough
to "publish": pypiserver picks the new files up on the next request. A rebuilt
artifact replaces the previous one of the same version (serve.ps1 runs the
server with `-o`, which allows overwriting).

Both a wheel and a source distribution are built. The sdist matters for
`dog-core`: its wheel only matches one Python version (`cp313` on this machine),
so uv needs the sdist to be able to resolve the project for the other Python
versions allowed by `requires-python`. Installing on the matching interpreter
still uses the wheel - nothing is compiled for it.

Parameters:
  -Packages  the distribution folders to build (default: all of them)

Examples:
  ./tools/local_index/publish.ps1
  ./tools/local_index/publish.ps1 -Packages cat_panel
#>
[CmdletBinding()]
param(
    [string[]]$Packages = @("cat_panel", "dog_panel", "dog_core")
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$packagesDir = Join-Path $PSScriptRoot "packages"
New-Item -ItemType Directory -Force -Path $packagesDir | Out-Null

foreach ($project in $Packages) {
    $source = Join-Path $repoRoot "packages/$project"
    if (-not (Test-Path $source)) {
        throw "No such package folder: $source"
    }
    Write-Host "Building $project"
    uv build --out-dir $packagesDir $source
    if ($LASTEXITCODE -ne 0) {
        throw "uv build failed for $project"
    }
}

Write-Host ""
Write-Host "Artifacts served from ${packagesDir}:"
Get-ChildItem -Path $packagesDir -File |
    Where-Object { $_.Name -match '\.(whl|tar\.gz)$' } |
    ForEach-Object { Write-Host "  $($_.Name)" }
