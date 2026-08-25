from __future__ import annotations

import copy
import os

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QKeySequenceEdit, QLabel, QListWidget,
    QTabWidget, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Signal

from ..audio import input_devices
from ..config import Settings
from .common import EditableRow, ThemedDialog, button_row, form_layout, move_item, populate_reorderable_list
from .history_view import HistoryView
from .models import TRANSCRIBE_MODELS, ModelCombo
from .preset_editor import NewPresetDialog, PresetEditor
from .theme import theme_stylesheet


class SettingsDialog(ThemedDialog):
    settings_saved = Signal(object)

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__("Speako settings", (360, 420), (500, 550), settings.theme == "dark", parent)
        self.settings = copy.deepcopy(settings)
        self.presets = self.settings.presets
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Speako")
        title.setStyleSheet("font: 700 24px 'Segoe UI';")
        header.addWidget(title)
        header.addStretch()
        badge_style = (
            "color: {color}; background: {bg}; border-radius: 10px; "
            "padding: 5px 12px; font: 600 11px 'Segoe UI';"
        )
        self.size_label = QLabel("")
        self.size_label.setStyleSheet(badge_style.format(color="#0D9488", bg="rgba(13, 148, 136, 0.14)"))
        header.addWidget(self.size_label)
        key_present = bool(os.getenv("OPENAI_API_KEY"))
        key_badge = QLabel(("●  API key detected") if key_present else "●  No API key")
        badge_color = "#0D9488" if key_present else "#E05252"
        badge_bg = "rgba(13, 148, 136, 0.14)" if key_present else "rgba(224, 82, 82, 0.14)"
        key_badge.setStyleSheet(badge_style.format(color=badge_color, bg=badge_bg))
        header.addWidget(key_badge)
        root.addLayout(header)

        self.notice = self._notice_label()
        root.addWidget(self.notice)

        tabs = QTabWidget()
        general_tab, presets_tab = QWidget(), QWidget()
        general = QVBoxLayout(general_tab)
        general.setContentsMargins(18, 16, 18, 16)
        general.setSpacing(8)
        presets_layout = QVBoxLayout(presets_tab)
        presets_layout.setContentsMargins(18, 16, 18, 16)
        presets_layout.setSpacing(8)
        self.history_view = HistoryView()
        tabs.addTab(general_tab, "General")
        tabs.addTab(presets_tab, "Presets")
        tabs.addTab(self.history_view, "History")
        tabs.currentChanged.connect(lambda index: self.history_view.reload() if index == 2 else None)
        root.addWidget(tabs, 1)

        form = form_layout()
        general.addLayout(form)

        self.hotkey = QKeySequenceEdit(QKeySequence(settings.hotkey))
        self.hotkey.setMaximumSequenceLength(4)
        form.addRow("Recording shortcut", self.hotkey)

        self.auto_paste = QCheckBox("Paste automatically after processing")
        self.auto_paste.setChecked(settings.auto_paste)
        form.addRow("Automatic paste", self.auto_paste)

        self.device = QComboBox()
        self.device.setFixedHeight(32)
        self.device.addItem("System default", None)
        for index, name in input_devices():
            self.device.addItem(name, index)
        self.device.setCurrentIndex(max(0, self.device.findData(settings.input_device)))
        form.addRow("Microphone", self.device)

        self.transcription = ModelCombo(TRANSCRIBE_MODELS, settings.transcription_model)
        form.addRow("Transcription model", self.transcription)

        self.transcription_language = QComboBox()
        self.transcription_language.setFixedHeight(32)
        self.transcription_language.addItem("Auto-detect", "auto")
        self.transcription_language.addItem("Hebrew", "he")
        self.transcription_language.addItem("English", "en")
        language_index = self.transcription_language.findData(settings.transcription_language)
        self.transcription_language.setCurrentIndex(max(0, language_index))
        form.addRow("Speech language", self.transcription_language)

        self.dark_mode = QCheckBox("Dark mode")
        self.dark_mode.setChecked(settings.theme == "dark")
        self.dark_mode.toggled.connect(lambda checked: self.setStyleSheet(theme_stylesheet(checked)))
        form.addRow("Theme", self.dark_mode)

        general.addStretch()

        self.preset_list = QListWidget()
        presets_layout.addWidget(self.preset_list, 1)
        self._load_presets()

        root.addLayout(button_row("Save settings", self._save))

        self._update_size_label()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_size_label()

    def _update_size_label(self) -> None:
        self.size_label.setText(f"{self.width()} × {self.height()}")

    def _load_presets(self) -> None:
        populate_reorderable_list(
            self.preset_list,
            self.presets,
            row_factory=lambda preset: EditableRow(
                f"{preset.name}\n{'Microphone' if preset.uses_microphone else 'Clipboard'}"
                f"  ·  {len(preset.nodes)} node{'' if len(preset.nodes) == 1 else 's'}",
                checked=preset.visible_in_chooser,
                checkbox_tooltip="Show in the hold-to-choose menu",
                remove_tooltip="Delete preset",
            ),
            row_height=54,
            on_toggle=self._set_preset_visible,
            on_edit=self._edit_preset,
            on_move=self._move_preset,
            on_remove=self._remove_preset,
            add_label="Add Preset",
            on_add=self._add_preset,
        )

    def _set_preset_visible(self, index: int, checked: bool) -> None:
        self.presets[index].visible_in_chooser = checked

    def _edit_preset(self, index: int) -> None:
        dialog = PresetEditor(self.presets[index], self.dark_mode.isChecked(), self)
        dialog.exec()
        self._load_presets()

    def _move_preset(self, index: int, offset: int) -> None:
        if move_item(self.presets, index, offset):
            self._load_presets()

    def _remove_preset(self, index: int) -> None:
        if len(self.presets) <= 1:
            self._show_notice(self.notice, "At least one preset is required.")
            return
        self.presets.pop(index)
        self._load_presets()

    def _add_preset(self) -> None:
        dialog = NewPresetDialog(self.dark_mode.isChecked(), self)
        if dialog.exec():
            self.presets.append(dialog.value())
            self._load_presets()

    def _save(self) -> None:
        hotkey = self.hotkey.keySequence().toString()
        if not hotkey:
            self._show_notice(self.notice, "Record a shortcut before saving.")
            return
        self.settings = Settings(
            hotkey=hotkey,
            input_device=self.device.currentData(),
            transcription_model=self.transcription.currentData(),
            transcription_language=self.transcription_language.currentData(),
            auto_paste=self.auto_paste.isChecked(),
            theme="dark" if self.dark_mode.isChecked() else "light",
            presets=self.presets,
        )
        self.settings_saved.emit(self.settings)
        self.accept()
