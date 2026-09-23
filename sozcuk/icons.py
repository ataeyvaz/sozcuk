"""Word (Fluent) tarzı ikonlar.

Keskinlik için:
- Tüm şekiller 20 px ızgarada, 1 px çizgiyle ve piksel merkezlerine (x,5) hizalı çizilir.
- İkon, istenen boyutta doğrudan çizilir (hazır bitmap küçültülmez) — IconEngine.
- Harfler (B, I, U, A…) SVG yolu yerine ipuçlamalı (hinted) gerçek yazı tipiyle çizilir.
"""

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

INK = "#424242"
DISABLED = "#b8b8b8"
GRID = 20

# "text" öğeleri: (metin, piksel boyutu, kalın, italik, (x, y, genişlik, yükseklik) 20'lik ızgarada)
_DOC = "M5.5 2.5H11.5L15.5 6.5V16.5A1 1 0 0 1 14.5 17.5H5.5A1 1 0 0 1 4.5 16.5V3.5A1 1 0 0 1 5.5 2.5Z M11.5 2.5V6.5H15.5"

ICONS = {
    "undo": {"svg": "M7.5 4.5L4.5 7.5L7.5 10.5 M4.5 7.5H12A3.5 3.5 0 0 1 12 14.5H9.5"},
    "redo": {"svg": "M12.5 4.5L15.5 7.5L12.5 10.5 M15.5 7.5H8A3.5 3.5 0 0 0 8 14.5H10.5"},
    "save": {"svg": "M4.5 3.5H13L16.5 7V15.5A1 1 0 0 1 15.5 16.5H4.5A1 1 0 0 1 3.5 15.5V4.5A1 1 0 0 1 4.5 3.5Z"
                    " M6.5 3.5V7.5H12.5V3.5 M6.5 16.5V11.5H13.5V16.5"},
    "new": {"svg": _DOC},
    "open": {"svg": "M2.5 15.5V4.5A1 1 0 0 1 3.5 3.5H7.5L9.5 5.5H15.5A1 1 0 0 1 16.5 6.5V8.5"
                    " M2.5 15.5L4.8 9.1A1 1 0 0 1 5.7 8.5H17.3A.7 .7 0 0 1 17.9 9.4L15.7 15A1 1 0 0 1 14.8 15.5Z"},
    "pdf": {"svg": _DOC + " M7.5 10.5H12.5 M7.5 13.5H12.5"},
    "print": {"svg": "M5.5 7.5V3.5H14.5V7.5 M5.5 14.5H4A1.5 1.5 0 0 1 2.5 13V9A1.5 1.5 0 0 1 4 7.5H16"
                     "A1.5 1.5 0 0 1 17.5 9V13A1.5 1.5 0 0 1 16 14.5H14.5 M5.5 11.5H14.5V17.5H5.5Z"},
    "exit": {"svg": "M8.5 3.5H4.5V16.5H8.5 M12.5 6.5L15.5 9.5L12.5 12.5 M15.5 9.5H7.5"},
    "bold": {"text": [("B", 15, True, False, (0, 1, 20, 17))]},
    "italic": {"text": [("I", 16, False, True, (0, 1, 20, 17))], "font": "Georgia"},
    "underline": {"svg": "M5.5 17.5H14.5", "text": [("U", 14, False, False, (0, 0, 20, 16))]},
    "strike": {"svg": "M2.5 10.5H17.5", "text": [("ab", 13, False, False, (0, 1, 20, 17))]},
    "font_color": {"text": [("A", 14, False, False, (0, -1, 20, 16))], "bar": True},
    "highlight": {"svg": "M12 1.5L16.5 6L10.5 12H6.5V8Z M9.5 4L14 8.5", "bar": True},
    "clear_format": {"svg": "M12.5 11.5L16.5 15.5 M16.5 11.5L12.5 15.5",
                     "text": [("A", 14, False, False, (0, 0, 14, 18))]},
    "grow_font": {"svg": "M13.5 6.5L15.5 4.5L17.5 6.5", "text": [("A", 15, False, False, (0, 1, 14, 18))]},
    "shrink_font": {"svg": "M13.5 4.5L15.5 6.5L17.5 4.5", "text": [("A", 12, False, False, (0, 3, 14, 16))]},
    "add_font": {"svg": "M15.5 2.5V8.5 M12.5 5.5H18.5", "text": [("A", 15, False, False, (0, 1, 14, 18))]},
    "align_left": {"svg": "M3.5 4.5H16.5 M3.5 8.5H11.5 M3.5 12.5H16.5 M3.5 16.5H11.5"},
    "align_center": {"svg": "M3.5 4.5H16.5 M6.5 8.5H13.5 M3.5 12.5H16.5 M6.5 16.5H13.5"},
    "align_right": {"svg": "M3.5 4.5H16.5 M8.5 8.5H16.5 M3.5 12.5H16.5 M8.5 16.5H16.5"},
    "align_justify": {"svg": "M3.5 4.5H16.5 M3.5 8.5H16.5 M3.5 12.5H16.5 M3.5 16.5H16.5"},
    "bullets": {"svg": "M8.5 4.5H17.5 M8.5 9.5H17.5 M8.5 14.5H17.5",
                "dots": [(4.5, 4.5), (4.5, 9.5), (4.5, 14.5)]},
    "numbers": {"svg": "M8.5 4.5H17.5 M8.5 9.5H17.5 M8.5 14.5H17.5",
                "text": [("1", 6, False, False, (1, 1, 6, 7)), ("2", 6, False, False, (1, 6, 6, 7)),
                         ("3", 6, False, False, (1, 11, 6, 7))]},
    "outdent": {"svg": "M3.5 3.5H16.5 M9.5 7.5H16.5 M9.5 11.5H16.5 M3.5 15.5H16.5 M6.5 7L4 9.5L6.5 12"},
    "indent": {"svg": "M3.5 3.5H16.5 M9.5 7.5H16.5 M9.5 11.5H16.5 M3.5 15.5H16.5 M4 7L6.5 9.5L4 12"},
    "line_spacing": {"svg": "M9.5 4.5H16.5 M9.5 9.5H16.5 M9.5 14.5H16.5 M4.5 3.5V16.5"
                           " M2.5 5.5L4.5 3.5L6.5 5.5 M2.5 14.5L4.5 16.5L6.5 14.5"},
    "table": {"svg": "M3.5 3.5H16.5V16.5H3.5Z M3.5 7.5H16.5 M3.5 11.5H16.5 M7.5 3.5V16.5 M11.5 3.5V16.5"},
    "ruler": {"svg": "M2.5 6.5H17.5V13.5H2.5Z M5.5 6.5V9.5 M8.5 6.5V10.5 M11.5 6.5V9.5 M14.5 6.5V10.5"},
    "zoom_out": {"svg": "M5.5 9.5H14.5"},
    "zoom_in": {"svg": "M5.5 9.5H14.5 M9.5 5.5V13.5"},
    "chevron_down": {"svg": "M6 8L10 12L14 8"},
    "chevron_up": {"svg": "M6 12L10 8L14 12"},
    "find": {"svg": "M13.5 13.5L17.5 17.5", "circle": (8.5, 8.5, 6)},
    "replace": {"svg": "M3.5 5.5H11.5 M3.5 5.5L6 3 M3.5 5.5L6 8 M16.5 13.5H8.5 M16.5 13.5L14 11 M16.5 13.5L14 16"},
    "close": {"svg": "M5.5 5.5L14.5 14.5 M14.5 5.5L5.5 14.5"},
    "info": {"svg": "M9.5 9.5V13.5", "circle": (9.5, 9.5, 7), "dots": [(9.5, 6.2)]},
    "cut": {"svg": "M7.2 12.3L14.5 2.5 M12.8 12.3L5.5 2.5", "circles": [(5.5, 14.5, 2.5), (14.5, 14.5, 2.5)]},
    "copy": {"svg": "M7.5 5.5H15.5V17.5H7.5Z M4.5 14.5V2.5H12.5"},
    "paste": {"svg": "M7.5 3.5H4.5V17.5H15.5V3.5H12.5 M7.5 2.5H12.5V5.5H7.5Z"},
    "paste_text": {"svg": "M7.5 3.5H4.5V17.5H15.5V3.5H12.5 M7.5 2.5H12.5V5.5H7.5Z M7.5 9.5H12.5 M10 9.5V14.5"},
    "row_above": {"svg": "M3.5 10.5H16.5V16.5H3.5Z M3.5 13.5H16.5 M10 1.5V7.5 M7 4.5H13"},
    "row_below": {"svg": "M3.5 3.5H16.5V9.5H3.5Z M3.5 6.5H16.5 M10 12.5V18.5 M7 15.5H13"},
    "col_left": {"svg": "M10.5 3.5H16.5V16.5H10.5Z M13.5 3.5V16.5 M1.5 10H7.5 M4.5 7V13"},
    "col_right": {"svg": "M3.5 3.5H9.5V16.5H3.5Z M6.5 3.5V16.5 M12.5 10H18.5 M15.5 7V13"},
    "delete": {"svg": "M3.5 5.5H16.5 M8.5 5.5V3.5H11.5V5.5 M5.5 5.5L6.5 17.5H13.5L14.5 5.5"},
    "merge": {"svg": "M3.5 3.5H16.5V16.5H3.5Z M6 10H14 M11.5 7.5L14 10L11.5 12.5 M8.5 7.5L6 10L8.5 12.5"},
    "split": {"svg": "M3.5 3.5H16.5V16.5H3.5Z M9.5 3.5V16.5"},
    "spell_check": {"svg": "M10.5 15.5L12.5 17.5L17.5 12.5", "text": [("abc", 10, False, False, (0, 1, 20, 11))]},
    "mic": {"svg": "M7.5 4.5A2 2 0 0 1 11.5 4.5V9.5A2 2 0 0 1 7.5 9.5Z M4.5 9.5A5 5 0 0 0 14.5 9.5"
                   " M9.5 14.5V17.5 M6.5 17.5H12.5"},
    # kayıt sırasında: dolu kapsül ve sağ üstte kayıt noktası
    "mic_recording": {"svg": "M4.5 9.5A5 5 0 0 0 14.5 9.5 M9.5 14.5V17.5 M6.5 17.5H12.5",
                      "fills": ["M7.5 4.5A2 2 0 0 1 11.5 4.5V9.5A2 2 0 0 1 7.5 9.5Z"],
                      "dots": [(16, 4)]},
    # görseller
    "image": {"svg": "M2.5 3.5H17.5V16.5H2.5Z M2.5 14.5L7.5 9.5L11.5 13.5L13.5 11.5L17.5 15.5",
              "circles": [(13.5, 7.5, 1.5)]},
    "image_file": {"svg": "M4.5 2.5H12.5L15.5 5.5V17.5H4.5Z M12.5 2.5V5.5H15.5 M4.5 15.5L8.5 11.5L11.5 14.5L15.5 10.5"},
    "crop": {"svg": "M5.5 1.5V14.5H18.5 M1.5 5.5H14.5V18.5"},
    "crop_reset": {"svg": "M5.5 1.5V14.5H18.5 M1.5 5.5H14.5V18.5 M8.5 8.5L11.5 11.5 M11.5 8.5L8.5 11.5"},
    "rotate_right": {"svg": "M15.5 11.5A6 6 0 1 1 13.2 5 M13.5 1.5V5.5H9.5"},
    "rotate_left": {"svg": "M4.5 11.5A6 6 0 1 0 6.8 5 M6.5 1.5V5.5H10.5"},
    "flip": {"svg": "M4.5 9.5A5.5 5.5 0 0 1 14 5.5 M15.5 10.5A5.5 5.5 0 0 1 6 14.5 M14.5 2.5V5.5H11.5 M5.5 17.5V14.5H8.5"},
    "image_size": {"svg": "M2.5 2.5H17.5V17.5H2.5Z M6.5 13.5L13.5 6.5 M9.5 6.5H13.5V10.5 M6.5 9.5V13.5H10.5"},
    # sayfa düzeni ve komut çubuğu
    "page_layout": {"svg": "M4.5 2.5H15.5V17.5H4.5Z M4.5 5.5H15.5 M4.5 14.5H15.5 M7.5 2.5V17.5 M12.5 2.5V17.5"},
    "margins": {"svg": "M3.5 2.5H16.5V17.5H3.5Z M6.5 5.5H13.5V14.5H6.5Z"},
    "orientation": {"svg": "M2.5 6.5H11.5V17.5H2.5Z M9.5 2.5H17.5V9.5 M14.5 6.5L17.5 9.5 M17.5 9.5L20 6.5"},
    "portrait": {"svg": "M5.5 2.5H14.5V17.5H5.5Z M8.5 6.5H11.5"},
    "landscape": {"svg": "M2.5 5.5H17.5V14.5H2.5Z M6.5 8.5H9.5"},
    "paper_size": {"svg": "M4.5 1.5H12.5L15.5 4.5V18.5H4.5Z M12.5 1.5V4.5H15.5 M7 9.5H13 M7 9.5L8.5 8 M7 9.5L8.5 11 M13 9.5L11.5 8 M13 9.5L11.5 11"},
    # sesli oku: hoparlör ve ses dalgaları; okurken hoparlör dolu
    "read_aloud": {"svg": "M3.5 7.5H6.5L10.5 4.5V15.5L6.5 12.5H3.5Z M13.5 7.5A3.5 3.5 0 0 1 13.5 12.5"
                          " M15.5 5.5A6.5 6.5 0 0 1 15.5 14.5"},
    "read_aloud_active": {"svg": "M13.5 7.5A3.5 3.5 0 0 1 13.5 12.5 M15.5 5.5A6.5 6.5 0 0 1 15.5 14.5",
                          "fills": ["M3.5 7.5H6.5L10.5 4.5V15.5L6.5 12.5H3.5Z"]},
    "translate": {"circle": (9.5, 9.5, 7.5), "svg": "M2 9.5H17 M9.5 2A11 11 0 0 1 9.5 17 M9.5 2A11 11 0 0 0 9.5 17"},
    "link": {"svg": "M8 12L12 8 M7.5 5.5L9.5 3.5A3.5 3.5 0 0 1 16.5 10.5L14.5 12.5"
                     " M12.5 14.5L10.5 16.5A3.5 3.5 0 0 1 3.5 9.5L5.5 7.5"},
    "link_remove": {"svg": "M7.5 5.5L9.5 3.5A3.5 3.5 0 0 1 16.5 10.5L14.5 12.5 M12.5 14.5L10.5 16.5A3.5 3.5 0 0 1 3.5 9.5L5.5 7.5"
                           " M2.5 2.5L17.5 17.5"},
    "page_number": {"svg": "M4.5 2.5H15.5V17.5H4.5Z M7 6.5H13 M7 9.5H13", "text": [("1", 8, False, False, (4, 10, 12, 8))]},
    "page_setup": {"svg": "M4.5 2.5H13.5V17.5H4.5Z M7 6.5H11 M7 9.5H11 M7 12.5H9", "circles": [(15, 14.5, 2.5)]},
    "help": {"circle": (9.5, 9.5, 7.5), "text": [("?", 12, True, False, (0, 0, 19, 19))]},
    "keyboard": {"svg": "M1.5 5.5H18.5V14.5H1.5Z M4.5 11.5H15.5", "dots": [(5, 8), (8.3, 8), (11.7, 8), (15, 8)]},
    "cloud": {"svg": "M5.5 15.5A3.5 3.5 0 0 1 5.2 8.5A4.5 4.5 0 0 1 13.8 7.2A4 4 0 0 1 14.5 15.5Z"},
    "more": {"svg": "M5.5 6L9.5 10L5.5 14 M10.5 6L14.5 10L10.5 14"},
    "customize": {"svg": "M3.5 5.5H16.5 M3.5 10H16.5 M3.5 14.5H16.5", "circles": [(7, 5.5, 1.5), (13, 10, 1.5), (9, 14.5, 1.5)]},
    "symbol": {"text": [("Ω", 15, False, False, (0, 0, 20, 20))]},
}

