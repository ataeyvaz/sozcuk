"""Çeviri — tamamen bilgisayarda çalışır (OPUS-MT / Argos Translate dil paketleri, CTranslate2 ile).

Neden böyle: Microsoft'un çeviri altyapısı (Word'ün Çevir komutu, Bing/Translator) bir bulut hizmetidir;
kullanmak için abonelik anahtarı gerekir ve metin Microsoft'un sunucularına gider. Windows 11'in cihaz üzerinde
çalışan çeviri API'si ise yalnızca Copilot+ bilgisayarlarda ve 24H2 sürümünde var (bu bilgisayarda yok).
Bu yüzden, sesle yazmada olduğu gibi, açık kaynaklı ve yerel bir model kullanılır: metin bilgisayardan çıkmaz,
internet yalnızca dil paketini bir kez indirmek için gerekir.

Argos Translate kütüphanesinin kendisi kullanılmaz: çeviriyi zaten CTranslate2 + SentencePiece yapıyor; Argos
yalnızca cümle bölmek için torch, stanza ve spacy getiriyordu (paketi ~500 MB büyütüyordu). Dil paketleri
(.argosmodel) aynı kalır; burada doğrudan okunur, cümleler basit kurallarla bölünür.

Dil paketlerinin arandığı yerler:
- uygulamayla gelen (Türkçe ⇄ İngilizce): sozcuk/diller/ (açılmış klasör; kopyalanmadan kullanılır)
- kurulumda seçilenler: Sozcuk.exe'nin yanındaki diller/ klasörü (Inno Setup indirip açar)
- sonradan indirilenler: %LOCALAPPDATA%\\Sözcük\\diller

Lisans: Argos Translate MIT, çeviri modelleri (OPUS-MT / Argos) CC-BY-4.0 — ücretsiz ve ticari kullanıma açık;
yardım metninde kaynak belirtilir.
"""

import json
import re
import shutil
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QThread, Qt, Signal
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

BUNDLE_DIR_NAME = "diller"
# Arayüzde gösterilen diller: Türkçe ⇄ İngilizce uygulamayla gelir, diğerleri kurulumda ya da sonradan indirilir
UI_LANGUAGES = ["en", "de", "it", "es", "fr", "ru", "zh", "ja", "hi", "ko", "ar", "pt"]

# Argos Translate'in paket dizini (indirme adresleri buradan alınır)
INDEX_URL = "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json"
DOWNLOAD_TIMEOUT = 60
# İndirme sunucusu (argos-net.com) Python'un varsayılan kimliğiyle gelen istekleri reddediyor (403)
USER_AGENT = "Sozcuk (https://github.com/ataeyvaz/sozcuk)"

# Argos Translate'in varsayılan çeviri ayarları
BEAM_SIZE = 4
LENGTH_PENALTY = 0.2
MAX_SENTENCE_CHARS = 400   # daha uzun "cümleler" (madde listeleri, noktasız paragraflar) virgülden bölünür

_lock = threading.Lock()
_index = None
_packages = None
_translators = {}


class TranslateError(Exception):
    pass


def language_name(code):
    return LANGUAGE_NAMES.get(code, code.upper())


def _engine():
    try:
        import ctranslate2
        import sentencepiece
    except ImportError as exc:  # kurulu değilse arayüz bunu kullanıcıya söyler
        raise TranslateError("Çeviri bileşeni kurulu değil (ctranslate2, sentencepiece).") from exc
    return ctranslate2, sentencepiece


def available():
    """Çeviri kullanılabilir mi (bileşen kurulu mu)."""
    try:
        _engine()
        return True
    except TranslateError:
        return False


# =============================================================================
# Dil paketleri
# =============================================================================

def user_dir():
    """Uygulamanın sonradan indirdiği paketler (büyük dosyalar: dolaşan profile değil, yerel klasöre)."""
    return Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / BUNDLE_DIR_NAME


