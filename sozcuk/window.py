"""Ana pencere: başlık şeridi, tek satır komut çubuğu, sayfalı editör, durum çubuğu ve dosya işlemleri."""

import json
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (

    QEventLoop,
    QMarginsF,
    QSettings,
    QSize,
    QSizeF,
    QStandardPaths,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QDesktopServices,
    QFont,
    QKeySequence,
    QPageLayout,
    QPageSize,
    QTextCursor,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFontComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from . import (
    cloud,
    converters,
    doc_text,
    docx_io,
    fonts,
    formats,
    icons,
    images,
    links,
    logbook,
    odt_io,
    page_setup,
    pdf_io,
    rtf_io,
    styles,
    symbols,
    tables,
    theme,
    translate as translate_module,
)
from .dictation import DictationController, vocabulary_path
from .help import show_help as open_help
from .spellcheck import SpellCheckController
from .vocabulary import Vocabulary
from .editor import Editor
from .find import FindBar
from .rulers import DocumentArea
from . import DEVELOPERS, __version__
from .widgets import (
    AboutDialog,
    ColorButton,
    CommandBar,
    CommandBarDialog,
    InsertTableDialog,
    MessageBar,
    TableGridPicker,
    ToggleSwitch,
    ZoomControl,
    bar_item_icon,
)

log = logbook.get("pencere")

AUTOSAVE_INTERVAL_MS = 2 * 60 * 1000
COUNTS_DELAY_MS = 400
AUTOSAVE_IDLE_MS = 4000
OPEN_FILTER = formats.open_filter()
LIBREOFFICE_URL = "https://www.libreoffice.org/download/download-libreoffice/"
CLOUD_AUTOSAVE_IDLE_MS = 2000   # bulut klasöründeki belge: yazmaya kısa ara verilince kaydet (canlı)
SAVE_RETRY_MS = 10000           # otomatik kayıt başarısızsa yeniden deneme
CLOUD_POLL_MS = 3000            # dosyanın başka yerde değişip değişmediğini yoklama aralığı


class BackgroundTask(QThread):
    """Uzun süren bir işi (ör. Word ile dönüştürme) arka planda çalıştırır; arayüz donmaz."""

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.function()
        except Exception as exc:  # çağıran tarafta kullanıcıya gösterilir
            self.error = exc


class PdfWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            self.done.emit(pdf_io.extract(self.path))
        except pdf_io.PdfError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # beklenmeyen PDF yapıları
            self.failed.emit(f"PDF dönüştürülemedi: {exc}")


class MainWindow(QMainWindow):
    untitled_counter = 0

    def __init__(self):
        super().__init__()
        self.settings = QSettings("Sözcük", "Sözcük")
        self.path = None
        self.display_name = self._next_untitled()
        self.session_id = uuid.uuid4().hex
        self.last_saved = None
        self._pdf_worker = None

        self.resize(1200, 860)
        self.setMinimumSize(760, 480)

        self.editor = Editor()
        central = QWidget(objectName="central")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        self.menu_row = QFrame(objectName="menuRow")
        layout.addWidget(self.menu_row)
        layout.addWidget(self._build_command_bar())
        self.message_bar = MessageBar()
        layout.addWidget(self.message_bar)
        self.find_bar = FindBar(self.editor, notify=lambda text: self.statusBar().showMessage(text, 5000))
        find_area = QWidget(objectName="commandArea")
        find_layout = QVBoxLayout(find_area)
        find_layout.setContentsMargins(8, 0, 8, 6)
        find_layout.addWidget(self.find_bar)
        find_area.setVisible(False)
        self.find_bar.visibilityChanged.connect(find_area.setVisible)
        self.find_area = find_area
        layout.addWidget(find_area)
        self.doc_area = DocumentArea(self.editor)
        layout.addWidget(self.doc_area, 1)
        self.setCentralWidget(central)

        self._build_file_actions()
        self._build_statusbar()
        self._connect_signals()
        # Kişisel sözlük: dikte ipuçları/düzeltmeleri ve yazım denetiminin "Sözlüğe Ekle" kelimeleri tek yerde
        self.vocabulary = Vocabulary(vocabulary_path())
        # Sesle yazma — tamamen yerel: ses ve dönüştürülen metin hiçbir sunucuya gönderilmez (dictation.py)
        self.dictation = DictationController(self.editor, self.act_dictate, self.mic_button, self.statusBar(),
                                             self.settings, self.vocabulary, notify=self.show_message, parent=self)
        # Yazım denetimi — Windows'un yerleşik Türkçe denetimi, çevrimdışı (spellcheck.py)
        self.spellcheck = SpellCheckController(self.editor, self.vocabulary, self.statusBar(), self.settings, self)
        self.editor.context_menu_hooks.append(self._link_menu)
        self.spellcheck.attach_shortcuts(self)
        self._build_menus()   # komut çubuğu, yazım denetimi ve dikte eylemlerini kullanır: en son kurulur

        # kurtarma kopyası periyodik; kayıtlı dosyalar yazmaya ara verilince kaydedilir (Word gibi)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start(AUTOSAVE_INTERVAL_MS)
        self.autosave_debounce = QTimer(self, singleShot=True, interval=AUTOSAVE_IDLE_MS)
        self.autosave_debounce.timeout.connect(self._autosave_file)
        self.editor.document().contentsChanged.connect(self._schedule_autosave)

        # Google Drive / OneDrive: dosya başka yerde (web, başka bilgisayar) değişirse fark et (cloud.py)
        self.tracker = cloud.ChangeTracker()
        self.change_timer = QTimer(self, interval=CLOUD_POLL_MS)
        self.change_timer.timeout.connect(self._check_external_change)
        self.change_timer.start()
        self._saving = False
        self._keep_format = False   # eski biçimdeki belge o biçimde kaydedilsin mi (kullanıcı seçti)

        self._after_load()
        theme.color_title_bar(self)
        QTimer.singleShot(300, self._offer_recovery)

    @classmethod
    def _next_untitled(cls):
        cls.untitled_counter += 1
        return f"Belge{cls.untitled_counter}"

    # =========================================================================
    # Arayüz kurulumu
    # =========================================================================

    def _action(self, icon_name, text, shortcut=None, slot=None, checkable=False, tip=None, icon_color=icons.INK):
        action = QAction(text, self)
        if icon_name:
            action.setIcon(icons.icon(icon_name, icon_color))
        action.setCheckable(checkable)
        tooltip = tip or text
        if shortcut:
            seq = QKeySequence(shortcut)
            action.setShortcut(seq)
            tooltip = f"{tooltip} ({seq.toString(QKeySequence.NativeText)})"
        action.setToolTip(tooltip)
        if slot:
            action.triggered.connect(slot)
        return action

    def _build_header(self):
        header = QFrame(objectName="header")
        header.setFixedHeight(40)
        row = QHBoxLayout(header)
        row.setContentsMargins(6, 0, 12, 0)
        row.setSpacing(2)

        left = QHBoxLayout()
        left.setSpacing(2)
        white = "#ffffff"
        self.act_save = self._action("save", "Kaydet", QKeySequence.Save, self.save, icon_color=white)
        self.act_undo = self._action("undo", "Geri Al", QKeySequence.Undo, self.editor.undo, icon_color=white)
        self.act_redo = self._action("redo", "Yinele", "Ctrl+Y", self.editor.redo, icon_color=white)
        for action in (self.act_save, self.act_undo, self.act_redo):
            button = QToolButton()
            button.setDefaultAction(action)
            button.setIconSize(QSize(20, 20))
            left.addWidget(button)
            self.addAction(action)
        self.act_undo.setEnabled(False)
        self.act_redo.setEnabled(False)

        center = QHBoxLayout()
        center.setSpacing(8)
        self.title_label = QLabel(objectName="docTitle")
        self.status_label = QLabel(objectName="docStatus")
        center.addWidget(self.title_label)
        center.addWidget(self.status_label)

        right = QHBoxLayout()
        right.setSpacing(8)
        right.addStretch()
        autosave_label = QLabel("Otomatik Kaydet")
        self.autosave_switch = ToggleSwitch()
        self.autosave_switch.setChecked(self.settings.value("autosave", True, type=bool))
        self.autosave_switch.setToolTip(
            "Açıkken belge birkaç dakikada bir kendiliğinden kaydedilir.\n"
            "Henüz kaydedilmemiş belgeler için kurtarma kopyası tutulur."
        )
        self.autosave_switch.toggled.connect(self._autosave_toggled)
        right.addWidget(autosave_label)
        right.addWidget(self.autosave_switch)
        right.addSpacing(6)
        self.act_help = self._action("help", "Yardım ve Nasıl Kullanılır", "F1", self.show_help, icon_color=white)
        self.addAction(self.act_help)
        help_button = QToolButton(objectName="helpButton")
        help_button.setDefaultAction(self.act_help)
        help_button.setIconSize(QSize(20, 20))
        right.addWidget(help_button)

        for part, stretch in ((left, 1), (center, 0), (right, 1)):
            box = QWidget()
            box.setLayout(part)
            part.setContentsMargins(0, 0, 0, 0)
            if part is left:
                part.addStretch()
            row.addWidget(box, stretch)
        return header

    def _build_menus(self):
        """Word'deki gibi konu başlıklarına göre menüler: Dosya, Düzen, Biçim, Ekle, Sayfa Düzeni, Görünüm, Yardım."""
        row = QHBoxLayout(self.menu_row)
        row.setContentsMargins(6, 0, 6, 0)
        row.setSpacing(0)
        ed = self.editor

        def add_menu(title, menu):
            button = QToolButton(objectName="menuButton")
            button.setText(title)
            button.setPopupMode(QToolButton.InstantPopup)
            button.setFocusPolicy(Qt.NoFocus)
            button.setMenu(menu)
            row.addWidget(button)
            return button

        def action(menu, icon_name, text, slot, shortcut=None, checkable=False):
            item = menu.addAction(text)
            if icon_name:
                item.setIcon(icons.icon(icon_name))
            if shortcut is not None:
                item.setShortcut(QKeySequence(shortcut))
                item.setShortcutVisibleInContextMenu(True)
            item.setCheckable(checkable)
            item.triggered.connect(slot)
            return item

        self.file_button = add_menu("Dosya", self.file_menu)
        self.file_button.setObjectName("menuButton")

        # --- Düzen
        edit_menu = QMenu(self)
        edit_menu.addAction(self.act_undo)
        edit_menu.addAction(self.act_redo)
        edit_menu.addSeparator()
        cut = action(edit_menu, "cut", "Kes", ed.cut, QKeySequence.Cut)
        copy = action(edit_menu, "copy", "Kopyala", ed.copy, QKeySequence.Copy)
        paste = action(edit_menu, "paste", "Yapıştır", ed.paste, QKeySequence.Paste)
        paste_text = action(edit_menu, "paste_text", "Yalnızca Metni Koru", lambda: ed.paste(plain=True), "Ctrl+Shift+V")
        edit_menu.addSeparator()
        action(edit_menu, None, "Tümünü Seç", ed.select_all, QKeySequence.SelectAll)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_find)
        edit_menu.addAction(self.act_replace)
        action(edit_menu, None, "Sonraki Bul", lambda: self._find_next(1), "F3")
        action(edit_menu, None, "Önceki Bul", lambda: self._find_next(-1), "Shift+F3")
        edit_menu.addSeparator()
        edit_menu.addAction(self.spellcheck.next_action)

        def update_edit():
            has_selection = ed.textCursor().hasSelection()
            cut.setEnabled(has_selection)
            copy.setEnabled(has_selection)
            can_paste = ed.can_paste()
            paste.setEnabled(can_paste)
            paste_text.setEnabled(can_paste)

        edit_menu.aboutToShow.connect(update_edit)
        add_menu("Düzen", edit_menu)

        # --- Biçim
        format_menu = QMenu(self)
        style_menu = format_menu.addMenu(icons.icon("bold"), "Stiller")
        for level, name in enumerate(styles.HEADING_NAMES):
            action(style_menu, None, name, lambda _=False, i=level: self._refocus(ed.set_heading, i))
        for act in (self.act_bold, self.act_italic, self.act_underline, self.act_strike):
            format_menu.addAction(act)
        size_menu = format_menu.addMenu(icons.icon("grow_font"), "Yazı Tipi Boyutu")
        action(size_menu, "grow_font", "Büyüt", lambda: self._refocus(ed.step_size, 1), "Ctrl+]")
        action(size_menu, "shrink_font", "Küçült", lambda: self._refocus(ed.step_size, -1), "Ctrl+[")
        size_menu.addSeparator()
        for size in styles.FONT_SIZES:
            action(size_menu, None, str(size), lambda _=False, v=size: self._refocus(ed.set_size, float(v)))
        color = format_menu.addMenu(icons.icon("font_color"), "Yazı Tipi Rengi")
        color.addMenu(self.color_button.menu()).setText("Renk Seç…")
        highlight = format_menu.addMenu(icons.icon("highlight"), "Metin Vurgu Rengi")
        highlight.addMenu(self.highlight_button.menu()).setText("Renk Seç…")
        format_menu.addSeparator()
        align_menu = format_menu.addMenu(icons.icon("align_left"), "Hizalama")
        for act in self.align_actions.values():
            align_menu.addAction(act)
        spacing_menu = format_menu.addMenu(icons.icon("line_spacing"), "Satır Aralığı")
        for act in self.spacing_actions.values():
            spacing_menu.addAction(act)
        list_menu = format_menu.addMenu(icons.icon("bullets"), "Listeler ve Girinti")
        list_menu.addAction(self.act_bullets)
        list_menu.addAction(self.act_numbers)
        list_menu.addSeparator()
        action(list_menu, "outdent", "Girintiyi Azalt", lambda: self._refocus(ed.change_indent, -1))
        action(list_menu, "indent", "Girintiyi Artır", lambda: self._refocus(ed.change_indent, 1))
        format_menu.addSeparator()
        action(format_menu, "clear_format", "Tüm Biçimlendirmeyi Temizle", lambda: self._refocus(ed.clear_formatting),
               "Ctrl+Space")
        action(format_menu, "add_font", "Yazı Tipi Ekle…", self._add_font)
        add_menu("Biçim", format_menu)

        # --- Ekle
        insert_menu = QMenu(self)
        insert_menu.addMenu(self.table_menu).setText("Tablo")
        insert_menu.addMenu(self.image_menu).setText("Resim")
        insert_menu.addMenu(self.symbol_menu).setText("Simge")
        for item, icon_name in ((insert_menu.actions()[0], "table"), (insert_menu.actions()[1], "image"),
                                (insert_menu.actions()[2], "symbol")):
            item.setIcon(icons.icon(icon_name))
        insert_menu.addAction(self.act_link)
        insert_menu.addSeparator()
        insert_menu.addAction(self.act_dictate)
        add_menu("Ekle", insert_menu)

        # --- Sayfa Düzeni (kenar boşlukları, yönlendirme, kâğıt boyutu)
        add_menu("Sayfa Düzeni", page_setup.build_menu(ed, self.menu_row, lambda change: self._refocus(change)))

        # --- Görünüm
        view_menu = QMenu(self)
        self.ruler_action = action(view_menu, "ruler", "Cetvel", lambda on: self.ruler_button.setChecked(on),
                                   checkable=True)
        view_menu.addSeparator()
        action(view_menu, "zoom_in", "Yakınlaştır", lambda: ed.set_zoom(ed.zoom() * 1.1), QKeySequence.ZoomIn)
        action(view_menu, "zoom_out", "Uzaklaştır", lambda: ed.set_zoom(ed.zoom() / 1.1), QKeySequence.ZoomOut)
        action(view_menu, None, "%100", lambda: ed.set_zoom(1.0))
        action(view_menu, None, "Sayfa Genişliği", ed.fit_width)
        action(view_menu, None, "Tam Sayfa", ed.fit_page)
        view_menu.addSeparator()
        action(view_menu, "customize", "Komut Çubuğunu Özelleştir…", self._customize_command_bar)
        action(view_menu, None, "Düğme Sırasını Sıfırla", self.reset_bar_order)
        view_menu.aboutToShow.connect(lambda: self.ruler_action.setChecked(self.ruler_button.isChecked()))
        add_menu("Görünüm", view_menu)

        # --- Gözden Geçir
        review_menu = QMenu(self)
        review_menu.addAction(self.spellcheck.live_action)
        review_menu.addAction(self.spellcheck.next_action)
        action(review_menu, "spell_check", "Dikte Sözlüğü…", lambda: self.dictation.open_vocabulary())
        review_menu.addSeparator()
        review_menu.addAction(self.act_translate)
        action(review_menu, None, "Dil Paketleri…", self.show_language_packs)
        add_menu("Gözden Geçir", review_menu)

        # --- Yardım
        help_menu = QMenu(self)
        help_menu.addAction(self.act_help)
        action(help_menu, None, "Klavye Kısayolları", lambda: self.show_help("kisayollar"))
        help_menu.addSeparator()
        action(help_menu, None, "Sözcük Hakkında", self.show_about)
        help_menu.addSeparator()
        action(help_menu, None, "Tanılama Günlüğü Klasörünü Aç", self._open_log_folder)
        add_menu("Yardım", help_menu)
        row.addStretch(1)

    def _build_command_bar(self):
        area = QWidget(objectName="commandArea")
        area_layout = QHBoxLayout(area)
        area_layout.setContentsMargins(8, 6, 8, 6)
        bar = QFrame(objectName="commandBar")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(6, 4, 6, 4)
        bar_layout.setSpacing(2)
        area_layout.addWidget(bar)

        # sığmayan düğmeler sağdaki » menüsünde; sağ tık özelleştirme menüsünü açar
        tb = CommandBar()
        tb.setContextMenuPolicy(Qt.CustomContextMenu)
        tb.customContextMenuRequested.connect(lambda pos: self._command_bar_menu().exec(tb.mapToGlobal(pos)))
        bar_layout.addWidget(tb, 1)
        self.command_bar = tb
        self.bar_items = []   # çubuktaki sırayla {key, label, group, widget}
        self.bar_groups = []  # {name, items}
        self._bar_group = None
        ed = self.editor

        # paragraf stili, yazı tipi ve boyutu
        self._bar_start_group("Yazı Tipi")
        self.heading_box = QComboBox()
        for i, name in enumerate(styles.HEADING_NAMES):
            self.heading_box.addItem(name)
            font = QFont(styles.DEFAULT_FAMILY)
            size, bold, _, _ = styles.HEADING_STYLES[i]
            font.setPointSizeF(min(size, 15))
            font.setBold(bold)
            self.heading_box.setItemData(i, font, Qt.FontRole)
        self.heading_box.setFixedWidth(112)
        self.heading_box.setToolTip("Stiller")
        self.heading_box.activated.connect(self._apply_heading)
        self._bar_add("styles", "Stiller", self._padded(self.heading_box, 6))

        self.font_box = QFontComboBox()
        self.font_box.setCurrentFont(QFont(styles.DEFAULT_FAMILY))
        self.font_box.setFixedWidth(170)
        self.font_box.setToolTip("Yazı Tipi")
        self.font_box.setMaxVisibleItems(16)
        self.font_box.textActivated.connect(self._apply_family)
        self._bar_add("font", "Yazı Tipi", self._padded(self.font_box, 4))

        self.size_box = QComboBox()
        self.size_box.setEditable(True)
        self.size_box.addItems([str(s) for s in styles.FONT_SIZES])
        self.size_box.setCurrentText(str(styles.DEFAULT_SIZE))
        self.size_box.setFixedWidth(58)
        self.size_box.setToolTip("Yazı Tipi Boyutu")
        self.size_box.setMaxVisibleItems(16)
        self.size_box.textActivated.connect(self._apply_size)
        self._bar_add("size", "Yazı Tipi Boyutu", self.size_box)
        self._bar_add("grow_font", "Yazı Tipini Büyüt",
                      self._action("grow_font", "Yazı Tipini Büyüt", "Ctrl+]", lambda: self._refocus(ed.step_size, 1)))
        self._bar_add("shrink_font", "Yazı Tipini Küçült",
                      self._action("shrink_font", "Yazı Tipini Küçült", "Ctrl+[", lambda: self._refocus(ed.step_size, -1)))

        # karakter biçimleri
        self._bar_start_group("Karakter Biçimi")
        self.act_bold = self._action("bold", "Kalın", QKeySequence.Bold, ed.set_bold, True)
        self.act_italic = self._action("italic", "İtalik", QKeySequence.Italic, ed.set_italic, True)
        self.act_underline = self._action("underline", "Altı Çizili", QKeySequence.Underline, ed.set_underline, True)
        self.act_strike = self._action("strike", "Üstü Çizili", None, ed.set_strike, True)
        for key, action in (("bold", self.act_bold), ("italic", self.act_italic),
                            ("underline", self.act_underline), ("strike", self.act_strike)):
            self._bar_add(key, action.text(), action)
        self.highlight_button = ColorButton("highlight", "Metin Vurgu Rengi", "#FFFF00", highlight=True)
        self.highlight_button.colorChosen.connect(lambda c: self._refocus(ed.set_highlight, c))
        self._bar_add("highlight", "Metin Vurgu Rengi", self.highlight_button)
        self.color_button = ColorButton("font_color", "Yazı Tipi Rengi", "#C00000")
        self.color_button.colorChosen.connect(lambda c: self._refocus(ed.set_text_color, c))
        self._bar_add("font_color", "Yazı Tipi Rengi", self.color_button)
        self._bar_add("clear_format", "Tüm Biçimlendirmeyi Temizle",
                      self._action("clear_format", "Tüm Biçimlendirmeyi Temizle", "Ctrl+Space",
                                   lambda: self._refocus(ed.clear_formatting)))

        # hizalama ve satır aralığı
        self._bar_start_group("Paragraf")
        self.align_group = QActionGroup(self)
        self.align_actions = {}
        for icon_name, text, shortcut, flag in (
            ("align_left", "Sola Hizala", "Ctrl+L", Qt.AlignLeft),
            ("align_center", "Ortala", "Ctrl+E", Qt.AlignHCenter),
            ("align_right", "Sağa Hizala", "Ctrl+R", Qt.AlignRight),
            ("align_justify", "İki Yana Yasla", "Ctrl+J", Qt.AlignJustify),
        ):
            action = self._action(icon_name, text, shortcut,
                                  lambda _=False, f=flag: self._refocus(ed.set_paragraph_alignment, f), True)
            self.align_group.addAction(action)
            self.align_actions[flag] = action
            self._bar_add(icon_name, text, action)

        self.spacing_button = QToolButton()
        self.spacing_button.setIcon(icons.icon("line_spacing"))
        self.spacing_button.setIconSize(QSize(20, 20))
        self.spacing_button.setToolTip("Satır ve Paragraf Aralığı")
        self.spacing_button.setPopupMode(QToolButton.InstantPopup)
        spacing_menu = QMenu(self.spacing_button)
        self.spacing_group = QActionGroup(self)
        self.spacing_actions = {}
        for factor in styles.LINE_SPACINGS:
            action = spacing_menu.addAction(f"{factor:g}".replace(".", ","))
            action.setCheckable(True)
            action.triggered.connect(lambda _=False, f=factor: self._refocus(ed.set_line_spacing, f))
            self.spacing_group.addAction(action)
            self.spacing_actions[factor] = action
        self.spacing_button.setMenu(spacing_menu)
        self._bar_add("line_spacing", "Satır ve Paragraf Aralığı", self.spacing_button)

        # listeler ve girinti
        self._bar_start_group("Listeler ve Girinti")
        self.act_bullets = self._action("bullets", "Madde İşaretleri", "Ctrl+Shift+L",
                                        lambda: self._refocus(ed.toggle_list, True), True)
        self.act_numbers = self._action("numbers", "Numaralandırma", "Ctrl+Shift+N",
                                        lambda: self._refocus(ed.toggle_list, False), True)
        self._bar_add("bullets", "Madde İşaretleri", self.act_bullets)
        self._bar_add("numbers", "Numaralandırma", self.act_numbers)
        self._bar_add("outdent", "Girintiyi Azalt",
                      self._action("outdent", "Girintiyi Azalt", None, lambda: self._refocus(ed.change_indent, -1)))
        self._bar_add("indent", "Girintiyi Artır",
                      self._action("indent", "Girintiyi Artır", None, lambda: self._refocus(ed.change_indent, 1)))

        # ekle ve sayfa düzeni
        self._bar_start_group("Ekle ve Sayfa")
        self.table_button = self._build_table_button()
        self.table_menu = self.table_button.menu()
        self._bar_add("table", "Tablo", self.table_button)
        self.image_button = self._build_image_button()
        self.image_menu = self.image_button.menu()
        self._bar_add("image", "Resim", self.image_button)
        self.symbol_button = self._build_symbol_button()
        self.symbol_menu = self.symbol_button.menu()
        self._bar_add("symbol", "Simge", self.symbol_button)
        self.act_link = self._action("link", "Bağlantı", "Ctrl+K", self.insert_link,
                                     tip="Bağlantı Ekle (web adresi ya da belgede bir yer)")
        self._bar_add("link", "Bağlantı", self.act_link)
        self._bar_add("page_layout", "Sayfa Düzeni", self._build_page_layout_button())

        # sesle yazma: kendi grubunda; denetleyici pencere kurulunca bağlanır (bkz. __init__)
        self._bar_start_group("Bul ve Değiştir")
        self.act_find = self._action("find", "Bul", QKeySequence.Find, lambda: self.find(False))
        self.act_replace = self._action("replace", "Değiştir", QKeySequence.Replace, lambda: self.find(True))
        self._bar_add("find", "Bul", self.act_find)
        self._bar_add("replace", "Değiştir", self.act_replace)

        self._bar_start_group("Gözden Geçir")
        self.act_translate = self._action("translate", "Çeviri", "Ctrl+Shift+T", self.show_translate,
                                          tip="Çeviri (bilgisayarda çalışır)")
        self._bar_add("translate", "Çeviri", self.act_translate)

        self._bar_start_group("Sesle Yazma")
        self.act_dictate = self._action("mic", "Sesle Yaz", "Ctrl+Shift+M", checkable=True)
        self.addAction(self.act_dictate)  # kısayol, düğme gizlense de çalışsın diye pencereye bağlanır
        self.mic_button = QToolButton(objectName="micButton")
        self.mic_button.setDefaultAction(self.act_dictate)
        self.mic_button.setIconSize(QSize(20, 20))
        self.mic_button.setFocusPolicy(Qt.NoFocus)
        self.mic_button.setPopupMode(QToolButton.MenuButtonPopup)  # ok: otomatik durdurma, gösterge, sözlük
        self._bar_add("dictate", "Sesle Yaz", self.mic_button)

        self._bar_start_group("Yazı Tipleri")
        self._bar_add("add_font", "Yazı Tipi Ekle…", self._action("add_font", "Yazı Tipi Ekle…", None, self._add_font,
                                                                   tip="Yazı Tipi Ekle (.ttf / .otf)"))
        self._bar_start_group(None)

        # özelleştirme düğmesi çubuğun dışında: taşma menüsüne düşmez, hep görünür
        customize = QToolButton()
        customize.setIcon(icons.icon("customize"))
        customize.setIconSize(QSize(20, 20))
        customize.setToolTip("Komut Çubuğunu Özelleştir")
        customize.setFocusPolicy(Qt.NoFocus)
        customize.setPopupMode(QToolButton.InstantPopup)
        customize.setMenu(QMenu(customize))
        customize.menu().aboutToShow.connect(lambda: self._command_bar_menu(customize.menu()))
        bar_layout.addWidget(customize, 0, Qt.AlignTop)
        self.customize_button = customize

        tb.orderChanged.connect(self._bar_order_changed)
        self._apply_bar_visibility()
        return area

    # --- komut çubuğu öğeleri ve özelleştirme ---------------------------------

    def _padded(self, widget, right):
        """Açılır kutunun sağına boşluk ekler (öğe gizlenince boşluk da gizlensin diye aynı kapta)."""
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, right, 0)
        row.setSpacing(0)
        row.addWidget(widget)
        return box

    def _bar_start_group(self, name):
        """Yeni düğme grubu başlatır; ayırıcılar gruplar arasına çubuk tarafından çizilir."""
        if name is not None:
            self._bar_group = {"name": name, "items": []}
            self.bar_groups.append(self._bar_group)

    def _bar_add(self, key, label, item):
        """Çubuğa düğme/kutu ekler. QAction'lar QToolButton'a sarılır ve pencereye bağlanır: düğme gizlense de
        kısayolu (Ctrl+B gibi) çalışmaya devam eder (gizli QAction'ın kısayolu çalışmaz)."""
        if isinstance(item, QAction):
            self.addAction(item)
            button = QToolButton()
            button.setDefaultAction(item)
            button.setIconSize(QSize(20, 20))  # ikonlar 20 px ızgarada çizilir; başka boyut bulanıklaştırır
            button.setAutoRaise(True)
            widget = button
        else:
            widget = item
        for child in [widget] + widget.findChildren(QToolButton):
            if isinstance(child, QToolButton):
                child.setFocusPolicy(Qt.NoFocus)  # tıklayınca odak metinde kalsın
        entry = self.command_bar.add_item(key, label, self._bar_group["name"], widget)
        self._bar_group["items"].append(entry)
        self.bar_items.append(entry)
        return entry

    def hidden_bar_items(self):
        value = self.settings.value("commandbar/hidden", None)
        if value is None:
            return set()
        if isinstance(value, str):
            value = [v for v in value.split(",") if v]
        return set(value)

    def set_bar_item_visible(self, key, visible):
        hidden = self.hidden_bar_items()
        (hidden.discard if visible else hidden.add)(key)
        self.settings.setValue("commandbar/hidden", ",".join(sorted(hidden)))
        self._apply_bar_visibility()

    def reset_command_bar(self):
        self.settings.setValue("commandbar/hidden", "")
        self._apply_bar_visibility()

    def _apply_bar_visibility(self):
        self.command_bar.set_hidden(self.hidden_bar_items())
        order = self.settings.value("commandbar/order", "")
        self.command_bar.set_order([k for k in str(order).split(",") if k])

    def _bar_order_changed(self, order):
        self.settings.setValue("commandbar/order", ",".join(order))

    def reset_bar_order(self):
        self.settings.setValue("commandbar/order", "")
        self.command_bar.set_order([])

    def _command_bar_menu(self, menu=None):
        """Word'deki "Hızlı Erişim Araç Çubuğunu Özelleştir" gibi: işaretli düğmeler çubukta görünür."""
        if menu is None:
            menu = QMenu(self)
            menu.setAttribute(Qt.WA_DeleteOnClose)
        menu.clear()
        title = menu.addAction("Komut Çubuğunda Gösterilecekler")
        title.setEnabled(False)
        hidden = self.hidden_bar_items()
        for group in self.bar_groups:
            submenu = menu.addMenu(group["name"])
            shown = sum(e["key"] not in hidden for e in group["items"])
            if shown == 0:
                submenu.setTitle(f"{group['name']} (gizli)")
            for entry in group["items"]:
                action = submenu.addAction(bar_item_icon(entry["widget"]), entry["label"])
                action.setCheckable(True)
                action.setChecked(entry["key"] not in hidden)
                action.toggled.connect(lambda on, k=entry["key"]: self.set_bar_item_visible(k, on))
            submenu.addSeparator()
            submenu.addAction("Tümünü Göster", lambda g=group: self._set_group_visible(g, True))
            submenu.addAction("Tümünü Gizle", lambda g=group: self._set_group_visible(g, False))
        menu.addSeparator()
        menu.addAction("Komut Çubuğunu Özelleştir…", self._customize_command_bar)
        hint = menu.addAction("Düğmeleri sürükleyerek sıralayın (menülü düğmeler için Alt + sürükle)")
        hint.setEnabled(False)
        order_reset = menu.addAction("Düğme Sırasını Sıfırla", self.reset_bar_order)
        order_reset.setEnabled(bool(self.settings.value("commandbar/order", "")))
        reset = menu.addAction("Gizlenenleri Geri Getir", self.reset_command_bar)
        reset.setEnabled(bool(hidden))
        return menu

    def _set_group_visible(self, group, visible):
        hidden = self.hidden_bar_items()
        for entry in group["items"]:
            (hidden.discard if visible else hidden.add)(entry["key"])
        self.settings.setValue("commandbar/hidden", ",".join(sorted(hidden)))
        self._apply_bar_visibility()

    def _customize_command_bar(self):
        dialog = CommandBarDialog(self.bar_groups, self.hidden_bar_items(), self)
        if dialog.exec() == QDialog.Accepted:
            self.settings.setValue("commandbar/hidden", ",".join(sorted(dialog.hidden())))
            self._apply_bar_visibility()

    def _build_page_layout_button(self):
        """Sayfa Düzeni: kenar boşlukları, yönlendirme, kâğıt boyutu ve Sayfa Yapısı penceresi."""
        button = QToolButton()
        button.setIcon(icons.icon("page_layout"))
        button.setIconSize(QSize(20, 20))
        button.setToolTip("Sayfa Düzeni (kenar boşlukları, yönlendirme, boyut)")
        button.setPopupMode(QToolButton.InstantPopup)
        self.page_layout_menu = page_setup.build_menu(self.editor, button, lambda change: self._refocus(change))
        button.setMenu(self.page_layout_menu)
        return button

    def _build_image_button(self):
        """Resim: dosyadan/panodan ekleme ve seçili görselin döndürme, kırpma, boyut işlemleri."""
        ed = self.editor
        button = QToolButton()
        button.setIcon(icons.icon("image"))
        button.setIconSize(QSize(20, 20))
        button.setToolTip("Resim")
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)

        def fill():
            menu.clear()
            menu.addAction(icons.icon("image_file"), "Dosyadan Resim Ekle…", self._insert_image_file)
            mime = QApplication.clipboard().mimeData()
            has_image = mime is not None and (mime.hasImage() or bool(images.local_image_files(mime)))
            paste = menu.addAction(icons.icon("paste"), "Panodaki Resmi Ekle",
                                   lambda: self._refocus(ed.insert_images_from_mime, QApplication.clipboard().mimeData()))
            paste.setEnabled(has_image)
            menu.addSeparator()
            for action in ed.add_image_menu(menu):
                action.triggered.connect(ed.setFocus)

        menu.aboutToShow.connect(fill)
        button.setMenu(menu)
        return button

    def _insert_image_file(self):
        folder = self.settings.value("images/folder", QStandardPaths.writableLocation(QStandardPaths.PicturesLocation))
        paths, _ = QFileDialog.getOpenFileNames(self, "Resim Ekle", folder, images.IMAGE_FILTER)
        if not paths:
            return
        self.settings.setValue("images/folder", str(Path(paths[0]).parent))
        failed = self.editor.insert_image_files(paths)
        self.editor.setFocus()
        if failed:
            QMessageBox.warning(self, "Resim eklenemedi", "Şu dosyalar açılamadı ya da desteklenmeyen biçimde:\n"
                                + "\n".join(Path(p).name for p in failed))

    def _build_symbol_button(self):
        """Simge: son kullanılanlar ızgarası ve tüm simgeler penceresi (Word'deki gibi)."""
        button = QToolButton()
        button.setIcon(icons.icon("symbol"))
        button.setIconSize(QSize(20, 20))
        button.setToolTip("Simge")
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)
        grid = symbols.SymbolGrid(columns=5, cell=36)
        grid.chosen.connect(lambda char: (menu.close(), self.insert_symbol(char)))
        grid_action = QWidgetAction(menu)
        grid_action.setDefaultWidget(grid)
        menu.addAction(grid_action)
        menu.addSeparator()
        menu.addAction(icons.icon("symbol"), "Diğer Simgeler…", self.show_symbol_dialog)
        menu.aboutToShow.connect(lambda: grid.set_chars(symbols.recent(self.settings), select_first=False))
        button.setMenu(menu)
        self._symbol_dialog = None
        return button

    def insert_symbol(self, char):
        symbols.remember(self.settings, char)
        cursor = self.editor.textCursor()
        cursor.insertText(char)  # imlecin yazı biçimiyle, tek geri-al adımı
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def show_symbol_dialog(self):
        if self._symbol_dialog is None:
            self._symbol_dialog = symbols.SymbolDialog(self.settings, self)
            self._symbol_dialog.inserted.connect(self._insert_symbol_from_dialog)
        self._symbol_dialog.refresh_recent()
        self._symbol_dialog.show()
        self._symbol_dialog.raise_()
        self._symbol_dialog.activateWindow()

    def _insert_symbol_from_dialog(self, char):
        cursor = self.editor.textCursor()
        cursor.insertText(char)
        self.editor.setTextCursor(cursor)

    def _build_table_button(self):
        ed = self.editor
        button = QToolButton()
        button.setIcon(icons.icon("table"))
        button.setIconSize(QSize(20, 20))
        button.setToolTip("Tablo")
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)

        picker = TableGridPicker()
        picker.chosen.connect(lambda rows, cols: (menu.close(), self._refocus(ed.insert_table, rows, cols)))
        picker_action = QWidgetAction(menu)
        picker_action.setDefaultWidget(picker)
        menu.addAction(picker_action)
        menu.addAction(icons.icon("table"), "Tablo Ekle…", self._insert_table_dialog)
        menu.addSeparator()

        table_actions = []
        for icon_name, text, action, args in (
            ("row_above", "Üste Satır Ekle", tables.insert_rows, (True,)),
            ("row_below", "Alta Satır Ekle", tables.insert_rows, (False,)),
            ("col_left", "Sola Sütun Ekle", tables.insert_columns, (True,)),
            ("col_right", "Sağa Sütun Ekle", tables.insert_columns, (False,)),
            (None, None, None, None),
            ("delete", "Satırları Sil", tables.delete_rows, ()),
            (None, "Sütunları Sil", tables.delete_columns, ()),
            (None, "Tabloyu Sil", tables.delete_table, ()),
            (None, None, None, None),
            ("merge", "Hücreleri Birleştir", tables.merge_cells, ()),
            ("split", "Hücreyi Böl", tables.split_cell, ()),
        ):
            if text is None:
                menu.addSeparator()
                continue
            item = menu.addAction(text, lambda a=action, x=args: self._refocus(ed.table_action, a, *x))
            if icon_name:
                item.setIcon(icons.icon(icon_name))
            table_actions.append((item, action))

        def update_enabled():
            cursor = ed.textCursor()
            in_table = cursor.currentTable() is not None
            for item, action in table_actions:
                if action is tables.merge_cells:
                    item.setEnabled(tables.can_merge(cursor))
                elif action is tables.split_cell:
                    item.setEnabled(tables.can_split(cursor))
                else:
                    item.setEnabled(in_table)

        menu.aboutToShow.connect(update_enabled)
        button.setMenu(menu)
        return button

    def _insert_table_dialog(self):
        dialog = InsertTableDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._refocus(self.editor.insert_table, dialog.rows.value(), dialog.cols.value())

    def _open_log_folder(self):
        folder = logbook.log_directory()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _build_file_actions(self):
        self.file_menu = QMenu(self)
        self.file_menu.aboutToShow.connect(lambda: self._update_cloud_actions())
        m = self.file_menu
        entries = [
            ("new", "Yeni", QKeySequence.New, self.new_document),
            ("open", "Aç…", QKeySequence.Open, self.open_document),
            "cloud_open",
            None,
            ("save", "Kaydet", None, self.save),
            (None, "Farklı Kaydet…", "F12", self.save_as),
            "cloud_save",
            ("pdf", "PDF Olarak Dışa Aktar…", None, self.export_pdf),
            None,
            ("print", "Yazdır…", QKeySequence.Print, self.print_document),
            None,
            ("help", "Yardım ve Nasıl Kullanılır\tF1", None, self.show_help),
            (None, "Tanılama Günlüğü Klasörünü Aç", None, self._open_log_folder),
            ("exit", "Kapat", None, self.close),
        ]
        self.cloud_actions = []  # (tür, sağlayıcı, eylem) — menü açılırken bulut klasörlerine göre gösterilir
        for entry in entries:
            if entry is None:
                m.addSeparator()
                continue
            if isinstance(entry, str):
                for provider in (cloud.GOOGLE, cloud.ONEDRIVE):
                    if entry == "cloud_open":
                        action = self._action("cloud", f"{provider}'dan Aç…", None,
                                              lambda _=False, p=provider: self.open_from_cloud(p))
                    else:
                        action = self._action("cloud", f"{provider}'a Kaydet…", None,
                                              lambda _=False, p=provider: self.save_to_cloud(p))
                    m.addAction(action)
                    self.cloud_actions.append((entry, provider, action))
                continue
            icon_name, text, shortcut, slot = entry
            if shortcut is None and slot == self.save:
                # kısayol başlıktaki Kaydet düğmesinde; burada yalnızca gösterilir
                text = f"{text}\t{QKeySequence(QKeySequence.Save).toString(QKeySequence.NativeText)}"
            action = self._action(icon_name, text, shortcut, slot)
            m.addAction(action)
            self.addAction(action)

    def _update_cloud_actions(self):
        available = {f.provider for f in cloud.cloud_folders(refresh=True)}
        for _, provider, action in self.cloud_actions:
            action.setVisible(provider in available)

    def _build_statusbar(self):
        bar = self.statusBar()
        bar.setSizeGripEnabled(False)
        self.page_label = QLabel()
        self.count_label = QLabel()
        language = QLabel("Türkçe (Türkiye)")
        self.save_label = QLabel()
        for label in (self.page_label, self.count_label, language):
            bar.addWidget(label)
        bar.addPermanentWidget(self.save_label)

        self.ruler_button = QToolButton()
        self.ruler_button.setIcon(icons.icon("ruler", theme.TEXT_MUTED))
        self.ruler_button.setIconSize(QSize(20, 20))
        self.ruler_button.setCheckable(True)
        self.ruler_button.setToolTip("Cetvel")
        self.ruler_button.toggled.connect(self._rulers_toggled)
        self.ruler_button.setChecked(self.settings.value("rulers", True, type=bool))
        self.doc_area.set_rulers_visible(self.ruler_button.isChecked())
        bar.addPermanentWidget(self.ruler_button)

        self.zoom_control = ZoomControl()
        self.zoom_control.zoomRequested.connect(self.editor.set_zoom)
        self.zoom_control.fitWidthRequested.connect(self.editor.fit_width)
        self.zoom_control.fitPageRequested.connect(self.editor.fit_page)
        self.editor.zoomChanged.connect(self._zoom_changed)
        bar.addPermanentWidget(self.zoom_control)
        self.editor.set_zoom(self.settings.value("zoom", 1.0, type=float))

    def _rulers_toggled(self, visible):
        self.doc_area.set_rulers_visible(visible)
        self.settings.setValue("rulers", visible)

    def _zoom_changed(self, zoom):
        self.zoom_control.set_zoom(zoom)
        self.settings.setValue("zoom", zoom)

    def _connect_signals(self):
        ed = self.editor
        doc = ed.document()
        ed.currentCharFormatChanged.connect(self._sync_format_controls)
        ed.cursorPositionChanged.connect(self._sync_format_controls)
        ed.cursorPositionChanged.connect(self._update_page)
        # sözcük sayacı tüm belgeyi sayar: her tuşta değil, yazmaya kısa bir ara verilince güncellenir
        self._counts_timer = QTimer(self, singleShot=True, interval=COUNTS_DELAY_MS)
        self._counts_timer.timeout.connect(self._update_counts)
        doc.contentsChanged.connect(self._counts_timer.start)
        # QTextEdit.undoAvailable geri al sırasında yanlış durum bildirebiliyor, belgeye soruyoruz
        doc.undoCommandAdded.connect(self._update_undo_redo)
        doc.contentsChanged.connect(self._update_undo_redo)
        doc.modificationChanged.connect(self._update_title)
        doc.documentLayout().pageCountChanged.connect(self._page_count_changed)

    def _refocus(self, func, *args):
        func(*args)
        self.editor.setFocus()
        self._sync_format_controls()

    def _find_next(self, direction):
        if not self.find_area.isVisible():
            self.find_bar.open()
            return
        self.find_bar.go(direction)

    def show_translate(self):
        """Çeviri penceresi — metin bilgisayarda çevrilir, hiçbir yere gönderilmez (translate.py)."""
        if not translate_module.available():
            QMessageBox.information(self, "Çeviri", "Çeviri bileşeni kurulu değil. Kurmak için: "
                                                    "pip install argostranslate")
            return
        window = getattr(self, "_translate_dialog", None)
        if window is None:
            window = translate_module.TranslateDialog(self.editor, self, self.settings)
            self._translate_dialog = window
        window.load_from_editor()
        window.show()
        window.raise_()
        window.activateWindow()
        return window

    def show_language_packs(self):
        """Çeviri dil paketleri: hangileri hazır, hangileri indirilecek."""
        if not translate_module.available():
            QMessageBox.information(self, "Çeviri", "Çeviri bileşeni kurulu değil (pip install argostranslate).")
            return
        translate_module.LanguagePacksDialog(self).exec()

    def insert_link(self):
        """Bağlantı ekler ya da imlecin üzerindeki bağlantıyı düzenler (Ctrl+K)."""
        ed = self.editor
        existing = ed.link_at_cursor()
        cursor = ed.textCursor()
        if existing:
            href, start, end = existing
            span = (start, end)
            selection = QTextCursor(ed.document())
            selection.setPosition(start)
            selection.setPosition(end, QTextCursor.KeepAnchor)
            text = selection.selectedText()
        else:
            href, span = "", None
            text = cursor.selectedText().replace("\u2029", " ") if cursor.hasSelection() else ""
        page, line = links.page_line_of(ed.document(), cursor.selectionStart())
        dialog = links.LinkDialog(self, text=text, href=href, page=page, line=line, max_page=ed.page_count())
        if dialog.exec() != QDialog.Accepted:
            return
        if dialog.removed:
            ed.remove_link(span)
            return
        ed.apply_link(dialog.href(), dialog.text(), span)

    def _link_menu(self, menu, cursor):
        link = self.editor.link_at_cursor()
        if link is None:
            return
        href, start, end = link
        menu.addSeparator()
        open_action = menu.addAction(icons.icon("link"), f"Bağlantıyı Aç  ({links.describe(href)})")
        open_action.triggered.connect(lambda: self.editor.open_link(href))
        edit_action = menu.addAction("Bağlantıyı Düzenle…")
        edit_action.triggered.connect(self.insert_link)
        remove_action = menu.addAction(icons.icon("link_remove"), "Bağlantıyı Kaldır")
        remove_action.triggered.connect(lambda: self.editor.remove_link((start, end)))

    def find(self, replace=False):
        """Bul ve Değiştir şeridini açar (Ctrl+F / Ctrl+H)."""
        self.find_bar.open(replace=replace)

    def show_about(self):
        AboutDialog(self, __version__, DEVELOPERS).exec()

    def show_help(self, topic=None):
        """Yardım ve Nasıl Kullanılır penceresi (içerik: sozcuk/yardim.md)."""
        return open_help(self, self.settings, topic if isinstance(topic, str) else None)

    def show_message(self, text, buttons=()):
        self.message_bar.show_message(text, buttons)

    # =========================================================================
    # Biçim eylemleri
    # =========================================================================

    def _apply_family(self, family):
        self._refocus(self.editor.set_family, family)

    def _apply_size(self, text):
        try:
            size = float(text.replace(",", "."))
        except ValueError:
            self._sync_format_controls()
            return
        if 1 <= size <= 1638:
            self._refocus(self.editor.set_size, size)

    def _apply_heading(self, index):
        self._refocus(self.editor.set_heading, index)

    def _add_font(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Yazı Tipi Ekle", "", "Yazı tipi dosyaları (*.ttf *.otf)")
        added, failed = [], []
        for path in paths:
            try:
                families = fonts.install_font(path)
            except OSError:
                families = []
            if families:
                added.extend(families)
            else:
                failed.append(Path(path).name)
        if failed:
            QMessageBox.warning(self, "Yazı tipi eklenemedi",
                                "Şu dosyalar geçerli bir yazı tipi olarak yüklenemedi:\n" + "\n".join(failed))
        if added:
            self.font_box.setWritingSystem(self.font_box.writingSystem())
            family = added[0]
            self.font_box.setCurrentFont(QFont(family))
            self._apply_family(family)
            self.statusBar().showMessage(f"Yazı tipi eklendi: {', '.join(dict.fromkeys(added))}", 5000)

    # =========================================================================
    # Dosya işlemleri
    # =========================================================================

    def _default_dir(self):
        if self.path:
            return str(self.path.parent)
        return self.settings.value("lastDir", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))

    def _maybe_save(self):
        if not self.editor.document().isModified():
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Sözcük")
        box.setIcon(QMessageBox.NoIcon)
        box.setText(f"<b>Değişiklikleriniz “{self.display_name}” belgesine kaydedilsin mi?</b>")
        box.setInformativeText("Kaydetmezseniz yaptığınız değişiklikler kaybolur.")
        save = box.addButton("Kaydet", QMessageBox.AcceptRole)
        discard = box.addButton("Kaydetme", QMessageBox.DestructiveRole)
        box.addButton("İptal", QMessageBox.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save:
            return self.save()
        return clicked is discard

    def _cloud_folder(self, provider):
        return next((f for f in cloud.cloud_folders() if f.provider == provider), None)

    def open_from_cloud(self, provider):
        folder = self._cloud_folder(provider)
        if folder is None:
            return
        start = str(self.path.parent) if cloud.provider_for(self.path) == provider else str(folder.path)
        path, _ = QFileDialog.getOpenFileName(self, f"{provider}'dan Aç", start, OPEN_FILTER)
        if path:
            self.open_document(path)

    def save_to_cloud(self, provider):
        folder = self._cloud_folder(provider)
        if folder is None:
            return False
        start = self.path.parent if cloud.provider_for(self.path) == provider else folder.path
        return self.save_as(directory=start, title=f"{provider}'a Kaydet")

    def _track(self, path):
        self.tracker.track(path)
        self.autosave_debounce.setInterval(CLOUD_AUTOSAVE_IDLE_MS if cloud.provider_for(path) else AUTOSAVE_IDLE_MS)

    def new_document(self):
        if not self._maybe_save():
            return
        self._discard_recovery()
        self.editor.reset()
        self.path = None
        self._track(None)
        self.display_name = self._next_untitled()
        self.last_saved = None
        self.message_bar.hide()
        self._after_load()

    def open_document(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Aç", self._default_dir(), OPEN_FILTER)
            if not path:
                return
        path = Path(path)
        if not self._maybe_save():
            return
        self.settings.setValue("lastDir", str(path.parent))

        if cloud.is_google_format(path):
            kind = cloud.GOOGLE_FORMATS[path.suffix.lower()]
            self.show_message(
                f"“{path.stem}” bir {kind} belgesi. Bu belgelerin içeriği bilgisayarda değil yalnızca Google'ın "
                "sunucusunda durur; Drive'daki dosya yalnızca bir bağlantıdır ve Sözcük açamaz. Tarayıcıda açıp "
                "<b>Dosya → İndir → Microsoft Word (.docx)</b> ile Word belgesi olarak indirip Drive'a koyarsanız "
                "Sözcük'te düzenleyebilirsiniz.",
                [("Tarayıcıda Aç", lambda: self._open_google_document(path))],
            )
            return
        fmt, problem = formats.effective_format(path)
        if problem:
            QMessageBox.warning(self, "Dosya açılamadı", f"“{path.name}” açılamadı.\n\n{problem}")
            return
        if fmt is None:
            QMessageBox.warning(self, "Desteklenmeyen dosya",
                                f"Sözcük “{path.suffix or path.name}” türündeki dosyaları açamaz.\n\nAçılabilen biçimler: "
                                + ", ".join(f.suffix for f in formats.FORMATS) + ".")
            return
        if fmt.kind == "pdf":
            self._open_pdf(path)
            return
        if fmt.kind == "legacy":
            self._open_legacy(path, fmt)
            return
        if fmt.kind == "docx":
            def prepare():
                return docx_io.Reader(path).read
        elif fmt.kind in formats.LOADERS:
            def prepare():
                return formats.prepare(path, fmt.kind)
        else:
            def prepare():
                return {"odt": odt_io, "rtf": rtf_io}[fmt.kind].prepare(path)

        if not self._load_with(path, fmt, prepare) and fmt.kind in ("odt", "rtf") and converters.available():
            # kendi okuyucumuz açamadıysa (sıra dışı bir dosya) Word/LibreOffice ile dene
            self._open_legacy(path, fmt)

    def _load_with(self, path, fmt, prepare, source_label=None, quiet=False):
        """prepare() dosyayı okuyup çözümler ve build(document) döndürür; hatalı dosya bu aşamada hata verir, böylece
        açık belgeye dokunulmaz. Başarıda belge durumunu ayarlar; başarı durumunu döndürür."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        started = time.monotonic()
        warnings = []
        try:
            build = prepare()
        except Exception as exc:
            log.error("açılamadı (%s): %s", fmt.suffix, type(exc).__name__)
            QApplication.restoreOverrideCursor()
            if not quiet and not (fmt.kind in ("odt", "rtf") and converters.available()):
                QMessageBox.critical(self, "Dosya açılamadı",
                                     f"“{path.name}” açılamadı. Dosya bozuk ya da geçerli bir {fmt.label} değil.\n\n{exc}")
            return False
        self.editor.load(lambda doc: warnings.extend(build(doc) or []))
        QApplication.restoreOverrideCursor()
        log.info("açıldı (%s): %.1f sn, %d paragraf, %d sayfa, uyarı=%d", fmt.suffix, time.monotonic() - started,
                 self.editor.document().blockCount(), self.editor.page_count(), len(warnings))

        self._discard_recovery()
        self.message_bar.hide()
        if fmt.template:
            # Word gibi: şablon yeni, adsız belge olarak açılır; şablonun kendisi değişmez
            self.path = None
            self._track(None)
            self.display_name = self._next_untitled()
        else:
            self.path = path
            self._track(path)
            self.display_name = path.name
        self.last_saved = None
        self._keep_format = False
        notes = list(warnings)
        if not fmt.template and fmt.suffix != ".docx":
            notes.append(f"<b>Uyumluluk Modu:</b> belge {fmt.label} ({fmt.suffix}) biçiminde"
                         + (f" ({source_label} ile dönüştürülerek açıldı)" if source_label else "") + ". "
                         "Kaydederken Word Belgesi (.docx) olarak kaydetmeniz önerilir; bazı biçimlendirmeler "
                         "eski biçimde korunamayabilir.")
            if fmt.suffix in (".docm", ".dotm"):
                notes.append("Belgedeki makrolar çalıştırılmaz ve kaydedilen belgede yer almaz.")
        elif warnings:
            notes.append("Kaydederseniz bu öğeler dosyadan çıkarılır.")
        if notes:
            self.show_message(" ".join(notes))
        self._after_load()
        return True

    def _run_in_background(self, function, message):
        """function'ı arka planda çalıştırır ve bitmesini arayüzü dondurmadan bekler; sonucunu döndürür."""
        task = BackgroundTask(function, self)
        loop = QEventLoop()
        task.finished.connect(loop.quit)
        central = self.centralWidget()
        central.setEnabled(False)          # beklerken belge değiştirilmesin
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage(message)
        task.start()
        loop.exec()
        QApplication.restoreOverrideCursor()
        central.setEnabled(True)
        self.statusBar().clearMessage()
        self.editor.setFocus()
        if task.error is not None:
            raise task.error
        return task.result

    def _open_legacy(self, path, fmt):
        """Eski/yabancı biçim: Word ya da LibreOffice ile .docx'e çevirip aç; ikisi de yoksa .doc için yalnızca metin."""
        engines = converters.available()
        if not engines:
            if fmt.suffix in (".doc", ".dot"):
                self._load_with(path, fmt, lambda: doc_text.prepare(path))
                return
            box = QMessageBox(QMessageBox.Information, "Dönüştürücü gerekiyor",
                              f"“{path.name}” bir {fmt.label}. Bu biçimi açmak için bilgisayarda Microsoft Word "
                              "ya da ücretsiz LibreOffice kurulu olmalı.", parent=self)
            download = box.addButton("LibreOffice'i İndir", QMessageBox.ActionRole)
            box.addButton("Kapat", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is download:
                QDesktopServices.openUrl(QUrl(LIBREOFFICE_URL))
            return
        try:
            converted, engine = self._run_in_background(
                lambda: converters.to_docx(path),
                f"“{path.name}” {engines[0]} ile açılıyor (arka planda dönüştürülüyor)…")
        except converters.ConversionError as exc:
            if fmt.suffix in (".doc", ".dot") and "parola" not in str(exc):
                if self._load_with(path, fmt, lambda: doc_text.prepare(path), quiet=True):
                    self.show_message(f"{exc} Belgenin yalnızca metni açıldı.")
                    return
            QMessageBox.warning(self, "Dosya açılamadı", f"“{path.name}” açılamadı.\n\n{exc}")
            return
        try:
            self._load_with(path, fmt, lambda: docx_io.Reader(converted).read, source_label=engine)
        finally:
            shutil.rmtree(converted.parent, ignore_errors=True)

    def _open_pdf(self, path):
        if self._pdf_worker and self._pdf_worker.isRunning():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage(f"“{path.name}” dönüştürülüyor…")
        worker = PdfWorker(path, self)
        worker.done.connect(lambda paragraphs: self._pdf_ready(path, paragraphs))
        worker.failed.connect(self._pdf_failed)
        worker.finished.connect(QApplication.restoreOverrideCursor)
        self._pdf_worker = worker
        worker.start()

    def _pdf_ready(self, path, paragraphs):
        log.info("PDF dönüştürüldü: %d paragraf", len(paragraphs))
        self.statusBar().clearMessage()
        self._discard_recovery()
        self.editor.load(lambda doc: pdf_io.build(paragraphs, doc))
        self.path = None
        self._track(None)
        self.display_name = path.stem
        self.last_saved = None
        self.show_message(
            "Bu belge PDF'ten düzenlenebilir metne dönüştürüldü. Sayfa düzeni, tablolar ve görseller "
            "birebir korunmamış olabilir. Kaydettiğinizde Word belgesi (.docx) olarak kaydedilir."
        )
        self._after_load()

    @staticmethod
    def _open_google_document(path):
        """Google Drive uygulaması .gdoc dosyasını doğrudan o belgenin sayfasıyla tarayıcıda açar; o uygulama
        yoksa (ör. dosya başka yoldan kopyalanmış) Drive'da adıyla arama sayfası açılır."""
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QDesktopServices.openUrl(QUrl(cloud.google_search_url(path)))

    def _pdf_failed(self, message):
        log.warning("PDF açılamadı: %s", message)
        self.statusBar().clearMessage()
        QMessageBox.warning(self, "PDF açılamadı", message)

    def _after_load(self):
        self.editor.setFocus()
        self.editor.verticalScrollBar().setValue(0)
        self._update_title()
        self._update_counts()
        self._update_undo_redo()
        self._update_page()
        self._sync_format_controls()
        self.spellcheck.recheck_all()

    def save(self):
        if self.path is None:
            return self.save_as()
        suffix = self.path.suffix.lower()
        if suffix != ".docx" and not self._keep_format:
            return self._save_compatibility()
        return self._write(self.path)

    def _can_write(self, suffix):
        return suffix == ".docx" or suffix in formats.WRITERS or (
            suffix in converters.WORD_FORMATS and bool(converters.available()))

    def _save_compatibility(self):
        """Eski biçimde açılmış belge (Word'ün "Uyumluluk Modu" gibi): .docx önerilir."""
        fmt = formats.format_for(self.path)
        label = fmt.label if fmt else self.path.suffix
        box = QMessageBox(self)
        box.setWindowTitle("Sözcük")
        box.setIcon(QMessageBox.NoIcon)
        box.setText(f"<b>“{self.path.name}” {label} biçiminde.</b>")
        info = "Word Belgesi (.docx) olarak kaydetmeniz önerilir: tüm biçimlendirmeler korunur ve Word'de sorunsuz açılır."
        keep = None
        if self._can_write(self.path.suffix.lower()):
            save_format = formats.SAVE_BY_SUFFIX.get(self.path.suffix.lower())
            if save_format and save_format.loses:
                info += f"\n\nÖzgün biçimde kaydederseniz: {save_format.loses}"
            keep = box.addButton(f"{self.path.suffix} Olarak Kaydet", QMessageBox.AcceptRole)
        else:
            info += f"\n\nSözcük {self.path.suffix} biçiminde kaydedemez."
        box.setInformativeText(info)
        docx = box.addButton("Word Belgesi Olarak Kaydet…", QMessageBox.AcceptRole)
        box.addButton("İptal", QMessageBox.RejectRole)
        box.setDefaultButton(docx)
        box.exec()
        clicked = box.clickedButton()
        if clicked is docx:
            return self.save_as(directory=self.path.parent, suffix=".docx")
        if keep is not None and clicked is keep:
            self._keep_format = True
            return self._write(self.path)
        return False

    def save_as(self, directory=None, title="Farklı Kaydet", suffix=None):
        directory = directory if isinstance(directory, (str, Path)) else self._default_dir()
        save_formats, filters = formats.save_filters(bool(converters.available()))
        wanted = suffix or ".docx"
        selected = next((f"{f.label} (*{f.suffix})" for f in save_formats if f.suffix == wanted), None)
        suggested = str(Path(directory) / (Path(self.display_name).stem + wanted))
        path, chosen_filter = QFileDialog.getSaveFileName(self, title, suggested, filters, selected)
        if not path:
            return False
        path = Path(path)
        chosen = next((f for f in save_formats if chosen_filter.startswith(f.label + " (")), save_formats[0])
        if path.suffix.lower() not in [f.suffix for f in save_formats] or (
                path.suffix.lower() != chosen.suffix and not (chosen.suffix == ".html" and path.suffix.lower() == ".htm")):
            path = path.with_name(path.name + chosen.suffix) if path.suffix.lower() != chosen.suffix else path
        save_format = formats.SAVE_BY_SUFFIX.get(path.suffix.lower(), chosen)
        if save_format.loses and save_format.suffix != ".docx":
            answer = QMessageBox.question(self, "Sözcük", f"{save_format.label} olarak kaydedilecek.\n\n{save_format.loses}",
                                          QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
            if answer != QMessageBox.Ok:
                return False
        self.settings.setValue("lastDir", str(path.parent))
        self._keep_format = path.suffix.lower() != ".docx"
        return self._write(path)

    def _save_document(self, path):
        """Uzantıya göre yazar: .docx doğrudan, .txt/.html/.odt Sözcük, .doc/.rtf Word ya da LibreOffice ile."""
        suffix = path.suffix.lower()
        document = self.editor.document()
        if suffix == ".docx":
            docx_io.save(document, path)
        elif suffix in formats.WRITERS:
            formats.WRITERS[suffix](document, path)
        elif suffix in converters.WORD_FORMATS and converters.available():
            work = Path(tempfile.mkdtemp(prefix="sozcuk-kayit-"))
            try:
                source = work / (path.stem + ".docx")
                docx_io.save(document, source)
                target = work / path.name
                try:
                    self._run_in_background(lambda: converters.convert(source, target),
                                            f"“{path.name}” {converters.available()[0]} ile kaydediliyor…")
                except converters.ConversionError as exc:
                    raise OSError(str(exc)) from exc
                docx_io._replace_with_retry(target, path) if target.drive == path.drive else shutil.move(str(target), str(path))
            finally:
                shutil.rmtree(work, ignore_errors=True)
        else:
            raise OSError(f"Sözcük {suffix} biçiminde kaydedemez.")

    def _write(self, path, silent=False):
        path = Path(path)
        same_file = self.path is not None and path == self.path
        if silent and same_file:
            # dosya başka yerde değişmişse kullanıcı karar verene kadar otomatik kayıt üzerine yazmaz
            if self.tracker.conflict:
                return False
            if self.tracker.changed():
                self._handle_external_change()
                return False
        started = time.monotonic()
        provider = cloud.provider_for(path)
        self._saving = True
        self._update_title()
        self.status_label.repaint()
        try:
            self._save_document(path)
        except OSError as exc:
            log.error("kaydedilemedi (otomatik=%s, bulut=%s): %s", silent, bool(provider), type(exc).__name__)
            self._saving = False
            self._save_failed = True
            self._update_title()
            if silent:
                self.save_label.setText("Otomatik kaydetme başarısız")
                self._write_recovery_copy()  # kayıt dosyaya gidemediyse kurtarma kopyası kalsın
                QTimer.singleShot(SAVE_RETRY_MS, self._autosave_file)  # yazmaya devam edilmese de yeniden dene
                if provider:
                    self.save_label.setToolTip(f"{provider} klasörüne yazılamadı. {provider} uygulamasının çalıştığını "
                                               "ve oturumun açık olduğunu denetleyin; Sözcük yeniden deneyecek.")
            else:
                QMessageBox.critical(
                    self, "Kaydedilemedi",
                    f"“{path.name}” kaydedilemedi. Dosya başka bir programda (ör. Word) açık olabilir.\n\n{exc}",
                )
            return False
        log.info("kaydedildi (otomatik=%s, bulut=%s): %.2f sn, %d paragraf", silent, bool(provider),
                 time.monotonic() - started, self.editor.document().blockCount())
        self._saving = False
        self._save_failed = False
        if not same_file:
            self._track(path)
        self.tracker.remember()
        self.path = Path(path)
        self.display_name = self.path.name
        self.last_saved = datetime.now()
        self.editor.document().setModified(False)
        self._discard_recovery()
        self._update_title()
        return True

    def export_pdf(self):
        suggested = str(Path(self._default_dir()) / (Path(self.display_name).stem + ".pdf"))
        path, _ = QFileDialog.getSaveFileName(self, "PDF Olarak Dışa Aktar", suggested, "PDF (*.pdf)")
        if not path:
            return
        path = Path(path)
        if path.suffix.lower() != ".pdf":
            path = path.with_name(path.name + ".pdf")
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(path))
        self._prepare_printer(printer)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.editor.print_document(printer)
        finally:
            QApplication.restoreOverrideCursor()
        if not path.exists():
            QMessageBox.critical(self, "Dışa aktarılamadı", f"“{path.name}” oluşturulamadı. Dosya açık olabilir.")
            return
        self.show_message(
            f"“{path.name}” olarak dışa aktarıldı.",
            [("Aç", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))))],
        )

    def _prepare_printer(self, printer):
        # belgenin kâğıt boyutu ve yönlendirmesi; bilinen boyutlar (A4, Letter…) yazıcıda adıyla eşleşir
        width, height = self.editor.page_size()
        landscape = width > height
        short, long = sorted((width, height))
        size = QPageSize(QSizeF(short / styles.PX_PER_CM * 10, long / styles.PX_PER_CM * 10), QPageSize.Millimeter,
                         "", QPageSize.FuzzyMatch)
        orientation = QPageLayout.Landscape if landscape else QPageLayout.Portrait
        printer.setPageLayout(QPageLayout(size, orientation, QMarginsF(0, 0, 0, 0)))
        printer.setFullPage(True)
        printer.setDocName("Sözcük")

    def print_document(self):
        printer = QPrinter(QPrinter.HighResolution)
        self._prepare_printer(printer)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Yazdır")
        if dialog.exec() == QPrintDialog.Accepted:
            self.editor.print_document(printer)

    def closeEvent(self, event):
        if self._maybe_save():
            self._discard_recovery()
            self.dictation.shutdown()
            event.accept()
        else:
            event.ignore()

    # =========================================================================
    # Otomatik kaydetme ve kurtarma
    # =========================================================================

    @staticmethod
    def _recovery_dir():
        base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "recovery"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _recovery_file(self):
        return self._recovery_dir() / f"{self.session_id}.docx"

    def _discard_recovery(self):
        for suffix in (".docx", ".json"):
            self._recovery_file().with_suffix(suffix).unlink(missing_ok=True)

    def _autosave_toggled(self, on):
        self.settings.setValue("autosave", on)
        if on:
            QTimer.singleShot(0, self._autosave_file)
        self._update_title()

    def _autosaves_to_file(self):
        """Otomatik kayıt dosyanın kendisine yalnızca .docx belgelerde yapılır; eski biçimlerde (dönüştürme ya da
        biçim kaybı olur) kurtarma kopyası tutulur, dosya kullanıcı kaydedince yazılır."""
        return (self.autosave_switch.isChecked() and self.path is not None
                and self.path.suffix.lower() == ".docx")

    def _schedule_autosave(self):
        if self._autosaves_to_file() and not self.editor.bulk_loading:
            self.autosave_debounce.start()

    def _autosave_file(self):
        if self._autosaves_to_file() and self.editor.document().isModified():
            self._write(self.path, silent=True)

    def _autosave(self):
        doc = self.editor.document()
        if not doc.isModified():
            return
        if self._autosaves_to_file() and not self.tracker.conflict:
            self._autosave_file()
            return
        self._write_recovery_copy()

    def _write_recovery_copy(self):
        """Kaydedilmemiş belge, kapalı otomatik kayıt ya da başarısız kayıt için kurtarma kopyası."""
        doc = self.editor.document()
        try:
            docx_io.save(doc, self._recovery_file())
            meta = {"name": self.display_name, "path": str(self.path) if self.path else None,
                    "time": datetime.now().isoformat(timespec="minutes")}
            self._recovery_file().with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
        except OSError:
            pass

    def _check_external_change(self):
        """Açık dosya başka yerde değiştiyse (ör. Google Drive web'de ya da başka bilgisayarda düzenlendi)."""
        if self.path is None or self._saving or not self.tracker.changed():
            return
        self._handle_external_change()

    def _handle_external_change(self):
        provider = cloud.provider_for(self.path)
        where = f"{provider} üzerinden " if provider else ""
        if not self.editor.document().isModified():
            # yerelde kaydedilmemiş değişiklik yok: Google Dokümanlar gibi yeni sürümü sessizce yükle
            log.info("dosya dışarıdan değişti, yeniden yüklendi (bulut=%s)", bool(provider))
            if self._reload(keep_position=True):
                self.statusBar().showMessage(f"Belgenin {where}gelen yeni sürümü yüklendi.", 6000)
            return
        log.info("dosya dışarıdan değişti, yerelde kaydedilmemiş değişiklik var (bulut=%s)", bool(provider))
        self.show_message(
            f"<b>“{self.path.name}” başka bir yerde değiştirildi</b> ({where}başka bir bilgisayar ya da program). "
            "Sizin kaydedilmemiş değişiklikleriniz de var; otomatik kayıt, siz karar verene kadar dosyanın üzerine "
            "yazmayacak.",
            [("Onların Sürümünü Yükle", lambda: self._reload(keep_position=True)),
             ("Benimkini Kaydet", self._overwrite_external),
             ("Benimkini Ayrı Kaydet", self._save_mine_separately)],
        )
        self._update_title()

    def _reload(self, keep_position=False):
        position = self.editor.textCursor().position()
        scroll = self.editor.verticalScrollBar().value()
        try:
            reader = docx_io.Reader(self.path)
            warnings = []
            self.editor.load(lambda doc: warnings.extend(reader.read(doc)))
        except Exception as exc:  # eşitleme yarım kalmış olabilir: sonraki yoklamada yeniden dene
            log.warning("yeniden yüklenemedi: %s", type(exc).__name__)
            self.tracker.conflict = False
            self.tracker.known = (-1, -1)  # sonraki yoklamada yeniden denensin
            return False
        self.tracker.remember()
        self.message_bar.hide()
        self._after_load()
        if keep_position:
            cursor = self.editor.textCursor()
            cursor.setPosition(min(position, self.editor.document().characterCount() - 1))
            self.editor.setTextCursor(cursor)
            self.editor.verticalScrollBar().setValue(scroll)
        return True

    def _overwrite_external(self):
        self.tracker.remember()
        self.message_bar.hide()
        self._write(self.path)

    def _save_mine_separately(self):
        original = self.path
        self.tracker.remember()  # özgün dosyaya dokunulmayacak; yeni dosya izlenecek
        self.message_bar.hide()
        if not self.save_as(directory=original.parent, title="Benim Sürümümü Ayrı Kaydet"):
            self.tracker.conflict = True
            self._handle_external_change()

    def _offer_recovery(self):
        files = sorted(self._recovery_dir().glob("*.docx"), key=os.path.getmtime, reverse=True)
        files = [f for f in files if f.stem != self.session_id]
        if not files:
            return
        latest = files[0]
        meta_path = latest.with_suffix(".json")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {"name": "Belge", "path": None, "time": ""}
        when = meta.get("time", "").replace("T", " ")

        def remove_all():
            for f in files:
                f.unlink(missing_ok=True)
                f.with_suffix(".json").unlink(missing_ok=True)

        def restore():
            if not self._maybe_save():
                return
            try:
                reader = docx_io.Reader(latest)
                self.editor.load(reader.read)
            except Exception as exc:
                QMessageBox.warning(self, "Kurtarılamadı", f"Kurtarma kopyası açılamadı.\n\n{exc}")
                return
            self.path = Path(meta["path"]) if meta.get("path") else None
            self.display_name = meta.get("name") or "Kurtarılan belge"
            self.editor.document().setModified(True)
            remove_all()
            self._after_load()

        self.show_message(
            f"Sözcük düzgün kapanmadığı için kaydedilmemiş bir belge kurtarıldı: "
            f"<b>{meta.get('name', 'Belge')}</b> ({when}).",
            [("Geri Yükle", restore), ("Sil", remove_all)],
        )

    # =========================================================================
    # Durum güncelleme
    # =========================================================================

    def _sync_format_controls(self, *_):
        ed = self.editor
        fmt = ed.currentCharFormat()
        font = fmt.font()

        self.act_bold.setChecked(fmt.fontWeight() >= 600)
        self.act_italic.setChecked(font.italic())
        self.act_underline.setChecked(font.underline())
        self.act_strike.setChecked(font.strikeOut())

        families = fmt.fontFamilies()
        family = families[0] if families else ed.document().defaultFont().family()
        if not self.font_box.hasFocus():
            self.font_box.blockSignals(True)
            self.font_box.setCurrentFont(QFont(family))
            self.font_box.setEditText(family)
            self.font_box.blockSignals(False)

        size = fmt.fontPointSize() or ed.document().defaultFont().pointSizeF()
        if not self.size_box.hasFocus():
            self.size_box.setCurrentText(f"{size:g}".replace(".", ","))

        self.heading_box.setCurrentIndex(min(ed.heading_level(), 2))

        alignment = ed.paragraph_alignment() & Qt.AlignHorizontal_Mask
        if alignment & Qt.AlignHCenter:
            key = Qt.AlignHCenter
        elif alignment & Qt.AlignJustify:
            key = Qt.AlignJustify
        elif alignment & Qt.AlignRight and not alignment & Qt.AlignLeft:
            key = Qt.AlignRight
        else:
            key = Qt.AlignLeft
        self.align_actions[key].setChecked(True)

        spacing = round(ed.line_spacing(), 2)
        for factor, action in self.spacing_actions.items():
            action.setChecked(abs(factor - spacing) < 0.01)

        current_list = ed.textCursor().currentList()
        bullet = styles.is_bullet(current_list.format().style()) if current_list else None
        self.act_bullets.setChecked(bullet is True)
        self.act_numbers.setChecked(bullet is False)

    def _update_undo_redo(self):
        doc = self.editor.document()
        self.act_undo.setEnabled(doc.isUndoAvailable())
        self.act_redo.setEnabled(doc.isRedoAvailable())

    def _update_counts(self):
        words, chars = self.editor.counts()
        self.count_label.setText(f"{words:,} sözcük".replace(",", "."))
        self.count_label.setToolTip(f"{chars:,} karakter (boşluklar dahil)".replace(",", "."))

    def _page_count_changed(self, *_):
        self.editor.viewport().update()
        self._update_page()

    def _update_page(self):
        self.page_label.setText(f"Sayfa {self.editor.current_page()} / {self.editor.page_count()}")

    def _update_title(self, *_):
        modified = self.editor.document().isModified()
        self.setWindowTitle(f"{self.display_name} - Sözcük")   # künye: Yardım → Sözcük Hakkında
        self.title_label.setText(Path(self.display_name).stem)
        provider = cloud.provider_for(self.path)
        tip = ""
        if self.path is None:
            state = "Kaydedilmedi"
        elif self._saving:
            state = f"{provider}'a kaydediliyor…" if provider else "Kaydediliyor…"
        elif self.tracker.conflict:
            state = "Başka yerde değiştirildi — otomatik kayıt bekliyor"
        elif getattr(self, "_save_failed", False):
            state = f"{provider}'a kaydedilemedi" if provider else "Kaydedilemedi"
        elif modified:
            state = "Değiştirildi"
        else:
            state = f"{provider}'a kaydedildi" if provider else "Kaydedildi"
        if provider:
            tip = (f"Belge {provider} klasöründe. Sözcük kaydettiğinde {provider} uygulaması değişiklikleri "
                   "buluta gönderir; internet yoksa bağlantı gelince gönderilir.")
            if self.autosave_switch.isChecked():
                tip += " Otomatik kaydetme açık: yazmaya kısa bir ara verdiğinizde kaydedilir."
        if self.path is not None and self.path.suffix.lower() != ".docx":
            state += f"  ·  Uyumluluk Modu ({self.path.suffix.lower()})"
            tip = (tip + "\n\n" if tip else "") + ("Belge Word Belgesi (.docx) dışında bir biçimde. Otomatik kayıt "
                                                  "yalnızca kurtarma kopyası tutar; Kaydet ile dosyaya yazılır.")
        self.status_label.setText(f"•  {state}")
        self.status_label.setToolTip(tip)
        if self.last_saved:
            self.save_label.setText(f"Son kaydetme: {self.last_saved:%H:%M:%S}" if provider
                                    else f"Son kaydetme: {self.last_saved:%H:%M}")
        else:
            self.save_label.setText("")
