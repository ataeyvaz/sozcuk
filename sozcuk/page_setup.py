"""Sayfa düzeni: Word'deki "Düzen" sekmesinin kenar boşlukları, yönlendirme ve boyut seçenekleri.

Komut çubuğundaki "Sayfa Düzeni" menüsü hazır ayarları sunar; "Özel Kenar Boşlukları…" ve "Diğer Kâğıt
Boyutları…" önizlemeli Sayfa Yapısı penceresini açar. Değerler belgeye aittir ve .docx'e yazılır.
"""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QActionGroup, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import icons, page_numbers, styles

CUSTOM = "custom"


def cm(pixels):
    return pixels / styles.PX_PER_CM


def cm_text(pixels):
    return f"{cm(pixels):.2f}".rstrip("0").rstrip(".").replace(".", ",") + " cm"


def matching_preset(document):
    margins = styles.all_margins(document)
    for name, *values in styles.MARGIN_PRESETS:
        if all(abs(cm(m) - v) < 0.01 for m, v in zip(margins, values)):
            return name
    return None


class PagePreview(QWidget):
    """Sayfanın oranını ve kenar boşluklarını gösteren küçük önizleme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 170)
        self.values = (21.0, 29.7, 2.5, 2.5, 2.5, 2.5)  # cm: genişlik, yükseklik, üst, alt, sol, sağ

    def sizeHint(self):
        return QSize(170, 190)

    def set_values(self, *values):
        self.values = values
        self.update()

    def paintEvent(self, _):
        width, height, top, bottom, left, right = self.values
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        area = QRectF(self.rect()).adjusted(12, 12, -12, -12)
        scale = min(area.width() / width, area.height() / height)
        page = QRectF(0, 0, width * scale, height * scale)
        page.moveCenter(area.center())
        p.fillRect(page.translated(2, 2), QColor(0, 0, 0, 30))
        p.fillRect(page, QColor("#ffffff"))
        p.setPen(QPen(QColor("#b0b0b0"), 1))
        p.drawRect(page)
        text = QRectF(page.left() + left * scale, page.top() + top * scale,
                      max(0.0, page.width() - (left + right) * scale), max(0.0, page.height() - (top + bottom) * scale))
        p.setPen(QPen(QColor("#185abd"), 1, Qt.DashLine))
        p.drawRect(text)
        p.setPen(QPen(QColor("#c8c8c8"), 1))
        line_gap = max(4.0, 7 * scale / 3)
        y = text.top() + line_gap
        while y < text.bottom() - 2:
            p.drawLine(QPointF(text.left() + 3, y), QPointF(text.right() - 3, y))
            y += line_gap


class PageSetupDialog(QDialog):
    """Sayfa Yapısı: kenar boşlukları, yönlendirme ve kâğıt boyutu (önizlemeli)."""

    def __init__(self, document, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sayfa Yapısı")
        width, height = styles.page_size(document)
        top, bottom, left, right = styles.all_margins(document)

        def spin(value, maximum=60.0):
            box = QDoubleSpinBox(decimals=2, minimum=0.0, maximum=maximum, singleStep=0.1, suffix=" cm")
            box.setValue(round(cm(value), 2))
            box.setFixedWidth(96)
            box.valueChanged.connect(self._changed)
            return box

        margins = QGroupBox("Kenar Boşlukları")
        grid = QGridLayout(margins)
        self.top, self.bottom, self.left, self.right = spin(top), spin(bottom), spin(left), spin(right)
        for row, (label_a, box_a, label_b, box_b) in enumerate((("Üst:", self.top, "Alt:", self.bottom),
                                                                ("Sol:", self.left, "Sağ:", self.right))):
            grid.addWidget(QLabel(label_a), row, 0)
            grid.addWidget(box_a, row, 1)
            grid.addWidget(QLabel(label_b), row, 2)
            grid.addWidget(box_b, row, 3)

        orientation = QGroupBox("Yönlendirme")
        row = QHBoxLayout(orientation)
        self.portrait = QRadioButton("Dikey")
        self.portrait.setIcon(icons.icon("portrait"))
        self.landscape = QRadioButton("Yatay")
        self.landscape.setIcon(icons.icon("landscape"))
        group = QButtonGroup(self)
        group.addButton(self.portrait)
        group.addButton(self.landscape)
        (self.landscape if width > height else self.portrait).setChecked(True)
        self.landscape.toggled.connect(self._orientation_changed)
        row.addWidget(self.portrait)
        row.addWidget(self.landscape)
        row.addStretch()

        paper = QGroupBox("Kâğıt Boyutu")
        paper_grid = QGridLayout(paper)
        self.paper = QComboBox()
        for key, label, w, h in styles.PAPER_SIZES:
            self.paper.addItem(f"{label}  ({w:g} × {h:g} cm)".replace(".", ","), key)
        self.paper.addItem("Özel boyut", CUSTOM)
        short, long = sorted((width, height))
        self.page_width, self.page_height = spin(short, 120.0), spin(long, 120.0)
        for box in (self.page_width, self.page_height):
            box.setMinimum(5.0)
        name = styles.paper_name(document)
        self.paper.setCurrentIndex(self.paper.findData(name if name else CUSTOM))
        self.paper.currentIndexChanged.connect(self._paper_changed)
        paper_grid.addWidget(self.paper, 0, 0, 1, 4)
        paper_grid.addWidget(QLabel("Genişlik:"), 1, 0)
        paper_grid.addWidget(self.page_width, 1, 1)
        paper_grid.addWidget(QLabel("Yükseklik:"), 1, 2)
        paper_grid.addWidget(self.page_height, 1, 3)

        self.preview = PagePreview()
        self.warning = QLabel()
        self.warning.setStyleSheet("color:#a4262c;")
        self.warning.setWordWrap(True)

        left_column = QVBoxLayout()
        left_column.addWidget(margins)
        left_column.addWidget(orientation)
        left_column.addWidget(paper)
        right_column = QVBoxLayout()
        right_column.addWidget(QLabel("Önizleme"))
        right_column.addWidget(self.preview, 1)
        body = QHBoxLayout()
        body.addLayout(left_column)
        body.addLayout(right_column)

        buttons = QDialogButtonBox()
        ok = buttons.addButton("Tamam", QDialogButtonBox.AcceptRole)
        ok.setDefault(True)
        buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(body)
        layout.addWidget(self.warning)
        layout.addWidget(buttons)
        self._changed()

    def _paper_changed(self):
        key = self.paper.currentData()
        for name, _, w, h in styles.PAPER_SIZES:
            if name == key:
                for box, value in ((self.page_width, w), (self.page_height, h)):
                    box.blockSignals(True)
                    box.setValue(value)
                    box.blockSignals(False)
        self._changed()

    def _orientation_changed(self):
        # Word gibi: yönlendirme değişince kenar boşlukları da döner
        top, bottom, left, right = (b.value() for b in (self.top, self.bottom, self.left, self.right))
        if self.landscape.isChecked():
            values = (left, right, bottom, top)
        else:
            values = (right, left, top, bottom)
        for box, value in zip((self.top, self.bottom, self.left, self.right), values):
            box.blockSignals(True)
            box.setValue(value)
            box.blockSignals(False)
        self._changed()

    def _changed(self):
        # boyut kutuları elle değiştirildiyse listede karşılığı olan kâğıdı seç
        short, long = sorted((self.page_width.value(), self.page_height.value()))
        key = CUSTOM
        for name, _, w, h in styles.PAPER_SIZES:
            if abs(short - w) < 0.01 and abs(long - h) < 0.01:
                key = name
        if self.paper.currentData() != key:
            self.paper.blockSignals(True)
            self.paper.setCurrentIndex(self.paper.findData(key))
            self.paper.blockSignals(False)
        width, height, top, bottom, left, right = self.values_cm()
        self.preview.set_values(width, height, top, bottom, left, right)
        problems = []
        if height - top - bottom < cm(styles.MIN_TEXT_HEIGHT):
            problems.append("üst ve alt kenar boşlukları")
        if width - left - right < cm(styles.MIN_TEXT_WIDTH):
            problems.append("sol ve sağ kenar boşlukları")
        self.warning.setText(
            f"Uyarı: {' ile '.join(problems)} sayfaya sığmıyor; en az 3 cm yazı alanı kalacak şekilde küçültülecek."
            if problems else "")

    def values_cm(self):
        short, long = sorted((self.page_width.value(), self.page_height.value()))
        width, height = (long, short) if self.landscape.isChecked() else (short, long)
        return (width, height, self.top.value(), self.bottom.value(), self.left.value(), self.right.value())

    def values_px(self):
        width, height, top, bottom, left, right = (v * styles.PX_PER_CM for v in self.values_cm())
        return dict(width=width, height=height, top=top, bottom=bottom, left=left, right=right)


class StartNumberDialog(QDialog):
    """Sayfa numarasının kaçtan başlayacağı (başka bir dosyadan devam eden belgeler için)."""

    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Başlangıç Numarası")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel("İlk sayfanın numarası:"))
        self.spin = QSpinBox(minimum=0, maximum=9999, value=int(value))
        self.spin.setFixedWidth(96)
        row.addWidget(self.spin)
        row.addStretch(1)
        layout.addLayout(row)
        note = QLabel("Belge başka bir dosyadan devam ediyorsa numaralandırmayı oradan sürdürebilirsiniz.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#616161;")
        layout.addWidget(note)
        buttons = QDialogButtonBox()
        ok = buttons.addButton("Tamam", QDialogButtonBox.AcceptRole)
        ok.setDefault(True)
        buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self):
        return self.spin.value()


def build_number_menu(editor, parent, refocus):
    """Sayfa numarası: aç/kapat, konum, biçim, başlangıç numarası (Word'ün Sayfa Numarası menüsü gibi)."""
    menu = QMenu(parent)
    toggle = menu.addAction("Sayfa Numarası Ekle")
    toggle.setCheckable(True)
    toggle.triggered.connect(lambda on: refocus(lambda: editor.set_page_numbers(enabled=on)))
    menu.addSeparator()

    position_menu = menu.addMenu("Konum")
    position_group = QActionGroup(menu)
    position_actions = {}
    for key, label, _, _ in page_numbers.POSITIONS:
        action = position_menu.addAction(label)
        action.setCheckable(True)
        position_group.addAction(action)
        action.triggered.connect(lambda _=False, k=key: refocus(lambda: editor.set_page_numbers(enabled=True, position=k)))
        position_actions[key] = action

    format_menu = menu.addMenu("Biçim")
    format_group = QActionGroup(menu)
    format_actions = {}
    for key, label, _ in page_numbers.FORMATS:
        action = format_menu.addAction(label)
        action.setCheckable(True)
        format_group.addAction(action)
        action.triggered.connect(lambda _=False, k=key: refocus(lambda: editor.set_page_numbers(enabled=True, format=k)))
        format_actions[key] = action

    start_action = menu.addAction("Başlangıç Numarası…")

    def ask_start():
        dialog = StartNumberDialog(editor.page_numbers().start, parent.window())
        if dialog.exec() == QDialog.Accepted:
            refocus(lambda: editor.set_page_numbers(enabled=True, start=dialog.value()))

    start_action.triggered.connect(ask_start)

    def sync():
        config = editor.page_numbers()
        toggle.setChecked(config.enabled)
        for group, actions, current in ((position_group, position_actions, config.position),
                                        (format_group, format_actions, config.format)):
            group.setExclusive(False)
            for key, action in actions.items():
                action.setChecked(config.enabled and key == current)
            group.setExclusive(True)
        position_menu.setEnabled(config.enabled)
        format_menu.setEnabled(config.enabled)
        start_action.setText(f"Başlangıç Numarası… ({config.start})" if config.start != 1 else "Başlangıç Numarası…")

    menu.aboutToShow.connect(sync)
    menu.sync = sync
    return menu


def build_menu(editor, parent, refocus):
    """Sayfa Düzeni menüsü: Kenar Boşlukları, Yönlendirme, Boyut alt menüleri ve Sayfa Yapısı…"""
    menu = QMenu(parent)
    margins_menu = menu.addMenu(icons.icon("margins"), "Kenar Boşlukları")
    orientation_menu = menu.addMenu(icons.icon("orientation"), "Yönlendirme")
    size_menu = menu.addMenu(icons.icon("paper_size"), "Boyut")
    number_menu = build_number_menu(editor, parent, refocus)
    number_menu.setTitle("Sayfa Numarası")
    number_menu.setIcon(icons.icon("page_number"))
    menu.addMenu(number_menu)
    menu.addSeparator()
    setup_action = menu.addAction(icons.icon("page_setup"), "Sayfa Yapısı…")

    def open_dialog():
        dialog = PageSetupDialog(editor.document(), parent.window())
        if dialog.exec() == QDialog.Accepted:
            refocus(lambda: editor.set_page_setup(**dialog.values_px()))

    setup_action.triggered.connect(open_dialog)

    margin_group = QActionGroup(menu)
    margin_actions = {}
    for name, top, bottom, left, right in styles.MARGIN_PRESETS:
        label = f"{name}\tÜst {top:g}  Alt {bottom:g}  Sol {left:g}  Sağ {right:g} cm".replace(".", ",")
        action = margins_menu.addAction(label)
        action.setCheckable(True)
        margin_group.addAction(action)
        values = {k: v * styles.PX_PER_CM for k, v in zip(("top", "bottom", "left", "right"), (top, bottom, left, right))}
        action.triggered.connect(lambda _=False, v=values: refocus(lambda: editor.set_page_setup(**v)))
        margin_actions[name] = action
    margins_menu.addSeparator()
    margins_menu.addAction("Özel Kenar Boşlukları…", open_dialog)

    orientation_group = QActionGroup(menu)
    portrait = orientation_menu.addAction(icons.icon("portrait"), "Dikey")
    landscape = orientation_menu.addAction(icons.icon("landscape"), "Yatay")
    for action, value in ((portrait, False), (landscape, True)):
        action.setCheckable(True)
        orientation_group.addAction(action)
        action.triggered.connect(lambda _=False, v=value: refocus(lambda: editor.set_orientation(v)))

    size_group = QActionGroup(menu)
    size_actions = {}
    for key, label, w, h in styles.PAPER_SIZES:
        action = size_menu.addAction(f"{label}\t{w:g} × {h:g} cm".replace(".", ","))
        action.setCheckable(True)
        size_group.addAction(action)
        action.triggered.connect(lambda _=False, k=key: refocus(lambda: editor.set_paper(k)))
        size_actions[key] = action
    size_menu.addSeparator()
    size_menu.addAction("Diğer Kâğıt Boyutları…", open_dialog)

    def sync():
        doc = editor.document()
        for group, actions, current in ((margin_group, margin_actions, matching_preset(doc)),
                                        (size_group, size_actions, styles.paper_name(doc))):
            group.setExclusive(False)
            for key, action in actions.items():
                action.setChecked(key == current)
            group.setExclusive(True)
        (landscape if styles.is_landscape(doc) else portrait).setChecked(True)
        number_menu.sync()

    menu.aboutToShow.connect(sync)
    menu.open_dialog = open_dialog
    return menu
