"""Köprüler (hyperlink): web adresleri ve belge içi hedefler.

Desteklenen hedefler:
- Web / e-posta: ``https://…``, ``http://…``, ``mailto:…`` — tarayıcıda (ya da e-posta programında) açılır
- Belge içi yer: ``sozcuk:sayfa=2&satir=5`` — belgenin 2. sayfasının 5. satırına gider (satır=0: sayfanın başı)
- Word'den gelen yer imleri: ``sozcuk:yerimi=AD`` — .docx içindeki w:bookmarkStart konumuna gider

Köprü, metnin karakter biçimidir (QTextCharFormat.anchorHref); .docx'e Word'ün kendi köprüsü olarak yazılır:
web adresleri ilişki (relationship) ile, belge içi hedefler ise hedef paragrafa konan bir yer imi ve
``w:hyperlink w:anchor`` ile. Böylece belge Word'de açıldığında bağlantılar çalışır.
"""

import re

from PySide6.QtCore import QPointF, QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

from . import styles

SCHEME = "sozcuk"
COLOR = "#0563c1"          # Word'ün köprü rengi
VISITED_COLOR = "#954f72"
BOOKMARKS_PROPERTY = "sozcuk_bookmarks"

WEB_PATTERN = re.compile(r"^(https?://|mailto:)", re.IGNORECASE)
# yazarken kendiliğinden köprüye çevrilenler
AUTO_PATTERN = re.compile(
    r"^(?:(?:https?://|www\.)[^\s]+|[^\s@]+@[^\s@]+\.[A-Za-zÇĞİÖŞÜçğıöşü]{2,})$")
TARGET_PATTERN = re.compile(r"^sozcuk:sayfa=(\d+)(?:&satir=(\d+))?$")
BOOKMARK_PATTERN = re.compile(r"^sozcuk:yerimi=(.+)$")
DOCX_BOOKMARK = re.compile(r"^sozcuk_s(\d+)_r(\d+)$")


def page_target(page, line=0):
    return f"{SCHEME}:sayfa={max(1, int(page))}" + (f"&satir={int(line)}" if line else "")


def bookmark_target(name):
    return f"{SCHEME}:yerimi={name}"


def bookmark_name(page, line):
    return f"sozcuk_s{max(1, int(page))}_r{max(0, int(line))}"


def parse(href):
    """(tür, değer): ("web", adres) | ("page", (sayfa, satır)) | ("bookmark", ad) | (None, None)"""
    if not href:
        return None, None
    match = TARGET_PATTERN.match(href)
    if match:
        return "page", (int(match.group(1)), int(match.group(2) or 0))
    match = BOOKMARK_PATTERN.match(href)
    if match:
        return "bookmark", match.group(1)
    if WEB_PATTERN.match(href):
        return "web", href
    if href.startswith("www."):
        return "web", "https://" + href
    if "@" in href and " " not in href:
        return "web", "mailto:" + href
    return None, None


def describe(href):
    kind, value = parse(href)
    if kind == "page":
        page, line = value
        return f"{page}. sayfa, {line}. satır" if line else f"{page}. sayfa"
    if kind == "bookmark":
        return f"belgedeki yer: {value}"
    if kind == "web":
        return value
    return href or ""


def normalize(text):
    """Kullanıcının yazdığı adresi kullanılabilir bir adrese çevirir."""
    text = (text or "").strip()
    if not text:
        return ""
    if WEB_PATTERN.match(text) or text.startswith(f"{SCHEME}:"):
        return text
    if text.startswith("www."):
        return "https://" + text
    if "@" in text and " " not in text and "/" not in text:
        return "mailto:" + text
    return "https://" + text


# =============================================================================
# Biçim
# =============================================================================

def link_format(base=None, visited=False):
    fmt = QTextCharFormat(base) if base is not None else QTextCharFormat()
    fmt.setAnchor(True)
    fmt.setForeground(QColor(VISITED_COLOR if visited else COLOR))
    fmt.setFontUnderline(True)
    return fmt


def apply(cursor, href, text=None):
    """Seçili metne (ya da verilen metne) köprü uygular. Kullanılan imleci döndürür."""
    href = href.strip()
    fmt = link_format(cursor.charFormat())
    fmt.setAnchorHref(href)
    if text is not None and (text != cursor.selectedText() or not cursor.hasSelection()):
        cursor.beginEditBlock()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        start = cursor.position()
        cursor.insertText(text, fmt)
        cursor.setPosition(start)
        cursor.setPosition(start + len(text), QTextCursor.KeepAnchor)
        cursor.endEditBlock()
    else:
        cursor.mergeCharFormat(fmt)
    return cursor


