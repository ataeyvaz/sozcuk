"""Dikte sözlüğü penceresi: elle kelime/düzeltme ekleme, öğrenilenleri onaylama ve silme."""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .vocabulary import LEARN_THRESHOLD, MANUAL


def _source_text(source):
    return "Doğrulandı" if source == MANUAL else "Öğrenildi"


class CorrectionDialog(QDialog):
    """Doğrulanmış dikte düzeltmesi: Whisper'ın yanlış tanıdığı ifade ve doğrusu."""

    def __init__(self, parent=None, wrong="", right=""):
        super().__init__(parent)
        self.setWindowTitle("Dikte Düzeltmesi Kaydet")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 12)
        layout.setSpacing(8)

        intro = QLabel(
            "Sesle yazarken yanlış tanınan bir ifadeyi ve doğrusunu kaydedin. Kayıt <b>doğrulanmış</b> "
            "sayılır: sonraki diktelerde hemen otomatik düzeltilir ve doğru hali tanımaya ipucu olarak verilir."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(intro)

        layout.addWidget(QLabel("Dikte ederken tanınan (yanlış):"))
        self.wrong_edit = QLineEdit(wrong)
        self.wrong_edit.setPlaceholderText("ör. tiktik")
        layout.addWidget(self.wrong_edit)
        layout.addWidget(QLabel("Doğrusu:"))
        self.right_edit = QLineEdit(right)
        self.right_edit.setPlaceholderText("ör. diktek")
        layout.addWidget(self.right_edit)

        self.status = QLabel()
        self.status.setStyleSheet("color: #c42b1c;")
        layout.addWidget(self.status)

        buttons = QDialogButtonBox()
        save = buttons.addButton("Kaydet", QDialogButtonBox.AcceptRole)
        save.setDefault(True)
        buttons.addButton("İptal", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        (self.right_edit if wrong and not right else self.wrong_edit if not wrong else self.right_edit).setFocus()

    def values(self):
        return self.wrong_edit.text().strip(), self.right_edit.text().strip()

    def _accept(self):
        wrong, right = self.values()
        if not wrong or not right:
            self.status.setText("Tanınan ve doğru hali birlikte yazın.")
            return
        if wrong.casefold() == right.casefold():
            self.status.setText("İki ifade aynı.")
            return
        self.accept()


def _table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().hide()
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    for column in range(1, len(headers)):
        table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
    return table


class VocabularyDialog(QDialog):
    def __init__(self, vocabulary, parent=None, initial_word=""):
        super().__init__(parent)
        self.vocabulary = vocabulary
        self.setWindowTitle("Dikte Sözlüğü")
        self.resize(560, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 12)
        layout.setSpacing(10)
        intro = QLabel(
            "<b>Kelimeler</b> (özel adlar, terimler) sesle yazarken tanımaya ipucu olarak verilir. "
            "<b>Düzeltmeler</b> (ör. “tiktik” → “diktek”) dikte edilen metne otomatik uygulanır.<br>"
            "Buradan ya da belgede kelimeye sağ tıklayarak eklenen kayıtlar <b>doğrulanmış</b> sayılır ve hemen "
            "etkin olur. Dikte ettiğiniz metinde bir kelimeyi düzelttiğinizde Sözcük bunu öğrenir ve doğrulamanızı "
            f"sorar; doğrulanmayan öğrenilmiş bir düzeltme {LEARN_THRESHOLD} kez görülünce etkin olur.<br>"
            "Sözlük yalnızca bu bilgisayarda saklanır."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(intro)

        tabs = QTabWidget()
        tabs.addTab(self._build_words_tab(initial_word), "Kelimeler")
        tabs.addTab(self._build_corrections_tab(), "Düzeltmeler")
        layout.addWidget(tabs, 1)

        buttons = QDialogButtonBox()
        close = buttons.addButton("Kapat", QDialogButtonBox.RejectRole)
        close.setDefault(False)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh()

    # --- kelimeler -------------------------------------------------------------

    def _build_words_tab(self, initial_word):
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.word_edit = QLineEdit(initial_word)
        self.word_edit.setPlaceholderText("Yeni kelime ya da ifade, ör. “Gülbeyaz Yılmazer”")
        self.word_edit.returnPressed.connect(self._add_word)
        add = QPushButton("Ekle")
        add.clicked.connect(self._add_word)
        row.addWidget(self.word_edit, 1)
        row.addWidget(add)
        layout.addLayout(row)

        self.word_table = _table(["Kelime / ifade", "Kaynak", "Kullanım"])
        self.word_table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.word_table, 1)

        actions = QHBoxLayout()
        self.word_status = QLabel()
        self.word_status.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        self.confirm_word_button = QPushButton("Doğrula")
        self.confirm_word_button.setToolTip("Öğrenilen kelimeyi doğrulanmış kayıt yap")
        self.confirm_word_button.clicked.connect(self._confirm_word)
        self.remove_word_button = QPushButton("Sil")
        self.remove_word_button.clicked.connect(self._remove_word)
        actions.addWidget(self.word_status, 1)
        actions.addWidget(self.confirm_word_button)
        actions.addWidget(self.remove_word_button)
        layout.addLayout(actions)
        return page

    def _add_word(self):
        text = self.word_edit.text().strip()
        if not text:
            return
        if self.vocabulary.add_word(text):
            self.word_status.setText(f"“{text}” eklendi.")
        else:
            self.word_status.setText(f"“{text}” zaten sözlükte.")
        self.word_edit.clear()
        self._refresh()

    def _selected_word(self):
        row = self.word_table.currentRow()
        item = self.word_table.item(row, 0) if row >= 0 else None
        return self.vocabulary.find_word(item.text()) if item else None

    def _confirm_word(self):
        word = self._selected_word()
        if word:
            self.vocabulary.confirm(word)
            self._refresh()

    def _remove_word(self):
        word = self._selected_word()
        if word:
            self.vocabulary.remove_word(word.text)
            self.word_status.setText(f"“{word.text}” silindi.")
            self._refresh()

    # --- düzeltmeler -----------------------------------------------------------

    def _build_corrections_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.wrong_edit = QLineEdit()
        self.wrong_edit.setPlaceholderText("Tanınan (yanlış), ör. “Ara yüzü”")
        self.right_edit = QLineEdit()
        self.right_edit.setPlaceholderText("Doğrusu, ör. “arayüzü”")
        self.right_edit.returnPressed.connect(self._add_correction)
        arrow = QLabel("→")
        add = QPushButton("Ekle")
        add.clicked.connect(self._add_correction)
        row.addWidget(self.wrong_edit, 1)
        row.addWidget(arrow)
        row.addWidget(self.right_edit, 1)
        row.addWidget(add)
        layout.addLayout(row)

        self.correction_table = _table(["Tanınan", "Doğrusu", "Kaynak", "Durum"])
        self.correction_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.correction_table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.correction_table, 1)

        actions = QHBoxLayout()
        self.correction_status = QLabel()
        self.correction_status.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        self.confirm_correction_button = QPushButton("Doğrula")
        self.confirm_correction_button.setToolTip("Öğrenilen düzeltmeyi doğrulanmış kayıt yap (hemen etkin olur)")
        self.confirm_correction_button.clicked.connect(self._confirm_correction)
        self.remove_correction_button = QPushButton("Sil")
        self.remove_correction_button.clicked.connect(self._remove_correction)
        actions.addWidget(self.correction_status, 1)
        actions.addWidget(self.confirm_correction_button)
        actions.addWidget(self.remove_correction_button)
        layout.addLayout(actions)
        return page

    def _add_correction(self):
        wrong, right = self.wrong_edit.text().strip(), self.right_edit.text().strip()
        if not wrong or not right:
            self.correction_status.setText("Tanınan ve doğru hali birlikte yazın.")
            return
        if self.vocabulary.add_correction(wrong, right) is None:
            self.correction_status.setText("İki ifade aynı; düzeltme eklenmedi.")
            return
        self.correction_status.setText(f"“{wrong}” → “{right}” eklendi.")
        self.wrong_edit.clear()
        self.right_edit.clear()
        self.wrong_edit.setFocus()
        self._refresh()

    def _selected_correction(self):
        row = self.correction_table.currentRow()
        item = self.correction_table.item(row, 0) if row >= 0 else None
        return self.vocabulary.find_correction(item.text()) if item else None

    def _confirm_correction(self):
        correction = self._selected_correction()
        if correction:
            self.vocabulary.confirm(correction)
            self._refresh()

    def _remove_correction(self):
        correction = self._selected_correction()
        if correction:
            self.vocabulary.remove_correction(correction.wrong)
            self.correction_status.setText(f"“{correction.wrong}” düzeltmesi silindi.")
            self._refresh()

    # --- ortak -----------------------------------------------------------------

    def _refresh(self):
        words = sorted(self.vocabulary.words, key=lambda w: (w.source != MANUAL, w.text.casefold()))
        self.word_table.setRowCount(len(words))
        for row, word in enumerate(words):
            self._set_row(self.word_table, row, [word.text, _source_text(word.source), str(word.uses)])

        corrections = sorted(self.vocabulary.corrections, key=lambda c: (c.source != MANUAL, c.wrong.casefold()))
        self.correction_table.setRowCount(len(corrections))
        for row, c in enumerate(corrections):
            state = "Etkin" if c.active else f"Öğreniliyor ({c.count}/{LEARN_THRESHOLD})"
            self._set_row(self.correction_table, row, [c.wrong, c.right, _source_text(c.source), state])
        self._update_buttons()

    @staticmethod
    def _set_row(table, row, values):
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))

    def _update_buttons(self):
        word = self._selected_word()
        self.remove_word_button.setEnabled(word is not None)
        self.confirm_word_button.setEnabled(word is not None and word.source != MANUAL)
        correction = self._selected_correction()
        self.remove_correction_button.setEnabled(correction is not None)
        self.confirm_correction_button.setEnabled(correction is not None and correction.source != MANUAL)
