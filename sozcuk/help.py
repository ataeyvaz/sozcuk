"""Uygulama içi yardım: "Yardım ve Nasıl Kullanılır" penceresi.

İçerik sozcuk/yardim.md dosyasındadır (konulara bölünmüş Markdown); yeni özellik eklendikçe oraya yazılır.
Pencere konu listesi, arama (Türkçe büyük/küçük harf duyarsız, eşleşmeler vurgulanır) ve konular arası
bağlantılar ([Başlık](konu:kimlik)) sunar. Tamamen çevrimdışıdır.
"""

import re
from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QTextFrameFormat, QTextLength, QTextTable
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme
from . import resource_dir

HELP_FILE = resource_dir() / "yardim.md"
TOPIC_RE = re.compile(r"^<!--\s*konu:\s*([\w-]+)\s*\|\s*(.+?)\s*\|\s*([\w-]+)\s*-->\s*$", re.MULTILINE)
LINK_SCHEME = "konu"


@dataclass
class Topic:
    key: str
    title: str
    icon: str
    body: str

    def plain(self):
        """Arama için işaretlerden arındırılmış metin."""
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", self.body)
        return re.sub(r"[`*#|>]", " ", text)


def load_topics(path=HELP_FILE):
    text = path.read_text(encoding="utf-8")
    matches = list(TOPIC_RE.finditer(text))
    topics = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        topics.append(Topic(match.group(1), match.group(2), match.group(3), text[match.end():end].strip()))
    return topics


