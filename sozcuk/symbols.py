"""Simge ekleme: Word'ün "Simge" menüsü gibi son kullanılanlar ızgarası ve kategorili, aranabilir simge penceresi.

Simgeler metne sıradan karakter olarak eklenir (imlecin yazı biçimiyle); böylece kaydetme, kopyalama,
yazım denetimi ve .docx dışa aktarımı ayrıca bir şey gerektirmez.
"""

import unicodedata

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

RECENT_KEY = "symbols/recent"
RECENT_LIMIT = 20

# Son kullanılan yokken menüde gösterilenler (Word'ün varsayılan listesine benzer, Türkçe yazıma göre)
DEFAULT_RECENT = "€₺$£©®™±≠≤≥÷×∞°µαβπΩ∑"


def _range(first, last, skip=()):
    return "".join(chr(code) for code in range(first, last + 1) if chr(code) not in skip)


CATEGORIES = [
    ("Sık Kullanılanlar", "©®™§¶†‡•·…–—‘’“”«»‹›°±×÷≠≈≤≥∞√∑€₺$£¥¢%‰№℃℉½¼¾¹²³✓✔✗✘★☆♥→←↑↓⇒⇔"),
    ("Noktalama ve Tipografi", "–—‒―‐‑‘’‚‛“”„‟«»‹›…•‣◦⁃·‧¡¿§¶†‡‰‱′″‴※‼⁇⁈⁉‽⁂⸮〃©®™℠№℮ªº"),
    ("Para Birimleri", "₺€$£¥¢₤₽₹₩₪₫₱₦₴₸₼₾₿ƒ¤"),
    ("Matematik", "±∓×÷⋅∙√∛∜∞∝∟∠∡∢∣∤∥∦∧∨∩∪∫∬∭∮∴∵∶∷∼≃≅≈≠≡≢≤≥≦≧≪≫⊂⊃⊄⊅⊆⊇⊕⊗⊥∀∁∂∃∄∅∆∇∈∉∋∌∏∐∑−∕∗"
                  "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞‰°′″"),
    ("Oklar", "←↑→↓↔↕↖↗↘↙↚↛↜↝↞↟↠↡↢↣↤↥↦↧↨↩↪↫↬↭↮↯↰↱↲↳↴↵↶↷↸↹↺↻⇄⇅⇆⇇⇈⇉⇊⇋⇌⇍⇎⇏⇐⇑⇒⇓⇔⇕⇖⇗⇘⇙⇚⇛"
              "➔➘➙➚➛➜➝➞➟➠➡➢➣➤➥➦➧➨"),
    ("Yunan Harfleri", _range(0x391, 0x3A9, skip="΢") + _range(0x3B1, 0x3C9)),
    ("Şekiller", "■□▢▣▤▥▦▧▨▩▪▫▬▭▮▯▰▱▲△▴▵▶▷▸▹►▻▼▽▾▿◀◁◂◃◄◅◆◇◈◉◊○◌◍◎●◐◑◒◓◔◕◖◗◘◙◢◣◤◥◦◯"
                "★☆✦✧✩✪✫✬✭✮✯✰❖"),
    ("İşaretler ve Semboller", "✓✔✕✖✗✘☐☑☒♠♣♥♦♤♧♡♢☀☁☂☃☄☎☏☑☕☘☚☛☜☝☞☟☠☢☣☮☯☹☺☻☼☽☾♀♂♨♩♪♫♬♭♮♯"
                              "✂✃✄✆✇✈✉✌✍✎✏✐✑✒❄❤❥❦❧⚐⚑⚠⚡⚪⚫⌘⌚⌛⏰⏳⌨✆"),
    ("Kutu Çizgileri", _range(0x2500, 0x257F) + _range(0x2580, 0x259F)),
    ("ASCII Karakterleri", _range(0x21, 0x7E)),
    ("Latin Harfleri", _range(0xC0, 0xFF, skip="×÷") + "ĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽžſ"),
    ("Emoji", "😀😁😂🙂😉😊😍😎🤔😐😢😡👍👎👏🙏👌✌💪👋🎉🎂🎁📌📎📝📅📞📧💡🔔🔒🔑⭐🔥💯✅❌❓❗⚠🚀🏠🚗✈☕🍎"),
]

