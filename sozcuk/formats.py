"""Belge biçimleri: hangi uzantının nasıl açılıp kaydedileceği ve ek program gerektirmeyen okuyucu/yazıcılar.

Açma yolları:
- "docx": .docx ve aynı Office Open XML paketindeki .docm (makrolar yok sayılır), .dotx/.dotm (şablon) — docx_io
- "pdf": pdf_io (arka planda)
- "text", "html", "mht": burada (Qt'nin HTML içe aktarımı)
- "odt": odt_io, "rtf": rtf_io — kendi okuyucularımız
- "legacy": .doc/.dot (Word 97-2003), .wps (Works), .wpd (WordPerfect), .xml (Word 2003 XML) — converters
  (Word ya da LibreOffice ile .docx'e çevirme); ikisi de yoksa .doc/.dot için doc_text ile yalnızca metin
"""

import base64
import email
import email.policy
import html as html_lib
import io
import re
import zipfile
from urllib.parse import unquote, urlparse
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import (
    QImage,
    QTextCursor,
    QTextDocument,
    QTextDocumentFragment,
    QTextDocumentWriter,
    QTextListFormat,
)

from . import styles, tables
from .builder import DocumentBuilder


@dataclass(frozen=True)
class Format:
    suffix: str
    label: str
    kind: str
    template: bool = False   # şablon: Word gibi yeni (adsız) belge olarak açılır


FORMATS = [
    Format(".docx", "Word Belgesi", "docx"),
    Format(".docm", "Makro İçerebilen Word Belgesi", "docx"),
    Format(".dotx", "Word Şablonu", "docx", template=True),
    Format(".dotm", "Makro İçerebilen Word Şablonu", "docx", template=True),
    Format(".doc", "Word 97-2003 Belgesi", "legacy"),
    Format(".dot", "Word 97-2003 Şablonu", "legacy", template=True),
    Format(".rtf", "Zengin Metin Biçimi", "rtf"),
    Format(".odt", "OpenDocument Metni", "odt"),
    Format(".txt", "Düz Metin", "text"),
    Format(".htm", "Web Sayfası", "html"),
    Format(".html", "Web Sayfası", "html"),
    Format(".mht", "Tek Dosya Web Sayfası", "mht"),
    Format(".mhtml", "Tek Dosya Web Sayfası", "mht"),
    Format(".xml", "Word 2003 XML Belgesi", "legacy"),
    Format(".wps", "Works 6-9 Belgesi", "legacy"),
    Format(".wpd", "WordPerfect Belgesi", "legacy"),
    Format(".pdf", "PDF", "pdf"),
]
BY_SUFFIX = {f.suffix: f for f in FORMATS}

OOXML_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
OOXML_VARIANTS = (
    "application/vnd.ms-word.document.macroEnabled.main+xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml",
    "application/vnd.ms-word.template.macroEnabledTemplate.main+xml",
)


def format_for(path):
    return BY_SUFFIX.get(Path(path).suffix.lower())


OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def sniff(path):
    """Dosyanın içeriğine bakarak gerçek türü: "docx", "odt", "rtf", "html", "mht", "pdf", "ole" (Word 97-2003,
    Works), "wpd", "wordxml" ya da None. Uzantısı yanlış dosyalar (ör. aslında RTF olan .doc) doğru okuyucuya gider;
    geçersiz dosyalar Word'e verilmez (Word her dosyayı düz metin olarak açabilir)."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(4096)
    except OSError:
        return None
    if head.startswith(OLE_MAGIC):
        return "ole"
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(path) as package:
                names = set(package.namelist())
                if "word/document.xml" in names:
                    return "docx"
                if "content.xml" in names:
                    return "odt"
        except zipfile.BadZipFile:
            return None
        return None
    text = head.lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if text.startswith(b"{\\rtf"):
        return "rtf"
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"\xffWPC"):
        return "wpd"
    if text.startswith(b"mime-version") or b"\nmime-version:" in text[:1024] or text.startswith(b"from:"):
        return "mht"   # Word'ün MHT'si içinde de <w:WordDocument> geçer; önce MIME başlığına bakılır
    if text.startswith(b"<?xml") and (b"wordml" in text or b"<w:worddocument" in text):
        return "wordxml"
    if text.startswith((b"<!doctype html", b"<html")) or b"<html" in text[:1024]:
        return "html"
    return None


SNIFF_FORMAT = {"docx": ".docx", "odt": ".odt", "rtf": ".rtf", "html": ".html", "mht": ".mht", "pdf": ".pdf"}
VALID_SNIFF = {".doc": {"ole"}, ".dot": {"ole"}, ".wps": {"ole"}, ".wpd": {"wpd"}, ".xml": {"wordxml"}}


def effective_format(path):
    """Açarken kullanılacak biçim: içerik uzantıdan farklı bir biçim gösteriyorsa o biçim (şablon bilgisi korunur).
    Dönüş (Format, hata metni)."""
    declared = format_for(path)
    if declared is None:
        return None, None
    actual = sniff(path)
    if declared.kind == "text":
        return declared, None
    if actual in SNIFF_FORMAT and BY_SUFFIX[SNIFF_FORMAT[actual]].kind != declared.kind:
        real = BY_SUFFIX[SNIFF_FORMAT[actual]]
        return Format(declared.suffix, declared.label, real.kind, declared.template), None
    if declared.suffix in VALID_SNIFF and actual not in VALID_SNIFF[declared.suffix]:
        return declared, f"Dosyanın içeriği bir {declared.label} değil (bozuk ya da yanlış uzantılı olabilir)."
    return declared, None


def open_filter():
    """Word'deki gibi: önce tüm desteklenenler, sonra biçim biçim."""
    word = [f for f in FORMATS if f.kind != "pdf"]
    all_patterns = " ".join(f"*{f.suffix}" for f in FORMATS)
    word_patterns = " ".join(f"*{f.suffix}" for f in word if f.kind in ("docx", "legacy") and f.suffix != ".xml")
    groups = {}
    for f in FORMATS:
        groups.setdefault(f.label, []).append(f"*{f.suffix}")
    parts = [f"Tüm Desteklenen Belgeler ({all_patterns})", f"Tüm Word Belgeleri ({word_patterns})"]
    parts += [f"{label} ({' '.join(patterns)})" for label, patterns in groups.items()]
    parts.append("Google Dokümanlar bağlantısı (*.gdoc *.gsheet *.gslides)")
    return ";;".join(parts)


