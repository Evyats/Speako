from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..history import load_recent_recordings

RECORDING_LABELS = ("Most recent", "2nd most recent", "3rd most recent")


class HistoryView(QWidget):
    """A read-only explanation of one of the last few recordings, picked via dropdown."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        self.combo = QComboBox()
        self.combo.setFixedHeight(32)
        self.combo.currentIndexChanged.connect(self._render_selected)
        layout.addWidget(self.combo)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QWidget()
        container.setObjectName("historyContent")
        self.content = QVBoxLayout(container)
        self.content.setContentsMargins(0, 8, 0, 0)
        self.content.setSpacing(10)
        self.scroll.setWidget(container)
        layout.addWidget(self.scroll, 1)

        self._records: list[dict] = []
        self.reload()

    def _clear(self) -> None:
        while self.content.count():
            item = self.content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _section(self, title: str, body: str) -> None:
        heading = QLabel(title)
        heading.setStyleSheet("font: 700 13px 'Segoe UI'; margin-top: 6px;")
        self.content.addWidget(heading)
        text = QLabel(body or "—")
        text.setObjectName("historyBody")
        text.setWordWrap(True)
        self.content.addWidget(text)

    def reload(self) -> None:
        self._records = load_recent_recordings()
        current = self.combo.currentIndex()
        self.combo.blockSignals(True)
        self.combo.clear()
        for index in range(len(self._records)):
            label = RECORDING_LABELS[index] if index < len(RECORDING_LABELS) else f"{index + 1} recordings ago"
            self.combo.addItem(label)
        self.combo.setCurrentIndex(max(0, min(current, len(self._records) - 1)))
        self.combo.blockSignals(False)
        self.combo.setVisible(bool(self._records))
        self._render_selected()

    def _render_selected(self) -> None:
        self._clear()
        if not self._records:
            empty = QLabel("No recording has completed yet. Your latest workflow details will appear here.")
            empty.setWordWrap(True)
            empty.setObjectName("muted")
            self.content.addWidget(empty)
            self.content.addStretch()
            return
        index = max(0, min(self.combo.currentIndex(), len(self._records) - 1))
        record = self._records[index]
        if record.get("error"):
            self._section("Error", record["error"])
        input_heading = "Clipboard text" if record.get("metadata", {}).get("input_source") == "clipboard" else "Transcription"
        self._section(input_heading, record.get("transcription", ""))
        for step in record.get("steps", []):
            if step.get("type") in ("transcription", "clipboard"):
                continue
            self._section(step.get("name", "Workflow step"), step.get("output", ""))
        self.content.addStretch()
