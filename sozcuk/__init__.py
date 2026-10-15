"""Sözcük — sade Türkçe kelime işlemci."""

import sys
from pathlib import Path

__version__ = "1.5"
DEVELOPERS = "Developed By Usta ve Ata"
APP_NAME = "Sözcük"
PAKET_ADI = "Eagle Office"  # ürün ailesinin ortak adı (Sözcük ve Tabcel bu paketin parçasıdır)
PAKET_URUNLERI = ((APP_NAME, "kelime işlemci"), ("Tabcel", "hesap tablosu"))  # Tabcel'dekiyle aynı kalmalı
ILETISIM_EPOSTA = "ataeyvaz@gmail.com"


def resource_dir():
    """Uygulamayla gelen dosyaların (yardim.md, diller/) bulunduğu klasör.
    Paketlenmiş (.exe) sürümde PyInstaller bunları geçici çıkarma klasörüne koyar."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = base / "sozcuk"
        if candidate.is_dir():
            return candidate
        return base
    return Path(__file__).resolve().parent