# =============================================================================
# Kaydetme biçimleri
# =============================================================================

@dataclass(frozen=True)
class SaveFormat:
    suffix: str
    label: str
    needs_converter: bool = False   # Word ya da LibreOffice gerekir
    loses: str = ""                 # bu biçimde nelerin kaybolacağı (uyarı)


SAVE_FORMATS = [
    SaveFormat(".docx", "Word Belgesi"),
    SaveFormat(".doc", "Word 97-2003 Belgesi", needs_converter=True,
               loses="Bazı yeni biçimlendirmeler eski Word biçiminde tam korunmayabilir."),
    SaveFormat(".rtf", "Zengin Metin Biçimi", needs_converter=True),
    SaveFormat(".odt", "OpenDocument Metni",
               loses="Sayfa yapısı (kâğıt boyutu, kenar boşlukları) .odt dosyasına yazılmaz."),
    SaveFormat(".txt", "Düz Metin", loses="Düz metinde biçimlendirme, tablo ve resimler kaybolur."),
    SaveFormat(".html", "Web Sayfası", loses="Sayfa yapısı web sayfasına yazılmaz; resimler yanındaki klasöre kaydedilir."),
]
SAVE_BY_SUFFIX = {f.suffix: f for f in SAVE_FORMATS}


def save_filters(converter_available):
    formats = [f for f in SAVE_FORMATS if converter_available or not f.needs_converter]
    return formats, ";;".join(f"{f.label} (*{f.suffix})" for f in formats)


# =============================================================================
# Office Open XML çeşitleri (.docm, .dotx, .dotm)
# =============================================================================

def open_ooxml_package(path):
    """python-docx yalnızca .docx içerik türünü kabul eder; .docm/.dotx/.dotm paketlerinin ana belge türü
    bellekte .docx'inkine çevrilir (makro kodu okunmaz, çalıştırılmaz). Dönüş: docx.Document'e verilebilir akış
    ya da .docx için yolun kendisi."""
    if Path(path).suffix.lower() == ".docx":
        return path
    source = zipfile.ZipFile(path)
    buffer = io.BytesIO()
    with source, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "[Content_Types].xml":
                text = data.decode("utf-8")
                for variant in OOXML_VARIANTS:
                    text = text.replace(variant, OOXML_MAIN)
                data = text.encode("utf-8")
            target.writestr(item, data)
    buffer.seek(0)
    return buffer


# =============================================================================
# Düz metin
# =============================================================================

def decode_text(data):
    """Metin dosyasının kodlaması: BOM, geçerli UTF-8, yoksa Windows Türkçe (1254)."""
    for bom, encoding in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if data.startswith(bom):
            return data.decode(encoding), encoding
    if len(data) >= 4 and data[1:4:2] == b"\x00\x00" and data[0:4:2] != b"\x00\x00":
        return data.decode("utf-16-le"), "utf-16-le"   # BOM'suz UTF-16 (Not Defteri "Unicode")
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp1254", errors="replace"), "cp1254"


