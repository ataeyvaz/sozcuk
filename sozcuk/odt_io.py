"""OpenDocument Metni (.odt) okuyucu — LibreOffice / OpenOffice / Word'ün ODF biçimi.

Paket bir zip: content.xml (metin ve otomatik stiller), styles.xml (adlandırılmış stiller, sayfa yapısı),
Pictures/ (resimler). Okunanlar: başlıklar, paragraf hizalama/girinti/aralık, kalın/italik/altı-üstü çizili,
yazı tipi, boyut, renk, vurgu, listeler (madde/numara, iç içe), tablolar (birleştirilmiş hücreler), resimler,
sayfa boyutu ve kenar boşlukları. Dipnot, yorum, çizim gibi öğeler atlanır ve bildirilir.
"""

import re
import zipfile

from lxml import etree
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QTextBlockFormat, QTextCharFormat

from . import styles
from .builder import DocumentBuilder

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}
UNIT_PX = {"cm": styles.PX_PER_CM, "mm": styles.PX_PER_CM / 10, "in": 96.0, "pt": styles.PX_PER_PT,
           "pc": styles.PX_PER_PT * 12, "px": 1.0}
ALIGN = {"center": Qt.AlignHCenter, "end": Qt.AlignRight, "right": Qt.AlignRight, "justify": Qt.AlignJustify,
         "start": Qt.AlignLeft, "left": Qt.AlignLeft}
SKIPPED = {
    f"{{{NS['text']}}}note": "dipnotlar",
    f"{{{NS['office']}}}annotation": "yorumlar",
    f"{{{NS['draw']}}}custom-shape": "şekiller ve çizimler",
    f"{{{NS['text']}}}table-of-content": None,   # içindekiler: sonuç metni okunur (aşağıda)
}


def q(name):
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


def length_px(value):
    if not value:
        return None
    match = re.fullmatch(r"\s*(-?[\d.]+)\s*([a-z]*)\s*", value)
    if not match:
        return None
    number, unit = float(match.group(1)), match.group(2) or "px"
    return number * UNIT_PX.get(unit, 1.0)


class OdtError(Exception):
    pass


