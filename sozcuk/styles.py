"""Belge biçimlendirme sabitleri: sayfa ölçüleri, varsayılan yazı tipi, başlık ve paragraf stilleri.

Tüm uzunluklar ekran pikselidir (96 DPI); punto değerleri yazı boyutları içindir.
"""

from PySide6.QtGui import QFont, QTextBlockFormat, QTextCharFormat, QTextListFormat

PX_PER_PT = 96 / 72
PX_PER_CM = 96 / 2.54

PAGE_GAP = 24                           # ekranda sayfalar arası boşluk
MIN_TEXT_HEIGHT = round(3 * PX_PER_CM)  # kenar boşlukları sayfada en az bu kadar yazı alanı bırakır
MIN_TEXT_WIDTH = round(3 * PX_PER_CM)
# kenar boşlukları belgeye kaydedildiği için yuvarlanmamış tam 2,5 cm (94 px'e yuvarlansa 2,49 cm yazılırdı)
DEFAULT_MARGIN = 2.5 * PX_PER_CM
DEFAULT_VERTICAL_MARGIN = DEFAULT_MARGIN

# Kâğıt boyutları (dikey, cm) — Word'ün Boyut listesindeki yaygın olanlar
PAPER_SIZES = [
    ("A4", "A4", 21.0, 29.7),
    ("A5", "A5", 14.8, 21.0),
    ("A3", "A3", 29.7, 42.0),
    ("B5", "B5 (JIS)", 18.2, 25.7),
    ("Letter", "Letter", 21.59, 27.94),
    ("Legal", "Legal", 21.59, 35.56),
    ("Executive", "Executive", 18.41, 26.67),
]
DEFAULT_PAPER = "A4"

# Kenar boşluğu hazır ayarları (Word TR): ad -> (üst, alt, sol, sağ) cm
MARGIN_PRESETS = [
    ("Normal", 2.5, 2.5, 2.5, 2.5),
    ("Dar", 1.27, 1.27, 1.27, 1.27),
    ("Orta", 2.54, 2.54, 1.91, 1.91),
    ("Geniş", 2.54, 2.54, 5.08, 5.08),
]

_MARGIN_PROPERTIES = ("sozcuk_margin_top", "sozcuk_margin_bottom", "sozcuk_margin_left", "sozcuk_margin_right")
_WIDTH_PROPERTY = "sozcuk_page_width"
_HEIGHT_PROPERTY = "sozcuk_page_height"


def _paper_px(key):
    for name, _, width, height in PAPER_SIZES:
        if name == key:
            return width * PX_PER_CM, height * PX_PER_CM
    raise KeyError(key)


def _prop(document, name, default):
    value = document.property(name)
    return default if value is None else float(value)


def page_size(document):
    """Belgenin sayfa genişliği ve yüksekliği (px, yönlendirme uygulanmış). Belgeye aittir: .docx'e yazılır."""
    width, height = _paper_px(DEFAULT_PAPER)
    return _prop(document, _WIDTH_PROPERTY, width), _prop(document, _HEIGHT_PROPERTY, height)


def is_landscape(document):
    width, height = page_size(document)
    return width > height


def paper_name(document):
    """Sayfa boyutuna karşılık gelen kâğıt adı (yönlendirmeden bağımsız); listede yoksa None."""
    size = sorted(page_size(document))
    for name, _, width, height in PAPER_SIZES:
        if abs(size[0] - width * PX_PER_CM) < 2 and abs(size[1] - height * PX_PER_CM) < 2:
            return name
    return None


def all_margins(document):
    """(üst, alt, sol, sağ) kenar boşlukları (px)."""
    return tuple(_prop(document, name, DEFAULT_MARGIN) for name in _MARGIN_PROPERTIES)


def page_margins(document):
    """Belgenin üst ve alt kenar boşlukları (px)."""
    return all_margins(document)[:2]


def side_margins(document):
    """Belgenin sol ve sağ kenar boşlukları (px)."""
    return all_margins(document)[2:]


def text_width(document):
    width, _ = page_size(document)
    left, right = side_margins(document)
    return width - left - right


