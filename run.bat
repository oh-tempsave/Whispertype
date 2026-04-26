@echo off
setlocal

:: ── Self-elevate to administrator ─────────────────────────────────────────────
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: ── Launch AHK hotkey (Win+S -> F18) ─────────────────────────────────────────
where autohotkey >nul 2>&1
if not errorlevel 1 (
    start "" autohotkey "%~dp0whispertype.ahk"
) else (
    for %%P in (
        "C:\Program Files\AutoHotkey\AutoHotkey.exe"
        "C:\Program Files\AutoHotkey\v1.1\AutoHotkey.exe"
        "C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
    ) do (
        if exist %%P (
            start "" %%P "%~dp0whispertype.ahk"
            goto :ahk_done
        )
    )
    echo [WARN] AutoHotkey not found. Win+S hotkey will not work.
    echo        Install from https://www.autohotkey.com
)
:ahk_done

:: ── Run WhisperType ───────────────────────────────────────────────────────────
echo.
python "%~dp0whispertype.py"

:: Keep window open on crash so user can read the error
echo.
echo WhisperType exited. Press any key to close.
pause >nul
