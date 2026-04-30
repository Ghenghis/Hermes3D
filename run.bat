@echo off
REM run.bat — Windows one-click launcher for Hermes3D-OS Lite.
REM
REM Equivalent to scripts\run-dev.ps1 with all defaults: starts the
REM Gradio UI on :7860, the REST API on :8765, and the supervisor daemon.
REM
REM Usage:
REM   run.bat               (start everything)
REM   run.bat ui-only       (just the Gradio UI)
REM   run.bat api-only      (just the REST API)

setlocal

set REPO_ROOT=%~dp0
set SCRIPT_DIR=%REPO_ROOT%scripts\scaffolding

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    set PWSH=pwsh
) else (
    where powershell >nul 2>&1
    if %ERRORLEVEL%==0 (
        set PWSH=powershell
    ) else (
        echo [FAIL] PowerShell not found. Install Windows PowerShell or PowerShell 7+.
        exit /b 1
    )
)

if "%~1"=="ui-only" (
    %PWSH% -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\run-dev.ps1" -UiOnly
) else if "%~1"=="api-only" (
    %PWSH% -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\run-dev.ps1" -ApiOnly
) else (
    %PWSH% -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\run-dev.ps1" %*
)

endlocal
exit /b %ERRORLEVEL%
