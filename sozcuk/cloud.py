"""Google Drive ve OneDrive ile çalışma — API'siz, masaüstü eşitleme uygulamaları üzerinden.

Google Drive masaüstü uygulaması Drive'ı ayrı bir sürücü ("Google Drive" etiketli birim, ör. G:\\Drive'ım),
OneDrive ise kullanıcı klasöründe bir klasör olarak gösterir. Oturum bu uygulamalarda açıktır; Sözcük
hesaba, şifreye ya da Google/Microsoft sunucularına hiç dokunmaz. Sözcük dosyayı bu klasöre kaydeder,
eşitleme uygulaması buluta gönderir.

Bu modül:
- bulut klasörlerini bulur ve bir dosyanın hangi buluttaki olduğunu söyler,
- dosyanın dışarıdan (web, başka bilgisayar) değiştiğini imza (boyut + değişiklik zamanı) karşılaştırarak anlar,
- .gdoc gibi Google biçimindeki belgeleri tanır (içerikleri bilgisayarda yoktur, yalnızca tarayıcıda açılır).
"""

import ctypes
import hashlib
import os
import string
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

GOOGLE = "Google Drive"
ONEDRIVE = "OneDrive"
GOOGLE_LABEL = "Google Drive"
MY_DRIVE_NAMES = ("Drive'ım", "My Drive", "Meine Ablage", "Mi unidad", "Mon Drive")
GOOGLE_FORMATS = {".gdoc": "Google Dokümanlar", ".gsheet": "Google E-Tablolar", ".gslides": "Google Slaytlar"}


@dataclass(frozen=True)
class CloudFolder:
    provider: str   # GOOGLE | ONEDRIVE
    path: Path      # kullanıcıya gösterilecek ana klasör (ör. G:\Drive'ım)
    root: Path      # bu buluta ait her şeyin altında olduğu kök (ör. G:\)


def _volume_label(root):
    if sys.platform != "win32":
        return ""
    buffer = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(ctypes.c_wchar_p(root), buffer, 261,
                                                      None, None, None, None, 0)
    return buffer.value if ok else ""


def _drive_letters():
    if sys.platform != "win32":
        return []
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    return [f"{letter}:\\" for i, letter in enumerate(string.ascii_uppercase) if mask >> i & 1]


def _google_drive_folders():
    folders = []
    old_mode = ctypes.windll.kernel32.SetErrorMode(1) if sys.platform == "win32" else None  # boş kart okuyucu uyarısı çıkmasın
    try:
        for root in _drive_letters():
            if root[0] in "AB" or _volume_label(root) != GOOGLE_LABEL:
                continue
            main = next((Path(root) / name for name in MY_DRIVE_NAMES if (Path(root) / name).is_dir()), Path(root))
            folders.append(CloudFolder(GOOGLE, main, Path(root)))
    finally:
        if old_mode is not None:
            ctypes.windll.kernel32.SetErrorMode(old_mode)
    # eski "Yedekleme ve Eşitleme" / yansıtma (mirror) modu: kullanıcı klasöründe
    home = Path.home()
    for name in ("Google Drive", "Drive'ım", "My Drive"):
        if (home / name).is_dir():
            folders.append(CloudFolder(GOOGLE, home / name, home / name))
    return folders


def _onedrive_folders():
    seen, folders = set(), []
    for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = os.environ.get(variable)
        if value and Path(value).is_dir() and value.lower() not in seen:
            seen.add(value.lower())
            folders.append(CloudFolder(ONEDRIVE, Path(value), Path(value)))
    return folders


_cache = None


def cloud_folders(refresh=False):
    """Bu bilgisayardaki bulut klasörleri (Google Drive önce)."""
    global _cache
    if _cache is None or refresh:
        _cache = _google_drive_folders() + _onedrive_folders()
    return list(_cache)


def folder_for(path):
    """Dosya bir bulut klasöründeyse CloudFolder, değilse None."""
    if path is None:
        return None
    try:
        resolved = Path(os.path.abspath(path))
    except (OSError, ValueError):
        return None
    for folder in cloud_folders():
        try:
            resolved.relative_to(folder.root)
            return folder
        except ValueError:
            continue
    return None


def provider_for(path):
    folder = folder_for(path)
    return folder.provider if folder else None


def is_google_format(path):
    return Path(path).suffix.lower() in GOOGLE_FORMATS


def google_search_url(path):
    """Google biçimli belgenin içeriği bilgisayarda olmadığı için Drive'da adıyla arama sayfası."""
    return "https://drive.google.com/drive/search?q=" + quote(Path(path).stem)


# =============================================================================
# Dışarıdan değişikliği fark etme
# =============================================================================

def signature(path):
    """Dosyanın (boyut, değişiklik zamanı) imzası; yoksa None."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return stat.st_size, stat.st_mtime_ns


def content_hash(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


class ChangeTracker:
    """Açık belgenin dosyasını izler. Sözcük'ün kendi kaydı remember() ile bildirilir; imza başka bir
    sebeple değişirse (eşitleme uygulaması web'de ya da başka bilgisayarda yapılan değişikliği indirdi)
    changed() True döner. Klasör izleme bildirimleri bulut sürücülerinde güvenilir olmadığı için yoklanır."""

    def __init__(self):
        self.path = None
        self.known = None       # (boyut, değişiklik zamanı)
        self.known_hash = None  # içerik özeti: eşitleme uygulaması yalnızca tarihi değiştirirse değişiklik sayılmaz
        self.conflict = False   # dışarıdan değişiklik görüldü, kullanıcı henüz karar vermedi

    def track(self, path):
        self.path = Path(path) if path else None
        self.remember()

    def remember(self):
        """Sözcük dosyayı yazdıktan (ya da yeniden yükledikten) sonra çağrılır."""
        self.known = signature(self.path) if self.path else None
        self.known_hash = content_hash(self.path) if self.path else None
        self.conflict = False

    def changed(self):
        if self.path is None or self.known is None or self.conflict:
            return False
        current = signature(self.path)
        if current is None:        # eşitleme sırasında kısa süre görünmeyebilir; silinme sayılmaz
            return False
        if current == self.known:
            return False
        digest = content_hash(self.path)
        if digest is not None and digest == self.known_hash:
            self.known = current  # içerik aynı (ör. eşitleme uygulaması tarihi güncelledi)
            return False
        if digest is None:        # dosya o an okunamıyor (eşitleniyor); sonra yeniden bakılır
            return False
        self.conflict = True
        return True
