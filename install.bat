@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   WhisperType Installer
echo ============================================
echo.

:: ── Python check ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [1/4] %PY_VER% found.

:: ── GPU detection ─────────────────────────────────────────────────────────────
set CUDA_AVAILABLE=0
nvidia-smi >nul 2>&1
if not errorlevel 1 (
    set CUDA_AVAILABLE=1
    for /f "tokens=*" %%g in ('nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2^>nul') do (
        echo [2/4] GPU detected: %%g
    )
) else (
    echo [2/4] No NVIDIA GPU found — CPU mode will be used.
    echo        Whisper will auto-select a model that fits your RAM.
)

:: ── Install packages ──────────────────────────────────────────────────────────
echo.
echo [3/4] Installing Python packages...
pip install --quiet sounddevice scipy numpy keyboard pyperclip psutil

if !CUDA_AVAILABLE!==1 (
    echo        Installing faster-whisper ^(GPU^)...
    pip install --quiet faster-whisper
    echo.
    echo [NOTE] GPU detected. If you see CUDA DLL errors at runtime:
    echo        Install CUDA Toolkit 12.x: https://developer.nvidia.com/cuda-downloads
    echo        faster-whisper will auto-fallback to CPU if DLLs are missing.
) else (
    echo        Installing faster-whisper ^(CPU^)...
    pip install --quiet faster-whisper
)

:: ── Speaker profile ───────────────────────────────────────────────────────────
echo.
echo [4/4] Setting up speaker profile...
if not exist "%~dp0speaker_profile.json" (
    (
        echo {
        echo   "vocabulary": [],
        echo   "hotwords": []
        echo }
    ) > "%~dp0speaker_profile.json"
    echo        Created speaker_profile.json
) else (
    echo        speaker_profile.json already exists — skipping.
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ============================================
echo   Installation complete!
echo.
echo   To use WhisperType:
echo     1. Double-click whispertype.ahk
echo        (installs Win+S hotkey)
echo     2. Run as admin:
echo        python "%~dp0whispertype.py"
echo     3. Hold Win+S anywhere to dictate
echo.
echo   To add vocabulary: edit speaker_profile.json
echo ============================================
echo.
pause