def remove(document, start, end):
    cursor = QTextCursor(document)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    fmt = QTextCharFormat(cursor.charFormat())
    fmt.setAnchor(False)
    fmt.setAnchorHref("")
    fmt.setFontUnderline(False)
    fmt.setForeground(QColor("#000000"))
    cursor.setCharFormat(fmt)
    return cursor


def link_at(document, position):
    """Konumdaki köprü: (href, başlangıç, bitiş) ya da None."""
    block = document.findBlock(position)
    if not block.isValid():
        return None
    iterator = block.begin()
    while not iterator.atEnd():
        fragment = iterator.fragment()
        if fragment.isValid():
            start, end = fragment.position(), fragment.position() + fragment.length()
            href = fragment.charFormat().anchorHref()
            if href and start <= position <= end:
                # aynı köprünün komşu parçalarını da kapsa
                return href, _extend(document, start, href, -1), _extend(document, end, href, 1)
        iterator += 1
    return None


def _extend(document, position, href, direction):
    """Aynı href'e sahip komşu metin parçalarını da içine alarak sınırı genişletir (paragrafı aşmadan)."""
    limits = document.findBlock(position if direction > 0 else max(0, position - 1))
    low, high = limits.position(), limits.position() + limits.length() - 1
    while True:
        probe = position - 1 if direction < 0 else position
        if probe < low or probe >= high or probe >= document.characterCount() - 1:
            return position
        cursor = QTextCursor(document)
        cursor.setPosition(probe)
        cursor.setPosition(probe + 1, QTextCursor.KeepAnchor)
        if cursor.charFormat().anchorHref() != href:
            return position
        position += direction


def links_in(document):
    """Belgedeki bütün köprüler: (href, başlangıç, bitiş)."""
    found = []
    block = document.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            href = fragment.charFormat().anchorHref() if fragment.isValid() else ""
            if href:
                start, end = fragment.position(), fragment.position() + fragment.length()
                if found and found[-1][0] == href and found[-1][2] == start:
                    found[-1] = (href, found[-1][1], end)
                else:
                    found.append((href, start, end))
            iterator += 1
        block = block.next()
    return found


# =============================================================================
# Belge içi hedefler
# =============================================================================

