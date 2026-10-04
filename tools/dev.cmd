@echo off
:: Wrapper around dev.ps1 so it runs without changing the PowerShell execution
:: policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
