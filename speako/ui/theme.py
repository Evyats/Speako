from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QPushButton


def theme_stylesheet(dark: bool) -> str:
    if dark:
        bg, card, text, muted, border, field, hover = "#0B1517", "#101F22", "#E8F5F3", "#9BB7B3", "#294247", "#14272B", "#193238"
    else:
        bg, card, text, muted, border, field, hover = "#F4F8F7", "#FFFFFF", "#123E3A", "#58726F", "#C8DEDA", "#FFFFFF", "#E9F5F3"
    return f"""
        QDialog {{ background: {bg}; }}
        QLabel {{ color: {text}; font: 13px 'Segoe UI'; }}
        QLabel#muted {{ color: {muted}; }}
        QLineEdit, QKeySequenceEdit, QComboBox, QTextEdit, QListWidget, QLabel#historyBody {{
            background: {field}; color: {text}; border: 1px solid {border};
            border-radius: 9px; padding: 8px; selection-background-color: #0D9488;
        }}
        QLineEdit:focus, QKeySequenceEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus {{
            border: 2px solid #14B8A6; padding: 7px;
        }}
        QComboBox {{ min-height: 28px; max-height: 30px; padding: 1px 9px; }}
        QComboBox::drop-down {{ width: 30px; border: none; }}
        QComboBox::down-arrow {{ image: none; width: 0; height: 0; }}
        QComboBox QAbstractItemView {{
            background: {card}; color: {text}; border: 1px solid {border};
            border-radius: 9px; outline: 0; padding: 5px;
            selection-background-color: {hover}; selection-color: {text};
        }}
        QListWidget::item {{ border-radius: 8px; padding: 5px; }}
        QListWidget::item:selected {{ background: {hover}; color: {text}; }}
        QPushButton {{
            min-height: 36px; padding: 0 14px; border: 1px solid {border};
            border-radius: 9px; background: {card}; color: {text}; font: 600 12px 'Segoe UI';
        }}
        QPushButton:hover {{ background: {hover}; border-color: #58BDB1; }}
        QPushButton:focus {{ border: 2px solid #14B8A6; }}
        QPushButton#primary {{ background: #0D9488; color: white; border: none; }}
        QPushButton#primary:hover {{ background: #0B8278; }}
        QPushButton#danger {{ color: #E05252; }}
        QPushButton:disabled {{ color: {muted}; background: {bg}; }}
        QCheckBox {{ color: {text}; spacing: 10px; }}
        QCheckBox::indicator {{
            width: 18px; height: 18px; border-radius: 9px;
            border: 1.5px solid {border}; background: {field};
        }}
        QCheckBox::indicator:hover {{ border-color: #58BDB1; }}
        QCheckBox::indicator:checked {{ background: #0D9488; border-color: #0D9488; }}
        QCheckBox::indicator:checked:hover {{ background: #0B8278; border-color: #0B8278; }}
        QTabWidget::pane {{ border: 1px solid {border}; border-radius: 10px; background: {card}; top: -1px; }}
        QTabBar::tab {{ color: {muted}; background: transparent; padding: 9px 16px; border-bottom: 2px solid transparent; font-weight: 600; }}
        QTabBar::tab:selected {{ color: {text}; border-bottom-color: #0D9488; }}
        QScrollArea {{ border: none; background: transparent; }}
        QWidget#historyContent {{ background: {card}; }}
    """


def app_icon() -> QPixmap:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0D9488"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 16, 16)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(29)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")
    painter.end()
    return pixmap


def _draw_icon(kind: str, color: QColor, size: int = 16) -> QIcon:
    """Draw a small vector glyph ourselves instead of relying on Unicode/emoji font coverage."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    if kind == "plus":
        pen = QPen(color, 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        mid, arm = size / 2, size * 0.3
        painter.drawLine(QPointF(mid - arm, mid), QPointF(mid + arm, mid))
        painter.drawLine(QPointF(mid, mid - arm), QPointF(mid, mid + arm))
    elif kind == "pencil":
        painter.save()
        painter.translate(size * 0.18, size * 0.84)
        painter.rotate(-45)
        painter.drawRoundedRect(QRectF(0, -1.8, size * 0.62, 3.6), 1.8, 1.8)
        painter.drawPolygon(QPolygonF([
            QPointF(size * 0.62, -2.6), QPointF(size * 0.62, 2.6), QPointF(size * 0.62 + 5, 0),
        ]))
        painter.restore()
    elif kind == "trash":
        painter.drawRoundedRect(QRectF(size * 0.40, size * 0.12, size * 0.20, size * 0.08), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(size * 0.18, size * 0.24, size * 0.64, size * 0.09), 2, 2)
        painter.drawPolygon(QPolygonF([
            QPointF(size * 0.27, size * 0.38), QPointF(size * 0.73, size * 0.38),
            QPointF(size * 0.65, size * 0.88), QPointF(size * 0.35, size * 0.88),
        ]))
    elif kind == "up":
        painter.drawPolygon(QPolygonF([
            QPointF(size * 0.5, size * 0.24), QPointF(size * 0.22, size * 0.68), QPointF(size * 0.78, size * 0.68),
        ]))
    elif kind == "down":
        painter.drawPolygon(QPolygonF([
            QPointF(size * 0.5, size * 0.76), QPointF(size * 0.22, size * 0.32), QPointF(size * 0.78, size * 0.32),
        ]))
    elif kind == "mic":
        head_w = size * 0.26
        painter.drawRoundedRect(QRectF(size * 0.5 - head_w / 2, size * 0.08, head_w, size * 0.44), head_w / 2, head_w / 2)
        mic_pen = QPen(color, 1.6)
        mic_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(mic_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(size * 0.22, size * 0.30, size * 0.56, size * 0.46), 200 * 16, 140 * 16)
        painter.drawLine(QPointF(size * 0.5, size * 0.76), QPointF(size * 0.5, size * 0.88))
        painter.drawLine(QPointF(size * 0.32, size * 0.88), QPointF(size * 0.68, size * 0.88))
    elif kind == "clipboard":
        painter.drawRoundedRect(QRectF(size * 0.22, size * 0.18, size * 0.56, size * 0.68), 3, 3)
        painter.drawRoundedRect(QRectF(size * 0.38, size * 0.10, size * 0.24, size * 0.14), 3, 3)
    painter.end()
    return QIcon(pixmap)


def _icon_button(kind: str, tooltip: str, color: str = "#6B8C88", size: int = 34, icon_size: int = 16) -> QPushButton:
    button = QPushButton()
    button.setIcon(_draw_icon(kind, QColor(color), icon_size))
    button.setIconSize(QSize(icon_size, icon_size))
    button.setToolTip(tooltip)
    button.setFixedSize(size, size)
    # Override the global QPushButton min-height/padding — otherwise they fight
    # this fixed small size and clip the icon (zero room left for content).
    button.setStyleSheet("QPushButton { padding: 0; min-width: 0; min-height: 0; }")
    return button
