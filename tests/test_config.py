from speako.config import Settings, agent_nodes
from pynput import keyboard

from speako.hotkey import GlobalHotkey, to_pynput


def test_defaults_are_the_single_editable_pipeline():
    settings = Settings()
    assert settings.transcription_model == "gpt-4o-mini-transcribe"
    assert settings.transcription_language == "auto"
    assert settings.auto_paste is True
    assert [node.name for node in settings.presets[0].nodes] == [
        "Translate to English",
        "Shape as an agent prompt",
    ]
    assert all(node.reasoning_effort == "none" for node in settings.presets[0].nodes)
    assert settings.presets[0].uses_microphone
    assert len(settings.presets) == 3


def test_default_nodes_are_not_shared():
    first = agent_nodes()
    second = agent_nodes()
    first[0].name = "Changed"
    assert second[0].name == "Translate to English"


def test_qt_hotkey_is_converted_for_pynput():
    assert to_pynput("Ctrl+Alt+Space") == "<ctrl>+<alt>+<space>"


def test_hotkey_has_distinct_press_and_release_events():
    events = []
    hotkey = GlobalHotkey("Ctrl+Alt+Space", lambda: events.append("press"), lambda: events.append("release"))
    hotkey._press(keyboard.Key.ctrl_l)
    hotkey._press(keyboard.Key.alt_l)
    hotkey._press(keyboard.Key.space)
    hotkey._release(keyboard.Key.space)
    assert events == ["press", "release"]
