from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI

from .config import PipelineNode, Preset, Settings
from .history import save_recording


ProgressCallback = Callable[[str], None]
ClientCallback = Callable[[OpenAI], None]


class ProcessingCancelled(RuntimeError):
    pass


def _check_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise ProcessingCancelled("Processing cancelled")

OUTPUT_CONTRACT = (
    "Return only the resulting text: no preamble, labels, quotation marks, "
    "or commentary."
)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def process_audio(
    audio,
    settings: Settings,
    preset: Preset,
    progress: ProgressCallback,
    recording_started_at: str | None = None,
    clipboard_text: str | None = None,
    cancel_event: threading.Event | None = None,
    client_ready: ClientCallback | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "recording_started_at": recording_started_at,
        "processing_started_at": _now(),
        "completed_at": None,
        "status": "processing",
        "error": None,
        "metadata": {
            "preset": preset.name,
            "input_source": "microphone" if preset.uses_microphone else "clipboard",
            "transcription_model": settings.transcription_model,
            "transcription_language": settings.transcription_language,
            "input_device_id": settings.input_device,
            "audio_duration_seconds": round(float(getattr(audio, "duration_seconds", 0.0)), 2),
            "automatic_paste_enabled": settings.auto_paste,
            "configured_nodes": [
                {"name": n.name, "enabled": n.enabled, "model": n.model, "reasoning_effort": n.reasoning_effort}
                for n in preset.nodes
            ],
        },
        "transcription": "",
        "final_output": "",
        "steps": [],
    }
    _check_cancelled(cancel_event)
    if not os.getenv("OPENAI_API_KEY"):
        record.update(status="failed", error="OPENAI_API_KEY is not set", completed_at=_now())
        save_recording(record)
        raise RuntimeError(record["error"])

    client = OpenAI(timeout=60.0, max_retries=1)
    if client_ready is not None:
        client_ready(client)
    try:
        _check_cancelled(cancel_event)
        if preset.uses_microphone:
            progress("Transcribing…")
            started = time.perf_counter()
            transcription_args = {"model": settings.transcription_model, "file": audio}
            if settings.transcription_language != "auto":
                transcription_args["language"] = settings.transcription_language
            transcription = client.audio.transcriptions.create(**transcription_args)
            _check_cancelled(cancel_event)
            text = transcription.text.strip()
            if not text:
                raise RuntimeError("The transcription was empty")
            record["steps"].append({
                "sequence": 1, "type": "transcription", "name": "Speech transcription",
                "model": settings.transcription_model, "reasoning_effort": None,
                "input": "Recorded microphone audio", "output": text, "status": "completed",
                "duration_ms": round((time.perf_counter() - started) * 1000),
                "request_id": getattr(transcription, "_request_id", None),
            })
        else:
            progress("Reading clipboard…")
            text = (clipboard_text or "").strip()
            _check_cancelled(cancel_event)
            if not text:
                raise RuntimeError("The clipboard is empty")
            record["steps"].append({
                "sequence": 1, "type": "clipboard", "name": "Clipboard text",
                "model": None, "reasoning_effort": None,
                "input": "Clipboard contents", "output": text, "status": "completed",
                "duration_ms": 0, "request_id": None,
            })
        record["transcription"] = text
        sequence = 2
        for node in preset.nodes:
            _check_cancelled(cancel_event)
            if not node.enabled:
                continue
            progress(f"Running {node.name}…")
            node_input = text
            started = time.perf_counter()
            text, request_id = run_node_with_metadata(client, node, text)
            _check_cancelled(cancel_event)
            record["steps"].append({
                "sequence": sequence, "type": "processing_node", "name": node.name,
                "model": node.model, "reasoning_effort": node.reasoning_effort,
                "instructions": node.prompt, "input": node_input, "output": text,
                "status": "completed", "duration_ms": round((time.perf_counter() - started) * 1000),
                "request_id": request_id,
            })
            sequence += 1
        record.update(status="completed", final_output=text.strip(), completed_at=_now())
        save_recording(record)
        return record
    except Exception as exc:
        cancelled = isinstance(exc, ProcessingCancelled) or bool(cancel_event and cancel_event.is_set())
        error = "Processing cancelled" if cancelled else str(exc)
        record.update(status="cancelled" if cancelled else "failed", error=error, completed_at=_now())
        record["steps"].append({
            "sequence": len(record["steps"]) + 1, "type": "error",
            "name": "Workflow cancelled" if cancelled else "Workflow error",
            "status": "cancelled" if cancelled else "failed", "output": error,
        })
        save_recording(record)
        if cancelled and not isinstance(exc, ProcessingCancelled):
            raise ProcessingCancelled(error) from exc
        raise
    finally:
        try:
            client.close()
        except Exception:
            pass


def run_node(client: OpenAI, node: PipelineNode, text: str) -> str:
    result, _ = run_node_with_metadata(client, node, text)
    return result


def run_node_with_metadata(client: OpenAI, node: PipelineNode, text: str) -> tuple[str, str | None]:
    response = client.responses.create(
        model=node.model,
        instructions=f"{node.prompt}\n\n{OUTPUT_CONTRACT}",
        input=text,
        reasoning={"effort": node.reasoning_effort},
    )
    result = response.output_text.strip()
    if not result:
        raise RuntimeError(f"{node.name} returned empty text")
    return result, getattr(response, "_request_id", None)
