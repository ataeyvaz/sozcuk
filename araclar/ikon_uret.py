"""Uygulama ikonunu (sozcuk.ico) üretir: Word mavisi bir sayfa üzerinde "S".

Kullanım: .venv\\Scripts\\python.exe araclar\\ikon_uret.py
Çok boyutlu ICO dosyası yazılır (16-256 px), böylece görev çubuğunda ve masaüstünde keskin görünür.
"""

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SIZES = [256, 128, 64, 48, 32, 16]
TARGET = Path(__file__).resolve().parent.parent / "sozcuk.ico"
ACCENT = "#185abd"
PAPER = "#ffffff"


def render(size):
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    unit = size / 32

    # yuvarlatılmış köşeli sayfa
    page = QRectF(4 * unit, 2 * unit, 24 * unit, 28 * unit)
    path = QPainterPath()
    path.addRoundedRect(page, 3 * unit, 3 * unit)
    painter.fillPath(path, QColor(PAPER))
    painter.setPen(QColor(0, 0, 0, 40))
    painter.drawPath(path)

    # mavi şerit: sayfanın içine kırpılır (köşeler sayfayla aynı yuvarlaklıkta kalsın)
    painter.save()
    painter.setClipPath(path)
    painter.fillRect(QRectF(4 * unit, 2 * unit, 24 * unit, 8 * unit), QColor(ACCENT))
    if size >= 48:   # küçük boyutlarda satırlar lekeye dönüşüyor
        painter.setPen(QColor("#dbe3f2"))
        for index in range(3):
            y = (23 + index * 2.5) * unit
            painter.drawLine(QPointF(8 * unit, y), QPointF(24 * unit, y))
    painter.restore()

    # "S"
    font = QFont("Segoe UI")
    font.setBold(True)
    font.setPixelSize(int(16 * unit))
    painter.setFont(font)
    painter.setPen(QColor(ACCENT))
    painter.drawText(QRectF(4 * unit, 10 * unit, 24 * unit, 12 * unit), Qt.AlignCenter, "S")

    painter.end()
    return image


def png_bytes(image):
    data = QByteArray()
    buffer = QBuffer(data)          # QByteArray'i ayrı tutmak gerekiyor: geçici nesne silinince çöküyor
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def write_ico(path, images):
    """PNG gömülü çok boyutlu ICO (Vista ve sonrası)."""
    entries, data, offset = [], [], 6 + 16 * len(images)
    for image in images:
        blob = png_bytes(image)
        size = image.width()
        entries.append(struct.pack("<BBBBHHII", 0 if size >= 256 else size, 0 if size >= 256 else size,
                                   0, 0, 1, 32, len(blob), offset))
        data.append(blob)
        offset += len(blob)
    with open(path, "wb") as handle:
        handle.write(struct.pack("<HHH", 0, 1, len(images)))
        for entry in entries:
            handle.write(entry)
        for blob in data:
            handle.write(blob)


app = None


def main():
    global app
    app = QApplication.instance() or QApplication(sys.argv)   # QPainter/QFont için gerekli
    write_ico(TARGET, [render(size) for size in SIZES])
    print(f"{TARGET} ({TARGET.stat().st_size / 1024:.0f} KB, {len(SIZES)} boyut)")


if __name__ == "__main__":
    main()
