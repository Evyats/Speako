from __future__ import annotations

import logging
import os
import sys
import ctypes
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pynput import keyboard
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .audio import Recorder
from .config import Preset, Settings, load_settings, save_settings
from .hotkey import GlobalHotkey
from .pipeline import ProcessingCancelled, process_audio
from .ui import PresetChooser, SettingsDialog, StatusPopup, app_icon, theme_stylesheet


def configure_logging() -> Path:
    log_dir = Path(os.getenv("LOCALAPPDATA", Path.home())) / "Speako"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "speako.log"
    logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s %(levelname)s %(threadName)s %(message)s", force=True)
    return log_path


class Bridge(QObject):
    hotkey_pressed = Signal()
    hotkey_released = Signal()
    preset_next = Signal()
    preset_previous = Signal()


class ProcessingWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        audio,
        settings: Settings,
        preset: Preset,
        recording_started_at: str | None,
        clipboard_text: str | None = None,
    ) -> None:
        super().__init__()
        self.audio = audio
        self.settings = settings
        self.preset = preset
        self.recording_started_at = recording_started_at
        self.clipboard_text = clipboard_text
        self.cancel_event = threading.Event()
        self._client = None
        self._client_lock = threading.Lock()

    def _set_client(self, client) -> None:
        with self._client_lock:
            self._client = client
            already_cancelled = self.cancel_event.is_set()
        if already_cancelled:
            try:
                client.close()
            except Exception:
                pass

    def request_cancel(self) -> None:
        self.cancel_event.set()
        with self._client_lock:
            client = self._client
        if client is not None:
            try:
                client.close()
            except Exception:
                logging.debug("Closing the OpenAI client during cancellation failed", exc_info=True)

    @Slot()
    def run(self) -> None:
        try:
            logging.info("Processing started with preset=%s", self.preset.name)
            result = process_audio(
                self.audio, self.settings, self.preset, self.progress.emit,
                self.recording_started_at, self.clipboard_text,
                self.cancel_event, self._set_client,
            )
            if self.cancel_event.is_set():
                raise ProcessingCancelled("Processing cancelled")
            logging.info("Processing completed")
            self.finished.emit(result)
        except ProcessingCancelled:
            logging.info("Processing cancelled")
            self.cancelled.emit()
        except Exception as exc:
            logging.exception("Processing failed")
            self.failed.emit(str(exc))