def bundle_dirs():
    """Uygulamayla ve kurulumla gelen dil paketlerinin klasörleri (varsa)."""
    folders = [resource_dir() / BUNDLE_DIR_NAME, Path(__file__).resolve().parent / BUNDLE_DIR_NAME]
    if getattr(sys, "frozen", False):
        folders.append(Path(sys.executable).resolve().parent / BUNDLE_DIR_NAME)
    seen, result = set(), []
    for folder in folders:
        folder = folder.resolve()
        if folder.is_dir() and folder not in seen:
            seen.add(folder)
            result.append(folder)
    return result


class Package:
    """Açılmış bir dil paketi klasörü: model/ (CTranslate2), sentencepiece.model ya da bpe.model, metadata.json."""

    def __init__(self, path, metadata):
        self.path = path
        self.source = metadata["from_code"]
        self.target = metadata["to_code"]
        self.target_prefix = metadata.get("target_prefix", "")
        self.version = metadata.get("package_version", "")
        self._tokenizer = None

    @property
    def pair(self):
        return self.source, self.target

    def encode(self, sentence):
        kind, tool = self._load_tokenizer()
        if kind == "spm":
            return tool.encode(sentence, out_type=str)
        normalizer, tokenizer, _, bpe = tool
        words = tokenizer.tokenize(normalizer.normalize(sentence))
        return bpe.segment_tokens(" ".join(words).strip("\r\n ").split(" "))

    def decode(self, tokens):
        kind, tool = self._load_tokenizer()
        if kind == "spm":
            # bazı 1.9 paketlerinde (ör. İngilizce → Fransızca) kelime ayırıcı "▁" metinde kalıyor
            return tool.decode(tokens).replace("▁", " ")
        return tool[2].detokenize(" ".join(tokens).replace("@@ ", "").split(" "))

    def _load_tokenizer(self):
        if self._tokenizer is None:
            spm_file = self.path / "sentencepiece.model"
            if spm_file.exists():
                _, sentencepiece = _engine()
                self._tokenizer = ("spm", sentencepiece.SentencePieceProcessor(model_file=str(spm_file)))
            else:
                # daha yeni (1.9) paketlerin bir kısmı Moses + BPE kullanır
                from sacremoses import MosesDetokenizer, MosesPunctNormalizer, MosesTokenizer

                from .apply_bpe import BPE

                with open(self.path / "bpe.model", encoding="utf-8") as codes:
                    bpe = BPE(codes)
                self._tokenizer = ("bpe", (MosesPunctNormalizer(self.source), MosesTokenizer(self.source),
                                           MosesDetokenizer(self.target), bpe))
        return self._tokenizer


def _read_package(folder):
    try:
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if metadata.get("type", "translate") != "translate" or not (folder / "model").is_dir():
        return None
    if not metadata.get("from_code") or not metadata.get("to_code"):
        return None
    return Package(folder, metadata)


def _scan():
    """Kurulu paketler: {(kaynak, hedef): Package}. Aynı çiftten birden fazla varsa ilk bulunan kullanılır."""
    found = {}
    for folder in bundle_dirs() + [user_dir()]:
        if not folder.is_dir():
            continue
        for child in sorted(folder.iterdir()):
            if child.is_dir():
                package = _read_package(child)
                if package is not None and package.pair not in found:
                    found[package.pair] = package
    return found


def installed_packages(refresh=False):
    global _packages
    if _packages is None or refresh:
        _packages = _scan()
    return _packages


def installed_pairs():
    """Bilgisayarda kurulu dil çiftleri: {(kaynak, hedef)}"""
    return set(installed_packages())


def _open(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT)


def index_pairs(refresh=False):
    """İndirilebilir dil çiftleri: {(kaynak, hedef): indirme adresleri}. İnternet yoksa boş döner."""
    global _index
    if _index is None or refresh:
        try:
            with _open(INDEX_URL) as response:
                entries = json.loads(response.read().decode("utf-8"))
            _index = {(entry["from_code"], entry["to_code"]): entry.get("links", [])
                      for entry in entries
                      if entry.get("type", "translate") == "translate" and entry.get("links")}
        except Exception:
            _index = {}
    return _index


