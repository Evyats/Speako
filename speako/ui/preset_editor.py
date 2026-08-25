from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QVBoxLayout, QWidget

from ..config import Preset
from .common import EditableRow, ThemedDialog, button_row, form_layout, move_item, populate_reorderable_list
from .node_editor import NodeEditor
from .theme import _draw_icon


def _pinned_source_row(preset: Preset) -> QWidget:
    """The fixed, non-interactive first row of a preset's node list, showing
    where its input comes from — this can't be a real node the API can run
    against, since transcription needs an audio file rather than text input,
    so it's a display-only indicator instead of an actual PipelineNode."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(10, 4, 6, 4)
    layout.setSpacing(10)
    if preset.uses_microphone:
        icon_kind, text = "mic", "Record & transcribe microphone audio"
    else:
        icon_kind, text = "clipboard", "Use clipboard text as input"
    icon = QLabel()
    icon.setPixmap(_draw_icon(icon_kind, QColor("#0D9488"), 16).pixmap(16, 16))
    layout.addWidget(icon)
    label = QLabel(text)
    label.setStyleSheet("font: 600 13px 'Segoe UI';")
    layout.addWidget(label, 1)
    fixed = QLabel("FIXED")
    fixed.setStyleSheet(
        "color: white; background: #0D9488; border-radius: 8px; "
        "padding: 2px 8px; font: 700 9px 'Segoe UI';"
    )
    layout.addWidget(fixed)
    return row


class NewPresetDialog(ThemedDialog):
    """Just a name — new presets start microphone-based. Whether a preset
    uses the microphone or the clipboard is changed later, in PresetEditor,
    so presets aren't locked into that choice at creation time."""

    def __init__(self, dark: bool = False, parent=None) -> None:
        super().__init__("New preset", (280, 160), (320, 170), dark, parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Preset name"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        layout.addStretch(1)

        self.error_label = self._notice_label()
        layout.addWidget(self.error_label)

        layout.addLayout(button_row("Create", self._create, self.reject))

    def _create(self) -> None:
        if not self.name_edit.text().strip():
            self._show_notice(self.error_label, "Name is required.")
            return
        self.accept()

    def value(self) -> Preset:
        return Preset(self.name_edit.text().strip(), [])


class PresetEditor(ThemedDialog):
    """A separate window for editing one preset's name and node pipeline —
    the node list here is exactly the same list used to be embedded in the
    Presets tab (EditableRow rows, hover actions, double-click to edit, dashed
    add row)."""

    def __init__(self, preset: Preset, dark: bool = False, parent=None) -> None:
        super().__init__(f"Edit preset · {preset.name}", (320, 380), (420, 480), dark, parent)
        self.preset = preset

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        form = form_layout()
        layout.addLayout(form)

        self.name_edit = QLineEdit(preset.name)
        self.name_edit.editingFinished.connect(self._apply_name)
        form.addRow("Preset name", self.name_edit)

        self.mic_checkbox = QCheckBox("Record from microphone")
        self.mic_checkbox.setChecked(preset.uses_microphone)
        self.mic_checkbox.toggled.connect(self._apply_mic_mode)
        form.addRow("Input source", self.mic_checkbox)

        layout.addWidget(QLabel("Nodes"))
        self.nodes = QListWidget()
        layout.addWidget(self.nodes, 1)
        self._load_nodes()

        layout.addLayout(button_row("Done", self.accept))

    def _apply_name(self) -> None:
        name = self.name_edit.text().strip()
        if name:
            self.preset.name = name
            self.setWindowTitle(f"Edit preset · {name}")
        else:
            self.name_edit.setText(self.preset.name)

    def _apply_mic_mode(self, checked: bool) -> None:
        self.preset.uses_microphone = checked
        self._load_nodes()

    def _load_nodes(self) -> None:
        populate_reorderable_list(
            self.nodes,
            self.preset.nodes,
            row_factory=lambda node: EditableRow(
                f"{node.name}\n{node.model}  ·  reasoning {node.reasoning_effort}",
                checked=node.enabled,
                remove_tooltip="Remove node",
                tooltip=node.prompt,
            ),
            row_height=54,
            on_toggle=self._set_enabled,
            on_edit=self._edit_node,
            on_move=self._move_node,
            on_remove=self._remove_node,
            add_label="Add node",
            on_add=self._add_node,
            pinned_widget=_pinned_source_row(self.preset),
        )

    def _set_enabled(self, index: int, checked: bool) -> None:
        self.preset.nodes[index].enabled = checked

    def _add_node(self) -> None:
        dialog = NodeEditor(dark=self.dark, parent=self)
        if dialog.exec():
            self.preset.nodes.append(dialog.value())
            self._load_nodes()

    def _edit_node(self, index: int) -> None:
        nodes = self.preset.nodes
        dialog = NodeEditor(nodes[index], self.dark, self)
        if dialog.exec():
            nodes[index] = dialog.value(nodes[index].enabled)
            self._load_nodes()

    def _move_node(self, index: int, offset: int) -> None:
        if move_item(self.preset.nodes, index, offset):
            self._load_nodes()

    def _remove_node(self, index: int) -> None:
        del self.preset.nodes[index]
        self._load_nodes()
