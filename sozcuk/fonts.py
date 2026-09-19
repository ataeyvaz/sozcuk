"""Kullanıcının eklediği .ttf/.otf yazı tipleri.

Eklenen dosyalar uygulama veri klasörüne kopyalanır ve her açılışta yeniden yüklenir.
"""

import shutil
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QFontDatabase

FONT_SUFFIXES = {".ttf", ".otf"}


def fonts_dir():
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    path = Path(base) / "fonts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_saved_fonts():
    for file in sorted(fonts_dir().iterdir()):
        if file.suffix.lower() in FONT_SUFFIXES:
            QFontDatabase.addApplicationFont(str(file))


def install_font(source):
    """Font dosyasını kopyalayıp yükler; eklenen aile adlarını döndürür.

    Dosya geçerli bir font değilse boş liste döner ve kopya silinir.
    """
    source = Path(source)
    target = fonts_dir() / source.name
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)

    font_id = QFontDatabase.addApplicationFont(str(target))
    if font_id == -1:
        target.unlink(missing_ok=True)
        return []
    return QFontDatabase.applicationFontFamilies(font_id)