def pairs_for_ui(refresh=False):
    """Arayüzde gösterilecek çiftler: kurulu olanlar önce, sonra indirilebilirler."""
    installed = installed_pairs()
    catalogue = set(index_pairs(refresh)) | installed
    return sorted(catalogue, key=lambda pair: (pair not in installed, language_name(pair[0]), language_name(pair[1])))


def _route(source, target, pairs):
    """Çeviri yolu: doğrudan ya da İngilizce üzerinden; yoksa None."""
    if (source, target) in pairs:
        return [(source, target)]
    if (source, "en") in pairs and ("en", target) in pairs:
        return [(source, "en"), ("en", target)]
    return None


def is_installed(source, target):
    """Doğrudan ya da İngilizce üzerinden çeviri yapılabiliyor mu."""
    return _route(source, target, installed_pairs()) is not None


def missing_packages(source, target):
    """Bu çeviri için indirilmesi gereken paketler."""
    pairs = installed_pairs()
    if _route(source, target, pairs):
        return []
    if (source, target) in index_pairs():
        return [(source, target)]
    return [pair for pair in ((source, "en"), ("en", target)) if pair[0] != pair[1] and pair not in pairs]


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
    return sum(PACKAGE_SIZES.get(pair, 120) for pair in missing_packages(source, target))


