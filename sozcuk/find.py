"""Bul ve Değiştir.

Arama belgedeki paragraflar üzerinde yapılır (tablo hücreleri dahil). Büyük/küçük harf duyarsız aramada
Türkçe kuralları kullanılır: "İ" ile "i", "I" ile "ı" eşleşir — Qt'nin kendi aramasında bu doğru çalışmaz.
Bulunan yerlerin tümü sarıyla, o an seçili olan turuncuyla boyanır (editor.set_highlights).
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolButton, QWidget

from . import icons

LIMIT = 20000   # çok uzun belgelerde vurgulanacak en fazla eşleşme


def tr_fold(text):
    """Türkçe kurallarıyla küçük harf: İ→i, I→ı."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def _boundary(text, index):
    return not (text[index].isalnum() or text[index] == "_") if 0 <= index < len(text) else True


def matches(document, needle, case_sensitive=False, whole_word=False, limit=LIMIT):
    """Belgedeki eşleşmelerin (başlangıç, bitiş) belge konumları, sırayla."""
    if not needle:
        return []
    found = []
    block = document.begin()
    while block.isValid():
        text = block.text()
        haystack = text if case_sensitive else tr_fold(text)
        target = needle if case_sensitive else tr_fold(needle)
        start = haystack.find(target)
        while start >= 0:
            end = start + len(target)
            if not whole_word or (_boundary(text, start - 1) and _boundary(text, end)):
                found.append((block.position() + start, block.position() + end))
                if len(found) >= limit:
                    return found
            start = haystack.find(target, start + 1)
        block = block.next()
    return found