_LIVE_ENGINES = []  # PySide sarmalayıcıları C++ tarafı kullanırken çöp toplanmasın


@lru_cache(maxsize=None)
def _renderer(svg_text):
    return QSvgRenderer(QByteArray(svg_text.encode()))


def _svg(path, color):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}" width="{GRID}" height="{GRID}">'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1" '
        'stroke-linecap="square" stroke-linejoin="round"/></svg>'
    )


def draw(painter, rect, name, color=INK, bar=None):
    """name ikonunu rect içine çizer. Ölçek 1 iken çizgiler tam piksele oturur."""
    spec = ICONS[name]
    scale = min(rect.width(), rect.height()) / GRID
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    # kare olmayan alanlarda ortala, tam piksele yuvarla
    ox = round(rect.x() + (rect.width() - GRID * scale) / 2)
    oy = round(rect.y() + (rect.height() - GRID * scale) / 2)
    painter.translate(ox, oy)
    ink = QColor(color)

    if "svg" in spec:
        _renderer(_svg(spec["svg"], ink.name())).render(painter, QRectF(0, 0, GRID * scale, GRID * scale))

    for path in spec.get("fills", []):
        filled = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}"><path d="{path}" fill="{ink.name()}" stroke="{ink.name()}" stroke-width="1"/></svg>'
        _renderer(filled).render(painter, QRectF(0, 0, GRID * scale, GRID * scale))

    painter.setPen(Qt.NoPen)
    painter.setBrush(ink)
    for cx, cy in spec.get("dots", []):
        painter.drawEllipse(QRectF((cx - 1.5) * scale, (cy - 1.5) * scale, 3 * scale, 3 * scale))
    painter.setBrush(Qt.NoBrush)
    for cx, cy, r in spec.get("circles", []) + ([spec["circle"]] if "circle" in spec else []):
        pen = painter.pen()
        painter.setPen(ink)
        painter.drawEllipse(QRectF((cx - r) * scale, (cy - r) * scale, 2 * r * scale, 2 * r * scale))
        painter.setPen(pen)

    for text, px, bold, italic, (x, y, w, h) in spec.get("text", []):
        font = QFont(spec.get("font", "Segoe UI"))
        font.setPixelSize(max(6, round(px * scale)))
        font.setBold(bold)
        font.setItalic(italic)
        font.setHintingPreference(QFont.PreferFullHinting)
        painter.setFont(font)
        painter.setPen(ink)
        painter.drawText(QRectF(x * scale, y * scale, w * scale, h * scale), Qt.AlignCenter, text)

    if spec.get("bar") and bar and bar != "none":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bar))
        painter.drawRect(QRectF(round(3 * scale), round(15 * scale), round(14 * scale), max(3, round(4 * scale))))
    painter.restore()


