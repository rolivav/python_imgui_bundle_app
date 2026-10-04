<#
.SYNOPSIS
Serve `tools/local_index/packages` as a throwaway PEP 503 package index.

.DESCRIPTION
Starts pypiserver - run through `uvx`, so nothing is installed globally - on
http://127.0.0.1:8080. The simple index lives at /simple.

The server is deliberately permissive for local testing:

  -i 127.0.0.1   bound to the local machine only
  -a . -P .      no authentication (uploads accepted anonymously)
  -o             allow overwriting an existing version on upload

Press Ctrl+C to stop it.
#>
$ErrorActionPreference = "Stop"

$packagesDir = Join-Path $PSScriptRoot "packages"
New-Item -ItemType Directory -Force -Path $packagesDir | Out-Null

Write-Host "Serving            $packagesDir"
Write-Host "  simple index:    http://127.0.0.1:8080/simple"
Write-Host "  upload endpoint: http://127.0.0.1:8080"
Write-Host "Press Ctrl+C to stop."

uvx --from pypiserver pypi-server run -p 8080 -i 127.0.0.1 -a . -P . -o $packagesDir