def set_page_setup(document, width=None, height=None, top=None, bottom=None, left=None, right=None):
    """Sayfa boyutu ve kenar boşluklarını geçerli aralığa sıkıştırıp belgeye yazar (verilmeyenler değişmez).
    Uygulanan (genişlik, yükseklik, üst, alt, sol, sağ) değerini döndürür."""
    old_width, old_height = page_size(document)
    width = max(5 * PX_PER_CM, float(width if width is not None else old_width))
    height = max(5 * PX_PER_CM, float(height if height is not None else old_height))
    old = all_margins(document)
    top, bottom, left, right = (float(v if v is not None else o) for v, o in zip((top, bottom, left, right), old))
    top = max(0.0, min(top, height - MIN_TEXT_HEIGHT))
    bottom = max(0.0, min(bottom, height - MIN_TEXT_HEIGHT - top))
    left = max(0.0, min(left, width - MIN_TEXT_WIDTH))
    right = max(0.0, min(right, width - MIN_TEXT_WIDTH - left))
    document.setProperty(_WIDTH_PROPERTY, width)
    document.setProperty(_HEIGHT_PROPERTY, height)
    for name, value in zip(_MARGIN_PROPERTIES, (top, bottom, left, right)):
        document.setProperty(name, value)
    return width, height, top, bottom, left, right


def set_page_margins(document, top, bottom):
    """Üst/alt kenar boşluklarını sıkıştırıp yazar; uygulanan (üst, alt) değerini döndürür."""
    return set_page_setup(document, top=top, bottom=bottom)[2:4]


def reset_page_setup(document):
    width, height = _paper_px(DEFAULT_PAPER)
    set_page_setup(document, width, height, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN)

DEFAULT_FAMILY = "Calibri"
DEFAULT_SIZE = 11
INDENT_WIDTH = 48                       # 0,5 inç = Word liste/girinti adımı

BODY_SPACING_AFTER = 8 * PX_PER_PT      # Word "Normal": sonra 8 nk, satır aralığı 1,08
BODY_LINE_HEIGHT = 108

# başlık seviyesi -> (punto, kalın, önce boşluk pt, sonra boşluk pt)
HEADING_STYLES = {
    0: (DEFAULT_SIZE, False, 0, 8),
    1: (20, True, 18, 6),
    2: (15, True, 12, 4),
}
HEADING_NAMES = ["Normal", "Başlık 1", "Başlık 2"]

LINE_SPACINGS = [1.0, 1.08, 1.15, 1.5, 2.0, 2.5, 3.0]
FONT_SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]

BULLET_STYLES = [QTextListFormat.ListDisc, QTextListFormat.ListCircle, QTextListFormat.ListSquare]
NUMBER_STYLES = [QTextListFormat.ListDecimal, QTextListFormat.ListLowerAlpha, QTextListFormat.ListLowerRoman]

# Word'ün vurgu renkleri (docx'te yalnızca bunlar saklanabilir)
HIGHLIGHT_COLORS = [
    ("YELLOW", "#FFFF00"), ("BRIGHT_GREEN", "#00FF00"), ("TURQUOISE", "#00FFFF"),
    ("PINK", "#FF00FF"), ("BLUE", "#0000FF"), ("RED", "#FF0000"),
    ("DARK_BLUE", "#000080"), ("TEAL", "#008080"), ("GREEN", "#008000"),
    ("VIOLET", "#800080"), ("DARK_RED", "#800000"), ("DARK_YELLOW", "#808000"),
    ("GRAY_50", "#808080"), ("GRAY_25", "#C0C0C0"), ("BLACK", "#000000"),
]


def is_bullet(style):
    return style in BULLET_STYLES


def list_style_for(bullet, indent):
    styles = BULLET_STYLES if bullet else NUMBER_STYLES
    return styles[(max(indent, 1) - 1) % len(styles)]


def heading_block_format(level, base=None):
    _, _, before, after = HEADING_STYLES[level]
    fmt = QTextBlockFormat(base) if base is not None else QTextBlockFormat()
    fmt.setHeadingLevel(level)
    fmt.setTopMargin(before * PX_PER_PT)
    fmt.setBottomMargin(after * PX_PER_PT)
    if not fmt.hasProperty(QTextBlockFormat.LineHeight):
        fmt.setLineHeight(BODY_LINE_HEIGHT, QTextBlockFormat.ProportionalHeight.value)
    return fmt


def heading_char_format(level):
    size, bold, _, _ = HEADING_STYLES[level]
    fmt = QTextCharFormat()
    fmt.setFontPointSize(size)
    fmt.setFontWeight(QFont.Bold if bold else QFont.Normal)
    return fmt


def body_block_format():
    return heading_block_format(0)


def body_char_format():
    fmt = QTextCharFormat()
    fmt.setFontFamilies([DEFAULT_FAMILY])
    fmt.setFontPointSize(DEFAULT_SIZE)
    return fmt
