@echo off
:: Wrapper around serve.ps1 so the script runs without changing the machine's
:: PowerShell execution policy (which blocks unsigned .ps1 files by default).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve.ps1" %*
