"""Parolayla şifrelenmiş Word belgeleri (Word: Dosya → Bilgi → Belgeyi Koru → Parolayla Şifrele).

Şifreli .docx bir ZIP paketi değil, içinde ECMA-376 ile şifrelenmiş paketi taşıyan bir OLE (CFB) kabıdır.
Çözme ve şifreleme msoffcrypto-tool ile yapılır.

GİZLİLİK:
- Şifresi çözülmüş belge yalnızca bellekte (io.BytesIO) tutulur; diske hiçbir zaman düz hâliyle yazılmaz.
- Parola yalnızca açık belge süresince bellekte kalır; ayarlara, son kullanılanlara ya da günlüğe yazılmaz.
"""

import io
import os
import zipfile
from pathlib import Path

import msoffcrypto
import olefile
from msoffcrypto import exceptions as crypto_errors
from msoffcrypto.format.ooxml import OOXMLFile

ENCRYPTED_OOXML = "ooxml"     # Word 2007+ (.docx/.docm/.dotx/.dotm) parolayla şifreli
ENCRYPTED_LEGACY = "legacy"   # Word 97-2003 (.doc) parolayla şifreli: desteklenmiyor


class WrongPassword(Exception):
    """Girilen parola belgeyi açmıyor."""


class EncryptedFileError(OSError):
    """Şifreli dosya okunamadı ya da yazılamadı; iletisi kullanıcıya gösterilebilir (Türkçe).
    OSError'dan türer: kaydetme yolu bunu diğer yazma hataları gibi "Kaydedilemedi" olarak gösterir."""


VERIFY_FAILED = ("Şifreli kayıt doğrulanamadı: yazılan dosya aynı parolayla geri açılamadı ya da içeriği "
                 "tutmadı. Dosyanın üzerine yazılmadı; belgeniz Sözcük'te açık duruyor. Farklı Kaydet ile "
                 "başka bir yere kaydetmeyi ya da parolayı kaldırıp kaydetmeyi deneyin.")


def probe(path):
    """Dosya parolayla şifreli mi: ENCRYPTED_OOXML, ENCRYPTED_LEGACY ya da None (şifresiz ya da tanınmayan).
    Hiçbir koşulda hata vermez; karar veremezse None döner ve normal açma yolu kendi hatasını gösterir."""
    try:
        if not olefile.isOleFile(str(path)):
            return None      # ZIP paketi (şifresiz .docx) ya da başka bir biçim
        with open(path, "rb") as handle:
            office = msoffcrypto.OfficeFile(handle)
            if not office.is_encrypted():
                return None
            return ENCRYPTED_OOXML if office.format == "ooxml" else ENCRYPTED_LEGACY
    except Exception:
        return None


def _decrypt_handle(handle, password):
    office = msoffcrypto.OfficeFile(handle)
    try:
        office.load_key(password=password, verify_password=True)
    except crypto_errors.InvalidKeyError as exc:
        raise WrongPassword() from exc
    plain = io.BytesIO()
    office.decrypt(plain)
    return plain


def decrypt(path, password):
    """Parolayı doğrular ve belgeyi yalnızca bellekte çözer. Dönüş: başa sarılmış io.BytesIO (ZIP paketi).
    path bir dosya yolu ya da bellekteki şifreli baytlar (bytes) olabilir.
    Yanlış parolada WrongPassword, okunamayan dosyada EncryptedFileError verir."""
    try:
        if isinstance(path, (bytes, bytearray)):
            plain = _decrypt_handle(io.BytesIO(path), password)
        else:
            with open(path, "rb") as handle:
                plain = _decrypt_handle(handle, password)
    except WrongPassword:
        raise
    except OSError as exc:
        raise EncryptedFileError("Dosya okunamadı. Başka bir programda açık ya da erişim izni olmayabilir.") from exc
    except Exception as exc:
        raise EncryptedFileError("Şifreli belge çözülemedi. Dosya bozuk olabilir ya da Word'ün bu şifreleme "
                                 "yöntemi desteklenmiyor olabilir.") from exc
    if not zipfile.is_zipfile(plain):
        raise EncryptedFileError("Şifre çözüldü ama içinden geçerli bir Word belgesi çıkmadı.")
    plain.seek(0)
    return plain


def encrypt(package, password):
    """Bellekteki .docx paketini (bytes) parolayla şifreler; şifreli dosyanın baytlarını döndürür."""
    try:
        office = OOXMLFile(io.BytesIO(package))
        out = io.BytesIO()
        office.encrypt(password, out)
    except Exception as exc:
        raise EncryptedFileError("Belge şifrelenemedi.") from exc
    return out.getvalue()


def verify(data, password, package):
    """Şifreli baytlar aynı parolayla çözülünce paketin kendisi mi çıkıyor. Şifreleme kütüphanesinin bu özelliği
    "deneysel" olduğu için her şifreli kayıt yerine konmadan önce denetlenir."""
    try:
        return decrypt(bytes(data), password).getvalue() == package
    except Exception:
        return False


def write_encrypted(package, password, path):
    """Paketi şifreleyip dosyaya güvenle yazar: aynı klasördeki geçici dosyaya YALNIZCA şifreli baytlar yazılır,
    diskten geri okunup aynı parolayla çözülerek doğrulanır, ancak tutarsa tek adımda yerine konur
    (docx_io'daki düz kayıtla aynı yöntem). Doğrulanamazsa asıl dosyaya dokunulmaz."""
    from .docx_io import _replace_with_retry
    data = encrypt(package, password)
    path = Path(path)
    tmp = path.with_name(f"~$sozcuk-{os.getpid()}-{path.name}")
    try:
        tmp.write_bytes(data)
        if not verify(tmp.read_bytes(), password, package):   # diske yazılanı denetle, bellekteki kopyayı değil
            raise EncryptedFileError(VERIFY_FAILED)
        _replace_with_retry(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
