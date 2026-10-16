"""Sözcük Hakkında penceresi: paket adı, sürüm, künye, iletişim ve kullanılan açık kaynak bileşenler."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout

from . import APP_NAME, DEVELOPERS, ILETISIM_EPOSTA, PAKET_ADI, PAKET_URUNLERI, __version__, resource_dir, theme

LOGO_FILE = "eagle-office-logo.png"
LOGO_WIDTH = 120  # mantıksal piksel; dosya 360 px, yüksek DPI'da keskin kalır

# (ad, ne için, lisans) — yeni bağımlılık eklenince buraya ve README'ye yazılır
CREDITS = [
    ("PySide6 (Qt)", "arayüz", "LGPL"),
    ("python-docx", "Word belgeleri (.docx)", "MIT"),
    ("pdfminer.six", "PDF okuma", "MIT"),
    ("olefile", "eski Word belgeleri (.doc) metni", "BSD"),
    ("msoffcrypto-tool + cryptography", "parolayla şifreli belgeler", "MIT / Apache 2.0"),
    ("comtypes", "Windows yazım denetimi ve dönüştürme", "MIT"),
    ("faster-whisper + Whisper modeli", "sesle yazma", "MIT"),
    ("soundfile + libsndfile", "ses dosyasından yazıya dökme (mp3, wav, opus, ogg, flac)", "BSD / LGPL 2.1"),
    ("CTranslate2 + SentencePiece", "çeviri motoru", "MIT / Apache 2.0"),
    ("Argos Translate dil paketleri + OPUS-MT modelleri", "çeviri", "MIT / CC-BY 4.0"),
    ("ONNX Runtime", "sesli okuma motoru", "MIT"),
    ("Piper (VITS) sesi, dfki Türkçe temel modelinden", "sesli okuma sesi", "CC BY-NC-SA 4.0"),
]

PRIVACY = ("Yazım denetimi, sesle yazma ve çeviri bu bilgisayarda çalışır; belgeleriniz "
           "hiçbir sunucuya gönderilmez.")


def paket_metni():
    """`Eagle Office paketi: Sözcük (kelime işlemci)  ·  Tabcel (hesap tablosu)`."""
    return f"{PAKET_ADI} paketi: " + "  ·  ".join(f"{ad} ({ne})" for ad, ne in PAKET_URUNLERI)


def hakkinda_metni():
    """Pencerenin düz metin özeti (test ve panoya kopyalama için)."""
    lines = [PAKET_ADI, APP_NAME, f"Sürüm {__version__}  ·  Türkçe kelime işlemci", DEVELOPERS, paket_metni(),
             f"İletişim: {ILETISIM_EPOSTA}", PRIVACY, "Kullanılan açık kaynak bileşenler:"]
    lines += [f"•  {name} — {use} ({licence})" for name, use, licence in CREDITS]
    return "\n".join(lines)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} Hakkında")
        self.setFixedWidth(460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(14)
        logo = self._logo_label()
        if logo is not None:
            header.addWidget(logo, 0, Qt.AlignTop)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        suite = QLabel(PAKET_ADI)
        suite_font = suite.font()
        suite_font.setPointSizeF(suite_font.pointSizeF() + 1)
        suite_font.setBold(True)
        suite_font.setLetterSpacing(QFont.PercentageSpacing, 108)
        suite.setFont(suite_font)
        suite.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        titles.addWidget(suite)

        title = QLabel(APP_NAME)
        font = title.font()
        font.setPointSizeF(font.pointSizeF() + 8)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet(f"color: {theme.ACCENT};")
        titles.addWidget(title)

        subtitle = QLabel(f"Sürüm {__version__}  ·  Türkçe kelime işlemci")
        subtitle.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        titles.addWidget(subtitle)
        titles.addStretch(1)

        credit = QLabel(DEVELOPERS)
        credit_font = credit.font()
        credit_font.setBold(True)
        credit.setFont(credit_font)
        layout.addWidget(credit)

        suite_line = QLabel(paket_metni())
        suite_line.setWordWrap(True)
        layout.addWidget(suite_line)

        contact = QLabel(f'İletişim: <a href="mailto:{ILETISIM_EPOSTA}">{ILETISIM_EPOSTA}</a>')
        contact.setTextFormat(Qt.RichText)
        contact.setOpenExternalLinks(True)
        contact.setTextInteractionFlags(Qt.TextBrowserInteraction)
        layout.addWidget(contact)

        privacy = QLabel(PRIVACY)
        privacy.setWordWrap(True)
        layout.addWidget(privacy)

        components = QLabel("Kullanılan açık kaynak bileşenler:\n" + "\n".join(
            f"•  {name} — {use} ({licence})" for name, use, licence in CREDITS))
        components.setWordWrap(True)
        components.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(components)

        buttons = QDialogButtonBox()
        close_button = buttons.addButton("Kapat", QDialogButtonBox.AcceptRole)
        close_button.setDefault(True)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _logo_label():
        """Eagle Office logosu; dosya yoksa (geliştirme ortamında eksikse) başlık logosuz görünür."""
        pixmap = QPixmap(str(resource_dir() / LOGO_FILE))
        if pixmap.isNull():
            return None
        scaled = pixmap.scaledToWidth(LOGO_WIDTH * 2, Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(2)
        label = QLabel()
        label.setPixmap(scaled)
        label.setFixedSize(LOGO_WIDTH, round(scaled.height() / 2))
        label.setObjectName("aboutLogo")
        return label
