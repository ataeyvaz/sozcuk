"""Belgenin sayfalarını JPEG olarak kaydetme (PDF'ten açılıp düzenlenen belgeler dâhil).

Dosya adları belge adına sayfa numarası eklenerek verilir: ornek01.jpeg, ornek02.jpeg …
Qt'ye bağlı olmayan yardımcılar (sayfa aralığı, dosya adı) testlerde doğrudan kullanılır.
"""

import re
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

DPI_CHOICES = [("Ekran (96 dpi)", 96), ("Normal (150 dpi)", 150), ("Yüksek (200 dpi)", 200), ("Baskı (300 dpi)", 300)]
EXTENSION = ".jpeg"


class RangeError(ValueError):
    pass


def parse_pages(text, total):
    """'1-3, 5, 8-' gibi bir aralığı sıralı, tekrarsız sayfa numaralarına çevirir. Hatalıysa RangeError."""
    pages = set()
    for part in re.split(r"[,;\s]+", text.strip()):
        if not part:
            continue
        match = re.fullmatch(r"(\d*)\s*[-–]\s*(\d*)", part)
        if match and (match.group(1) or match.group(2)):
            start = int(match.group(1) or 1)
            end = int(match.group(2) or total)
        elif part.isdigit():
            start = end = int(part)
        else:
            raise RangeError(f"“{part}” anlaşılamadı. Örnek: 1-3, 5, 8-")
        if start > end:
            raise RangeError(f"“{part}” aralığı ters.")
        if start < 1 or end > total:
            raise RangeError(f"Sayfa numaraları 1 ile {total} arasında olmalı.")
        pages.update(range(start, end + 1))
    if not pages:
        raise RangeError("Sayfa seçilmedi.")
    return sorted(pages)


def file_name(stem, page, total):
    """ornek + 7 sayfa -> ornek1.jpeg değil ornek01.jpeg: numara en az iki hane, toplama göre genişler."""
    digits = max(2, len(str(total)))
    return f"{stem}{page:0{digits}d}{EXTENSION}"


class JpegExportDialog(QDialog):
    def __init__(self, parent, total, stem, folder):
        super().__init__(parent)
        self.setWindowTitle("JPEG Olarak Kaydet")
        self.total = total
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Belgede {total} sayfa var. Her sayfa ayrı bir JPEG dosyası olarak kaydedilir."))

        self.all_radio = QRadioButton("Tüm sayfalar")
        self.some_radio = QRadioButton("Seçilen sayfalar:")
        self.all_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.all_radio)
        group.addButton(self.some_radio)
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("örn. 1-3, 5, 8-")
        self.range_edit.textEdited.connect(lambda: self.some_radio.setChecked(True))
        layout.addWidget(self.all_radio)
        layout.addWidget(self.some_radio)
        layout.addWidget(self.range_edit)

        form = QFormLayout()
        self.name_edit = QLineEdit(stem)
        self.folder_edit = QLineEdit(str(folder))
        browse = QDialogButtonBox()
        browse_button = browse.addButton("Gözat…", QDialogButtonBox.ActionRole)
        browse_button.clicked.connect(self._browse)
        self.dpi_combo = QComboBox()
        for label, dpi in DPI_CHOICES:
            self.dpi_combo.addItem(label, dpi)
        self.dpi_combo.setCurrentIndex(1)
        self.quality = QSpinBox()
        self.quality.setRange(10, 100)
        self.quality.setValue(90)
        self.quality.setSuffix(" %")
        self.preview = QLabel()
        form.addRow("Dosya adı:", self.name_edit)
        form.addRow("Klasör:", self.folder_edit)
        form.addRow("", browse)
        form.addRow("Çözünürlük:", self.dpi_combo)
        form.addRow("Kalite:", self.quality)
        form.addRow("Örnek ad:", self.preview)
        layout.addLayout(form)

        self.error = QLabel()
        self.error.setStyleSheet("color: #b00020;")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Kaydet")
        buttons.button(QDialogButtonBox.Cancel).setText("Vazgeç")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.name_edit.textChanged.connect(self._update_preview)
        self._update_preview()
        self.pages = []

    def _update_preview(self):
        self.preview.setText(file_name(self.name_edit.text().strip() or "belge", 1, self.total))

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç", self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)

    def _accept(self):
        try:
            self.pages = list(range(1, self.total + 1)) if self.all_radio.isChecked() \
                else parse_pages(self.range_edit.text(), self.total)
        except RangeError as exc:
            self.error.setText(str(exc))
            return
        if not self.name_edit.text().strip():
            self.error.setText("Dosya adı boş olamaz.")
            return
        if not Path(self.folder_edit.text()).is_dir():
            self.error.setText("Klasör bulunamadı.")
            return
        self.accept()

    def result_values(self):
        return {
            "pages": self.pages,
            "stem": re.sub(r'[\\/:*?"<>|]', "_", self.name_edit.text().strip()),
            "folder": Path(self.folder_edit.text()),
            "dpi": self.dpi_combo.currentData(),
            "quality": self.quality.value(),
        }