def load_text(path, document):
    text, _ = decode_text(Path(path).read_bytes())
    builder = DocumentBuilder(document)
    for line in re.split(r"\r\n|\r|\n", text):
        builder.paragraph(styles.body_block_format(), styles.body_char_format())
        builder.text(line.replace("\f", ""), styles.body_char_format())
    return []


def save_text(document, path):
    text = document.toPlainText().replace("\u2028", "\n").replace("\ufffc", "")
    Path(path).write_bytes(text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


# =============================================================================
# Web sayfaları
# =============================================================================

META_CHARSET = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?([\w-]+)""", re.IGNORECASE)


def decode_html(data):
    for bom, encoding in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if data.startswith(bom):
            return data.decode(encoding)
    match = META_CHARSET.search(data[:4096])
    if match:
        try:
            return data.decode(match.group(1).decode("ascii"), errors="replace")
        except LookupError:
            pass
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1254", errors="replace")


IMG_SRC = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE)
LIST_MARKER = re.compile(r"^\s*(?:([\u2022\u00b7o\u00a7\u25aa\u25a0\u25e6\uf0b7\uf0a7-])|(\d{1,3}|[a-zA-Z]|[ivxIVX]{1,5})[.)])[\s\u00a0]{2,}")


def _load_image(src, folder, resources):
    """<img src> için resmi bulur: belgeyle gelen kaynaklar (MHT), data: adresi ya da HTML dosyasına göre yerel yol."""
    if src.startswith("data:"):
        header, _, data = src.partition(",")
        raw = base64.b64decode(data) if ";base64" in header else unquote(data).encode("latin-1")
        return QImage.fromData(raw)
    if resources:
        if src in resources:
            return resources[src]
        tail = unquote(src).replace("\\", "/").lstrip("./")
        for name, image in resources.items():   # MHT: file:///C:/.../ornek_dosyalar/image001.png ~ ornek_dosyalar/image001.png
            if unquote(name).replace("\\", "/").endswith("/" + tail) or name.endswith(tail):
                return image
    if folder is not None:
        parsed = urlparse(src)
        if parsed.scheme in ("http", "https"):
            return QImage()   # internete çıkılmaz
        local = Path(unquote(parsed.path).lstrip("/")) if parsed.scheme == "file" else folder / unquote(src)
        if local.is_file():
            return QImage(str(local))
    return QImage()


def _word_lists(document, start):
    """Word'ün kaydettiği web sayfalarında liste maddeleri "•" + boşluklar olarak yazılır; gerçek listeye çevir."""
    from . import styles as st
    block = document.findBlock(start)
    lists = {}
    previous = None
    while block.isValid():
        match = LIST_MARKER.match(block.text())
        if match and block.textList() is None and not block.blockFormat().headingLevel():
            bullet = match.group(1) is not None
            cursor = QTextCursor(block)
            cursor.setPosition(block.position() + match.end(), QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            fmt = cursor.blockFormat()
            fmt.setTextIndent(0)
            fmt.setLeftMargin(0)
            cursor.setBlockFormat(fmt)
            key = bullet
            if previous is not None and previous.next() == block and key in lists:
                lists[key].add(block)
            else:
                list_format = QTextListFormat()
                list_format.setStyle(st.list_style_for(bullet, 1))
                lists = {key: cursor.createList(list_format)}
            previous = block
        block = block.next()


def _insert_html(document, html, folder=None, resources=None):
    """HTML'i belgeye ekler; resimler belgeye gömülür (dosya taşınınca da kaybolmasın). Uyarı listesi döner."""
    warnings = []
    for match in IMG_SRC.finditer(html):
        src = html_lib.unescape(next(g for g in match.groups() if g is not None))
        image = _load_image(src, folder, resources)
        if not image.isNull():
            document.addResource(QTextDocument.ImageResource, QUrl(src), image)
    html = re.sub(r"<!--\[if gte vml 1\]>.*?<!\[endif\]-->", "", html, flags=re.DOTALL)  # Word'ün VML kopyaları
    cursor = QTextCursor(document)
    cursor.insertFragment(QTextDocumentFragment.fromHtml(html, document))
    tables.style_pasted_tables(document, 0, document.characterCount())
    _word_lists(document, 0)

    missing = 0
    block = document.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            fmt = fragment.charFormat()
            if fragment.isValid() and fmt.isImageFormat():
                image_format = fmt.toImageFormat()
                resource = document.resource(QTextDocument.ImageResource, QUrl(image_format.name()))
                image = resource if isinstance(resource, QImage) else QImage()
                if image.isNull() and isinstance(resource, (bytes, bytearray)):
                    image = QImage.fromData(bytes(resource))
                edit = QTextCursor(document)
                edit.setPosition(fragment.position())
                edit.setPosition(fragment.position() + fragment.length(), QTextCursor.KeepAnchor)
                if image.isNull():
                    missing += 1
                    edit.removeSelectedText()     # internetteki ya da bulunamayan resim: boş kutu bırakma
                    iterator = block.begin()
                    continue
                from . import images
                name = images.add_resource(document, image)
                image_format.setName(name)
                width = image_format.width() or image.width()
                height = image_format.height() or image.height() * width / max(1, image.width())
                width, height = images.fit_size(width, height, document)
                image_format.setWidth(width)
                image_format.setHeight(height)
                edit.setCharFormat(image_format)
            iterator += 1
        block = block.next()
    if missing:
        warnings.append(f"{missing} resim bulunamadığı ya da internette olduğu için alınmadı.")
    return warnings


def load_html(path, document):
    html = decode_html(Path(path).read_bytes())
    return _insert_html(document, html, Path(path).resolve().parent)


def load_mht(path, document):
    """Tek dosya web sayfası (MIME): HTML bölümü ve içindeki resimler."""
    message = email.message_from_bytes(Path(path).read_bytes(), policy=email.policy.default)
    html, resources = None, {}
    for part in message.walk():
        content_type = part.get_content_type()
        if part.is_multipart():
            continue
        payload = part.get_payload(decode=True) or b""
        if content_type == "text/html" and html is None:
            charset = part.get_content_charset()
            html = payload.decode(charset, errors="replace") if charset else decode_html(payload)
        elif content_type.startswith("image/"):
            image = QImage.fromData(payload)
            if image.isNull():
                continue
            if part.get("Content-Location"):
                resources[part["Content-Location"].strip()] = image
            if part.get("Content-ID"):
                resources["cid:" + part["Content-ID"].strip("<> ")] = image
    if html is None:
        raise ValueError("Dosyada web sayfası bölümü bulunamadı.")
    return _insert_html(document, html, None, resources)


def save_html(document, path):
    """Web sayfası olarak kaydeder; resimler "<ad>_dosyalar" klasörüne yazılır."""
    path = Path(path)
    clone = document.clone()
    root = clone.rootFrame().frameFormat()
    root.setMargin(0)
    clone.rootFrame().setFrameFormat(root)
    folder = path.with_name(path.stem + "_dosyalar")
    count = 0
    block = clone.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            fmt = fragment.charFormat()
            if fragment.isValid() and fmt.isImageFormat():
                image_format = fmt.toImageFormat()
                resource = document.resource(QTextDocument.ImageResource, QUrl(image_format.name()))
                if isinstance(resource, QImage) and not resource.isNull():
                    count += 1
                    folder.mkdir(exist_ok=True)
                    file_name = f"resim{count}.png"
                    resource.save(str(folder / file_name), "PNG")
                    image_format.setName(f"{folder.name}/{file_name}")
                    edit = QTextCursor(clone)
                    edit.setPosition(fragment.position())
                    edit.setPosition(fragment.position() + fragment.length(), QTextCursor.KeepAnchor)
                    edit.setCharFormat(image_format)
            iterator += 1
        block = block.next()
    html = clone.toHtml()
    html = html.replace("<head>", '<head><meta charset="utf-8">', 1)
    path.write_text(html, encoding="utf-8")


# =============================================================================
# OpenDocument yazma (Qt'nin yerleşik ODF yazıcısı)
# =============================================================================

def save_odt(document, path):
    clone = document.clone()
    root = clone.rootFrame().frameFormat()
    top, bottom, left, right = styles.all_margins(document)
    root.setTopMargin(0)  # ekrandaki sayfa arası boşluk dosyaya yazılmasın
    clone.rootFrame().setFrameFormat(root)
    # clone() kaynakları taşımaz: resimleri yeniden ekle
    block = clone.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fmt = iterator.fragment().charFormat()
            if fmt.isImageFormat():
                name = fmt.toImageFormat().name()
                clone.addResource(QTextDocument.ImageResource, QUrl(name),
                                  document.resource(QTextDocument.ImageResource, QUrl(name)))
            iterator += 1
        block = block.next()
    tmp = Path(path).with_name(f"~$sozcuk-{Path(path).name}")
    writer = QTextDocumentWriter(str(tmp), b"ODF")
    if not writer.write(clone):
        tmp.unlink(missing_ok=True)
        raise OSError(f"“{Path(path).name}” yazılamadı.")
    from .docx_io import _replace_with_retry
    _replace_with_retry(tmp, Path(path))


WRITERS = {".txt": save_text, ".html": save_html, ".htm": save_html, ".odt": save_odt}
LOADERS = {"text": load_text, "html": load_html, "mht": load_mht}


def prepare(path, kind):
    """Metin ve web sayfası: dosya önce ayrı bir belgede denenir (hızlı), hata verirse asıl belgeye dokunulmaz."""
    probe = QTextDocument()
    LOADERS[kind](path, probe)
    return lambda document: LOADERS[kind](path, document)
