from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QTextEdit, QVBoxLayout

from ..config import PipelineNode
from .common import ThemedDialog, button_row, form_layout
from .models import TEXT_MODELS, ModelCombo


class NodeEditor(ThemedDialog):
    def __init__(self, node: PipelineNode | None = None, dark: bool = False, parent=None) -> None:
        super().__init__("Pipeline node", (300, 360), (380, 430), dark, parent)
        node = node or PipelineNode("New node", "Transform the input.")
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        form = form_layout()
        layout.addLayout(form)

        self.name = QLineEdit(node.name)
        form.addRow("Node name", self.name)

        self.model = ModelCombo(TEXT_MODELS, node.model)
        form.addRow("Model", self.model)

        self.reasoning = QComboBox()
        self.reasoning.setFixedHeight(32)
        for effort in ("none", "low", "medium", "high"):
            self.reasoning.addItem(effort.title(), effort)
        self.reasoning.setCurrentIndex(max(0, self.reasoning.findData(node.reasoning_effort)))
        form.addRow("Reasoning effort", self.reasoning)

        layout.addWidget(QLabel("Instructions"))
        self.prompt = QTextEdit(node.prompt)
        layout.addWidget(self.prompt, 1)

        self.error_label = self._notice_label()
        layout.addWidget(self.error_label)

        layout.addLayout(button_row("Save node", self._save, self.reject))

    def _save(self) -> None:
        if not self.name.text().strip() or not self.prompt.toPlainText().strip():
            self._show_notice(self.error_label, "Name and instructions are required.")
            return
        self.accept()

    def value(self, enabled: bool = True) -> PipelineNode:
        return PipelineNode(self.name.text().strip(), self.prompt.toPlainText().strip(), enabled, self.model.currentData(), self.reasoning.currentData())