class IconEngine(QIconEngine):
    def __init__(self, name, color=INK, bar=None):
        super().__init__()
        self.name, self.color, self.bar = name, color, bar

    def _color(self, mode):
        return DISABLED if mode == QIcon.Disabled else self.color

    def paint(self, painter, rect, mode, state):
        bar = self.bar if mode != QIcon.Disabled or not self.bar else DISABLED
        draw(painter, QRectF(rect), self.name, self._color(mode), bar)

    def pixmap(self, size, mode, state):
        return self.scaledPixmap(size, mode, state, 1.0)

    def scaledPixmap(self, size, mode, state, scale):
        pixmap = QPixmap(QSize(round(size.width() * scale), round(size.height() * scale)))
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, pixmap.rect(), mode, state)
        painter.end()
        pixmap.setDevicePixelRatio(scale)
        return pixmap

    def clone(self):
        engine = IconEngine(self.name, self.color, self.bar)
        _LIVE_ENGINES.append(engine)
        return engine


@lru_cache(maxsize=None)
def icon(name, color=INK, bar=None):
    engine = IconEngine(name, color, bar)
    _LIVE_ENGINES.append(engine)
    return QIcon(engine)


def chevron_svg(color, size=12):
    """Stil sayfası (açılır kutu okları) için kendi boyutunda keskin ok."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
        f'<path d="M3 4.5L6 7.5L9 4.5" fill="none" stroke="{color}" stroke-width="1" stroke-linecap="round"/></svg>'
    )
