from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QWidget,
)

from .theme import _icon_button, theme_stylesheet


def _dashed_add_row(list_widget: QListWidget, label: str, height: int, callback) -> None:
    """Append a dashed '+ <label>' row at the bottom of a QListWidget, used by both
    the node list and the preset list so their "add" affordance stays identical."""
    item = QListWidgetItem()
    item.setSizeHint(QSize(0, height))
    item.setFlags(Qt.ItemFlag.NoItemFlags)
    button = QPushButton(f"+  {label}")
    button.setStyleSheet(
        "QPushButton { text-align: center; border: 1.5px dashed rgba(130, 150, 148, 0.55); "
        "border-radius: 9px; background: transparent; font-weight: 600; }"
        "QPushButton:hover { border-color: #58BDB1; color: #0D9488; }"
    )
    button.clicked.connect(callback)
    list_widget.addItem(item)
    list_widget.setItemWidget(item, button)


def move_item(items: list, index: int, offset: int) -> bool:
    """Swap items[index] with its neighbour `offset` away in place.

    Returns False (no-op) if the target position is out of range, so callers
    can skip re-rendering their list when nothing actually moved.
    """
    target = index + offset
    if target < 0 or target >= len(items):
        return False
    items[index], items[target] = items[target], items[index]
    return True


def populate_reorderable_list(
    list_widget: QListWidget,
    items: list,
    row_factory,
    row_height: int,
    on_toggle,
    on_edit,
    on_move,
    on_remove,
    add_label: str,
    on_add,
    pinned_widget: QWidget | None = None,
    pinned_height: int = 44,
) -> None:
    """Fill `list_widget` with one row per item (built by `row_factory`, an
    EditableRow) plus a trailing dashed "add" row. Shared by the node list
    (PresetEditor) and the preset list (SettingsDialog) since both are the
    same interaction: checkbox + reorder/remove + double-click edit + add.
    """
    list_widget.clear()
    if pinned_widget is not None:
        pinned = QListWidgetItem()
        pinned.setSizeHint(QSize(0, pinned_height))
        pinned.setFlags(Qt.ItemFlag.NoItemFlags)
        list_widget.addItem(pinned)
        list_widget.setItemWidget(pinned, pinned_widget)
    for index, entry in enumerate(items):
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, row_height))
        row = row_factory(entry)
        row.toggled.connect(lambda checked, i=index: on_toggle(i, checked))
        row.edit_requested.connect(lambda i=index: on_edit(i))
        row.move_up_requested.connect(lambda i=index: on_move(i, -1))
        row.move_down_requested.connect(lambda i=index: on_move(i, 1))
        row.remove_requested.connect(lambda i=index: on_remove(i))
        list_widget.addItem(item)
        list_widget.setItemWidget(item, row)
    _dashed_add_row(list_widget, add_label, 44, on_add)


class EditableRow(QWidget):
    """A checkbox + two-line label list row with reorder/remove actions
    revealed on hover, and double-click to edit. Used for both pipeline
    nodes and presets — the two lists share an identical interaction model,
    so this is the single widget behind both instead of two near-duplicates.
    """

    toggled = Signal(bool)
    edit_requested = Signal()
    move_up_requested = Signal()
    move_down_requested = Signal()
    remove_requested = Signal()

    def __init__(
        self,
        label_text: str,
        checked: bool,
        checkbox_tooltip: str = "",
        remove_tooltip: str = "Remove",
        tooltip: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        if checkbox_tooltip:
            self.checkbox.setToolTip(checkbox_tooltip)
        self.checkbox.toggled.connect(self.toggled)
        layout.addWidget(self.checkbox)

        label = QLabel(label_text)
        if tooltip:
            label.setToolTip(tooltip)
        layout.addWidget(label, 1)

        self.actions = QWidget()
        actions_layout = QHBoxLayout(self.actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)
        up = _icon_button("up", "Move up", size=28, icon_size=13)
        up.clicked.connect(self.move_up_requested)
        down = _icon_button("down", "Move down", size=28, icon_size=13)
        down.clicked.connect(self.move_down_requested)
        remove = _icon_button("trash", remove_tooltip, color="#E05252", size=28, icon_size=13)
        remove.clicked.connect(self.remove_requested)
        actions_layout.addWidget(up)
        actions_layout.addWidget(down)
        actions_layout.addWidget(remove)
        layout.addWidget(self.actions)
        self.actions.setVisible(False)

    def enterEvent(self, event) -> None:
        self.actions.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.actions.setVisible(False)
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.edit_requested.emit()
        super().mouseDoubleClickEvent(event)


def form_layout() -> QFormLayout:
    """The column convention shared by NodeEditor, PresetEditor and
    SettingsDialog's General tab: label column left of a fixed-spacing
    field column."""
    form = QFormLayout()
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
    form.setHorizontalSpacing(16)
    form.setVerticalSpacing(10)
    return form


def button_row(primary_text: str, on_primary, on_cancel=None, primary_object_name: str = "primary") -> QHBoxLayout:
    """A right-aligned Cancel/primary button pair (Cancel omitted if
    `on_cancel` isn't given), shared by every dialog's footer."""
    row = QHBoxLayout()
    row.addStretch()
    if on_cancel is not None:
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(on_cancel)
        row.addWidget(cancel)
    primary = QPushButton(primary_text)
    primary.setObjectName(primary_object_name)
    primary.clicked.connect(on_primary)
    row.addWidget(primary)
    return row


class ThemedDialog(QDialog):
    """Base for the app's dialogs: applies the shared stylesheet/sizing and
    owns a reusable red validation/notice label, so each dialog doesn't
    reimplement the same setup and styling by hand."""

    def __init__(self, title: str, min_size: tuple[int, int], size: tuple[int, int], dark: bool, parent=None) -> None:
        super().__init__(parent)
        self.dark = dark
        self.setWindowTitle(title)
        self.setMinimumSize(*min_size)
        self.resize(*size)
        self.setStyleSheet(theme_stylesheet(dark))

    def _notice_label(self) -> QLabel:
        label = QLabel("")
        label.setWordWrap(True)
        label.setStyleSheet("color: #E05252; font-weight: 600;")
        label.hide()
        return label

    @staticmethod
    def _show_notice(label: QLabel, message: str) -> None:
        label.setText(message)
        label.show()