# Arama ve açıklama için Türkçe adlar (diğerlerinde Unicode adı kullanılır)
NAMES = {
    "©": "telif hakkı", "®": "tescilli marka", "™": "ticari marka", "§": "paragraf bölüm", "¶": "paragraf işareti",
    "†": "hançer ölüm", "‡": "çift hançer", "•": "madde işareti nokta", "·": "orta nokta", "…": "üç nokta",
    "–": "kısa tire en dash", "—": "uzun tire em dash", "‘": "tek tırnak açma", "’": "tek tırnak kapama kesme",
    "“": "çift tırnak açma", "”": "çift tırnak kapama", "«": "açılı tırnak açma", "»": "açılı tırnak kapama",
    "°": "derece", "±": "artı eksi", "×": "çarpı çarpma", "÷": "bölü bölme", "≠": "eşit değil", "≈": "yaklaşık eşit",
    "≤": "küçük eşit", "≥": "büyük eşit", "∞": "sonsuz", "√": "karekök kök", "∑": "toplam sigma", "∏": "çarpım",
    "∫": "integral", "∂": "kısmi türev", "∆": "delta fark", "∇": "nabla", "∈": "elemanı", "∉": "elemanı değil",
    "∅": "boş küme", "∩": "kesişim", "∪": "birleşim", "⊂": "alt küme", "⊃": "üst küme", "∀": "her için",
    "∃": "vardır", "≡": "denk özdeş", "∝": "orantılı", "∠": "açı", "⊥": "dik", "∥": "paralel", "−": "eksi",
    "€": "avro euro", "₺": "türk lirası tl", "$": "dolar", "£": "sterlin pound", "¥": "yen", "¢": "sent",
    "₽": "ruble", "₹": "rupi", "₿": "bitcoin", "%": "yüzde", "‰": "binde", "№": "numara", "℃": "santigrat derece",
    "½": "yarım bir bölü iki", "¼": "çeyrek", "¾": "dörtte üç", "¹": "üst simge bir", "²": "kare üst simge iki",
    "³": "küp üst simge üç", "µ": "mikro", "π": "pi", "α": "alfa", "β": "beta", "γ": "gama", "δ": "delta",
    "ε": "epsilon", "θ": "teta", "λ": "lamda", "μ": "mü", "σ": "sigma", "φ": "fi", "ω": "omega", "Ω": "omega ohm",
    "✓": "onay tik", "✔": "kalın onay tik", "✗": "çarpı hayır", "✘": "kalın çarpı", "☐": "onay kutusu boş",
    "☑": "onay kutusu işaretli", "☒": "onay kutusu çarpı", "★": "dolu yıldız", "☆": "boş yıldız",
    "♥": "kalp", "♠": "maça", "♣": "sinek", "♦": "karo", "☎": "telefon", "✉": "zarf mektup e-posta",
    "✂": "makas", "✈": "uçak", "☀": "güneş", "☁": "bulut", "☂": "şemsiye", "❄": "kar tanesi", "⚠": "uyarı dikkat",
    "⚡": "şimşek elektrik", "♀": "kadın dişi", "♂": "erkek eril", "♪": "nota müzik", "☺": "gülen yüz",
    "→": "sağ ok", "←": "sol ok", "↑": "yukarı ok", "↓": "aşağı ok", "↔": "iki yönlü ok", "⇒": "çift sağ ok ise",
    "⇔": "çift iki yönlü ok ancak ve ancak", "⇐": "çift sol ok", "↵": "enter satır başı", "↻": "saat yönünde döndür",
    "↺": "saat yönünün tersine döndür", "■": "dolu kare", "□": "boş kare", "▲": "dolu üçgen", "△": "boş üçgen",
    "▶": "oynat sağ üçgen", "▼": "aşağı üçgen", "◆": "dolu elmas", "◇": "boş elmas", "●": "dolu daire",
    "○": "boş daire", "◉": "hedef daire", "Ğ": "yumuşak g", "ğ": "yumuşak g", "İ": "noktalı büyük i",
    "ı": "noktasız i", "Ş": "şe", "ş": "şe", "Ç": "çe", "ç": "çe", "Ö": "ö", "ö": "ö", "Ü": "ü", "ü": "ü",
    "─": "yatay çizgi kutu", "│": "dikey çizgi kutu", "┌": "sol üst köşe kutu", "┐": "sağ üst köşe kutu",
    "└": "sol alt köşe kutu", "┘": "sağ alt köşe kutu", "═": "çift yatay çizgi", "║": "çift dikey çizgi",
    "█": "dolu blok", "░": "açık gölge", "▒": "orta gölge", "▓": "koyu gölge",
    "😀": "gülümseyen yüz", "😂": "gülmekten ağlayan", "👍": "beğen başparmak", "👎": "beğenme", "🎉": "kutlama",
    "📌": "raptiye", "📎": "ataç", "📝": "not", "📅": "takvim", "📞": "telefon", "📧": "e-posta", "💡": "fikir ampul",
    "🔒": "kilit", "🔑": "anahtar", "⭐": "yıldız", "🔥": "ateş", "✅": "tamam onay", "❌": "hata çarpı",
    "❓": "soru", "❗": "ünlem", "🚀": "roket", "🏠": "ev", "☕": "kahve", "❤": "kalp",
}