def extract_package(archive, destination):
    """.argosmodel (zip) arşivini hedef klasöre açar; cümle bölücü (stanza/) klasörü gerekmediği için atlanır."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        names = [name for name in bundle.namelist() if "/stanza/" not in name]
        tops = {name.split("/", 1)[0] for name in names}
        if len(tops) != 1 or any(name.startswith(("/", "\\")) or ".." in Path(name).parts for name in names):
            raise TranslateError("Dil paketi beklenen biçimde değil.")
        top = tops.pop()
        final = destination / top
        staging = Path(tempfile.mkdtemp(prefix="dil-", dir=destination))
        try:
            for name in names:
                bundle.extract(name, staging)
            if final.exists():
                shutil.rmtree(final)
            (staging / top).rename(final)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return final


def download_package(pair, destination, on_progress=None):
    """Dil paketini indirip hedef klasöre açar (internet gerekir)."""
    links = index_pairs().get(pair) or index_pairs(refresh=True).get(pair)
    if not links:
        raise TranslateError(f"{language_name(pair[0])} → {language_name(pair[1])} için dil paketi bulunamadı.")
    if on_progress:
        on_progress(f"indiriliyor: {language_name(pair[0])} → {language_name(pair[1])}")
    destination.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(suffix=".argosmodel", dir=destination)
    try:
        with open(handle, "wb") as file:
            for link in links:
                try:
                    with _open(link) as response:
                        shutil.copyfileobj(response, file, 1 << 20)
                    break
                except Exception:
                    file.seek(0)
                    file.truncate()
            else:
                raise TranslateError("Dil paketi indirilemedi. İlk kullanım için internet bağlantısı gerekir.")
        return extract_package(temporary, destination)
    except zipfile.BadZipFile as exc:
        raise TranslateError("İndirilen dil paketi bozuk; lütfen yeniden deneyin.") from exc
    finally:
        Path(temporary).unlink(missing_ok=True)


def install(source, target, on_progress=None):
    """Dil paketini (gerekirse İngilizce üzerinden iki paketi) indirir ve açar; uzun sürer: arka planda çağırın."""
    _engine()
    for pair in missing_packages(source, target) or [(source, target)]:
        download_package(pair, user_dir(), on_progress)
    installed_packages(refresh=True)


def detect(text, candidates=("tr", "en")):
    """Metnin dili (yalnızca Türkçe / diğer ayrımı için basit bir sezgi)."""
    sample = text.strip()[:2000]
    if not sample:
        return candidates[0]
    if TURKISH_LETTERS.search(sample) or TURKISH_WORDS.search(sample):
        return "tr" if "tr" in candidates else candidates[0]
    return "en" if "en" in candidates else candidates[-1]


# =============================================================================
# Çeviri
# =============================================================================

# Cümle sonu: . ! ? … (ardından tırnak/parantez olabilir), boşluk ve büyük harf ya da rakamla başlayan yeni cümle.
_SENTENCE_END = re.compile(r"(?<=[.!?…])[\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-ZÇĞİÖŞÜÂÎÛ0-9])")
# Nokta taşıyan kısaltmalar cümle sonu sayılmaz
_ABBREVIATIONS = {"dr", "prof", "doç", "yrd", "av", "sn", "vb", "vs", "bkz", "örn", "no", "st", "mr", "mrs", "ms",
                  "e.g", "i.e", "etc", "vol", "fig", "inc", "ltd", "jr", "sr", "a.ş", "ör"}


def split_sentences(text):
    """Metni cümlelere böler (Argos'un stanza/spacy bölücüsünün yerine hafif kurallar)."""
    pieces, start = [], 0
    for match in _SENTENCE_END.finditer(text):
        candidate = text[start:match.start()].rstrip()
        last_word = candidate.rsplit(None, 1)[-1] if candidate.split() else ""
        if last_word.rstrip(".").lower() in _ABBREVIATIONS or re.fullmatch(r"[A-ZÇĞİÖŞÜ]\.", last_word):
            continue   # "Dr. Ahmet", "A. Yılmaz"
        pieces.append(text[start:match.end()].strip())
        start = match.end()
    pieces.append(text[start:].strip())
    result = []
    for piece in filter(None, pieces):
        while len(piece) > MAX_SENTENCE_CHARS:
            cut = max(piece.rfind(mark, 0, MAX_SENTENCE_CHARS) for mark in (", ", "; ", ": "))
            if cut <= 0:
                cut = piece.rfind(" ", 0, MAX_SENTENCE_CHARS)
            if cut <= 0:
                break
            result.append(piece[:cut + 1].strip())
            piece = piece[cut + 1:].strip()
        result.append(piece)
    return result


def _translator(package):
    translator = _translators.get(package.path)
    if translator is None:
        ctranslate2, _ = _engine()
        # "default": modeli kaydedildiği hassasiyette çalıştır. "auto" bu işlemcide int8'e çeviriyor ve
        # İspanyolca (1.9) paketi int8'de anlamsız çıktı veriyor ("mainstre@@ mainstre@@…"); Argos'ta da vardı.
        translator = ctranslate2.Translator(str(package.path / "model"), device="cpu", compute_type="default")
        _translators[package.path] = translator
    return translator


def _translate_line(line, package):
    sentences = split_sentences(line)
    tokens = [package.encode(sentence) for sentence in sentences]
    prefix = [[package.target_prefix]] * len(tokens) if package.target_prefix else None
    results = _translator(package).translate_batch(
        tokens, target_prefix=prefix, beam_size=BEAM_SIZE, length_penalty=LENGTH_PENALTY,
        replace_unknowns=True, max_batch_size=32)
    output = []
    for result in results:
        value = package.decode(result.hypotheses[0]).strip()
        if package.target_prefix and value.startswith(package.target_prefix):
            value = value[len(package.target_prefix):].strip()
        output.append(value)
    return " ".join(output)


def translate(text, source, target, on_progress=None):
    """Metni çevirir; paragraf ve satır yapısı korunur. Uzun sürebilir: arka planda çağırın."""
    _engine()
    if source == target:
        return text
    if not is_installed(source, target):
        install(source, target, on_progress)
    packages = installed_packages()
    route = [packages[pair] for pair in _route(source, target, set(packages))]
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
                result = stripped
                for package in route:
                    result = _translate_line(result, package)
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
        note += " Türkçe ⇄ İngilizce uygulamayla birlikte gelir; kurulumda seçtiğiniz diller de hazırdır."
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
