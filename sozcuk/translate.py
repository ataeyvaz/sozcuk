"""Çeviri — tamamen bilgisayarda çalışır (Argos Translate / OPUS-MT modelleri).

Neden böyle: Microsoft'un çeviri altyapısı (Word'ün Çevir komutu, Bing/Translator) bir bulut hizmetidir;
kullanmak için abonelik anahtarı gerekir ve metin Microsoft'un sunucularına gider. Windows 11'in cihaz üzerinde
çalışan çeviri API'si ise yalnızca Copilot+ bilgisayarlarda ve 24H2 sürümünde var (bu bilgisayarda yok).
Bu yüzden, sesle yazmada olduğu gibi, açık kaynaklı ve yerel bir model kullanılır: metin bilgisayardan çıkmaz,
internet yalnızca dil paketini bir kez indirmek için gerekir.

Lisans: Argos Translate MIT, çeviri modelleri (OPUS-MT / Argos) CC-BY-4.0 — ücretsiz ve ticari kullanıma açık;
yardım metninde kaynak belirtilir.
"""

import re
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from . import resource_dir

LANGUAGE_NAMES = {
    "tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "fr": "Fransızca", "es": "İspanyolca",
    "it": "İtalyanca", "pt": "Portekizce", "ru": "Rusça", "ar": "Arapça", "az": "Azerbaycan Türkçesi",
    "fa": "Farsça", "nl": "Felemenkçe", "pl": "Lehçe", "uk": "Ukraynaca", "el": "Yunanca", "zh": "Çince",
    "ja": "Japonca", "ko": "Korece", "sv": "İsveççe", "da": "Danca", "fi": "Fince", "cs": "Çekçe",
    "hu": "Macarca", "ro": "Romence", "bg": "Bulgarca", "sr": "Sırpça", "he": "İbranice", "hi": "Hintçe",
    "id": "Endonezce", "ms": "Malayca", "th": "Tayca", "vi": "Vietnamca", "sq": "Arnavutça", "ca": "Katalanca",
    "sk": "Slovakça", "sl": "Slovence", "lt": "Litvanca", "lv": "Letonca", "et": "Estonca", "nb": "Norveççe",
    "ga": "İrlandaca", "eo": "Esperanto", "bn": "Bengalce", "ur": "Urduca", "tl": "Filipince", "eu": "Baskça",
}
# Türkçeye özgü harfler (büyük/küçük ayrımı yapılmaz; IGNORECASE burada "İ"yi "i" ile eşleştirip yanıltıyor)
TURKISH_LETTERS = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
TURKISH_WORDS = re.compile(r"\b(ve|bir|için|ile|bu|olarak|değil|daha|kadar|gibi|mi|de|da)\b", re.IGNORECASE)
AUTO = "auto"
DEFAULT_SOURCE = "tr"
DEFAULT_TARGET = "en"

# Uygulamayla birlikte gelen dil paketleri: bu klasördeki .argosmodel dosyaları ilk kullanımda
# kendiliğinden kurulur (kullanıcı indirmez). Paketlenmiş (.exe) sürümde uygulamanın yanındaki klasöre de bakılır.
BUNDLE_DIR_NAME = "diller"
# Arayüzde gösterilen diller: önce uygulamayla gelenler (İngilizce, Almanca, İtalyanca, İspanyolca),
# sonra istenirse indirilenler
UI_LANGUAGES = ["en", "de", "it", "es", "fr", "ru", "zh", "ja", "hi", "ko", "ar", "pt"]

_lock = threading.Lock()
_index = None
_bundle_installed = False


class TranslateError(Exception):
    pass


def language_name(code):
    return LANGUAGE_NAMES.get(code, code.upper())


def _modules():
    try:
        import argostranslate.package as package
        import argostranslate.translate as translate
    except ImportError as exc:  # kurulu değilse arayüz bunu kullanıcıya söyler
        raise TranslateError("Çeviri bileşeni kurulu değil (argostranslate).") from exc
    return package, translate


def available():
    """Çeviri kullanılabilir mi (bileşen kurulu mu)."""
    try:
        _modules()
        return True
    except TranslateError:
        return False


def bundle_dirs():
    """Uygulamayla gelen dil paketlerinin aranacağı klasörler (paketlenmiş .exe sürümde de bulunur)."""
    folders = [resource_dir() / BUNDLE_DIR_NAME, Path(__file__).resolve().parent / BUNDLE_DIR_NAME]
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
        folders += [base / BUNDLE_DIR_NAME, base / "_internal" / "sozcuk" / BUNDLE_DIR_NAME]
    seen, result = set(), []
    for folder in folders:
        if folder.is_dir() and folder not in seen:
            seen.add(folder)
            result.append(folder)
    return result