def unicode_name(char):
    try:
        return unicodedata.name(char).title()
    except (ValueError, TypeError):
        return ""


def display_name(char):
    turkish = NAMES.get(char)
    name = unicode_name(char)
    return f"{turkish[0].upper()}{turkish[1:]}" if turkish else (name or "Simge")


def code_label(char):
    return "U+" + "+".join(f"{ord(c):04X}" for c in char)


def all_symbols():
    seen, result = set(), []
    for _, chars in CATEGORIES:
        for char in chars:
            if char not in seen:
                seen.add(char)
                result.append(char)
    return result


def _fold(text):
    return text.replace("İ", "i").replace("I", "ı").lower()


def search(query):
    """Türkçe ad, Unicode adı, karakterin kendisi ya da U+ koduyla arar."""
    query = query.strip()
    if not query:
        return []
    folded = _fold(query)
    code = folded.upper().removeprefix("U+")
    parts = folded.split()
    exact, turkish, other = [], [], []
    for char in all_symbols():
        if query == char or (len(code) >= 2 and f"{ord(char):04X}" == code.zfill(4)):
            exact.append(char)
            continue
        # her sorgu parçası bir kelimenin başıyla eşleşmeli ("tl" → "türk lirası tl", "stress outlined" değil)
        words_tr = _fold(NAMES.get(char, "")).split()
        words = words_tr + unicode_name(char).lower().split()
        if all(any(word.startswith(part) for word in words) for part in parts):
            (turkish if all(any(w.startswith(p) for w in words_tr) for p in parts) else other).append(char)
    return exact + turkish + other


def recent(settings):
    value = settings.value(RECENT_KEY, "")
    chars = [c for c in (value if isinstance(value, list) else str(value).split("\t")) if c]
    for char in DEFAULT_RECENT:  # menü hep dolu görünsün
        if len(chars) >= RECENT_LIMIT:
            break
        if char not in chars:
            chars.append(char)
    return chars[:RECENT_LIMIT]


def remember(settings, char):
    value = settings.value(RECENT_KEY, "")
    chars = [c for c in (value if isinstance(value, list) else str(value).split("\t")) if c and c != char]
    settings.setValue(RECENT_KEY, "\t".join([char] + chars[:RECENT_LIMIT - 1]))


# =============================================================================
# Arayüz
# =============================================================================

