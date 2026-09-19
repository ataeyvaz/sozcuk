"""Eski ve yabancı biçimleri dönüştürme: bilgisayarda kurulu Microsoft Word ya da LibreOffice ile.

Word 97-2003 (.doc/.dot), Works (.wps), WordPerfect (.wpd) ve Word 2003 XML biçimlerini biçimlendirmesiyle
okuyan, lisansı uygun bir Python kütüphanesi yok. Bu biçimler bilgisayardaki Word (yoksa LibreOffice) ile
arka planda, görünmeden .docx'e çevrilip öyle açılır; kaydederken de ters yönde çevrilir.

Güvenlik ve gizlilik:
- Belge bilgisayardan çıkmaz, internet kullanılmaz.
- Word'de makrolar zorla kapatılır (AutomationSecurity), belge salt okunur açılır, "son kullanılanlar"a eklenmez,
  uyarı pencereleri gösterilmez; parola korumalı belgede parola sorulmaz, hata verilir.
- Kullanıcının açık Word penceresine dokunulmaz: Sözcük kendi Word örneğini başlatır; bir şekilde kullanıcının
  örneğine bağlanılırsa (açık belgesi varsa) Word kapatılmaz.
- LibreOffice kullanıcının kendi profiliyle çakışmasın diye geçici profille çalıştırılır.

Ölçüm (Word 16): Word'ün açılışı ~6 sn, dönüştürme 0,2–1,4 sn.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import logbook

log = logbook.get("dönüştürme")

WORD = "Microsoft Word"
LIBREOFFICE = "LibreOffice"

# Word'ün SaveAs2 biçim kodları
WORD_FORMATS = {".docx": 16, ".doc": 0, ".dot": 1, ".rtf": 6, ".odt": 23}
# LibreOffice --convert-to filtreleri
LIBREOFFICE_FILTERS = {".docx": "docx:MS Word 2007 XML", ".doc": "doc:MS Word 97", ".rtf": "rtf:Rich Text Format",
                       ".odt": "odt:writer8", ".dot": "dot:MS Word 97 Vorlage"}
MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 3
LIBREOFFICE_TIMEOUT = 180


class ConversionError(Exception):
    pass


# =============================================================================
# Bulma
# =============================================================================

def word_installed():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return True
    except OSError:
        return False


def libreoffice_path():
    candidates = []
    if sys.platform == "win32":
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\LibreOffice\UNO\InstallPath") as key:
                    candidates.append(Path(winreg.QueryValueEx(key, "")[0]) / "soffice.exe")
            except OSError:
                pass
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                candidates.append(Path(base) / "LibreOffice" / "program" / "soffice.exe")
    else:
        found = shutil.which("soffice") or shutil.which("libreoffice")
        if found:
            candidates.append(Path(found))
    return next((c for c in candidates if c.is_file()), None)


_availability = None


def available(refresh=False):
    """Kullanılabilir dönüştürücüler, tercih sırasıyla (Word önce)."""
    global _availability
    if _availability is None or refresh:
        _availability = ([WORD] if word_installed() else []) + ([LIBREOFFICE] if libreoffice_path() else [])
    return list(_availability)


# =============================================================================
# Word
# =============================================================================

class _WordSession:
    """Arka planda görünmeyen bir Word. Aynı iş parçacığında (COM) kullanılmalı."""

    def __init__(self):
        import comtypes
        import comtypes.client
        comtypes.CoInitialize()
        self._comtypes = comtypes
        try:
            self.word = comtypes.client.CreateObject("Word.Application", dynamic=True)
        except Exception as exc:
            comtypes.CoUninitialize()
            raise ConversionError("Microsoft Word başlatılamadı.") from exc
        try:
            self.owned = self.word.Documents.Count == 0   # kullanıcının açık Word'üne bağlanıldıysa kapatma
        except Exception:
            self.owned = True
        self.word.Visible = False
        self.word.DisplayAlerts = 0
        try:
            self.word.AutomationSecurity = MSO_AUTOMATION_SECURITY_FORCE_DISABLE
        except Exception:
            pass

    def convert(self, source, target, suffix):
        code = WORD_FORMATS[suffix]
        # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles, PasswordDocument, PasswordTemplate, Revert,
        #      WritePasswordDocument, WritePasswordTemplate, Format, Encoding, Visible)
        try:
            doc = self.word.Documents.Open(str(source), False, True, False, "sozcuk-parola-yok", "sozcuk-parola-yok",
                                           False, "", "", 0)
        except Exception as exc:
            text = str(exc).lower()
            if "password" in text or "parola" in text:
                raise ConversionError("Belge parola korumalı; Sözcük parola korumalı belgeleri açamaz.") from exc
            raise ConversionError("Microsoft Word belgeyi açamadı (bozuk ya da desteklenmeyen dosya olabilir).") from exc
        try:
            doc.SaveAs2(str(target), code)
        except Exception as exc:
            raise ConversionError("Microsoft Word belgeyi dönüştüremedi.") from exc
        finally:
            try:
                doc.Close(False)
            except Exception:
                pass

    def close(self):
        try:
            if self.owned and self.word.Documents.Count == 0:
                self.word.Quit(False)
        except Exception:
            pass
        self.word = None
        self._comtypes.CoUninitialize()


# =============================================================================
# LibreOffice
# =============================================================================

def _libreoffice_convert(source, target, suffix):
    soffice = libreoffice_path()
    if soffice is None:
        raise ConversionError("LibreOffice bulunamadı.")
    with tempfile.TemporaryDirectory(prefix="sozcuk-lo-") as work:
        profile = Path(work) / "profil"
        out_dir = Path(work) / "cikti"
        out_dir.mkdir()
        command = [str(soffice), "--headless", "--norestore", "--nolockcheck",
                   f"-env:UserInstallation={profile.as_uri()}",
                   "--convert-to", LIBREOFFICE_FILTERS[suffix], "--outdir", str(out_dir), str(source)]
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            subprocess.run(command, capture_output=True, timeout=LIBREOFFICE_TIMEOUT, creationflags=flags, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ConversionError("LibreOffice dönüştürmesi çok uzun sürdü.") from exc
        produced = out_dir / (Path(source).stem + suffix)
        if not produced.is_file():
            raise ConversionError("LibreOffice belgeyi dönüştüremedi.")
        shutil.move(str(produced), str(target))


# =============================================================================
# Genel arayüz
# =============================================================================

def convert(source, target, engines=None):
    """source'u target'ın uzantısındaki biçime çevirir; kullanılan dönüştürücünün adını döndürür.
    Uzun sürebilir (Word'ün açılışı): arka plan iş parçacığında çağırın."""
    source, target = Path(source).resolve(), Path(target).resolve()  # Word göreli yolları kendi klasörüne göre çözer
    suffix = target.suffix.lower()
    engines = available() if engines is None else engines
    if not engines:
        raise ConversionError("Bu biçim için Microsoft Word ya da LibreOffice gerekiyor; bilgisayarda ikisi de bulunamadı.")
    errors = []
    for engine in engines:
        try:
            if engine == WORD and suffix in WORD_FORMATS:
                session = _WordSession()
                try:
                    session.convert(source, target, suffix)
                finally:
                    session.close()
            elif engine == LIBREOFFICE and suffix in LIBREOFFICE_FILTERS:
                _libreoffice_convert(source, target, suffix)
            else:
                continue
            log.info("dönüştürüldü: %s -> %s (%s)", source.suffix.lower(), suffix, engine)
            return engine
        except ConversionError as exc:
            log.warning("dönüştürülemedi (%s): %s", engine, exc)
            errors.append(exc)
    raise errors[-1] if errors else ConversionError("Bu dönüştürme desteklenmiyor.")


def to_docx(source, engines=None):
    """Geçici bir .docx'e çevirir; (yol, dönüştürücü) döndürür. Geçici klasörü çağıran siler (parent)."""
    work = Path(tempfile.mkdtemp(prefix="sozcuk-donusum-"))
    target = work / (Path(source).stem + ".docx")
    try:
        engine = convert(source, target, engines)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return target, engine
