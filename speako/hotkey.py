from __future__ import annotations

import logging
from collections.abc import Callable

from pynput import keyboard


SPECIAL_KEYS = {
    "ctrl": keyboard.Key.ctrl,
    "alt": keyboard.Key.alt,
    "shift": keyboard.Key.shift,
    "meta": keyboard.Key.cmd,
    "win": keyboard.Key.cmd,
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
}


def parse_hotkey(sequence: str) -> set[object]:
    keys: set[object] = set()
    for part in sequence.lower().split("+"):
        token = part.strip()
        keys.add(SPECIAL_KEYS[token] if token in SPECIAL_KEYS else keyboard.KeyCode.from_char(token))
    return keys


def to_pynput(sequence: str) -> str:
    display = {
        "ctrl": "<ctrl>", "alt": "<alt>", "shift": "<shift>",
        "meta": "<cmd>", "win": "<cmd>", "space": "<space>", "tab": "<tab>",
    }
    return "+".join(display.get(p.strip().lower(), p.strip().lower()) for p in sequence.split("+"))


class GlobalHotkey:
    def __init__(
        self,
        sequence: str,
        on_pressed: Callable[[], None],
        on_released: Callable[[], None] | None = None,
        on_next: Callable[[], None] | None = None,
        on_previous: Callable[[], None] | None = None,
    ) -> None:
        self.sequence = sequence
        self.on_pressed = on_pressed
        self.on_released = on_released or (lambda: None)
        self.on_next = on_next or (lambda: None)
        self.on_previous = on_previous or (lambda: None)
        self.required = parse_hotkey(sequence)
        self.current: set[object] = set()
        self.active = False
        self._listener: keyboard.Listener | None = None

    @staticmethod
    def _canonical(key):
        aliases = {
            keyboard.Key.ctrl_l: keyboard.Key.ctrl, keyboard.Key.ctrl_r: keyboard.Key.ctrl,
            keyboard.Key.alt_l: keyboard.Key.alt, keyboard.Key.alt_r: keyboard.Key.alt,
            keyboard.Key.shift_l: keyboard.Key.shift, keyboard.Key.shift_r: keyboard.Key.shift,
            keyboard.Key.cmd_l: keyboard.Key.cmd, keyboard.Key.cmd_r: keyboard.Key.cmd,
        }
        return aliases.get(key, key)

    def _press(self, key) -> None:
        canonical = self._canonical(key)
        self.current.add(canonical)
        if not self.active and self.required.issubset(self.current):
            self.active = True
            logging.debug("GlobalHotkey %s activated", self.sequence)
            self.on_pressed()
        elif self.active and canonical == keyboard.Key.up:
            self.on_previous()
        elif self.active and canonical == keyboard.Key.down:
            self.on_next()

    def _release(self, key) -> None:
        key = self._canonical(key)
        was_active = self.active
        self.current.discard(key)
        if was_active and not self.required.issubset(self.current):
            self.active = False
            logging.debug("GlobalHotkey %s deactivated (released %s)", self.sequence, key)
            self.on_released()

    def start(self) -> None:
        self.stop()
        self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
        self.current.clear()
        self.active = False