class Reader:
    def __init__(self, path):
        try:
            self.zip = zipfile.ZipFile(path)
            self.content = etree.fromstring(self.zip.read("content.xml"))
            self.styles_xml = etree.fromstring(self.zip.read("styles.xml")) if "styles.xml" in self.zip.namelist() else None
        except (zipfile.BadZipFile, KeyError, etree.XMLSyntaxError) as exc:
            raise OdtError("Dosya geçerli bir OpenDocument metni değil.") from exc
        self.skipped = set()
        self.fonts = {}
        self.text_styles = {}       # ad -> (üst stil, metin özellikleri öğesi, paragraf özellikleri öğesi)
        self.list_styles = {}       # ad -> {seviye: "bullet"|"number"}
        self.available_fonts = set(QFontDatabase.families())
        for root in (self.styles_xml, self.content):
            if root is not None:
                self._collect_styles(root)
        self.list_counter = 0

    # --- stiller -----------------------------------------------------------

    def _collect_styles(self, root):
        for face in root.iter(q("style:font-face")):
            family = face.get(q("svg:font-family"), "").strip("'\"")
            self.fonts[face.get(q("style:name"))] = family or face.get(q("style:name"))
        for style in root.iter(q("style:style"), q("style:default-style")):
            name = style.get(q("style:name")) or f"__default_{style.get(q('style:family'))}"
            self.text_styles[name] = (style.get(q("style:parent-style-name")),
                                      style.find(q("style:text-properties")),
                                      style.find(q("style:paragraph-properties")),
                                      style.get(q("style:list-style-name")))
        for list_style in root.iter(q("text:list-style")):
            levels = {}
            for child in list_style:
                level = int(child.get(q("text:level"), "1"))
                levels[level] = "bullet" if child.tag == q("text:list-level-style-bullet") else "number"
            self.list_styles[list_style.get(q("style:name"))] = levels

    def _chain(self, name, family="paragraph"):
        """Stil ve üst stilleri (en genelden en özele)."""
        chain, seen = [], set()
        while name and name in self.text_styles and name not in seen:
            seen.add(name)
            chain.append(self.text_styles[name])
            name = self.text_styles[name][0]
        default = self.text_styles.get(f"__default_{family}")
        if default:
            chain.append(default)
        return list(reversed(chain))

    def _apply_text(self, fmt, props):
        if props is None:
            return
        get = props.get
        if get(q("fo:font-weight")):
            fmt.setFontWeight(QFont.Bold if get(q("fo:font-weight")) in ("bold", "600", "700", "800", "900") else QFont.Normal)
        if get(q("fo:font-style")):
            fmt.setFontItalic(get(q("fo:font-style")) in ("italic", "oblique"))
        if get(q("style:text-underline-style")):
            fmt.setFontUnderline(get(q("style:text-underline-style")) != "none")
        if get(q("style:text-line-through-style")):
            fmt.setFontStrikeOut(get(q("style:text-line-through-style")) != "none")
        color = get(q("fo:color"))
        if color and QColor(color).isValid():
            fmt.setForeground(QColor(color))
        background = get(q("fo:background-color"))
        if background and background != "transparent" and QColor(background).isValid():
            fmt.setBackground(QColor(background))
        size = get(q("fo:font-size"))
        if size:
            if size.endswith("%"):
                base = fmt.fontPointSize() or styles.DEFAULT_SIZE
                fmt.setFontPointSize(base * float(size[:-1]) / 100)
            else:
                px = length_px(size)
                if px:
                    fmt.setFontPointSize(round(px / styles.PX_PER_PT, 1))
        family = self.fonts.get(get(q("style:font-name"))) or get(q("fo:font-family"))
        if family:
            family = family.strip("'\"")
            fmt.setFontFamilies([family if family in self.available_fonts else styles.DEFAULT_FAMILY])
        position = get(q("style:text-position"))
        if position:
            if position.startswith("super"):
                fmt.setVerticalAlignment(QTextCharFormat.AlignSuperScript)
            elif position.startswith("sub"):
                fmt.setVerticalAlignment(QTextCharFormat.AlignSubScript)

    def _apply_paragraph(self, fmt, props):
        if props is None:
            return
        get = props.get
        if get(q("fo:text-align")) in ALIGN:
            fmt.setAlignment(ALIGN[get(q("fo:text-align"))])
        for attribute, setter in (("fo:margin-left", fmt.setLeftMargin), ("fo:margin-right", fmt.setRightMargin),
                                  ("fo:text-indent", fmt.setTextIndent), ("fo:margin-top", fmt.setTopMargin),
                                  ("fo:margin-bottom", fmt.setBottomMargin)):
            value = length_px(get(q(attribute)))
            if value is not None:
                setter(value)
        line = get(q("fo:line-height"))
        if line and line.endswith("%"):
            fmt.setLineHeight(float(line[:-1]), QTextBlockFormat.ProportionalHeight.value)

    def char_format(self, style_name, base=None):
        fmt = QTextCharFormat(base) if base is not None else styles.body_char_format()
        for _, text_props, _, _ in self._chain(style_name, "text" if base is not None else "paragraph"):
            self._apply_text(fmt, text_props)
        return fmt

    def block_format(self, style_name, level=0):
        fmt = styles.heading_block_format(level)
        for _, _, paragraph_props, _ in self._chain(style_name):
            self._apply_paragraph(fmt, paragraph_props)
        return fmt

    # --- sayfa -------------------------------------------------------------

    def _read_page_setup(self, document):
        if self.styles_xml is None:
            return
        master = self.styles_xml.find(f".//{q('style:master-page')}")
        if master is None:
            return
        name = master.get(q("style:page-layout-name"))
        for layout in self.styles_xml.iter(q("style:page-layout")):
            if layout.get(q("style:name")) != name:
                continue
            props = layout.find(q("style:page-layout-properties"))
            if props is None:
                return
            values = {key: length_px(props.get(q(attribute))) for key, attribute in (
                ("width", "fo:page-width"), ("height", "fo:page-height"), ("top", "fo:margin-top"),
                ("bottom", "fo:margin-bottom"), ("left", "fo:margin-left"), ("right", "fo:margin-right"))}
            styles.set_page_setup(document, **values)
            return

    # --- içerik ------------------------------------------------------------

    def read(self, document):
        self._read_page_setup(document)
        body = self.content.find(f"{q('office:body')}/{q('office:text')}")
        if body is None:
            raise OdtError("Belgede metin bölümü bulunamadı.")
        builder = DocumentBuilder(document)
        self._blocks(builder, body, list_context=None)
        warnings = []
        if self.skipped:
            warnings.append("Desteklenmeyen öğeler atlandı: " + ", ".join(sorted(self.skipped)) + ".")
        return warnings

    def _blocks(self, builder, parent, list_context):
        for child in parent:
            tag = child.tag
            if tag == q("text:p"):
                self._paragraph(builder, child, 0, list_context)
            elif tag == q("text:h"):
                level = min(2, max(1, int(child.get(q("text:outline-level"), "1"))))
                self._paragraph(builder, child, level, list_context)
            elif tag == q("text:list"):
                self._list(builder, child, list_context)
            elif tag == q("table:table"):
                self._table(builder, child)
            elif tag in (q("text:section"), q("text:index-body"), q("text:table-of-content")):
                body = child.find(q("text:index-body"))
                self._blocks(builder, body if body is not None else child, list_context)
            elif tag in (q("text:soft-page-break"), q("text:sequence-decls"), q("office:forms"),
                         q("text:variable-decls"), q("text:user-field-decls")):
                continue
            elif tag in SKIPPED and SKIPPED[tag]:
                self.skipped.add(SKIPPED[tag])

    def _paragraph(self, builder, element, level, list_context):
        style_name = element.get(q("text:style-name"))
        block = self.block_format(style_name, level)
        base = self.char_format(style_name)
        if level:
            heading = styles.heading_char_format(level)
            base.setFontPointSize(heading.fontPointSize())
            base.setFontWeight(heading.fontWeight())
        if list_context is not None:
            block.setTextIndent(0)
            block.setLeftMargin(0)
        builder.paragraph(block, base)
        if list_context is not None and not list_context.get("used"):
            key, style, depth = list_context["key"], list_context["style"], list_context["depth"]
            builder.list_item(key, style, depth)
            list_context["used"] = True
        self._inline(builder, element, base, first=True)

    def _inline(self, builder, element, fmt, first=False):
        if element.text:
            builder.text(re.sub(r"[\r\n\t ]+", " ", element.text) if not first else element.text.replace("\n", " "), fmt)
        for child in element:
            tag = child.tag
            if tag == q("text:span"):
                self._inline(builder, child, self.char_format(child.get(q("text:style-name")), fmt))
            elif tag == q("text:a"):
                self._inline(builder, child, fmt)
            elif tag == q("text:s"):
                builder.text(" " * int(child.get(q("text:c"), "1")), fmt)
            elif tag == q("text:tab"):
                builder.text("\t", fmt)
            elif tag == q("text:line-break"):
                builder.text(" ", fmt)
            elif tag == q("draw:frame"):
                self._image(builder, child)
            elif tag in SKIPPED:
                if SKIPPED[tag]:
                    self.skipped.add(SKIPPED[tag])
            elif tag in (q("text:bookmark"), q("text:bookmark-start"), q("text:bookmark-end"),
                         q("text:soft-page-break"), q("office:annotation-end")):
                pass
            else:
                self._inline(builder, child, fmt)   # alanlar (tarih, sayfa no…): içindeki metin
            if child.tail:
                builder.text(child.tail.replace("\n", " "), fmt)

    def _image(self, builder, frame):
        image_element = frame.find(q("draw:image"))
        if image_element is None:
            if frame.find(q("draw:text-box")) is not None:
                self.skipped.add("metin kutuları")
            return
        href = image_element.get(q("xlink:href"), "")
        try:
            data = self.zip.read(href)
        except KeyError:
            self.skipped.add("bağlantılı (dosyaya gömülmemiş) resimler")
            return
        image = QImage.fromData(data)
        if image.isNull():
            self.skipped.add("desteklenmeyen biçimdeki resimler")
            return
        width = length_px(frame.get(q("svg:width"))) or image.width()
        height = length_px(frame.get(q("svg:height"))) or image.height()
        max_width = styles.text_width(builder.doc)
        if width > max_width:
            height, width = height * max_width / width, max_width
        builder.image(image, width, height)

    def _list(self, builder, element, parent_context):
        depth = 1 if parent_context is None else parent_context["depth"] + 1
        style_name = element.get(q("text:style-name")) or (parent_context or {}).get("style_name")
        kind = self.list_styles.get(style_name, {}).get(depth, "bullet")
        if parent_context is None:
            self.list_counter += 1
            list_id = self.list_counter
        else:
            list_id = parent_context["list_id"]
        for item in element:
            if item.tag not in (q("text:list-item"), q("text:list-header")):
                continue
            context = {"key": ("odt", list_id, depth), "style": styles.list_style_for(kind == "bullet", depth),
                       "depth": depth, "list_id": list_id, "style_name": style_name, "used": item.tag == q("text:list-header")}
            for child in item:
                if child.tag == q("text:list"):
                    self._list(builder, child, context)
                elif child.tag in (q("text:p"), q("text:h")):
                    self._paragraph(builder, child, 0 if child.tag == q("text:p") else 1,
                                    context if not context["used"] else None)
                else:
                    self._blocks(builder, [child], None)   # liste maddesindeki tablo vb.

    def _table(self, builder, element):
        rows = []
        for row in self._rows(element):
            repeat = min(int(row.get(q("table:number-rows-repeated"), "1")), 100)
            rows.extend([row] * repeat)
        if not rows:
            return
        columns = 0
        for row in rows:
            count = 0
            for cell in row:
                if cell.tag in (q("table:table-cell"), q("table:covered-table-cell")):
                    count += min(int(cell.get(q("table:number-columns-repeated"), "1")), 64)
            columns = max(columns, count)
        columns = max(1, min(columns, 63))
        table = builder.table(len(rows), columns)
        merges = []
        for r, row in enumerate(rows):
            c = 0
            for cell in row:
                if cell.tag not in (q("table:table-cell"), q("table:covered-table-cell")):
                    continue
                repeat = min(int(cell.get(q("table:number-columns-repeated"), "1")), 64)
                for _ in range(repeat):
                    if c >= columns:
                        break
                    if cell.tag == q("table:table-cell"):
                        span_c = int(cell.get(q("table:number-columns-spanned"), "1"))
                        span_r = int(cell.get(q("table:number-rows-spanned"), "1"))
                        if span_c > 1 or span_r > 1:
                            merges.append((r, c, min(span_r, len(rows) - r), min(span_c, columns - c)))
                        self._blocks(builder.cell(table, r, c), cell, None)
                    c += 1
        for r, c, rs, cs in merges:
            table.mergeCells(r, c, rs, cs)

    def _rows(self, element):
        """Tablonun kendi satırları (iç içe tabloların satırları hariç)."""
        for child in element:
            if child.tag == q("table:table-row"):
                yield child
            elif child.tag in (q("table:table-header-rows"), q("table:table-rows"), q("table:table-row-group")):
                yield from self._rows(child)


def prepare(path):
    return Reader(path).read


def load(path, document):
    return Reader(path).read(document)
