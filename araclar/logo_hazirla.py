"""Eagle Office logosundan kurulum görsellerini üretir.

Kullanım:  .venv\\Scripts\\python.exe araclar\\logo_hazirla.py <logo.png | logo.svg>

Üretilenler (kurulum\\gorsel\\): eagle-office.ico (16-256 px), sihirbaz-buyuk.bmp (164×314), sihirbaz-kucuk.bmp (55×55),
eagle-office-128.png; ayrıca sozcuk\eagle-office-logo.png (Hakkında penceresi). kurulum\\eagle-office.iss bu dosyaları varsa kullanır, yoksa Sözcük simgesine döner.
Logo kare olmak zorunda değildir; oranı korunarak ortalanır. Saydam arka planlı PNG önerilir.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ikon_uret import write_ico  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "kurulum" / "gorsel"
SIZES = [256, 128, 64, 48, 32, 16]
SUITE_NAME = "Eagle Office"
TEXT_COLOR = "#242424"


def load_logo(path):
    """Logoyu QImage (ARGB32) olarak yükler; SVG ise 1024 px'e çizilir."""
    if path.suffix.lower() == ".svg":
        renderer = QSvgRenderer(str(path))
        size = renderer.defaultSize()
        scale = 1024 / max(size.width(), size.height(), 1)
        image = QImage(round(size.width() * scale), round(size.height() * scale), QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        return image
    image = QImage(str(path))
    if image.isNull():
        raise SystemExit(f"Logo okunamadı: {path}")
    return image.convertToFormat(QImage.Format_ARGB32)


def clean(logo):
    """Arka planı yarı kirli beyaz olan logolarda (JPEG/ekran görüntüsü artığı) açık tonları saf beyaza çeker;
    saydam arka planlı logolara dokunmaz."""
    image = logo.copy()
    for y in range(image.height()):
        for x in range(image.width()):
            c = QColor(image.pixel(x, y))
            if c.alpha() == 255 and min(c.red(), c.green(), c.blue()) >= 225:
                image.setPixelColor(x, y, QColor(255, 255, 255))
    return image


def fit(painter, logo, rect):
    """Logoyu oranını koruyarak rect içine ortalar."""
    scale = min(rect.width() / logo.width(), rect.height() / logo.height())
    width, height = logo.width() * scale, logo.height() * scale
    target = QRectF(rect.x() + (rect.width() - width) / 2, rect.y() + (rect.height() - height) / 2, width, height)
    painter.drawImage(target, logo)


def square(logo, size, padding=0.04, tile=False):
    """Kare görüntü. tile=True: logo beyaz yuvarlak köşeli bir karonun içine konur (koyu görev çubuğunda da okunur)."""
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.Antialiasing)
    if tile:
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), size * 0.18, size * 0.18)
        painter.fillPath(path, QColor("#ffffff"))
        painter.setPen(QColor(0, 0, 0, 40))
        painter.drawPath(path)
        painter.setClipPath(path)
        padding = max(padding, 0.1)
    margin = size * padding
    fit(painter, logo, QRectF(margin, margin, size - 2 * margin, size - 2 * margin))
    painter.end()
    return image


def wizard_large(logo):
    image = QImage(164, 314, QImage.Format_RGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.TextAntialiasing)
    fit(painter, logo, QRectF(12, 70, 140, 140))
    font = QFont("Segoe UI")
    font.setBold(True)
    font.setPixelSize(20)
    painter.setFont(font)
    painter.setPen(QColor(TEXT_COLOR))
    painter.drawText(QRectF(0, 222, 164, 30), Qt.AlignCenter, SUITE_NAME)
    painter.end()
    return image


def wizard_small(logo):
    image = QImage(55, 55, QImage.Format_RGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    fit(painter, logo, QRectF(3, 3, 49, 49))
    painter.end()
    return image


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841 (QPainter/QFont için gerekli)
    path = Path(sys.argv[1])
    if not path.is_file():
        raise SystemExit(f"Dosya yok: {path}")
    logo = clean(load_logo(path))
    OUT.mkdir(parents=True, exist_ok=True)
    write_ico(OUT / "eagle-office.ico", [square(logo, size, tile=True) for size in SIZES])
    wizard_large(logo).save(str(OUT / "sihirbaz-buyuk.bmp"), "BMP")
    wizard_small(logo).save(str(OUT / "sihirbaz-kucuk.bmp"), "BMP")
    square(logo, 128, tile=True).save(str(OUT / "eagle-office-128.png"), "PNG")
    # Hakkında penceresi için (uygulamayla birlikte paketlenir); saydamlık gerekmez, pencere zemini beyaz
    app_logo = logo.scaledToWidth(360, Qt.SmoothTransformation)
    app_logo.save(str(ROOT / "sozcuk" / "eagle-office-logo.png"), "PNG")
    print("sozcuk/eagle-office-logo.png")
    for item in sorted(OUT.iterdir()):
        print(f"{item.relative_to(ROOT)}  ({item.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
