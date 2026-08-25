import threading
from types import SimpleNamespace

import pytest

from speako.config import PipelineNode, Preset, Settings
from speako.history import load_recent_recordings
from speako.pipeline import OUTPUT_CONTRACT, ProcessingCancelled, process_audio, run_node


class FakeResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=f"processed: {kwargs['input']}")


def test_node_call_contains_only_its_instruction_and_current_text():
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)
    node = PipelineNode("Clean", "Clean this text", reasoning_effort="low")

    result = run_node(client, node, "raw words")

    assert result == "processed: raw words"
    assert responses.calls == [
        {
            "model": "gpt-5.6-luna",
            "instructions": f"Clean this text\n\n{OUTPUT_CONTRACT}",
            "input": "raw words",
            "reasoning": {"effort": "low"},
        }
    ]


def test_workflow_returns_and_persists_each_step(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    responses = FakeResponses()
    fake_client = SimpleNamespace(
        responses=responses,
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(text="שלום", _request_id="transcribe-id")
            )
        ),
    )
    monkeypatch.setattr("speako.pipeline.OpenAI", lambda **kwargs: fake_client)
    audio = SimpleNamespace(duration_seconds=2.5)
    preset = Preset("Test", [PipelineNode("Translate", "Translate it")], True)

    result = process_audio(audio, Settings(presets=[preset]), preset, lambda _: None, "2026-01-01T10:00:00+00:00")

    assert result["transcription"] == "שלום"
    assert result["final_output"] == "processed: שלום"
    assert [step["type"] for step in result["steps"]] == ["transcription", "processing_node"]


def test_transcription_language_is_omitted_for_auto_and_sent_for_hebrew(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls = []

    def transcribe(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text="text")

    fake_client = SimpleNamespace(
        responses=FakeResponses(),
        audio=SimpleNamespace(transcriptions=SimpleNamespace(create=transcribe)),
    )
    monkeypatch.setattr("speako.pipeline.OpenAI", lambda **kwargs: fake_client)
    preset = Preset("Raw", [])
    audio = SimpleNamespace(duration_seconds=1)

    process_audio(audio, Settings(transcription_language="auto", presets=[preset]), preset, lambda _: None)
    process_audio(audio, Settings(transcription_language="he", presets=[preset]), preset, lambda _: None)

    assert "language" not in calls[0]
    assert calls[1]["language"] == "he"


def test_cancellation_after_transcription_stops_before_nodes(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cancel_event = threading.Event()
    responses = FakeResponses()

    def transcribe(**kwargs):
        cancel_event.set()
        return SimpleNamespace(text="captured text")

    fake_client = SimpleNamespace(
        responses=responses,
        audio=SimpleNamespace(transcriptions=SimpleNamespace(create=transcribe)),
        close=lambda: None,
    )
    monkeypatch.setattr("speako.pipeline.OpenAI", lambda **kwargs: fake_client)
    preset = Preset("Test", [PipelineNode("Never run", "Do work")])

    with pytest.raises(ProcessingCancelled):
        process_audio(
            SimpleNamespace(duration_seconds=1), Settings(presets=[preset]), preset,
            lambda _: None, cancel_event=cancel_event,
        )

    assert responses.calls == []
    assert load_recent_recordings()[0]["status"] == "cancelled"
