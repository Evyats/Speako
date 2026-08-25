from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class PipelineNode:
    name: str
    prompt: str
    enabled: bool = True
    model: str = "gpt-5.6-luna"
    reasoning_effort: str = "none"


def agent_nodes() -> list[PipelineNode]:
    return [
        PipelineNode(
            name="Translate to English",
            prompt=(
                "Translate the input to natural English if it contains Hebrew or another "
                "language. If it is already English, preserve it. Keep every meaningful "
                "requirement and technical term."
            ),
        ),
        PipelineNode(
            name="Shape as an agent prompt",
            prompt=(
                "Rewrite the input as a concise, professional prompt for an AI agent. "
                "Remove filler, repetition, false starts, and irrelevant muttering. Replace "
                "improvised wording with likely professional terminology, but never invent "
                "requirements. Organize the request clearly and preserve all constraints."
            ),
        ),
    ]


@dataclass
class Preset:
    name: str
    nodes: list[PipelineNode] = field(default_factory=list)
    uses_microphone: bool = True
    visible_in_chooser: bool = True


def default_presets() -> list[Preset]:
    return [
        Preset("Agent prompt", agent_nodes()),
        Preset(
            "Clean English",
            [
                PipelineNode(
                    "Translate and polish",
                    "Translate the input to natural English when needed. Remove filler, false starts, and repetition while preserving all meaning and technical terms.",
                )
            ],
        ),
        Preset("Raw transcript", []),
    ]


@dataclass
class Settings:
    hotkey: str = "Ctrl+Alt+Space"
    input_device: int | None = None
    transcription_model: str = "gpt-4o-mini-transcribe"
    transcription_language: str = "auto"
    auto_paste: bool = True
    theme: str = "light"
    presets: list[Preset] = field(default_factory=default_presets)


def config_path() -> Path:
    root = Path(os.getenv("APPDATA", Path.home())) / "Speako"
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"


def load_settings() -> Settings:
    path = config_path()
    if not path.exists():
        return Settings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        # Migrate the original single-pipeline settings without losing user edits.
        legacy_nodes = raw.pop("nodes", None)
        if "presets" in raw:
            raw["presets"] = [
                Preset(
                    name=preset["name"],
                    nodes=[PipelineNode(**node) for node in preset.get("nodes", [])],
                    uses_microphone=preset.get("uses_microphone", True),
                    visible_in_chooser=preset.get("visible_in_chooser", True),
                )
                for preset in raw["presets"]
            ]
        elif legacy_nodes is not None:
            presets = default_presets()
            presets[0].nodes = [PipelineNode(**node) for node in legacy_nodes]
            raw["presets"] = presets
        return Settings(**raw)
    except (OSError, ValueError, TypeError):
        # Don't silently discard a settings file we failed to parse — preserve
        # it alongside the fresh defaults so it can be recovered by hand.
        try:
            path.replace(path.with_suffix(".json.bak"))
        except OSError:
            pass
        return Settings()


def save_settings(settings: Settings) -> None:
    config_path().write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8"
    )