def _pair_from_name(stem):
    """"translate-en_fr-1_9" gibi paket adından (kaynak, hedef) çıkarır."""
    for part in stem.split("-"):
        codes = part.split("_")
        if len(codes) == 2 and all(1 < len(code) <= 3 and code.isalpha() for code in codes):
            return tuple(codes)
    return None


def install_bundled():
    """Uygulamayla gelen paketleri (varsa) kurar; kurulan çiftleri döndürür. İlk kullanımda bir kez çalışır."""
    global _bundle_installed
    if _bundle_installed:
        return set()
    _bundle_installed = True
    package, _ = _modules()
    installed = {(p.from_code, p.to_code) for p in package.get_installed_packages()}
    added = set()
    for folder in bundle_dirs():
        for path in sorted(folder.glob("*.argosmodel")):
            try:
                pair = _pair_from_name(path.stem)
                if pair and pair in installed:
                    continue
                package.install_from_path(str(path))
                added.add(pair)
            except Exception:
                continue   # bozuk paket kurulumu çeviriyi engellemesin
    return added


def installed_pairs():
    """Bilgisayarda kurulu dil çiftleri: {(kaynak, hedef)}"""
    package, _ = _modules()
    install_bundled()
    return {(p.from_code, p.to_code) for p in package.get_installed_packages()}


def index_pairs(refresh=False):
    """İndirilebilir dil çiftleri (internet gerekir; başarısızsa kurulu olanlar döner)."""
    global _index
    package, _ = _modules()
    if _index is None or refresh:
        try:
            package.update_package_index()
            _index = package.get_available_packages()
        except Exception:
            _index = []
    return {(p.from_code, p.to_code): p for p in _index}


def pairs_for_ui(refresh=False):
    """Arayüzde gösterilecek çiftler: kurulu olanlar önce, sonra indirilebilirler."""
    installed = installed_pairs()
    catalogue = set(index_pairs(refresh)) | installed
    return sorted(catalogue, key=lambda pair: (pair not in installed, language_name(pair[0]), language_name(pair[1])))


def is_installed(source, target):
    """Doğrudan ya da İngilizce üzerinden çeviri yapılabiliyor mu."""
    pairs = installed_pairs()
    if (source, target) in pairs:
        return True
    return (source, "en") in pairs and ("en", target) in pairs


def missing_packages(source, target):
    """Bu çeviri için indirilmesi gereken paketler."""
    pairs = installed_pairs()
    if (source, target) in pairs:
        return []
    if (source, target) in index_pairs():
        return [(source, target)]
    needed = [pair for pair in ((source, "en"), ("en", target)) if pair[0] != pair[1] and pair not in pairs]
    return needed


# Ölçülen paket boyutları (MB) — dizin bu bilgiyi vermiyor, indirme adresinden ölçüldü
PACKAGE_SIZES = {
    ("tr", "en"): 121, ("en", "tr"): 125, ("en", "de"): 151, ("de", "en"): 151, ("en", "fr"): 65,
    ("fr", "en"): 67, ("en", "es"): 88, ("es", "en"): 285, ("en", "ru"): 196, ("ru", "en"): 156,
    ("en", "zh"): 71, ("zh", "en"): 74, ("en", "ja"): 120, ("ja", "en"): 117, ("en", "hi"): 107,
    ("hi", "en"): 102, ("en", "ko"): 121, ("ko", "en"): 119, ("en", "ar"): 105, ("ar", "en"): 105,
    ("en", "it"): 88, ("it", "en"): 87, ("en", "pt"): 105, ("pt", "en"): 105,
}


def package_size(source, target):
    """Bu çeviri için indirilecek toplam boyut (MB); indirilecek bir şey yoksa 0."""
    total = 0
    for pair in missing_packages(source, target):
        total += PACKAGE_SIZES.get(pair, 120)
    return total


def install(source, target, on_progress=None):
    """Dil paketini (gerekirse İngilizce üzerinden iki paketi) indirir ve kurar; uzun sürer: arka planda çağırın."""
    package, _ = _modules()
    for pair in missing_packages(source, target) or [(source, target)]:
        entry = index_pairs().get(pair)
        if entry is None:
            index_pairs(refresh=True)
            entry = index_pairs().get(pair)
        if entry is None:
            raise TranslateError(f"{language_name(pair[0])} → {language_name(pair[1])} için dil paketi bulunamadı.")
        if on_progress:
            on_progress(f"indiriliyor: {language_name(pair[0])} → {language_name(pair[1])}")
        try:
            path = entry.download()
            package.install_from_path(path)
        except Exception as exc:
            raise TranslateError("Dil paketi indirilemedi. İlk kullanım için internet bağlantısı gerekir.") from exc


