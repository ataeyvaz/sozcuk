"""Word 97-2003 (.doc/.dot) dosyasından yalnızca metni çıkaran yedek okuyucu.

Bilgisayarda ne Word ne LibreOffice varsa kullanılır. Biçimlendirme, tablo yapısı ve resimler okunmaz;
paragraflar ve metin gelir. Biçim tanımı: Microsoft [MS-DOC] — WordDocument akışındaki FIB, tablo akışındaki
parça tablosu (Clx/PlcPcd). Dosya bir OLE (Compound File) kabıdır; olefile ile okunur.
"""

import struct

import olefile

from . import styles
from .builder import DocumentBuilder

FIB_MAGIC = 0xA5EC
FC_CLX_INDEX = 33          # FibRgFcLcb97 içinde fcClx/lcbClx çiftinin sırası
CCP_TEXT_INDEX = 3         # FibRgLw97 içinde ana metnin karakter sayısı


class DocTextError(Exception):
    pass


def extract_text(path):
    try:
        ole = olefile.OleFileIO(str(path))
    except OSError as exc:
        raise DocTextError("Dosya bir Word 97-2003 belgesi değil.") from exc
    with ole:
        if not ole.exists("WordDocument"):
            raise DocTextError("Dosya bir Word 97-2003 belgesi değil.")
        word = ole.openstream("WordDocument").read()
        if len(word) < 64 or struct.unpack_from("<H", word, 0)[0] != FIB_MAGIC:
            raise DocTextError("Word belgesi başlığı okunamadı.")
        flags = struct.unpack_from("<H", word, 0x0A)[0]
        if flags & 0x0100:
            raise DocTextError("Belge parola korumalı (şifreli).")
        table_name = "1Table" if flags & 0x0200 else "0Table"
        if not ole.exists(table_name):
            raise DocTextError("Word belgesinin tablo akışı bulunamadı.")
        table = ole.openstream(table_name).read()

    # FIB: FibBase (32) + csw (2) + fibRgW (csw*2) + cslw (2) + fibRgLw (cslw*4) + cbRgFcLcb (2) + fibRgFcLcb
    position = 32
    csw = struct.unpack_from("<H", word, position)[0]
    position += 2 + csw * 2
    cslw = struct.unpack_from("<H", word, position)[0]
    lw_start = position + 2
    ccp_text = struct.unpack_from("<i", word, lw_start + CCP_TEXT_INDEX * 4)[0]
    position = lw_start + cslw * 4
    position += 2
    fc_clx, lcb_clx = struct.unpack_from("<II", word, position + FC_CLX_INDEX * 8)
    if lcb_clx == 0 or fc_clx + lcb_clx > len(table):
        raise DocTextError("Word belgesinin metin tablosu okunamadı.")

    clx = table[fc_clx:fc_clx + lcb_clx]
    offset = 0
    while offset < len(clx) and clx[offset] == 0x01:          # Prc: biçim değişiklikleri, atla
        size = struct.unpack_from("<h", clx, offset + 1)[0]
        offset += 3 + size
    if offset >= len(clx) or clx[offset] != 0x02:
        raise DocTextError("Word belgesinin parça tablosu bulunamadı.")
    lcb = struct.unpack_from("<I", clx, offset + 1)[0]
    plc = clx[offset + 5:offset + 5 + lcb]
    count = (lcb - 4) // 12
    cps = struct.unpack_from(f"<{count + 1}I", plc, 0)
    pieces = []
    for i in range(count):
        pcd = plc[(count + 1) * 4 + i * 8:(count + 1) * 4 + (i + 1) * 8]
        fc = struct.unpack_from("<I", pcd, 2)[0]
        compressed = bool(fc & 0x40000000)
        fc &= 0x3FFFFFFF
        length = cps[i + 1] - cps[i]
        if compressed:
            raw = word[fc // 2:fc // 2 + length]
            pieces.append(raw.decode("cp1252", errors="replace"))
        else:
            raw = word[fc:fc + length * 2]
            pieces.append(raw.decode("utf-16-le", errors="replace"))
    text = "".join(pieces)
    return clean(text[:ccp_text] if 0 < ccp_text <= len(text) else text)


def clean(text):
    """Word denetim karakterlerini düz metne çevirir: alan kodları atılır (sonuç kalır), hücre işaretleri sekme olur."""
    result, depth, show = [], 0, [True]
    for ch in text:
        if ch == "\x13":            # alan başı: kod bölümü gizli
            depth += 1
            show.append(False)
        elif ch == "\x14":          # alan ayırıcı: sonuç görünür
            if depth:
                show[-1] = True
        elif ch == "\x15":          # alan sonu
            if depth:
                depth -= 1
                show.pop()
        elif not all(show):
            continue
        elif ch == "\x07":          # hücre sonu sekme; art arda ikinci işaret satır sonudur
            if result and result[-1] == "\t":
                result[-1] = "\r"
            else:
                result.append("\t")
        elif ch in "\x0b\x0c":      # satır sonu, sayfa sonu
            result.append("\r")
        elif ch in "\x01\x08\x02\x05" or (ord(ch) < 32 and ch not in "\r\t"):
            continue
        else:
            result.append(ch)
    return "".join(result)


def prepare(path):
    text = extract_text(path)

    def build(document):
        builder = DocumentBuilder(document)
        for line in text.split("\r"):
            builder.paragraph(styles.body_block_format(), styles.body_char_format())
            builder.text(line.rstrip("\t"), styles.body_char_format())
        return ["Bu eski Word belgesinden yalnızca metin alınabildi: biçimlendirme, tablolar ve resimler için "
                "Microsoft Word ya da ücretsiz LibreOffice kurulu olmalı."]
    return build


def load(path, document):
    return prepare(path)(document)
