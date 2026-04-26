"""
WhisperType — system-wide voice-to-text.
Hold Win+S (AHK sends F18) to record, release to transcribe and type.
"""
import os, sys, json, glob, tempfile, time
from pathlib import Path

import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import keyboard
import pyperclip

# ── CUDA DLL setup (Windows — required for faster-whisper GPU) ───────────────
def _setup_cuda_dlls():
    if sys.platform != "win32":
        return
    for pat in [
        "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v*/bin",
        "C:/Program Files/NVIDIA/CUDNN/v*/bin",
        "C:/tools/cuda/bin",
    ]:
        for p in glob.glob(pat):
            if os.path.isdir(p):
                try:
                    os.add_dll_directory(p)
                except Exception:
                    pass

_setup_cuda_dlls()
from faster_whisper import WhisperModel  # noqa: E402 — must follow DLL setup

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
PROFILE_PATH = HERE / "speaker_profile.json"
SAMPLE_RATE = 16_000

# ── Speaker profile (input jack) ──────────────────────────────────────────────
# This is the plug point for a future shared speaker profile DB.
# All voice tools in EmergeQ will load from this same file.
def load_speaker_profile() -> dict:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"vocabulary": [], "hotwords": []}

PROFILE = load_speaker_profile()

def _build_prompt() -> str:
    base = (
        "EmergeQ, MindQ, PryoQ, DevBrain, Qlip, TaskQuest, Scourly, Noa, Helene, "
        "Tailscale, Obsidian, Deepgram, Telegram, Anthropic"
    )
    extras = ", ".join(PROFILE.get("vocabulary", []) + PROFILE.get("hotwords", []))
    return f"{base}, {extras}".rstrip(", ") if extras else base

# ── Hardware detection ────────────────────────────────────────────────────────
def _nvidia_vram_gb() -> float:
    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return int(r.stdout.strip().split("\n")[0]) / 1024
    except Exception:
        pass
    return 0.0

def detect_hardware() -> tuple:
    vram = _nvidia_vram_gb()
    if vram >= 8:
        return "large-v3", "cuda", "float16"
    if vram >= 4:
        return "medium", "cuda", "float16"
    if vram > 0:
        return "small", "cuda", "int8"
    try:
        import psutil
        ram = psutil.virtual_memory().total / 1e9
    except ImportError:
        ram = 8.0
    if ram >= 16:
        return "medium", "cpu", "int8"
    if ram >= 8:
        return "small", "cpu", "int8"
    return "base", "cpu", "int8"

# ── Load model ────────────────────────────────────────────────────────────────
print("WhisperType starting...")
_model_size, _device, _compute = detect_hardware()
print(f"  Auto-detected        -> {_model_size} on {_device} ({_compute})")
try:
    _model = WhisperModel(_model_size, device=_device, compute_type=_compute)
except Exception as e:
    print(f"  GPU init failed ({e}), falling back to CPU int8...")
    _model = WhisperModel(_model_size, device="cpu", compute_type="int8")
print(f"  Model ready: {_model_size}\n")

# ── Recording state ───────────────────────────────────────────────────────────
_recording = False
_frames: list = []

def _audio_callback(indata, frames, time_info, status):
    if _recording:
        _frames.append(indata.copy().flatten())

# ── Transcribe ────────────────────────────────────────────────────────────────
def _transcribe(audio: np.ndarray) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    try:
        wav.write(tmp, SAMPLE_RATE, (audio * 32767).astype(np.int16))
        segs, _ = _model.transcribe(
            tmp,
            beam_size=5,
            language="en",
            vad_filter=True,
            temperature=0,
            condition_on_previous_text=False,
            initial_prompt=_build_prompt(),
        )
        return " ".join(s.text.strip() for s in segs).strip()
    finally:
        os.unlink(tmp)

# ── Typing — paste via clipboard so all punctuation survives ─────────────────
def _type_text(text: str):
    if not text:
        return
    old = ""
    try:
        old = pyperclip.paste()
    except Exception:
        pass
    pyperclip.copy(text + " ")
    keyboard.send("ctrl+v")
    time.sleep(0.15)
    try:
        pyperclip.copy(old)
    except Exception:
        pass

# ── Hotkey handlers (AHK sends Ctrl+Shift+F12 on press, Ctrl+Shift+F11 on release) ──
def _on_press():
    global _recording, _frames
    if not _recording:
        _recording = True
        _frames = []
        print("  [REC] ...", end="\r", flush=True)

def _on_release():
    global _recording
    if _recording:
        _recording = False
        print("  [REC] transcribing...", end="\r", flush=True)
        if _frames:
            audio = np.concatenate(_frames)
            text = _transcribe(audio)
            if text:
                print(f"  >> {text}          ")
                _type_text(text)
            else:
                print("  (nothing heard)           ")

# ── Main ──────────────────────────────────────────────────────────────────────
print("Ready. Hold Right Win+S to dictate. Ctrl+C to quit.")
print("(Run as administrator if hotkey doesn't respond)\n")

_stream = sd.InputStream(
    samplerate=SAMPLE_RATE, channels=1, dtype="float32",
    callback=_audio_callback,
)
_stream.start()

keyboard.add_hotkey("ctrl+shift+f12", _on_press, suppress=True)
keyboard.add_hotkey("ctrl+shift+f11", _on_release, suppress=True)

try:
    keyboard.wait()
except KeyboardInterrupt:
    pass
finally:
    _stream.stop()