def fold(text):
    """Türkçe kurallarıyla küçük harfe çevirir (İ→i, I→ı)."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def search(topics, query):
    """Tüm sorgu kelimelerini içeren konular, ilgiye göre sıralı: başlıkta geçen, sonra ifadenin ve
    kelimelerin konuda kaç kez geçtiği ("Yenilikler" her şeyden söz ettiği için yalnızca bahsetmek öne almaz)."""
    words = fold(query).split()
    if not words:
        return list(topics)
    phrase = " ".join(words)
    scored = []
    for index, topic in enumerate(topics):
        title, text = fold(topic.title), fold(topic.plain())
        if not all(w in title or w in text for w in words):
            continue
        score = 100 * sum(w in title for w in words) + 5 * text.count(phrase) + sum(text.count(w) for w in words)
        scored.append((-score, index, topic))
    return [topic for _, _, topic in sorted(scored)]


def shortcuts_in(topics):
    """Yardımda geçen kısayollar (test: uygulamada tanımlı olduklarını denetlemek için)."""
    keys = set()
    for topic in topics:
        for code in re.findall(r"`([^`]+)`", topic.body):
            if re.fullmatch(r"(Ctrl\+|Shift\+|Alt\+)*(F\d{1,2}|[A-Z\[\]]|Space)", code):
                keys.add(code)
    return keys


class HelpWindow(QWidget):
    def __init__(self, settings=None, parent=None):
        super().__init__(parent, Qt.Window)
        self.settings = settings
        self.setWindowTitle("Sözcük — Yardım ve Nasıl Kullanılır")
        self.setWindowIcon(icons.icon("help"))
        self.resize(980, 700)
        self.topics = load_topics()
        self.by_key = {t.key: t for t in self.topics}
        self.current = None

        self.search_box = QLineEdit(placeholderText="Yardımda ara (ör. kırp, kenar boşluğu, kısayol)")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._filter)
        self.search_box.returnPressed.connect(self._open_first_result)
        self.result_label = QLabel()
        self.result_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")

        self.list = QListWidget()
        self.list.setIconSize(QSize(20, 20))
        self.list.setMinimumWidth(220)
        self.list.currentItemChanged.connect(lambda item, _: item and self.show_topic(item.data(Qt.UserRole)))

        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._link)
        self.browser.document().setDocumentMargin(24)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.list, 1)
        left_layout.addWidget(self.result_label)
        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self.browser)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 740])

        top = QHBoxLayout()
        top.addWidget(self.search_box, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)

        self._filter("")
        last = settings.value("help/topic", "baslarken") if settings is not None else "baslarken"
        self.open_topic(last if last in self.by_key else self.topics[0].key)

    # --- konular -----------------------------------------------------------

    def open_topic(self, key):
        if key not in self.by_key:
            return
        if self.search_box.text() and key not in [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]:
            self.search_box.clear()
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == key:
                self.list.setCurrentRow(i)
        self.show_topic(key)

    def show_topic(self, key):
        topic = self.by_key[key]
        if self.current != key:
            self.current = key
            self.browser.setMarkdown(topic.body)
            self._style_document()
            self.browser.verticalScrollBar().setValue(0)
            if self.settings is not None:
                self.settings.setValue("help/topic", key)
        self._highlight()

    def _style_document(self):
        doc = self.browser.document()
        font = QFont("Segoe UI")
        font.setPointSizeF(10.5)
        doc.setDefaultFont(font)
        # Markdown tabloları kenarlıksız gelir; okunaklı olsun diye çerçeve ve hücre boşluğu ver
        for frame in doc.rootFrame().childFrames():
            if not isinstance(frame, QTextTable):
                continue
            table = frame
            fmt = table.format()
            fmt.setBorder(1)
            fmt.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
            fmt.setBorderBrush(QColor("#d6d6d6"))
            fmt.setBorderCollapse(True)
            fmt.setCellPadding(6)
            fmt.setWidth(QTextLength(QTextLength.PercentageLength, 100))
            table.setFormat(fmt)
            for column in range(table.columns()):
                cell = table.cellAt(0, column)
                cell_fmt = cell.format()
                cell_fmt.setBackground(QColor("#eef3fa"))
                cell.setFormat(cell_fmt)
        # başlık renkleri ve kısayol kodları
        block = doc.begin()
        while block.isValid():
            level = block.blockFormat().headingLevel()
            if level:
                cursor = QTextCursor(block)
                cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                fmt = QTextCharFormat()
                fmt.setForeground(QColor("#185abd" if level == 1 else "#1f1f1f"))
                cursor.mergeCharFormat(fmt)
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().fontFixedPitch():
                    cursor = QTextCursor(doc)
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(fragment.position() + fragment.length(), QTextCursor.KeepAnchor)
                    key_fmt = QTextCharFormat()
                    key_fmt.setBackground(QColor("#f0f0f0"))
                    key_fmt.setForeground(QColor("#1f1f1f"))
                    key_fmt.setFontFamilies(["Segoe UI"])
                    key_fmt.setFontWeight(QFont.DemiBold)
                    cursor.mergeCharFormat(key_fmt)
                iterator += 1
            block = block.next()
        doc.setModified(False)

    def _link(self, url):
        if url.scheme() == LINK_SCHEME:
            self.open_topic(url.path())

    # --- arama -------------------------------------------------------------

    def _filter(self, text):
        found = search(self.topics, text)
        self.list.blockSignals(True)
        self.list.clear()
        for topic in found:
            item = QListWidgetItem(icons.icon(topic.icon), topic.title)
            item.setData(Qt.UserRole, topic.key)
            self.list.addItem(item)
            if topic.key == self.current:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if text.strip():
            self.result_label.setText(f"{len(found)} konu bulundu" if found else "Sonuç bulunamadı")
            if found and self.current not in [t.key for t in found]:
                self.list.setCurrentRow(0)
        else:
            self.result_label.setText("")
        self._highlight()

    def _open_first_result(self):
        if self.list.count():
            self.list.setCurrentRow(0)
            self.show_topic(self.list.item(0).data(Qt.UserRole))

    def _highlight(self):
        """Arama kelimelerini açık konuda sarıyla vurgular ve ilk eşleşmeye kaydırır."""
        words = fold(self.search_box.text()).split()
        doc = self.browser.document()
        selections = []
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#fff3a3"))
        if words:
            text = fold(doc.toPlainText())
            for word in words:
                start = text.find(word)
                while start >= 0:
                    cursor = QTextCursor(doc)
                    cursor.setPosition(start)
                    cursor.setPosition(start + len(word), QTextCursor.KeepAnchor)
                    selection = QTextEdit.ExtraSelection()
                    selection.cursor, selection.format = cursor, fmt
                    selections.append(selection)
                    start = text.find(word, start + len(word))
        self.browser.setExtraSelections(selections)
        if selections:
            first = min(selections, key=lambda s: s.cursor.position())
            cursor = QTextCursor(doc)
            cursor.setPosition(first.cursor.selectionStart())  # seçim rengi değil, yalnızca sarı vurgu görünsün
            self.browser.setTextCursor(cursor)
            self.browser.ensureCursorVisible()


def show_help(parent, settings, topic=None):
    """Yardım penceresini (tek örnek) açar ve öne getirir."""
    window = getattr(parent, "_help_window", None)
    if window is None:
        window = HelpWindow(settings, parent)
        parent._help_window = window
    if topic:
        window.open_topic(topic)
    window.show()
    window.raise_()
    window.activateWindow()
    return window