def detect(text, candidates=("tr", "en")):
    """Metnin dili (yalnızca Türkçe / diğer ayrımı için basit bir sezgi)."""
    sample = text.strip()[:2000]
    if not sample:
        return candidates[0]
    if TURKISH_LETTERS.search(sample) or TURKISH_WORDS.search(sample):
        return "tr" if "tr" in candidates else candidates[0]
    return "en" if "en" in candidates else candidates[-1]


def translate(text, source, target, on_progress=None):
    """Metni çevirir; paragraf ve satır yapısı korunur. Uzun sürebilir: arka planda çağırın."""
    _, translator = _modules()
    if source == target:
        return text
    if not is_installed(source, target):
        install(source, target, on_progress)
    lines = text.split("\n")
    output = []
    with _lock:   # model yüklemesi iş parçacıkları arasında paylaşılır
        for index, line in enumerate(lines):
            if on_progress and len(lines) > 1:
                on_progress(f"{index + 1}/{len(lines)}")
            stripped = line.strip()
            if not stripped:
                output.append(line)
                continue
            try:
                result = translator.translate(stripped, source, target)
            except Exception as exc:
                raise TranslateError(f"Çeviri yapılamadı: {exc}") from exc
            prefix = line[:len(line) - len(line.lstrip())]
            output.append(prefix + result)
    return "\n".join(output)


# =============================================================================
# Çeviri penceresi
# =============================================================================

class _Worker(QThread):
    """Çeviriyi (ve gerekiyorsa dil paketi indirmeyi) arka planda yapar; arayüz donmaz."""

    progress = Signal(str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, text, source, target, parent=None):
        super().__init__(parent)
        self.text, self.source, self.target = text, source, target

    def run(self):
        try:
            self.done.emit(translate(self.text, self.source, self.target, self.progress.emit))
        except TranslateError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # beklenmeyen model hataları
            self.failed.emit(f"Çeviri yapılamadı: {exc}")


