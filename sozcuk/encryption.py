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


class EncryptedFileError(Exception):
    """Şifreli dosya okunamadı ya da yazılamadı; iletisi kullanıcıya gösterilebilir (Türkçe)."""


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


def decrypt(path, password):
    """Parolayı doğrular ve belgeyi yalnızca bellekte çözer. Dönüş: başa sarılmış io.BytesIO (ZIP paketi).
    Yanlış parolada WrongPassword, okunamayan dosyada EncryptedFileError verir."""
    try:
        with open(path, "rb") as handle:
            office = msoffcrypto.OfficeFile(handle)
            try:
                office.load_key(password=password, verify_password=True)
            except crypto_errors.InvalidKeyError as exc:
                raise WrongPassword() from exc
            plain = io.BytesIO()
            office.decrypt(plain)
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


def write_encrypted(package, password, path):
    """Paketi şifreleyip dosyaya güvenle yazar: aynı klasördeki geçici dosyaya YALNIZCA şifreli baytlar yazılır,
    sonra tek adımda yerine konur (docx_io'daki düz kayıtla aynı yöntem)."""
    from .docx_io import _replace_with_retry
    data = encrypt(package, password)
    path = Path(path)
    tmp = path.with_name(f"~$sozcuk-{os.getpid()}-{path.name}")
    try:
        tmp.write_bytes(data)
        _replace_with_retry(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
