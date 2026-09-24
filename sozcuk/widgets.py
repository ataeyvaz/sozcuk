"""Özel arayüz bileşenleri: renk seçici buton, açma/kapama anahtarı, bilgi çubuğu."""

import math

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QMimeData,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QDrag, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from . import icons, theme
from .styles import HIGHLIGHT_COLORS

BAR_ITEM_MIME = "application/x-sozcuk-komut"

THEME_COLORS = ["#FFFFFF", "#000000", "#E7E6E6", "#44546A", "#4472C4",
                "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47"]
STANDARD_COLORS = ["#C00000", "#FF0000", "#FFC000", "#FFFF00", "#92D050",
                   "#00B050", "#00B0F0", "#0070C0", "#002060", "#7030A0"]


def _tint(hex_color, amount):
    """amount > 0 açar, < 0 koyulaştırır (Word tema paleti gibi)."""
    c = QColor(hex_color)
    channels = [c.red(), c.green(), c.blue()]
    if amount > 0:
        channels = [round(v + (255 - v) * amount) for v in channels]
    else:
        channels = [round(v * (1 + amount)) for v in channels]
    return QColor(*channels).name()


class _Swatch(QToolButton):
    def __init__(self, color, size=16, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(size + 4, size + 4)
        self.setToolTip(color.upper())
        self.setStyleSheet(
            f"QToolButton {{ background: {color}; border: 1px solid #d0d0d0; border-radius: 0; margin: 1px; }}"
            f"QToolButton:hover {{ border: 1px solid #f29436; }}"
        )


class _SectionLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-weight: 600; padding: 4px 2px 2px 2px;")


class ColorButton(QToolButton):
    """Tıklayınca son rengi uygular; ok kısmı Word'deki gibi renk paletini açar."""

    colorChosen = Signal(object)  # QColor, ya da "renk yok" için None

    def __init__(self, icon_name, tooltip, default_color, highlight=False, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.current = default_color
        self.setToolTip(tooltip)
        self.setPopupMode(QToolButton.MenuButtonPopup)
        self.setIconSize(QSize(20, 20))
        self.clicked.connect(lambda: self.colorChosen.emit(QColor(self.current) if self.current else None))

        menu = QMenu(self)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(2)

        if highlight:
            grid = QGridLayout()
            grid.setSpacing(0)
            for i, (_, hex_color) in enumerate(HIGHLIGHT_COLORS):
                grid.addWidget(self._swatch(hex_color, menu, 20), i // 5, i % 5)
            layout.addLayout(grid)
            none_button = self._text_button("Renk yok", menu, None)
            layout.addWidget(none_button)
        else:
            layout.addWidget(self._text_button("Otomatik", menu, None))
            layout.addWidget(_SectionLabel("Tema Renkleri"))
            grid = QGridLayout()
            grid.setSpacing(0)
            for col, base in enumerate(THEME_COLORS):
                grid.addWidget(self._swatch(base, menu), 0, col)
                shades = [0.8, 0.6, 0.4, -0.25, -0.5] if base not in ("#FFFFFF", "#000000") else (
                    [-0.05, -0.15, -0.25, -0.35, -0.5] if base == "#FFFFFF" else [0.5, 0.35, 0.25, 0.15, 0.05])
                for row, amount in enumerate(shades, start=1):
                    grid.addWidget(self._swatch(_tint(base, amount), menu), row, col)
            layout.addLayout(grid)
            layout.addWidget(_SectionLabel("Standart Renkler"))
            row = QHBoxLayout()
            row.setSpacing(0)
            for hex_color in STANDARD_COLORS:
                row.addWidget(self._swatch(hex_color, menu))
            layout.addLayout(row)
            more = self._text_button("Diğer Renkler…", menu, "more")
            layout.addWidget(more)

        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.setMenu(menu)
        self._refresh_icon()

    def _swatch(self, hex_color, menu, size=16):
        swatch = _Swatch(hex_color, size)
        swatch.clicked.connect(lambda: self._choose(QColor(hex_color), menu))
        return swatch

    def _text_button(self, text, menu, kind):
        button = QPushButton(text)
        button.setFlat(True)
        button.setStyleSheet(
            "QPushButton { text-align: left; border: none; padding: 5px 6px; border-radius: 4px; min-width: 0; }"
            f"QPushButton:hover {{ background: {theme.HOVER}; }}"
        )
        if kind == "more":
            button.clicked.connect(lambda: self._more(menu))
        else:
            button.clicked.connect(lambda: self._choose(None, menu))
        return button

    def _more(self, menu):
        menu.close()
        color = QColorDialog.getColor(QColor(self.current or "#000000"), self.window(), "Renk seç")
        if color.isValid():
            self._choose(color, None)

    def _choose(self, color, menu):
        if menu:
            menu.close()
        self.current = color.name() if color else None
        self._refresh_icon()
        self.colorChosen.emit(color)

    def _refresh_icon(self):
        bar = self.current or ("#000000" if self.icon_name == "font_color" else "none")
        self.setIcon(icons.icon(self.icon_name, bar=bar))


class ToggleSwitch(QAbstractButton):
    """Fluent tarzı açma/kapama anahtarı (başlık şeridi için beyaz tonlarda)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 20)
        self._offset = 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked):
        super().setChecked(checked)
        self._anim.stop()
        self._offset = 1.0 if checked else 0.0
        self.update()

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def sizeHint(self):
        return QSize(38, 20)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QRectF(1, 1, self.width() - 2, self.height() - 2)
        radius = track.height() / 2
        if self.isChecked():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#ffffff"))
        else:
            p.setPen(QColor(255, 255, 255, 220))
            p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(track, radius, radius)

        knob = 12 if self.isChecked() else 10
        x = track.left() + 4 + self._offset * (track.width() - 8 - 12) + (12 - knob) / 2
        y = track.center().y() - knob / 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.ACCENT) if self.isChecked() else QColor("#ffffff"))
        p.drawEllipse(QRectF(x, y, knob, knob))


class ZoomControl(QWidget):
    """Word durum çubuğundaki yakınlaştırma: [−] kaydırıcı [+] %100 (yüzdeye tıklayınca hazır seçenekler)."""

    zoomRequested = Signal(float)
    fitWidthRequested = Signal()
    fitPageRequested = Signal()

    PRESETS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(2)
        self._zoom = 1.0

        minus = self._button("zoom_out", "Uzaklaştır", lambda: self._step(-1))
        plus = self._button("zoom_in", "Yakınlaştır", lambda: self._step(1))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 200)
        self.slider.setFixedWidth(110)
        self.slider.setToolTip("Yakınlaştır")
        self.slider.valueChanged.connect(self._slider_moved)

        self.percent = QToolButton()
        self.percent.setToolTip("Yakınlaştırma düzeyi")
        self.percent.setPopupMode(QToolButton.InstantPopup)
        self.percent.setFixedWidth(46)
        menu = QMenu(self.percent)
        for preset in self.PRESETS:
            menu.addAction(f"%{round(preset * 100)}", lambda p=preset: self.zoomRequested.emit(p))
        menu.addSeparator()
        menu.addAction("Sayfa Genişliği", self.fitWidthRequested.emit)
        menu.addAction("Tam Sayfa", self.fitPageRequested.emit)
        self.percent.setMenu(menu)
        self.percent.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0; }")

        for widget in (minus, self.slider, plus, self.percent):
            layout.addWidget(widget)
        self.set_zoom(1.0)

    @staticmethod
    def _button(icon_name, tip, slot):
        button = QToolButton()
        button.setIcon(icons.icon(icon_name, theme.TEXT_MUTED))
        button.setIconSize(QSize(16, 16))
        button.setToolTip(tip)
        button.setAutoRepeat(True)
        button.clicked.connect(slot)
        return button

    # Word'deki gibi: kaydırıcının sol yarısı %10–100, sağ yarısı %100–500
    @staticmethod
    def _to_slider(zoom):
        return round((zoom - 0.1) / 0.9 * 100) if zoom <= 1 else round(100 + (zoom - 1) / 4 * 100)

    @staticmethod
    def _from_slider(value):
        return 0.1 + value / 100 * 0.9 if value <= 100 else 1 + (value - 100) / 100 * 4

    def _slider_moved(self, value):
        if self.slider.signalsBlocked():
            return
        zoom = self._from_slider(value)
        if abs(zoom - 1) < 0.04:  # %100'e yapış
            zoom = 1.0
        self.zoomRequested.emit(zoom)

    def _step(self, direction):
        # Word: 10'luk adımlar
        current = round(self._zoom * 100)
        target = (current // 10 + 1) * 10 if direction > 0 else ((current - 1) // 10) * 10
        self.zoomRequested.emit(max(10, min(500, target)) / 100)

    def set_zoom(self, zoom):
        self._zoom = zoom
        self.slider.blockSignals(True)
        self.slider.setValue(self._to_slider(zoom))
        self.slider.blockSignals(False)
        self.percent.setText(f"%{round(zoom * 100)}")


class LevelMeter(QWidget):
    """Durum çubuğunda kayıt sırasında görünen küçük ses seviyesi göstergesi (LED çubuk).

    Ölçek desibeldir: doğrusal çizilse kısık bir mikrofonun konuşması çubuğun ilk yüzde beşinde ezilir.
    Konuşma algılanmadan önce soluk mavi, sonra yeşil; yüksekte sarı, kırpılma bölgesinde kırmızı yanar.
    Koyu tepe çizgisi en yüksek değeri kısa süre tutar ve yavaşça iner.
    """

    FLOOR_DB = -60.0
    SEGMENTS = 20
    PEAK_FALL_DB = 1.5  # her güncellemede tepe çizgisinin inişi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(136, 20)  # çubuk 124 px; sağda pencere kenarından boşluk
        self.setToolTip("Mikrofon ses seviyesi — konuşurken çubuk yeşilin ortasına kadar dolmalı")
        self.reset()

    def reset(self):
        self._rms_db = self.FLOOR_DB
        self._hold_db = self.FLOOR_DB
        self._speaking = False
        self.update()

    @classmethod
    def to_db(cls, amplitude):
        return cls.FLOOR_DB if amplitude <= 1e-5 else max(cls.FLOOR_DB, 20 * math.log10(amplitude))

    @classmethod
    def to_fill(cls, db):
        return min(1.0, max(0.0, (db - cls.FLOOR_DB) / -cls.FLOOR_DB))

    def set_level(self, rms, peak, speaking):
        self._rms_db = self.to_db(rms)
        peak_db = self.to_db(peak)
        self._hold_db = peak_db if peak_db >= self._hold_db else max(peak_db, self._hold_db - self.PEAK_FALL_DB)
        self._speaking = speaking
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        bar = QRectF(2, 5, self.width() - 14, 10)
        gap = 1.0
        width = (bar.width() - gap * (self.SEGMENTS - 1)) / self.SEGMENTS
        lit = round(self.to_fill(self._rms_db) * self.SEGMENTS)
        for i in range(self.SEGMENTS):
            position = (i + 1) / self.SEGMENTS
            if i >= lit:
                color = QColor("#dcdcdc")
            elif not self._speaking:
                color = QColor("#8fa9c9")
            elif position > 0.92:
                color = QColor("#d9534f")
            elif position > 0.78:
                color = QColor("#e0a030")
            else:
                color = QColor("#3fae68")
            p.fillRect(QRectF(bar.left() + i * (width + gap), bar.top(), width, bar.height()), color)
        hold = self.to_fill(self._hold_db)
        if hold > 0:
            x = round(bar.left() + hold * (bar.width() - 2))
            p.fillRect(QRectF(x, bar.top() - 2, 2, bar.height() + 4), QColor("#424242"))


class TableGridPicker(QWidget):
    """Word'deki gibi fareyle satır×sütun seçilen tablo ızgarası."""

    chosen = Signal(int, int)  # satır, sütun

    COLS, ROWS, CELL, GAP = 10, 8, 16, 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._rows = self._cols = 0
        width = self.COLS * (self.CELL + self.GAP) + 16
        height = self.ROWS * (self.CELL + self.GAP) + 40
        self.setFixedSize(width, height)

    def _cell_at(self, pos):
        x, y = pos.x() - 8, pos.y() - 30
        if x < 0 or y < 0:
            return 0, 0
        col = min(self.COLS, int(x // (self.CELL + self.GAP)) + 1)
        row = min(self.ROWS, int(y // (self.CELL + self.GAP)) + 1)
        return row, col

    def mouseMoveEvent(self, event):
        cell = self._cell_at(event.position())
        if cell != (self._rows, self._cols):
            self._rows, self._cols = cell
            self.update()

    def leaveEvent(self, _):
        self._rows = self._cols = 0
        self.update()

    def mouseReleaseEvent(self, event):
        rows, cols = self._cell_at(event.position())
        if rows and cols:
            self.chosen.emit(rows, cols)

    def paintEvent(self, _):
        p = QPainter(self)
        title = f"{self._cols}x{self._rows} Tablo" if self._rows else "Tablo Ekle"
        p.setPen(QColor(theme.TEXT))
        font = p.font()
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(8, 4, self.width() - 16, 22), Qt.AlignLeft | Qt.AlignVCenter, title)
        for r in range(self.ROWS):
            for c in range(self.COLS):
                x = 8 + c * (self.CELL + self.GAP) + 0.5
                y = 30 + r * (self.CELL + self.GAP) + 0.5
                active = r < self._rows and c < self._cols
                p.setPen(QColor("#f29436" if active else "#b8b8b8"))
                p.setBrush(QColor("#fde7d2" if active else "#ffffff"))
                p.drawRect(QRectF(x, y, self.CELL - 1, self.CELL - 1))


class InsertTableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tablo Ekle")
        form = QFormLayout(self)
        form.setContentsMargins(16, 16, 16, 12)
        form.setSpacing(10)
        self.cols = QSpinBox(minimum=1, maximum=63, value=5)
        self.rows = QSpinBox(minimum=1, maximum=500, value=2)
        form.addRow("Sütun sayısı:", self.cols)
        form.addRow("Satır sayısı:", self.rows)
        buttons = QDialogButtonBox()
        ok = buttons.addButton("Tamam", QDialogButtonBox.AcceptRole)
        ok.setDefault(True)
        buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class _BarSeparator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(13)
        self.hide()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(QRectF(6, 5, 1, max(0, self.height() - 10)), QColor(theme.BORDER))


class CommandBar(QWidget):
    """Komut çubuğu: düğmeler en çok MAX_ROWS satıra yayılır, sığmayanlar sağdaki » menüsüne düşer.
    Düğmeler Alt ile (ya da menüsüz düğmelerde doğrudan) sürüklenerek yeniden sıralanabilir; sıra ve gizlenenler
    pencerede saklanır. (Qt'nin QToolBar'ı bir yerleşim içinde taşma düğmesini açamadığı için yerleşim burada.)"""

    SPACING = 1
    ROW_SPACING = 3
    MAX_ROWS = 2

    orderChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = []          # {key, label, group, widget}
        self.hidden = set()
        self.order = []            # kullanıcı sırası (anahtarlar); boşsa eklenme sırası
        self.overflow = []
        self.rows_used = 1
        self._separators = []
        self._press = None         # (entry, konum)
        self._drop_index = None
        self.more = QToolButton(self, objectName="moreButton")
        self.more.setIcon(icons.icon("more"))
        self.more.setIconSize(QSize(20, 20))
        self.more.setToolTip("Sığmayan komutlar")
        self.more.setFocusPolicy(Qt.NoFocus)
        self.more.setPopupMode(QToolButton.InstantPopup)
        self.more.setMenu(QMenu(self.more))
        self.more.menu().aboutToShow.connect(self._fill_more)
        self.more.hide()
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # --- öğeler ------------------------------------------------------------

    def add_item(self, key, label, group, widget):
        widget.setParent(self)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)
        entry = {"key": key, "label": label, "group": group, "widget": widget}
        self.entries.append(entry)
        self._separators.append(_BarSeparator(self))
        self._relayout()
        return entry

    def set_hidden(self, keys):
        self.hidden = set(keys)
        self._relayout()

    def set_order(self, keys):
        """Kullanıcının düğme sırası; listede olmayanlar kendi yerlerinde kalır."""
        self.order = [k for k in keys if any(e["key"] == k for e in self.entries)]
        self._relayout()

    def ordered_entries(self):
        if not self.order:
            return list(self.entries)
        index = {key: i for i, key in enumerate(self.order)}
        default = {e["key"]: i for i, e in enumerate(self.entries)}
        return sorted(self.entries, key=lambda e: (index.get(e["key"], len(index) + default[e["key"]]),))

    def current_order(self):
        return [e["key"] for e in self.ordered_entries()]

    def is_shown(self, key):
        return any(e["key"] == key and e["widget"].isVisible() for e in self.entries)

    # --- yerleşim ------------------------------------------------------------

    def _item_width(self, widget):
        # sabit genişlikli kutularda (yazı tipi boyutu gibi) sizeHint gerçek genişlikten küçük olabilir
        return max(widget.sizeHint().width(), widget.minimumWidth())

    def _row_height(self):
        heights = [e["widget"].sizeHint().height() for e in self.entries] + [self.more.sizeHint().height()]
        return max(heights) if heights else 28

    def sizeHint(self):
        return QSize(400, self.rows_used * self._row_height() + (self.rows_used - 1) * self.ROW_SPACING)

    def minimumSizeHint(self):
        return QSize(self.more.sizeHint().width(), self.sizeHint().height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def showEvent(self, event):
        super().showEvent(event)
        self._relayout()

    def _plan(self, width, rows_allowed):
        """Öğeleri satırlara yerleştirir: [(satır, x, öğe/ayırıcı)], taşanlar ve kullanılan satır sayısı."""
        visible = [e for e in self.ordered_entries() if e["key"] not in self.hidden]
        placed, overflow = [], []
        row, x, previous_group = 0, 0, None
        for entry in visible:
            item_width = self._item_width(entry["widget"])
            separator = previous_group is not None and entry["group"] != previous_group
            needed = item_width + (self.SPACING + 13 if separator else self.SPACING if x else 0)
            if x + needed > width:
                if row + 1 < rows_allowed:
                    row, x, separator = row + 1, 0, False
                    needed = item_width
                else:
                    overflow = visible[visible.index(entry):]
                    break
            if separator:
                placed.append((row, x + self.SPACING, "sep"))
                x += self.SPACING + 13
            elif x:
                x += self.SPACING
            placed.append((row, x, entry))
            x += item_width
            previous_group = entry["group"]
        return placed, overflow, row + 1

    def _relayout(self):
        for entry in self.entries:
            entry["widget"].hide()
        for separator in self._separators:
            separator.hide()
        if self.width() <= 1:
            return
        placed, overflow, rows = self._plan(self.width(), self.MAX_ROWS)
        if overflow:   # » düğmesine yer bırak
            placed, overflow, rows = self._plan(max(1, self.width() - self.more.sizeHint().width() - 4), self.MAX_ROWS)
        self.overflow = overflow
        if rows != self.rows_used:
            self.rows_used = rows
            self.updateGeometry()
        row_height = self._row_height()
        separators = iter(self._separators)
        for row, x, item in placed:
            widget = next(separators) if item == "sep" else item["widget"]
            height = row_height if item == "sep" else min(row_height, widget.sizeHint().height())
            y = row * (row_height + self.ROW_SPACING) + (row_height - height) // 2
            widget.setGeometry(int(x), int(y), int(13 if item == "sep" else self._item_width(widget)), int(height))
            widget.show()
        if overflow:
            hint = self.more.sizeHint()
            self.more.setGeometry(self.width() - hint.width(), (self.height() - hint.height()) // 2,
                                  hint.width(), hint.height())
            self.more.show()
            self.more.raise_()
        else:
            self.more.hide()

    # --- sürükleyerek sıralama ------------------------------------------------

    def _entry_for(self, widget):
        while widget is not None and widget is not self:
            for entry in self.entries:
                if entry["widget"] is widget:
                    return entry
            widget = widget.parentWidget()
        return None

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            entry = self._entry_for(watched)
            if entry is not None:
                if event.modifiers() & Qt.AltModifier:
                    self._start_drag(entry)      # Alt + sürükle: her düğme için
                    return True
                menu_button = isinstance(entry["widget"], QToolButton) and entry["widget"].menu() is not None
                self._press = None if menu_button else (entry, event.globalPosition().toPoint())
        elif event.type() == QEvent.MouseMove and self._press is not None:
            entry, start = self._press
            if (event.globalPosition().toPoint() - start).manhattanLength() >= QApplication.startDragDistance():
                self._press = None
                if isinstance(entry["widget"], QToolButton):
                    entry["widget"].setDown(False)
                self._start_drag(entry)
                return True
        elif event.type() == QEvent.MouseButtonRelease:
            self._press = None
        return super().eventFilter(watched, event)

    def _start_drag(self, entry):
        widget = entry["widget"]
        drag = QDrag(self)
        data = QMimeData()
        data.setData(BAR_ITEM_MIME, entry["key"].encode())
        drag.setMimeData(data)
        pixmap = widget.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        try:
            drag.exec(Qt.MoveAction)
        finally:
            QApplication.restoreOverrideCursor()
            self._drop_index = None
            self.update()

    def _insert_index(self, position):
        """Bırakma noktasına en yakın ekleme yeri (görünür öğeler arasında)."""
        visible = [e for e in self.ordered_entries() if e["key"] not in self.hidden and e["widget"].isVisible()]
        row_height = self._row_height() + self.ROW_SPACING
        row = min(max(0, position.y() // row_height), max(0, self.rows_used - 1))
        best, index = None, len(visible)
        for i, entry in enumerate(visible):
            rect = entry["widget"].geometry()
            entry_row = rect.center().y() // row_height
            for edge, candidate in ((rect.left(), i), (rect.right(), i + 1)):
                distance = (abs(entry_row - row) * 10000) + abs(position.x() - edge)
                if best is None or distance < best:
                    best, index = distance, candidate
        return index, visible

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(BAR_ITEM_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat(BAR_ITEM_MIME):
            return
        self._drop_index = self._insert_index(event.position().toPoint())
        self.update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._drop_index = None
        self.update()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(BAR_ITEM_MIME):
            return
        key = bytes(event.mimeData().data(BAR_ITEM_MIME)).decode()
        index, visible = self._insert_index(event.position().toPoint())
        order = self.current_order()
        target_key = visible[index]["key"] if index < len(visible) else None
        order.remove(key)
        order.insert(order.index(target_key) if target_key in order else len(order), key)
        self._drop_index = None
        self.set_order(order)
        self.orderChanged.emit(order)
        event.acceptProposedAction()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_index is None:
            return
        index, visible = self._drop_index
        painter = QPainter(self)
        painter.setPen(QPen(QColor(theme.ACCENT), 2))
        if visible:
            rect = visible[min(index, len(visible) - 1)]["widget"].geometry()
            x = rect.left() - 1 if index < len(visible) else rect.right() + 1
            painter.drawLine(x, rect.top(), x, rect.bottom())

    # --- taşma menüsü ---------------------------------------------------------

    def _fill_more(self):
        menu = self.more.menu()
        menu.clear()
        group = None
        for entry in self.overflow:
            if entry["key"] in self.hidden:
                continue
            if group is not None and entry["group"] != group:
                menu.addSeparator()
            group = entry["group"]
            self._add_to_menu(menu, entry)

    def _add_to_menu(self, menu, entry):
        widget, label = entry["widget"], entry["label"]
        buttons = [widget] if isinstance(widget, QToolButton) else widget.findChildren(QToolButton)
        if not buttons:
            if isinstance(widget, QWidget) and widget.findChildren(QComboBox):
                combo = widget.findChildren(QComboBox)[0]
                if not isinstance(combo, QFontComboBox) and combo.count() <= 30:
                    submenu = menu.addMenu(label)
                    for i in range(combo.count()):
                        action = submenu.addAction(combo.itemText(i))
                        action.triggered.connect(lambda _=False, c=combo, i=i: (c.setCurrentIndex(i), c.activated.emit(i),
                                                                               c.textActivated.emit(c.itemText(i))))
            return
        button = buttons[0]
        action = button.defaultAction()
        own_menu = button.menu()
        if action is not None and own_menu is None:
            menu.addAction(action)
            return
        icon = action.icon() if action is not None else button.icon()
        if action is not None:
            menu.addAction(action)
        if own_menu is not None:
            submenu_action = menu.addMenu(own_menu)
            submenu_action.setText(f"{label} Seçenekleri" if action is not None else label)
            submenu_action.setIcon(icon)
            # renk paleti, tablo ızgarası gibi gömülü panellerden seçim yapılınca ana menü de kapansın
            own_menu.aboutToHide.connect(lambda: QTimer.singleShot(0, self._close_more_if_done))

    def _close_more_if_done(self):
        menu = self.more.menu()
        if menu.isVisible() and not menu.underMouse() and QApplication.activePopupWidget() is menu:
            menu.close()


def bar_item_icon(widget):
    """Komut çubuğu öğesinin ikonu (menü ve özelleştirme listesinde göstermek için)."""
    buttons = [widget] if isinstance(widget, QToolButton) else widget.findChildren(QToolButton)
    for button in buttons:
        action = button.defaultAction()
        icon = action.icon() if action is not None else button.icon()
        if not icon.isNull():
            return icon
    return QIcon()


class CommandBarDialog(QDialog):
    """Komut çubuğunda hangi düğmelerin görüneceğini seçme penceresi (gruplu, işaret kutulu)."""

    def __init__(self, groups, hidden, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Komut Çubuğunu Özelleştir")
        self.resize(380, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        info = QLabel("İşaretli düğmeler komut çubuğunda görünür. Gizlenen düğmelerin klavye kısayolları "
                      "çalışmaya devam eder. Pencere darsa sığmayan düğmeler çubuğun sonundaki » menüsündedir.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setIconSize(QSize(20, 20))
        self._items = []
        for group in groups:
            parent_item = QTreeWidgetItem(self.tree, [group["name"]])
            parent_item.setFlags(parent_item.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
            for entry in group["items"]:
                child = QTreeWidgetItem(parent_item, [entry["label"]])
                child.setIcon(0, bar_item_icon(entry["widget"]))
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked if entry["key"] in hidden else Qt.Checked)
                child.setData(0, Qt.UserRole, entry["key"])
                self._items.append(child)
            parent_item.setExpanded(True)
        layout.addWidget(self.tree, 1)

        buttons = QDialogButtonBox()
        show_all = buttons.addButton("Tümünü Göster", QDialogButtonBox.ResetRole)
        show_all.clicked.connect(lambda: [item.setCheckState(0, Qt.Checked) for item in self._items])
        ok = buttons.addButton("Tamam", QDialogButtonBox.AcceptRole)
        ok.setDefault(True)
        buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def hidden(self):
        return {item.data(0, Qt.UserRole) for item in self._items if item.checkState(0) != Qt.Checked}


class MessageBar(QWidget):
    """Sayfanın üstünde görünen, kapatılabilir bilgi çubuğu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("commandArea")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 0, 8, 6)
        frame = QFrame(objectName="messageBar")
        outer.addWidget(frame)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(8)

        icon = QLabel()
        icon.setPixmap(icons.icon("info", "#8a6d00").pixmap(20, 20))
        layout.addWidget(icon)
        self.label = QLabel()
        self.label.setWordWrap(True)
        layout.addWidget(self.label, 1)
        self.button_box = QHBoxLayout()
        self.button_box.setSpacing(6)
        layout.addLayout(self.button_box)

        close = QToolButton()
        close.setIcon(icons.icon("close"))
        close.setIconSize(QSize(14, 14))
        close.setToolTip("Kapat")
        close.clicked.connect(self.hide)
        layout.addWidget(close)
        self.hide()

    def show_message(self, text, buttons=()):
        """buttons: (metin, fonksiyon) çiftleri. Butona basınca çubuk kapanır."""
        self.label.setText(text)
        while self.button_box.count():
            item = self.button_box.takeAt(0)
            item.widget().deleteLater()
        for caption, callback in buttons:
            button = QPushButton(caption)
            button.clicked.connect(self.hide)
            button.clicked.connect(callback)
            self.button_box.addWidget(button)
        self.show()


class AboutDialog(QDialog):
    """Sözcük Hakkında: sürüm, künye ve kullanılan açık kaynak bileşenler."""

    CREDITS = [
        ("PySide6 (Qt)", "arayüz", "LGPL"),
        ("python-docx", "Word belgeleri (.docx)", "MIT"),
        ("pdfminer.six", "PDF okuma", "MIT"),
        ("olefile", "eski Word belgeleri (.doc) metni", "BSD"),
        ("comtypes", "Windows yazım denetimi ve dönüştürme", "MIT"),
        ("faster-whisper + Whisper modeli", "sesle yazma", "MIT"),
        ("CTranslate2 + SentencePiece", "çeviri motoru", "MIT / Apache 2.0"),
        ("Argos Translate dil paketleri + OPUS-MT modelleri", "çeviri", "MIT / CC-BY 4.0"),
        ("ONNX Runtime", "sesli okuma motoru", "MIT"),
        ("Piper (VITS) sesi, dfki Türkçe temel modelinden", "sesli okuma sesi", "CC BY-NC-SA 4.0"),
    ]

    def __init__(self, parent=None, version="", developers=""):
        super().__init__(parent)
        self.setWindowTitle("Sözcük Hakkında")
        self.setFixedWidth(460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(10)

        title = QLabel("Sözcük")
        font = title.font()
        font.setPointSizeF(font.pointSizeF() + 8)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet(f"color: {theme.ACCENT};")
        layout.addWidget(title)

        subtitle = QLabel(f"Sürüm {version}  ·  Türkçe kelime işlemci")
        subtitle.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(subtitle)

        credit = QLabel(developers)
        credit_font = credit.font()
        credit_font.setBold(True)
        credit.setFont(credit_font)
        layout.addWidget(credit)

        privacy = QLabel("Yazım denetimi, sesle yazma ve çeviri bu bilgisayarda çalışır; belgeleriniz "
                         "hiçbir sunucuya gönderilmez.")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)

        components = QLabel("Kullanılan açık kaynak bileşenler:\n" + "\n".join(
            f"•  {name} — {use} ({licence})" for name, use, licence in self.CREDITS))
        components.setWordWrap(True)
        components.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(components)

        buttons = QDialogButtonBox()
        close_button = buttons.addButton("Kapat", QDialogButtonBox.AcceptRole)
        close_button.setDefault(True)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