class SymbolGrid(QWidget):
    """Simgeleri kare hücrelerde gösterir. Tıklama: chosen; seçim değişimi: current; çift tık: activated."""

    chosen = Signal(str)
    current = Signal(str)
    activated = Signal(str)

    def __init__(self, chars=(), columns=10, cell=34, parent=None):
        super().__init__(parent)
        self.columns, self.cell = columns, cell
        self.chars = list(chars)
        self.hover = -1
        self.selected = -1
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.font_family = "Segoe UI Symbol"

    def set_chars(self, chars, select_first=True):
        self.chars = list(chars)
        self.hover = -1
        self.selected = 0 if self.chars and select_first else -1
        self.updateGeometry()
        self.adjustSize()
        self.update()
        if self.selected == 0:
            self.current.emit(self.chars[0])

    def sizeHint(self):
        rows = max(1, (len(self.chars) + self.columns - 1) // self.columns)
        return QSize(self.columns * self.cell + 1, rows * self.cell + 1)

    def minimumSizeHint(self):
        return self.sizeHint()

    def index_at(self, pos):
        column, row = int(pos.x() // self.cell), int(pos.y() // self.cell)
        index = row * self.columns + column
        return index if 0 <= column < self.columns and 0 <= index < len(self.chars) else -1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = QFont(self.font_family)
        font.setPixelSize(round(self.cell * 0.55))
        painter.setFont(font)
        grid = QColor("#e1dfdd")
        for index, char in enumerate(self.chars):
            rect = QRectF(index % self.columns * self.cell, index // self.columns * self.cell, self.cell, self.cell)
            if not rect.intersects(QRectF(event.rect())):
                continue
            if index == self.selected:
                painter.fillRect(rect, QColor("#cfe3fb"))
            elif index == self.hover:
                painter.fillRect(rect, QColor("#eaf2fc"))
            painter.setPen(grid)
            painter.drawRect(rect)
            painter.setPen(QColor("#1f1f1f"))
            painter.drawText(rect, Qt.AlignCenter, char)
        if 0 <= self.selected < len(self.chars):
            rect = QRectF(self.selected % self.columns * self.cell, self.selected // self.columns * self.cell,
                          self.cell, self.cell)
            painter.setPen(QColor("#185abd"))
            painter.drawRect(rect)

    def mouseMoveEvent(self, event):
        index = self.index_at(event.position())
        if index != self.hover:
            self.hover = index
            self.setToolTip(f"{display_name(self.chars[index])}  ({code_label(self.chars[index])})"
                            if index >= 0 else "")
            self.update()

    def leaveEvent(self, event):
        self.hover = -1
        self.update()

    def mousePressEvent(self, event):
        index = self.index_at(event.position())
        if index >= 0 and event.button() == Qt.LeftButton:
            self.selected = index
            self.update()
            self.current.emit(self.chars[index])
            self.chosen.emit(self.chars[index])

    def mouseDoubleClickEvent(self, event):
        index = self.index_at(event.position())
        if index >= 0:
            self.activated.emit(self.chars[index])

    def keyPressEvent(self, event):
        if not self.chars:
            return super().keyPressEvent(event)
        moves = {Qt.Key_Left: -1, Qt.Key_Right: 1, Qt.Key_Up: -self.columns, Qt.Key_Down: self.columns}
        if event.key() in moves:
            self.selected = min(max(0, self.selected + moves[event.key()]), len(self.chars) - 1)
            self.update()
            self.current.emit(self.chars[self.selected])
            parent = self.parentWidget()
            while parent is not None and not isinstance(parent, QScrollArea):
                parent = parent.parentWidget()
            if parent is not None:
                row = self.selected // self.columns
                parent.ensureVisible(0, row * self.cell + self.cell // 2, 0, self.cell)
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.selected >= 0:
            self.activated.emit(self.chars[self.selected])
        else:
            super().keyPressEvent(event)


class SymbolDialog(QDialog):
    """Kategorili, aranabilir simge penceresi. Açık kalır; art arda birçok simge eklenebilir (Word gibi)."""

    inserted = Signal(str)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Simge")
        self.setModal(False)
        self.resize(640, 460)

        self.search_box = QLineEdit(placeholderText="Simge ara (ör. ok, derece, tl, yıldız, U+20BA)")
        self.search_box.setClearButtonEnabled(True)
        self.categories = QListWidget()
        self.categories.setFixedWidth(180)
        for name, _ in CATEGORIES:
            self.categories.addItem(name)
        self.grid = SymbolGrid(columns=12, cell=34)
        scroll = QScrollArea()
        scroll.setWidget(self.grid)
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(self.grid.columns * self.grid.cell + 1 + scroll.verticalScrollBar().sizeHint().width() + 4)
        self.scroll = scroll

        self.preview = QLabel(alignment=Qt.AlignCenter)
        self.preview.setFixedSize(72, 72)
        self.preview.setStyleSheet("background:#ffffff;border:1px solid #d1d1d1;")
        font = QFont("Segoe UI Symbol")
        font.setPixelSize(40)
        self.preview.setFont(font)
        self.name_label = QLabel(wordWrap=True)
        self.code_label = QLabel()
        self.code_label.setStyleSheet("color:#616161;")
        self.empty_label = QLabel("Sonuç bulunamadı", alignment=Qt.AlignCenter)
        self.empty_label.setStyleSheet("color:#616161;")
        self.empty_label.hide()

        self.recent_grid = SymbolGrid(columns=RECENT_LIMIT, cell=28)
        self.insert_button = QPushButton("Ekle")
        self.insert_button.setDefault(True)
        close_button = QPushButton("Kapat")

        middle = QHBoxLayout()
        middle.addWidget(self.categories)
        grid_column = QVBoxLayout()
        grid_column.addWidget(scroll, 1)
        grid_column.addWidget(self.empty_label)
        middle.addLayout(grid_column, 1)

        info = QHBoxLayout()
        info.addWidget(self.preview)
        texts = QVBoxLayout()
        texts.addStretch(1)
        texts.addWidget(self.name_label)
        texts.addWidget(self.code_label)
        texts.addStretch(1)
        info.addLayout(texts, 1)
        buttons = QVBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.insert_button)
        buttons.addWidget(close_button)
        info.addLayout(buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_box)
        layout.addLayout(middle, 1)
        layout.addWidget(QLabel("Son kullanılan simgeler:"))
        layout.addWidget(self.recent_grid)
        layout.addLayout(info)

        self._current = ""
        self.categories.currentRowChanged.connect(self._show_category)
        self.categories.itemClicked.connect(lambda item: self._show_category(self.categories.row(item)))
        self.search_box.textChanged.connect(self._search)
        for grid in (self.grid, self.recent_grid):
            grid.current.connect(self._preview)
            grid.activated.connect(self.insert)
        self.insert_button.clicked.connect(lambda: self.insert(self._current))
        close_button.clicked.connect(self.close)
        self.categories.setCurrentRow(0)
        self.refresh_recent()

    def refresh_recent(self):
        self.recent_grid.set_chars(recent(self.settings), select_first=False)

    def _show_category(self, row):
        if row < 0:
            return
        if self.search_box.text():
            self.search_box.blockSignals(True)
            self.search_box.clear()
            self.search_box.blockSignals(False)
        self._fill(CATEGORIES[row][1])

    def _search(self, text):
        if not text.strip():
            self._show_category(max(0, self.categories.currentRow()))
            return
        self.categories.blockSignals(True)
        self.categories.clearSelection()  # arama sonuçları tüm kategorilerden gelir
        self.categories.blockSignals(False)
        self._fill(search(text))

    def _fill(self, chars):
        self.grid.set_chars(chars)
        self.scroll.verticalScrollBar().setValue(0)
        self.empty_label.setVisible(not chars)
        if not chars:
            self._preview("")

    def _preview(self, char):
        self._current = char
        self.preview.setText(char)
        self.name_label.setText(display_name(char) if char else "")
        self.code_label.setText(code_label(char) if char else "")
        self.insert_button.setEnabled(bool(char))

    def insert(self, char):
        if not char:
            return
        remember(self.settings, char)
        self.inserted.emit(char)
        self.refresh_recent()