def line_positions(document, page_height=None):
    """Belgedeki her satırın (sayfa, satır sırası, belge konumu) listesi; sayfa ve satır 1'den başlar."""
    layout = document.documentLayout()
    slot = (page_height if page_height is not None else styles.page_size(document)[1]) + styles.PAGE_GAP
    result = []
    counters = {}
    block = document.begin()
    while block.isValid():
        block_layout = block.layout()
        if block_layout is not None and block_layout.lineCount():
            top = layout.blockBoundingRect(block).y()
            for i in range(block_layout.lineCount()):
                line = block_layout.lineAt(i)
                page = int((top + line.y() + line.height() / 2) // slot) + 1
                counters[page] = counters.get(page, 0) + 1
                result.append((page, counters[page], block.position() + line.textStart()))
        block = block.next()
    return result


def position_for(document, page, line=0):
    """Sayfa ve satır numarasına karşılık gelen belge konumu (yoksa en yakını)."""
    lines = line_positions(document)
    if not lines:
        return 0
    on_page = [item for item in lines if item[0] == page]
    if not on_page:
        on_page = [item for item in lines if item[0] >= page] or [lines[-1]]
        return on_page[0][2]
    if line <= 1:
        return on_page[0][2]
    for item in on_page:
        if item[1] == line:
            return item[2]
    return on_page[-1][2]


def page_line_of(document, position):
    """Konumun (sayfa, satır) karşılığı — bağlantı penceresini imlecin bulunduğu yerle açmak için."""
    found = (1, 1)
    for page, line, start in line_positions(document):
        if start > position:
            break
        found = (page, line)
    return found


def bookmarks(document):
    value = document.property(BOOKMARKS_PROPERTY)
    return dict(value) if isinstance(value, dict) else {}


def set_bookmarks(document, mapping):
    document.setProperty(BOOKMARKS_PROPERTY, dict(mapping))


# =============================================================================
# Açma
# =============================================================================

def open_link(editor, href):
    """Köprüyü açar: web adresi tarayıcıda, belge içi hedef imleci oraya taşır. Başarı durumunu döndürür."""
    kind, value = parse(href)
    if kind == "web":
        return QDesktopServices.openUrl(QUrl(value))
    document = editor.document()
    if kind == "page":
        page, line = value
        position = position_for(document, page, line)
    elif kind == "bookmark":
        position = bookmarks(document).get(value)
        if position is None:
            return False
    else:
        return False
    cursor = editor.textCursor()
    cursor.setPosition(min(position, document.characterCount() - 1))
    editor.setTextCursor(cursor)
    editor.ensure_cursor_visible()
    editor.setFocus()
    return True


def cursor_over_link(editor, scene_point):
    """Fare bir köprünün üzerindeyse (href, başlangıç, bitiş)."""
    position = editor.document().documentLayout().hitTest(QPointF(scene_point), Qt.ExactHit)
    if position < 0:
        return None
    return link_at(editor.document(), position)


def auto_link_at(document, position):
    """İmlecin solundaki sözcük bir adres gibiyse (başlangıç, bitiş, href); değilse None.
    Word gibi: adresin arkasına boşluk ya da Enter gelince kendiliğinden köprü olur."""
    block = document.findBlock(position)
    if not block.isValid():
        return None
    text = block.text()
    end = position - block.position()
    start = end
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    word = text[start:end].rstrip(".,;:!?)»\"'")
    if not word or not AUTO_PATTERN.match(word):
        return None
    cursor = QTextCursor(document)
    cursor.setPosition(block.position() + start)
    cursor.setPosition(block.position() + start + 1, QTextCursor.KeepAnchor)
    if cursor.charFormat().anchorHref():
        return None
    return block.position() + start, block.position() + start + len(word), normalize(word)


# =============================================================================
# Bağlantı penceresi
# =============================================================================

class LinkDialog(QDialog):
    """Köprü ekleme/düzenleme: web adresi ya da belgedeki bir yer (sayfa ve satır)."""

    def __init__(self, parent=None, text="", href="", page=1, line=1, max_page=1):
        super().__init__(parent)
        self.setWindowTitle("Bağlantıyı Düzenle" if href else "Bağlantı Ekle")
        self.removed = False
        kind, value = parse(href)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.addWidget(QLabel("Görüntülenecek metin:"), 0, 0)
        self.text_edit = QLineEdit(text)
        self.text_edit.setMinimumWidth(280)
        grid.addWidget(self.text_edit, 0, 1, 1, 3)

        self.web_radio = QRadioButton("Web adresi ya da e-posta")
        self.place_radio = QRadioButton("Bu belgede bir yer")
        grid.addWidget(self.web_radio, 1, 0, 1, 4)
        self.address_edit = QLineEdit(value if kind == "web" else "")
        self.address_edit.setPlaceholderText("https://ornek.com ya da ad@ornek.com")
        grid.addWidget(self.address_edit, 2, 1, 1, 3)

        grid.addWidget(self.place_radio, 3, 0, 1, 4)
        grid.addWidget(QLabel("Sayfa:"), 4, 1)
        self.page_spin = QSpinBox(minimum=1, maximum=max(1, max_page), value=page)
        self.page_spin.setFixedWidth(80)
        grid.addWidget(self.page_spin, 4, 2)
        self.line_box = QCheckBox("Satır:")
        self.line_spin = QSpinBox(minimum=1, maximum=999, value=max(1, line))
        self.line_spin.setFixedWidth(80)
        grid.addWidget(self.line_box, 5, 1)
        grid.addWidget(self.line_spin, 5, 2)
        layout.addLayout(grid)

        note = QLabel("Belgedeki bir yere bağlantı, o sayfanın (istenirse belirtilen satırın) başına gider. "
                      "Bağlantıyı açmak için üzerine Ctrl ile tıklayın.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#616161;")
        layout.addWidget(note)

        buttons = QDialogButtonBox()
        self.ok_button = buttons.addButton("Tamam", QDialogButtonBox.AcceptRole)
        self.ok_button.setDefault(True)
        if href:
            remove_button = buttons.addButton("Bağlantıyı Kaldır", QDialogButtonBox.DestructiveRole)
            remove_button.clicked.connect(self._remove)
        buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if kind == "page":
            target_page, target_line = value
            self.page_spin.setValue(max(1, min(target_page, self.page_spin.maximum())))
            self.line_box.setChecked(bool(target_line))
            if target_line:
                self.line_spin.setValue(target_line)
            self.place_radio.setChecked(True)
        else:
            self.web_radio.setChecked(True)
        self.web_radio.toggled.connect(self._update)
        self.address_edit.textChanged.connect(self._update)
        self.text_edit.textChanged.connect(self._update)
        self.line_box.toggled.connect(self._update)
        self._update()

    def _update(self):
        web = self.web_radio.isChecked()
        self.address_edit.setEnabled(web)
        for widget in (self.page_spin, self.line_box):
            widget.setEnabled(not web)
        self.line_spin.setEnabled(not web and self.line_box.isChecked())
        self.ok_button.setEnabled(bool(self.text_edit.text().strip())
                                  and (not web or bool(self.address_edit.text().strip())))

    def _remove(self):
        self.removed = True
        self.accept()

    def href(self):
        if self.web_radio.isChecked():
            return normalize(self.address_edit.text())
        return page_target(self.page_spin.value(), self.line_spin.value() if self.line_box.isChecked() else 0)

    def text(self):
        return self.text_edit.text()