class SpeakoController(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.settings = load_settings()
        app.setStyleSheet(theme_stylesheet(self.settings.theme == "dark"))
        self.recorder = Recorder()
        self.recording = False
        self.processing = False
        self.popup = StatusPopup()
        self.chooser = PresetChooser()
        self.chooser.selected.connect(self._select_preset)
        self.active_preset_index = self._default_preset_index()
        self.bridge = Bridge()
        self.bridge.hotkey_pressed.connect(self._hotkey_pressed)
        self.bridge.hotkey_released.connect(self._hotkey_released)
        self.bridge.preset_next.connect(self._preset_next)
        self.bridge.preset_previous.connect(self._preset_previous)
        self.thread: QThread | None = None
        self.worker: ProcessingWorker | None = None
        self.recording_started_at: str | None = None
        self.target_window: int | None = None

        icon = QIcon(app_icon())
        app.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, app)
        menu = QMenu()
        toggle = QAction("Start / stop recording", menu)
        toggle.triggered.connect(self.toggle)
        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self.open_settings)
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(toggle)
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        self._restart_hotkey()
        self.popup.show_status(f"Ready · {self.settings.hotkey}", auto_hide_ms=1600)

    def _restart_hotkey(self) -> None:
        if hasattr(self, "hotkey"):
            self.hotkey.stop()
        self.hotkey = GlobalHotkey(
            self.settings.hotkey,
            self.bridge.hotkey_pressed.emit,
            self.bridge.hotkey_released.emit,
            self.bridge.preset_next.emit,
            self.bridge.preset_previous.emit,
        )
        self.hotkey.start()

    def _default_preset_index(self) -> int:
        return 0

    @property
    def active_preset(self) -> Preset:
        return self.settings.presets[self.active_preset_index]

    @Slot()
    def _hotkey_pressed(self) -> None:
        logging.info("Hotkey pressed; recording=%s processing=%s", self.recording, self.processing)
        if self.processing:
            self._cancel_processing()
            return
        if self.recording:
            self.chooser.hide()
            self.toggle()
            return
        self.active_preset_index = self._default_preset_index()
        self.toggle()
        if self.recording:
            self.chooser.show_presets(self.settings.presets, self.active_preset_index, above=self.popup)

    @Slot()
    def _hotkey_released(self) -> None:
        logging.info("Hotkey released; hiding chooser")
        self.chooser.hide()
        if self.recording and not self.active_preset.uses_microphone:
            # Nothing to keep listening for — run the flow immediately
            # instead of waiting for a second press of the hotkey. This
            # only fires on release, not while still browsing presets
            # with the arrow keys or hovering one with the mouse.
            self.toggle()

    @Slot(int)
    def _select_preset(self, index: int) -> None:
        if not (0 <= index < len(self.settings.presets)):
            return
        self.active_preset_index = index
        self.chooser.show_presets(self.settings.presets, index, above=self.popup)
        self.popup.show_status(f"Listening · {self.active_preset.name}", True)

    @Slot()
    def _preset_next(self) -> None:
        self._cycle_preset(1)

    @Slot()
    def _preset_previous(self) -> None:
        self._cycle_preset(-1)

    def _cycle_preset(self, offset: int) -> None:
        if not self.chooser.isVisible():
            return
        visible_indices = [i for i, preset in enumerate(self.settings.presets) if preset.visible_in_chooser]
        if not visible_indices:
            return
        pos = visible_indices.index(self.active_preset_index) if self.active_preset_index in visible_indices else -offset
        pos = (pos + offset) % len(visible_indices)
        self._select_preset(visible_indices[pos])

    @Slot()
    def toggle(self) -> None:
        if self.processing:
            self._cancel_processing()
            return
        if not self.recording:
            try:
                self.target_window = ctypes.windll.user32.GetForegroundWindow()
                self.recording_started_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
                self.recorder.start(self.settings.input_device)
                self.recording = True
                self.popup.show_status(f"Listening · {self.active_preset.name}", True)
            except Exception as exc:
                self._error(str(exc))
            return
        preset = self.active_preset
        try:
            try:
                audio = self.recorder.stop()
            except RuntimeError:
                if preset.uses_microphone:
                    raise
                audio = None
            self.recording = False
            self.processing = True
            self.popup.show_status("Preparing audio…" if preset.uses_microphone else "Reading clipboard…")
            self._process(audio, preset)
        except Exception as exc:
            self.recording = False
            self._error(str(exc))

    def _process(self, audio, preset: Preset) -> None:
        clipboard_text = None if preset.uses_microphone else self.app.clipboard().text()
        self.thread = QThread(self)
        self.worker = ProcessingWorker(
            audio, self.settings, preset, self.recording_started_at, clipboard_text
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._progress)
        self.worker.finished.connect(self._complete)
        self.worker.failed.connect(self._error)
        self.worker.cancelled.connect(self._processing_cancelled)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.cancelled.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    @Slot()
    def _cancel_processing(self) -> None:
        if not self.processing or self.worker is None:
            return
        self.popup.show_status("Cancelling processing…")
        self.worker.request_cancel()

    @Slot()
    def _processing_cancelled(self) -> None:
        self.processing = False
        self.popup.show_status("Processing cancelled", auto_hide_ms=1800)

    @Slot(str)
    def _progress(self, text: str) -> None:
        self.popup.show_status(text)

    @Slot(object)
    def _complete(self, result: dict) -> None:
        text = str(result.get("final_output", ""))
        self.app.clipboard().setText(text)
        self.processing = False
        if self.settings.auto_paste:
            self.popup.show_status("Copied · pasting automatically", auto_hide_ms=1800)
            QTimer.singleShot(120, self._paste_result)
        else:
            self.popup.show_status("Copied to clipboard", auto_hide_ms=1800)

    @Slot()
    def _paste_result(self) -> None:
        try:
            if self.target_window:
                ctypes.windll.user32.SetForegroundWindow(self.target_window)
            QTimer.singleShot(80, self._send_paste)
        except Exception as exc:
            self._report_paste_failure(exc)

    @Slot()
    def _send_paste(self) -> None:
        try:
            controller = keyboard.Controller()
            with controller.pressed(keyboard.Key.ctrl):
                controller.press("v")
                controller.release("v")
        except Exception as exc:
            self._report_paste_failure(exc)

    def _report_paste_failure(self, exc: Exception) -> None:
        logging.exception("Automatic paste failed")
        self.popup.show_error(f"Automatic paste failed: {exc}", auto_hide_ms=5000)

    @Slot(str)
    def _error(self, message: str) -> None:
        self.processing = False
        self.chooser.hide()
        self.popup.show_error(message, auto_hide_ms=6000)

    def open_settings(self) -> None:
        if self.recording or self.processing:
            self.popup.show_error("Finish the current recording before opening Settings.", auto_hide_ms=3500)
            return
        dialog = SettingsDialog(self.settings)
        dialog.settings_saved.connect(self._apply_settings)
        dialog.exec()

    @Slot(object)
    def _apply_settings(self, settings: Settings) -> None:
        self.settings = settings
        self.active_preset_index = self._default_preset_index()
        save_settings(settings)
        self.app.setStyleSheet(theme_stylesheet(settings.theme == "dark"))
        self._restart_hotkey()
        self.popup.show_status(f"Settings saved · {settings.hotkey}", auto_hide_ms=1800)

    def _tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings()

    def quit(self) -> None:
        self.hotkey.stop()
        self.chooser.hide()
        self.tray.hide()
        self.app.quit()


def main() -> int:
    # During development, load the project-local .env without replacing an
    # environment variable that the user explicitly supplied to Windows.
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
    log_path = configure_logging()
    logging.info("Speako starting; log=%s", log_path)
    app = QApplication(sys.argv)
    app.setApplicationName("Speako")
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logging.error("A Windows system tray is required")
        return 1
    controller = SpeakoController(app)
    app.controller = controller
    def handle_exception(exc_type, exc_value, exc_tb) -> None:
        logging.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        controller.popup.show_error(str(exc_value), auto_hide_ms=6000)
    sys.excepthook = handle_exception
    return app.exec()
