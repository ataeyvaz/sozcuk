"""Sayfa numarası — sayfa düzeyinde bir ayar, belgenin metnine karışmaz.

Kapsam bilinçli olarak dardır: tam bir üst bilgi / alt bilgi düzeni yoktur; yalnızca sayfa numarası vardır.
Numara belgenin akışına eklenmez (kullanıcı içine yazamaz), sayfanın kenar boşluğuna çizilir: ekranda
PageBackground, yazdırma ve PDF'te editor.print_document tarafından.

Ayarlar belgeye aittir (QTextDocument dinamik özellikleri, styles.page_size gibi) ve .docx'e Word'ün kendi
sayfa numarası alanı (PAGE / NUMPAGES) olarak yazılır: dosya Word'de açıldığında canlı alan olarak kalır.
Word'de hazırlanmış bir belgedeki sayfa numarası alanı da okunur ve aynı ayarlara çevrilir.
"""

from dataclasses import dataclass, replace

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF

from . import styles

# konum: (dikey, yatay)
POSITIONS = [
    ("bottom_center", "Alt Orta", "bottom", Qt.AlignHCenter),
    ("bottom_right", "Alt Sağ", "bottom", Qt.AlignRight),
    ("bottom_left", "Alt Sol", "bottom", Qt.AlignLeft),
    ("top_right", "Üst Sağ", "top", Qt.AlignRight),
    ("top_left", "Üst Sol", "top", Qt.AlignLeft),
    ("top_center", "Üst Orta", "top", Qt.AlignHCenter),
]
POSITION_BY_KEY = {key: (label, side, alignment) for key, label, side, alignment in POSITIONS}
DEFAULT_POSITION = "bottom_center"

FORMATS = [
    ("plain", "1, 2, 3", "{page}"),
    ("page_x", "Sayfa 1, Sayfa 2", "Sayfa {page}"),
    ("x_of_y", "1 / 12", "{page} / {total}"),
]
FORMAT_BY_KEY = {key: (label, pattern) for key, label, pattern in FORMATS}
DEFAULT_FORMAT = "plain"

EDGE_DISTANCE = 1.25 * styles.PX_PER_CM   # Word'ün alt/üst bilgi uzaklığı
MIN_EDGE_DISTANCE = 0.4 * styles.PX_PER_CM
FONT_SIZE = 10.0

_ENABLED = "sozcuk_pagenum_enabled"
_POSITION = "sozcuk_pagenum_position"
_FORMAT = "sozcuk_pagenum_format"
_START = "sozcuk_pagenum_start"


@dataclass(frozen=True)
class Settings:
    enabled: bool = False
    position: str = DEFAULT_POSITION
    format: str = DEFAULT_FORMAT
    start: int = 1

    @property
    def side(self):
        return POSITION_BY_KEY[self.position][1]

    @property
    def alignment(self):
        return POSITION_BY_KEY[self.position][2]

    @property
    def pattern(self):
        return FORMAT_BY_KEY[self.format][1]

    @property
    def needs_total(self):
        return "{total}" in self.pattern


def settings(document):
    position = document.property(_POSITION)
    fmt = document.property(_FORMAT)
    start = document.property(_START)
    try:
        start = max(0, int(start)) if start is not None else 1
    except (TypeError, ValueError):
        start = 1
    return Settings(
        enabled=bool(document.property(_ENABLED)),
        position=position if position in POSITION_BY_KEY else DEFAULT_POSITION,
        format=fmt if fmt in FORMAT_BY_KEY else DEFAULT_FORMAT,
        start=start,
    )


def set_settings(document, **values):
    """Verilen alanları değiştirir; uygulanan ayarı döndürür."""
    current = replace(settings(document), **values)
    document.setProperty(_ENABLED, current.enabled)
    document.setProperty(_POSITION, current.position)
    document.setProperty(_FORMAT, current.format)
    document.setProperty(_START, current.start)
    return current


def reset(document):
    return set_settings(document, enabled=False, position=DEFAULT_POSITION, format=DEFAULT_FORMAT, start=1)


def text_for(page, total, config):
    """page: 1'den başlayan sayfa sırası; total: belgedeki sayfa sayısı (durum çubuğundaki sayıyla aynı)."""
    number = config.start + page - 1
    return config.pattern.format(page=number, total=config.start + total - 1)


# =============================================================================
# Çizim (ekran, yazdırma, PDF — hepsi aynı yerleşimi kullanır)
# =============================================================================

def font(document):
    result = QFont(document.defaultFont())
    result.setPointSizeF(FONT_SIZE)
    result.setBold(False)
    result.setItalic(False)
    return result


def band_rect(document, page_rect, config):
    """Numaranın çizileceği şerit (sayfanın kenar boşluğu içinde)."""
    top, bottom, left, right = styles.all_margins(document)
    text_height = FONT_SIZE * styles.PX_PER_PT * 1.6
    if config.side == "bottom":
        distance = min(EDGE_DISTANCE, max(MIN_EDGE_DISTANCE, bottom - text_height / 2))
        y = page_rect.bottom() - distance - text_height / 2
    else:
        distance = min(EDGE_DISTANCE, max(MIN_EDGE_DISTANCE, top - text_height / 2))
        y = page_rect.top() + distance - text_height / 2
    return QRectF(page_rect.left() + left, y, max(1.0, page_rect.width() - left - right), text_height)


def draw(painter, document, page_rect, page, total, config=None):
    """Bir sayfanın numarasını çizer. page 1'den başlar; page_rect sayfanın (kâğıdın) dikdörtgenidir."""
    config = config or settings(document)
    if not config.enabled:
        return
    text = text_for(page, total, config)
    painter.save()
    painter.setPen(QColor("#1f1f1f"))
    painter.setFont(font(document))
    rect = band_rect(document, page_rect, config)
    painter.drawText(rect, int(config.alignment | Qt.AlignVCenter), text)
    painter.restore()


def measure(document, config=None):
    """Numaranın kapladığı yükseklik (ölçüm ve testler için)."""
    config = config or settings(document)
    return QFontMetricsF(font(document)).height()
