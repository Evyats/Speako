from __future__ import annotations

import io
import threading
import wave

import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, sample_rate: int = 16_000) -> None:
        self.sample_rate = sample_rate
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    def start(self, device: int | None = None) -> None:
        if self._stream is not None:
            return
        self._chunks = []

        def callback(indata: np.ndarray, frames: int, time, status) -> None:
            del frames, time, status
            with self._lock:
                self._chunks.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=device,
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> io.BytesIO:
        if self._stream is None:
            raise RuntimeError("Recording has not started")
        stream, self._stream = self._stream, None
        stream.stop()
        stream.close()
        with self._lock:
            audio = np.concatenate(self._chunks, axis=0) if self._chunks else np.empty((0, 1))
        if len(audio) == 0:
            raise RuntimeError("No audio was recorded")
        pcm = (np.clip(audio[:, 0], -1, 1) * 32767).astype("<i2")
        output = io.BytesIO()
        output.name = "recording.wav"
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(pcm.tobytes())
        output.seek(0)
        output.duration_seconds = len(pcm) / self.sample_rate
        return output



def input_devices() -> list[tuple[int, str]]:
    """List real input devices, deduplicated to Windows WASAPI where available.

    PortAudio exposes each physical device once per Windows host API (MME,
    DirectSound, WASAPI, WDM-KS), so the raw device list is full of
    duplicates and legacy virtual entries (Sound Mapper, Primary Capture
    Driver). WASAPI alone lists each real device exactly once.
    """
    hostapis = sd.query_hostapis()
    wasapi_index = next(
        (i for i, api in enumerate(hostapis) if api["name"] == "Windows WASAPI"), None
    )
    devices = list(enumerate(sd.query_devices()))
    if wasapi_index is not None:
        devices = [(i, d) for i, d in devices if d["hostapi"] == wasapi_index]
    return [(i, str(d["name"])) for i, d in devices if int(d["max_input_channels"]) > 0]
