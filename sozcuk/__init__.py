"""Sözcük — sade Türkçe kelime işlemci."""

import sys
from pathlib import Path

__version__ = "1.0"
DEVELOPERS = "Developed By Usta ve Ata"


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
