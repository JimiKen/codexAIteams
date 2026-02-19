from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QLinearGradient, QPainter, QPen


def icon_output_path(project_root: Path) -> Path:
    return project_root / "assets" / "app.ico"


def ensure_app_icon(project_root: Path) -> Path:
    out_path = icon_output_path(project_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)

    bg = QLinearGradient(0, 0, 256, 256)
    bg.setColorAt(0.0, QColor("#06130E"))
    bg.setColorAt(1.0, QColor("#0F2620"))
    painter.setBrush(bg)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(12, 12, 232, 232, 56, 56)

    painter.setBrush(QColor("#1ED79A"))
    painter.drawRoundedRect(30, 30, 196, 196, 44, 44)

    painter.setBrush(QColor("#0B1B16"))
    painter.drawRoundedRect(50, 50, 156, 156, 34, 34)

    painter.setPen(QPen(QColor("#66FFD2"), 8))
    painter.drawRoundedRect(62, 62, 132, 132, 28, 28)

    painter.setPen(QPen(QColor("#66FFD2"), 7))
    painter.drawRoundedRect(72, 72, 112, 112, 24, 24)

    title_font = QFont("Segoe UI", 62, QFont.Bold)
    painter.setFont(title_font)
    painter.setPen(QColor("#E5FFF6"))
    painter.drawText(0, 26, 256, 152, Qt.AlignCenter, "AI")

    sub_font = QFont("Segoe UI", 24, QFont.Bold)
    painter.setFont(sub_font)
    painter.setPen(QColor("#8EFFE0"))
    painter.drawText(0, 160, 256, 74, Qt.AlignCenter, "TEAMS")
    painter.end()

    if not image.save(str(out_path), "ICO"):
        raise RuntimeError(f"failed to write icon file: {out_path}")
    return out_path


def load_app_icon(project_root: Path) -> QIcon:
    path = ensure_app_icon(project_root)
    return QIcon(str(path))
