from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QFontMetrics
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..config import Preset


class StatusPopup(QWidget):
    """A single-line status pill, always sized exactly to its (elided) text.

    The size is computed from font metrics and forced with setFixedSize() on
    every call, rather than relying on QWidget.adjustSize()/sizeHint() — a
    frameless always-on-top tool window does not reliably shrink back down
    via adjustSize() after showing a longer message, which used to leave
    stale trailing space. Margins are defined once as class constants and
    reused for both the layout and the size math, so they can't drift apart.
    """

    CARD_MARGIN_LEFT = 14
    CARD_MARGIN_RIGHT = 22
    CARD_MARGIN_V = 12
    DOT_WIDTH = 14
    SPACING = 8
    SCREEN_MARGIN = 28

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("popupCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(self.CARD_MARGIN_LEFT, self.CARD_MARGIN_V, self.CARD_MARGIN_RIGHT, self.CARD_MARGIN_V)
        card_layout.setSpacing(self.SPACING)
        self.dot = QLabel("●")
        self.dot.setFixedWidth(self.DOT_WIDTH)
        self.dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("Listening…")
        self.label.setWordWrap(False)
        card_layout.addWidget(self.dot)
        card_layout.addWidget(self.label)
        layout.addWidget(card)
        self.setStyleSheet("#popupCard { background: #102F31; border: 1px solid #285356; border-radius: 14px; } QLabel { color: white; font: 600 14px 'Segoe UI'; }")

    def show_status(self, text: str, recording: bool = False, auto_hide_ms: int | None = None) -> None:
        self._hide_timer.stop()
        self.dot.setStyleSheet(f"color: {'#FB923C' if recording else '#5EEAD4'}")

        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        chrome = self.CARD_MARGIN_LEFT + self.CARD_MARGIN_RIGHT + self.DOT_WIDTH + self.SPACING
        max_card_width = max(240, area.width() - self.SCREEN_MARGIN * 2)

        metrics = QFontMetrics(self.label.font())
        elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, max_card_width - chrome)
        self.label.setText(elided)

        card_width = chrome + metrics.horizontalAdvance(elided)
        card_height = self.CARD_MARGIN_V * 2 + max(metrics.height(), self.DOT_WIDTH)
        self.setFixedSize(card_width, card_height)

        x = area.x() + area.width() - card_width - self.SCREEN_MARGIN
        y = area.y() + area.height() - card_height - self.SCREEN_MARGIN
        self.move(max(area.x() + self.SCREEN_MARGIN, x), max(area.y() + self.SCREEN_MARGIN, y))
        self.show()
        self.raise_()
        if auto_hide_ms is not None:
            self._hide_timer.start(auto_hide_ms)

    def show_error(self, message: str, auto_hide_ms: int | None = None) -> None:
        self.show_status(f"Error · {message}", auto_hide_ms=auto_hide_ms)
        self.dot.setStyleSheet("color: #F87171")


class PresetChooser(QWidget):
    selected = Signal(int)

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def show_presets(self, presets: list[Preset], selected: int = 0, above: QWidget | None = None) -> None:
        already_visible = self.isVisible()
        while self.layout.count():
            child = self.layout.takeAt(0).widget()
            if child:
                child.deleteLater()
        card = QFrame()
        card.setObjectName("chooser")
        box = QVBoxLayout(card)
        box.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Hold the shortcut · ↑↓ or click to choose")
        title.setObjectName("chooserTitle")
        box.addWidget(title)
        for index, preset in enumerate(presets):
            if not preset.visible_in_chooser:
                continue
            button = QPushButton(("✓  " if index == selected else "    ") + preset.name + ("  ·  Clipboard" if not preset.uses_microphone else ""))
            button.setProperty("selected", index == selected)
            button.clicked.connect(lambda checked=False, i=index: self.selected.emit(i))
            box.addWidget(button)
        self.layout.addWidget(card)
        self.setStyleSheet("""
            #chooser { background: #102F31; border: 1px solid #285356; border-radius: 16px; }
            #chooserTitle { color: #A9C7C4; font: 12px 'Segoe UI'; padding: 2px 6px 6px; }
            QPushButton { text-align: left; min-width: 280px; min-height: 38px; padding: 0 12px; color: white; background: transparent; border: none; border-radius: 8px; font: 600 13px 'Segoe UI'; }
            QPushButton:hover, QPushButton[selected="true"] { background: #1B4B4B; }
        """)
        self.adjustSize()
        if not already_visible:
            # Only place the window on its first appearance for this hold gesture;
            # re-selecting a preset (arrow keys or click) must never move it.
            stack_above = above is not None and above.isVisible()
            screen = (above.screen() if stack_above else None) or QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
            area = screen.availableGeometry()
            margin = 20
            x = max(area.left() + margin, area.right() - self.width() - margin + 1)
            if stack_above:
                y = above.frameGeometry().y() - self.height() - 12
            else:
                y = area.bottom() - self.height() - margin
            y = max(area.top() + margin, y)
            self.move(x, y)
        self.show()
        self.raise_()