class TranslateDialog(QDialog):
    """Seçili metni ya da belgenin tamamını çevirir; sonucu seçimin yerine koyabilir."""

    def __init__(self, editor, parent=None, settings=None):
        super().__init__(parent)
        self.editor = editor
        self.settings = settings
        self.worker = None
        self.setWindowTitle("Çeviri")
        self.resize(760, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.source_box = QComboBox()
        self.target_box = QComboBox()
        for box in (self.source_box, self.target_box):
            box.setMinimumWidth(180)
        self.swap_button = QPushButton("⇄")
        self.swap_button.setFixedWidth(40)
        self.swap_button.setToolTip("Dilleri değiştir")
        self.swap_button.clicked.connect(self._swap)
        top.addWidget(QLabel("Kaynak dil:"))
        top.addWidget(self.source_box)
        top.addWidget(self.swap_button)
        top.addWidget(QLabel("Hedef dil:"))
        top.addWidget(self.target_box)
        top.addStretch(1)
        layout.addLayout(top)

        texts = QHBoxLayout()
        self.source_text = QPlainTextEdit()
        self.source_text.setPlaceholderText("Çevrilecek metin")
        self.result_text = QPlainTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("Çeviri burada görünecek")
        texts.addWidget(self.source_text)
        texts.addWidget(self.result_text)
        layout.addLayout(texts, 1)

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#616161;")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        self.translate_button = QPushButton("Çevir")
        self.translate_button.setDefault(True)
        self.translate_button.clicked.connect(self.start)
        self.replace_button = QPushButton("Seçimin Yerine Koy")
        self.replace_button.clicked.connect(self._replace)
        self.copy_button = QPushButton("Panoya Kopyala")
        self.copy_button.clicked.connect(self._copy)
        self.packs_button = QPushButton("Dil Paketleri…")
        self.packs_button.clicked.connect(self.show_packs)
        close_button = QPushButton("Kapat")
        close_button.clicked.connect(self.close)
        buttons.addWidget(self.translate_button)
        buttons.addWidget(self.replace_button)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.packs_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self._fill_languages()
        self.source_box.currentIndexChanged.connect(self._source_changed)
        self.result_text.textChanged.connect(self._update_buttons)
        self._update_buttons()

    # --- diller ------------------------------------------------------------

    def _fill_languages(self):
        pairs = pairs_for_ui()
        installed = installed_pairs()
        self.pairs = pairs
        sources = []
        for source, target in pairs:
            if source not in sources:
                sources.append(source)
        self.source_box.addItem("Otomatik algıla", AUTO)
        for code in sources:
            self.source_box.addItem(language_name(code), code)
        remembered = self.settings.value("translate/target", DEFAULT_TARGET) if self.settings else DEFAULT_TARGET
        self._source_changed()
        index = self.target_box.findData(remembered)
        if index >= 0:
            self.target_box.setCurrentIndex(index)
        self.installed = installed

    def _source_changed(self):
        source = self.source_box.currentData()
        current = self.target_box.currentData()
        self.target_box.blockSignals(True)
        self.target_box.clear()
        targets = []
        for a, b in self.pairs:
            if (source in (AUTO, a)) and b not in targets:
                targets.append(b)
        reference = DEFAULT_SOURCE if source == AUTO else source
        for code in targets:
            size = 0 if code == reference else package_size(reference, code)
            suffix = f"  (indirilecek ≈{size} MB)" if size else ""
            self.target_box.addItem(language_name(code) + suffix, code)
        index = self.target_box.findData(current)
        self.target_box.setCurrentIndex(max(0, index))
        self.target_box.blockSignals(False)

    def _swap(self):
        source, target = self.source_box.currentData(), self.target_box.currentData()
        if source == AUTO:
            source = detect(self.source_text.toPlainText())
        index = self.source_box.findData(target)
        if index >= 0:
            self.source_box.setCurrentIndex(index)
        index = self.target_box.findData(source)
        if index >= 0:
            self.target_box.setCurrentIndex(index)
        self.source_text.setPlainText(self.result_text.toPlainText())
        self.result_text.clear()

    # --- kullanım -----------------------------------------------------------

    def load_from_editor(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText().replace("\u2029", "\n").replace("\u2028", "\n")
            self.status.setText("Seçili metin çevrilecek.")
        else:
            text = self.editor.toPlainText()
            self.status.setText("Seçim olmadığı için belgenin tamamı alındı; isterseniz metni düzenleyebilirsiniz.")
        self.source_text.setPlainText(text.replace("\ufffc", ""))
        self.result_text.clear()
        self._update_buttons()

    def start(self):
        if self.worker is not None and self.worker.isRunning():
            return
        text = self.source_text.toPlainText().strip()
        if not text:
            self.status.setText("Çevrilecek metin yok.")
            return
        source = self.source_box.currentData()
        if source == AUTO:
            source = detect(text, [code for code, _ in self.pairs] or ["tr", "en"])
            index = self.source_box.findData(source)
            if index >= 0:
                self.source_box.setCurrentIndex(index)
        target = self.target_box.currentData()
        if source == target:
            self.status.setText("Kaynak ve hedef dil aynı.")
            return
        if self.settings is not None:
            self.settings.setValue("translate/target", target)
        size = package_size(source, target)
        if not is_installed(source, target):
            note = f" (≈{size} MB)" if size else ""
            self.status.setText(f"{language_name(source)} → {language_name(target)} dil paketi indiriliyor{note}. "
                                "Bu yalnızca ilk kullanımda olur ve internet gerektirir…")
        else:
            self.status.setText("Çeviriliyor…")
        self.translate_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.worker = _Worker(self.source_text.toPlainText(), source, target, self)
        self.worker.progress.connect(self._progress)
        self.worker.done.connect(self._finished)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _progress(self, text):
        if text == "indiriliyor":
            return
        self.status.setText(f"Çeviriliyor… ({text})")

    def _finished(self, text):
        QApplication.restoreOverrideCursor()
        self.translate_button.setEnabled(True)
        self.result_text.setPlainText(text)
        self.status.setText("Çeviri tamamlandı. Metin bilgisayarınızda çevrildi, hiçbir yere gönderilmedi.")
        self._update_buttons()

    def _failed(self, message):
        QApplication.restoreOverrideCursor()
        self.translate_button.setEnabled(True)
        self.status.setText(message)

    def _update_buttons(self):
        has_result = bool(self.result_text.toPlainText().strip())
        self.replace_button.setEnabled(has_result and self.editor.textCursor().hasSelection())
        self.copy_button.setEnabled(has_result)

    def _replace(self):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return
        cursor.insertText(self.result_text.toPlainText())
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        self.status.setText("Çeviri belgeye yerleştirildi.")
        self._update_buttons()

    def _copy(self):
        QApplication.clipboard().setText(self.result_text.toPlainText())
        self.status.setText("Çeviri panoya kopyalandı.")

    def show_packs(self):
        dialog = LanguagePacksDialog(self)
        dialog.exec()
        current = self.target_box.currentData()
        self._source_changed()
        index = self.target_box.findData(current)
        if index >= 0:
            self.target_box.setCurrentIndex(index)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(50)
        super().closeEvent(event)


class _InstallWorker(QThread):
    """Dil paketlerini arka planda indirip kurar."""

    progress = Signal(str)
    finished_with = Signal(list, str)   # kurulanlar, hata metni ("" ise sorun yok)

    def __init__(self, pairs, parent=None):
        super().__init__(parent)
        self.pairs = list(pairs)

    def run(self):
        done, error = [], ""
        for source, target in self.pairs:
            try:
                self.progress.emit(f"{language_name(source)} → {language_name(target)} indiriliyor…")
                install(source, target)
                done.append((source, target))
            except TranslateError as exc:
                error = str(exc)
                break
            except Exception as exc:
                error = f"Dil paketi kurulamadı: {exc}"
                break
        self.finished_with.emit(done, error)


class LanguagePacksDialog(QDialog):
    """Dil paketleri: hangi diller hazır, hangileri indirilecek. Toplu indirme buradan yapılır."""

    def __init__(self, parent=None, languages=None):
        super().__init__(parent)
        self.setWindowTitle("Dil Paketleri")
        self.resize(520, 480)
        self.worker = None
        self.languages = list(languages or UI_LANGUAGES)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)
        info = QLabel("Çeviri bilgisayarınızda yapılır. Buradaki diller Türkçeden çevirmek ve Türkçeye çevirmek "
                      "için kullanılır; işaretlediklerinizi bir kez indirdikten sonra internet gerekmez.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list = QListWidget()
        layout.addWidget(self.list, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#616161;")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        self.download_button = QPushButton("Seçilenleri İndir")
        self.download_button.clicked.connect(self.start)
        close_button = QPushButton("Kapat")
        close_button.clicked.connect(self.close)
        buttons.addWidget(self.download_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self):
        self.list.clear()
        bundled = bool(bundle_dirs())
        total_missing = 0
        for code in self.languages:
            pairs = [("tr", code), (code, "tr")]
            missing = []
            for source, target in pairs:
                missing += [pair for pair in missing_packages(source, target) if pair not in missing]
            size = sum(PACKAGE_SIZES.get(pair, 120) for pair in missing)
            total_missing += size
            item = QListWidgetItem(f"Türkçe ⇄ {language_name(code)}" + ("" if missing else "   ✔ hazır")
                                   + (f"   (indirilecek ≈{size} MB)" if missing else ""))
            item.setData(Qt.UserRole, missing)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            if not missing:
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable & ~Qt.ItemIsEnabled)
            self.list.addItem(item)
        ready = sum(1 for i in range(self.list.count()) if not self.list.item(i).data(Qt.UserRole))
        note = f"{ready} dil hazır." if ready else "Henüz hazır dil yok."
        if bundled:
            note += " Uygulamayla gelen paketler kendiliğinden kuruldu."
        if total_missing:
            note += f" Tümünü indirmek ≈{total_missing} MB yer kaplar."
        self.status.setText(note)
        self.download_button.setEnabled(any(self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())))

    def selected_pairs(self):
        pairs = []
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.checkState() == Qt.Checked:
                for pair in item.data(Qt.UserRole):
                    if pair not in pairs:
                        pairs.append(pair)
        return pairs

    def start(self):
        pairs = self.selected_pairs()
        if not pairs:
            self.status.setText("İndirilecek dilleri işaretleyin.")
            return
        size = sum(PACKAGE_SIZES.get(pair, 120) for pair in pairs)
        self.download_button.setEnabled(False)
        self.status.setText(f"İndiriliyor (≈{size} MB)… Bu işlem bağlantı hızınıza göre birkaç dakika sürebilir.")
        self.worker = _InstallWorker(pairs, self)
        self.worker.progress.connect(self.status.setText)
        self.worker.finished_with.connect(self._done)
        self.worker.start()

    def _done(self, installed, error):
        self.refresh()
        self.download_button.setEnabled(True)
        if error:
            self.status.setText(error)
        elif installed:
            self.status.setText(f"{len(installed)} dil paketi kuruldu; artık çevrimdışı kullanılabilir.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("İndirme sürüyor; pencereyi kapatabilirsiniz, indirme arka planda tamamlanır.")
        super().closeEvent(event)
