"""Voice service — mirrors src/services/voice.ts."""
from __future__ import annotations

import asyncio
import subprocess
import sys
from typing import Callable, Optional

RECORDING_SAMPLE_RATE = 16000
RECORDING_CHANNELS = 1


def _has_command(cmd: str) -> bool:
    try:
        result = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            timeout=3,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


def _get_platform() -> str:
    return sys.platform


def is_voice_available() -> bool:
    """Check if voice recording is available on this platform.

    Mirrors isVoiceAvailable logic from voice.ts.
    """
    platform = _get_platform()
    if platform == "darwin":
        # macOS — try native audio
        return True
    if platform == "linux":
        return _has_command("sox") or _has_command("arecord")
    return False


class VoiceRecorder:
    """Audio recorder for push-to-talk voice input.

    Mirrors the VoiceRecorder class from voice.ts.
    """

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._recording = False

    def start(self, output_path: str) -> None:
        """Start recording audio to the given output path."""
        if self._recording:
            return
        platform = _get_platform()
        try:
            if platform == "linux":
                if _has_command("sox"):
                    self._process = subprocess.Popen(
                        [
                            "rec",
                            "-r", str(RECORDING_SAMPLE_RATE),
                            "-c", str(RECORDING_CHANNELS),
                            "-e", "signed-integer",
                            "-b", "16",
                            output_path,
                            "silence", "1", "0.1", "3%", "1", "2.0", "3%",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                elif _has_command("arecord"):
                    self._process = subprocess.Popen(
                        [
                            "arecord",
                            "-r", str(RECORDING_SAMPLE_RATE),
                            "-c", str(RECORDING_CHANNELS),
                            "-f", "S16_LE",
                            output_path,
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            self._recording = self._process is not None
        except Exception:
            self._process = None

    def stop(self) -> None:
        """Stop recording."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                pass
            self._process = None
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording


is_voice_available_fn = is_voice_available