class FindBar(QFrame):
    """Word'ün Bul ve Değiştir'i gibi çalışan, belgenin üstünde açılan şerit."""

    closed = Signal()
    visibilityChanged = Signal(bool)

    def __init__(self, editor, notify=None, parent=None):
        super().__init__(parent)
        self.setObjectName("findBar")
        self.editor = editor
        self.notify = notify or (lambda text: None)
        self.ranges = []
        self.current = -1
        self._dirty = True

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 6, 6)
        row.setSpacing(6)

        self.find_edit = QLineEdit(placeholderText="Aranan")
        self.find_edit.setClearButtonEnabled(True)
        self.find_edit.setMinimumWidth(180)
        self.find_edit.setMaximumWidth(320)
        self.find_edit.textChanged.connect(self._search_changed)
        self.find_edit.returnPressed.connect(lambda: self.go(1))
        row.addWidget(QLabel("Bul:"))
        row.addWidget(self.find_edit)

        self.count_label = QLabel(objectName="findCount")
        self.count_label.setMinimumWidth(96)
        row.addWidget(self.count_label)

        previous = self._button("chevron_up", "Önceki (Shift+F3)", lambda: self.go(-1))
        following = self._button("chevron_down", "Sonraki (F3)", lambda: self.go(1))
        row.addWidget(previous)
        row.addWidget(following)

        self.case_box = QCheckBox("Aa")
        self.case_box.setToolTip("Büyük/küçük harf duyarlı")
        self.case_box.toggled.connect(self._options_changed)
        self.word_box = QCheckBox("Tam sözcük")
        self.word_box.setToolTip("Yalnızca sözcüğün tamamı eşleşsin")
        self.word_box.toggled.connect(self._options_changed)
        row.addWidget(self.case_box)
        row.addWidget(self.word_box)

        self.replace_widgets = QWidget()
        replace_row = QHBoxLayout(self.replace_widgets)
        replace_row.setContentsMargins(0, 0, 0, 0)
        replace_row.setSpacing(6)
        self.replace_edit = QLineEdit(placeholderText="Yeni değer")
        self.replace_edit.setMinimumWidth(160)
        self.replace_edit.setMaximumWidth(320)
        self.replace_edit.returnPressed.connect(self.replace_current)
        replace_row.addWidget(QLabel("Değiştir:"))
        replace_row.addWidget(self.replace_edit)
        self.replace_button = QPushButton("Değiştir")
        self.replace_button.clicked.connect(self.replace_current)
        self.replace_all_button = QPushButton("Tümünü Değiştir")
        self.replace_all_button.clicked.connect(self.replace_all)
        replace_row.addWidget(self.replace_button)
        replace_row.addWidget(self.replace_all_button)
        row.addWidget(self.replace_widgets)
        row.addStretch(1)

        close = QToolButton()
        close.setIcon(icons.icon("close"))
        close.setIconSize(QSize(14, 14))
        close.setToolTip("Kapat (Esc)")
        close.clicked.connect(self.close_bar)
        row.addWidget(close)

        QShortcut(QKeySequence("Esc"), self, self.close_bar)
        QShortcut(QKeySequence("Shift+Return"), self.find_edit, lambda: self.go(-1))
        editor.document().contentsChanged.connect(self._document_changed)
        self.hide()

    @staticmethod
    def _button(icon_name, tip, slot):
        button = QToolButton()
        button.setIcon(icons.icon(icon_name))
        button.setIconSize(QSize(20, 20))
        button.setToolTip(tip)
        button.setFocusPolicy(Qt.NoFocus)
        button.clicked.connect(slot)
        return button

    # --- açma / kapama ------------------------------------------------------

    def open(self, replace=False, text=None):
        self.replace_widgets.setVisible(replace)
        self.show()
        if text:
            self.find_edit.setText(text)
        elif self.editor.textCursor().hasSelection():
            selected = self.editor.textCursor().selectedText()
            if selected and " " not in selected:
                self.find_edit.setText(selected)
        self.visibilityChanged.emit(True)
        self.find_edit.setFocus()
        self.find_edit.selectAll()
        self.refresh(move=False)

    def close_bar(self):
        self.hide()
        self.visibilityChanged.emit(False)
        self.editor.set_highlights([], -1)
        self.editor.setFocus()
        self.closed.emit()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.editor.set_highlights([], -1)

    def is_open(self):
        return self.parentWidget() is not None and self.parentWidget().isVisible() and not self.isHidden()

    # --- arama --------------------------------------------------------------

    def _document_changed(self):
        self._dirty = True
        if self.isVisible():
            self.refresh(move=False, keep_current=True)

    def _search_changed(self):
        self.refresh(move=True, from_start=True)

    def _options_changed(self):
        self.refresh(move=True, from_start=True)

    def refresh(self, move=True, from_start=False, keep_current=False):
        needle = self.find_edit.text()
        position = self.editor.textCursor().selectionStart()
        self.ranges = matches(self.editor.document(), needle, self.case_box.isChecked(), self.word_box.isChecked())
        self._dirty = False
        if not self.ranges:
            self.current = -1
            self.count_label.setText("Sonuç yok" if needle else "")
            self.count_label.setProperty("empty", bool(needle))
            self.editor.set_highlights([], -1)
            self._update_style()
            return
        if not keep_current:
            self.current = next((i for i, (start, _) in enumerate(self.ranges) if start >= position), 0)
        else:
            self.current = min(max(self.current, 0), len(self.ranges) - 1)
        if move:
            self._select_current()
        else:
            self._paint()
        self._update_count()

    def _update_count(self):
        total = len(self.ranges)
        if total >= LIMIT:
            self.count_label.setText(f"{self.current + 1} / {total}+")
        else:
            self.count_label.setText(f"{self.current + 1} / {total}")
        self.count_label.setProperty("empty", False)
        self._update_style()

    def _update_style(self):
        self.count_label.style().unpolish(self.count_label)
        self.count_label.style().polish(self.count_label)

    def _paint(self):
        self.editor.set_highlights(self.ranges, self.current)

    def _select_current(self):
        start, end = self.ranges[self.current]
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensure_cursor_visible()
        self._paint()

    def go(self, direction):
        if self._dirty or not self.ranges:
            self.refresh(move=False)
        if not self.ranges:
            if self.find_edit.text():
                self.notify(f"“{self.find_edit.text()}” bulunamadı.")
            return
        position = self.editor.textCursor().selectionStart()
        if direction > 0:
            index = next((i for i, (start, _) in enumerate(self.ranges) if start > position), 0)
        else:
            index = next((i for i in range(len(self.ranges) - 1, -1, -1) if self.ranges[i][0] < position),
                         len(self.ranges) - 1)
        self.current = index
        self._select_current()
        self._update_count()

    # --- değiştirme ----------------------------------------------------------

    def replace_current(self):
        if not self.ranges:
            self.refresh(move=True)
            return
        cursor = self.editor.textCursor()
        selection = (cursor.selectionStart(), cursor.selectionEnd())
        if selection not in self.ranges:
            self.go(1)
            return
        cursor.insertText(self.replace_edit.text())
        self.editor.setTextCursor(cursor)
        self.refresh(move=False)
        self.go(1)

    def replace_all(self):
        needle = self.find_edit.text()
        if not needle:
            return
        replacement = self.replace_edit.text()
        found = matches(self.editor.document(), needle, self.case_box.isChecked(), self.word_box.isChecked())
        count = len(found)
        if count:
            edit = QTextCursor(self.editor.document())
            edit.beginEditBlock()
            # sondan başa: önceki değişiklikler sonraki konumları kaydırmaz; hepsi tek geri-al adımı
            for start, end in reversed(found):
                edit.setPosition(start)
                edit.setPosition(end, QTextCursor.KeepAnchor)
                edit.insertText(replacement)
            edit.endEditBlock()
        self.editor.set_highlights([], -1)
        self.refresh(move=False)
        self.notify(f"{count} değişiklik yapıldı." if count else f"“{needle}” bulunamadı.")
