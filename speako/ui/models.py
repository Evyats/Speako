from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPalette
from PySide6.QtWidgets import QApplication, QComboBox, QStyledItemDelegate, QStyleOptionViewItem

MODEL_ROLE = Qt.ItemDataRole.UserRole
STATS_ROLE = Qt.ItemDataRole.UserRole + 1
RECOMMENDED_ROLE = Qt.ItemDataRole.UserRole + 2

TEXT_MODELS = [
    ("gpt-5.6-luna", (5, 3, 1), True),
    ("gpt-5.6-terra", (4, 4, 2), False),
    ("gpt-5.6-sol", (2, 5, 5), False),
]
TRANSCRIBE_MODELS = [
    ("gpt-4o-mini-transcribe", (5, 4, 1), True),
    ("gpt-4o-transcribe", (4, 5, 2), False),
]


class ModelDelegate(QStyledItemDelegate):
    """Paint model choices with real meters instead of text-bar characters."""

    def sizeHint(self, option, index) -> QSize:
        return QSize(340, 52)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        selected = bool(option.state & option.state.State_Selected)
        palette = option.widget.palette() if option.widget else QApplication.palette()
        bg = palette.color(QPalette.ColorRole.Highlight if selected else QPalette.ColorRole.Base)
        fg = palette.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text)
        painter.fillRect(option.rect.adjusted(2, 2, -2, -2), bg)
        rect = option.rect.adjusted(14, 4, -12, -4)
        name = index.data(MODEL_ROLE)
        recommended = bool(index.data(RECOMMENDED_ROLE))
        stats = index.data(STATS_ROLE) or (3, 3, 3)
        painter.setPen(fg)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(rect.x(), rect.y(), 190, 22), Qt.AlignmentFlag.AlignVCenter, name)
        if recommended:
            badge_font = QFont(font)
            badge_font.setBold(True)
            badge_font.setPointSize(8)
            badge_width = QFontMetrics(badge_font).horizontalAdvance("RECOMMENDED") + 20
            badge = QRect(rect.right() - badge_width, rect.y() + 1, badge_width, 20)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#0D9488"))
            painter.drawRoundedRect(badge, 8, 8)
            painter.setPen(QColor("white"))
            painter.setFont(badge_font)
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "RECOMMENDED")
        labels = (("Speed", stats[0], False), ("Quality", stats[1], False), ("Cost", stats[2], True))
        small = QFont(font)
        small.setBold(False)
        small.setPointSize(8)
        painter.setFont(small)
        metrics = QFontMetrics(small)
        for col, (label, value, costly) in enumerate(labels):
            x = rect.x() + col * 104
            y = rect.y() + 29
            painter.setPen(fg)
            painter.drawText(x, y + 9, label)
            bars_x = x + metrics.horizontalAdvance(label) + 8
            for bar in range(5):
                color = QColor("#E67E46") if costly else QColor("#14B8A6")
                if bar >= value:
                    color.setAlpha(45)
                painter.fillRect(QRect(bars_x + bar * 10, y + 2, 8, 8), color)
        painter.restore()


class ModelCombo(QComboBox):
    def __init__(self, models, current: str, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setItemDelegate(ModelDelegate(self))
        self.view().setMinimumWidth(340)
        for name, stats, recommended in models:
            self.addItem(name + ("  ·  Recommended" if recommended else ""), name)
            row = self.count() - 1
            self.setItemData(row, stats, STATS_ROLE)
            self.setItemData(row, recommended, RECOMMENDED_ROLE)
            self.setItemData(row, name, MODEL_ROLE)
        self.setCurrentIndex(max(0, self.findData(current)))
