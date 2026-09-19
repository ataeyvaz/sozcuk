"""Zengin Metin Biçimi (.rtf) okuyucu.

RTF, denetim sözcükleri ({\\b kalın} gibi) ve gruplardan oluşan düz metin bir biçimdir. Okunanlar: metin ve
Türkçe karakterler (kod sayfaları, \\u Unicode), kalın/italik/altı-üstü çizili, yazı tipi, boyut, renk, vurgu,
üst/alt simge, paragraf hizalama/girinti/aralık/satır aralığı, başlıklar (stil adı ya da ana hat düzeyi), listeler,
tablolar, PNG/JPEG resimler, alan sonuçları (ör. köprü metni), sayfa boyutu ve kenar boşlukları.
Atlananlar (bildirilir): üst/alt bilgi, dipnot, yorum, WMF/EMF resimler, gömülü nesneler.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QTextBlockFormat, QTextCharFormat

from . import styles
from .builder import DocumentBuilder

TWIP_PX = 1 / 15      # 1440 twip = 1 inç = 96 px
CHARSET_CODEPAGE = {0: 1252, 1: 1252, 2: 1252, 77: 10000, 128: 932, 129: 949, 134: 936, 136: 950, 161: 1253,
                    162: 1254, 163: 1258, 177: 1255, 178: 1256, 186: 1257, 204: 1251, 222: 874, 238: 1250}
SPECIAL = {"tab": "\t", "line": "\u2028", "emdash": "\u2014", "endash": "\u2013", "bullet": "\u2022",
           "lquote": "\u2018", "rquote": "\u2019", "ldblquote": "\u201c", "rdblquote": "\u201d",
           "emspace": "\u2003", "enspace": "\u2002", "qmspace": "\u2005", "~": "\u00a0", "_": "\u2011", "-": ""}
SKIP_DESTINATIONS = {
    "info", "stylesheet", "listtable", "listoverridetable", "rsidtbl", "generator", "xmlnstbl", "mmathPr",
    "themedata", "colorschememapping", "latentstyles", "datastore", "docvar", "pgdsctbl", "nonshppict",
    "revtbl", "filetbl", "protusertbl", "wgrffmtfilter", "fchars", "lchars", "pnseclvl", "listpicture",
    "operator", "author", "title", "subject", "company", "template", "defchp", "defpap", "blipuid", "bkmkstart",
    "bkmkend", "xe", "tc", "shpinst", "sp", "userprops",
}
REPORTED_DESTINATIONS = {
    "header": "üst bilgi", "headerl": "üst bilgi", "headerr": "üst bilgi", "headerf": "üst bilgi",
    "footer": "alt bilgi", "footerl": "alt bilgi", "footerr": "alt bilgi", "footerf": "alt bilgi",
    "footnote": "dipnotlar", "annotation": "yorumlar", "atnid": None, "atnauthor": None, "object": "gömülü nesneler",
}
HEADING_NAMES = {"heading 1": 1, "başlık 1": 1, "heading 2": 2, "başlık 2": 2, "heading 3": 2, "başlık 3": 2}
TOKEN = re.compile(r"\\([a-zA-Z]{1,32})(-?\d{1,10})? ?|\\'([0-9a-fA-F]{2})|\\([^a-zA-Z])|([{}])|([^\\{}\r\n]+)|[\r\n]+")


class RtfError(Exception):
    pass


@dataclass
class CharState:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    font: int = -1
    size: float = 0.0          # punto (0: varsayılan)
    color: int = 0
    highlight: int = 0
    background: int = 0
    valign: int = 0            # 0 normal, 1 üst simge, 2 alt simge


@dataclass
class ParaState:
    align: object = None
    left: float = 0.0
    right: float = 0.0
    first: float = 0.0
    before: float = 0.0
    after: float = 0.0
    line: float = 0.0          # yüzde; 0 = varsayılan
    style: int = 0
    outline: int = -1
    in_table: bool = False
    list_id: int = 0
    list_level: int = 0


@dataclass
class State:
    char: CharState = field(default_factory=CharState)
    para: ParaState = field(default_factory=ParaState)
    destination: str = ""      # "" normal metin; "skip"; "fonttbl"; "colortbl"; "stylesheet"; "pict"; "listtext"
    uc: int = 1

    def copy(self):
        return State(CharState(**vars(self.char)), ParaState(**vars(self.para)), self.destination, self.uc)


@dataclass
class Paragraph:
    runs: list
    para: ParaState
    list_marker: str = ""


class Parser:
    def __init__(self, data):
        self.data = data
        self.fonts = {}            # numara -> [ad, kod sayfası]
        self.colors = []
        self.style_names = {}      # numara -> ad
        self.codepage = 1252
        self.default_font = -1
        self.skipped = set()
        self.page = {}
        self.blocks = []           # Paragraph ya da ("table", satırlar)
        self.runs = []
        self.table_rows, self.row_cells, self.cell_paragraphs = [], [], []
        self.list_marker = ""
        self.pict = None

    # --- çözümleme ---------------------------------------------------------

    def parse(self):
        text = self.data.decode("latin-1")
        if not text.lstrip().startswith("{\\rtf"):
            raise RtfError("Dosya geçerli bir RTF belgesi değil.")
        state = State()
        stack = []
        pending_bytes = bytearray()
        skip_chars = 0
        group_start = False       # "{" sonrası ilk denetim sözcüğü hedef olabilir
        ignorable = False

        def flush_bytes():
            if pending_bytes:
                codepage = self._codepage(state)
                try:
                    decoded = bytes(pending_bytes).decode(f"cp{codepage}", errors="replace")
                except LookupError:
                    decoded = bytes(pending_bytes).decode("cp1252", errors="replace")
                pending_bytes.clear()
                self._text(state, decoded)

        for match in TOKEN.finditer(text):
            word, param, hex_byte, symbol, brace, chunk = match.groups()
            if hex_byte is not None:
                if skip_chars:
                    skip_chars -= 1
                elif state.destination == "pict":
                    self.pict["hex"].append(hex_byte)
                else:
                    pending_bytes.append(int(hex_byte, 16))
                group_start = False
                continue
            flush_bytes()
            if brace == "{":
                stack.append(state.copy())
                group_start, ignorable = True, False
                continue
            if brace == "}":
                if state.destination == "pict" and self.pict is not None and (not stack or stack[-1].destination != "pict"):
                    self._finish_pict(state)
                if not stack:
                    break
                state = stack.pop()
                group_start, skip_chars = False, 0
                continue
            if symbol is not None:
                if symbol == "*":
                    ignorable = True
                    continue
                group_start = False
                if symbol in "\\{}":
                    if skip_chars:
                        skip_chars -= 1
                    else:
                        self._text(state, symbol)
                elif symbol in ("\n", "\r"):
                    self._paragraph_end(state)
                elif symbol in SPECIAL:
                    self._text(state, SPECIAL[symbol])
                continue
            if chunk is not None:
                group_start = False
                if skip_chars:
                    consumed = min(skip_chars, len(chunk))
                    skip_chars -= consumed
                    chunk = chunk[consumed:]
                if chunk:
                    if state.destination == "pict":
                        self.pict["hex"].append(chunk)
                    else:
                        self._text(state, chunk)
                continue
            if word is None:
                continue
            number = int(param) if param is not None else None
            if group_start:
                group_start = False
                destination = self._destination(word, ignorable, state)
                ignorable = False
                if destination is not None:
                    state.destination = destination
                    if destination == "pict":
                        self.pict = {"hex": [], "type": None, "w": 0, "h": 0, "goalw": 0, "goalh": 0, "sx": 100, "sy": 100}
                    continue
            if word == "u" and number is not None:
                if state.destination in ("", "listtext"):
                    self._text(state, chr(number + 65536 if number < 0 else number))
                skip_chars = state.uc
                continue
            if word == "uc" and number is not None:
                state.uc = number
                continue
            self._control(state, word, number)
        flush_bytes()
        self._paragraph_end(state, final=True)
        self._flush_table()
        return self.blocks

    def _codepage(self, state):
        font = self.fonts.get(state.char.font if state.char.font >= 0 else self.default_font)
        return font[1] if font and font[1] else self.codepage

    def _destination(self, word, ignorable, state):
        if state.destination == "skip":
            return None
        if state.destination == "pict":
            # resim grubunun içindeki {\*\blipuid …} gibi alt gruplar resim verisine karışmasın
            return "skip" if ignorable or word in SKIP_DESTINATIONS else None
        if word == "fonttbl":
            return "fonttbl"
        if word == "colortbl":
            return "colortbl"
        if word == "stylesheet":
            return "stylesheet"
        if word == "pict":
            return "pict" if state.destination != "skip" else None
        if word in ("listtext", "pntext"):
            return "listtext"
        if word in ("fldinst",):
            return "skip"
        if word == "shppict" or word == "fldrslt" or word == "field" or word == "shp":
            return None
        if word in REPORTED_DESTINATIONS:
            label = REPORTED_DESTINATIONS[word]
            if label:
                self.skipped.add(label)
            return "skip"
        if word in SKIP_DESTINATIONS or ignorable:
            return "skip"
        return None

    # --- denetim sözcükleri --------------------------------------------------

    def _control(self, state, word, number):
        destination = state.destination
        if destination == "skip":
            return
        if destination == "fonttbl":
            if word == "f" and number is not None:
                self._current_font = number
                self.fonts.setdefault(number, ["", 0])
            elif word == "fcharset" and number is not None and hasattr(self, "_current_font"):
                self.fonts[self._current_font][1] = CHARSET_CODEPAGE.get(number, 0)
            elif word == "cpg" and number is not None and hasattr(self, "_current_font"):
                self.fonts[self._current_font][1] = number
            return
        if destination == "colortbl":
            if not self.colors:
                self.colors.append([None, 0, 0, 0])
            if word in ("red", "green", "blue") and number is not None:
                self.colors[-1][0] = True
                self.colors[-1][{"red": 1, "green": 2, "blue": 3}[word]] = number
            return
        if destination == "stylesheet":
            if word == "s" and number is not None:
                self._current_style = number
            return
        if destination == "pict":
            pict = self.pict
            if word in ("pngblip", "jpegblip"):
                pict["type"] = word
            elif word in ("emfblip", "wmetafile", "macpict", "dibitmap", "wbitmap"):
                pict["type"] = pict["type"] or "unsupported"
            elif word == "picw":
                pict["w"] = number or 0
            elif word == "pich":
                pict["h"] = number or 0
            elif word == "picwgoal":
                pict["goalw"] = number or 0
            elif word == "pichgoal":
                pict["goalh"] = number or 0
            elif word == "picscalex":
                pict["sx"] = number or 100
            elif word == "picscaley":
                pict["sy"] = number or 100
            return

        char, para = state.char, state.para
        on = number is None or number != 0
        if word == "ansicpg" and number:
            self.codepage = number
        elif word == "deff" and number is not None:
            self.default_font = number
        elif word == "plain":
            state.char = CharState()
        elif word == "b":
            char.bold = on
        elif word == "i":
            char.italic = on
        elif word in ("ul", "uld", "uldash", "uldb", "ulth", "ulw", "ulwave"):
            char.underline = on
        elif word == "ulnone":
            char.underline = False
        elif word in ("strike", "striked"):
            char.strike = on
        elif word == "fs" and number:
            char.size = number / 2
        elif word == "f" and number is not None:
            char.font = number
        elif word == "cf" and number is not None:
            char.color = number
        elif word == "highlight" and number is not None:
            char.highlight = number
        elif word in ("cb", "chcbpat") and number is not None:
            char.background = number
        elif word == "super":
            char.valign = 1
        elif word == "sub":
            char.valign = 2
        elif word == "nosupersub":
            char.valign = 0
        elif word == "pard":
            state.para = ParaState()
        elif word == "par":
            self._paragraph_end(state)
        elif word == "page":
            self._paragraph_end(state)
        elif word in SPECIAL:
            self._text(state, SPECIAL[word])
        elif word in ("ql", "qc", "qr", "qj", "qd"):
            para.align = {"ql": Qt.AlignLeft, "qc": Qt.AlignHCenter, "qr": Qt.AlignRight}.get(word, Qt.AlignJustify)
        elif word in ("li", "lin") and number is not None:
            para.left = number * TWIP_PX
        elif word in ("ri", "rin") and number is not None:
            para.right = number * TWIP_PX
        elif word == "fi" and number is not None:
            para.first = number * TWIP_PX
        elif word == "sb" and number is not None:
            para.before = number * TWIP_PX
        elif word == "sa" and number is not None:
            para.after = number * TWIP_PX
        elif word == "sl" and number is not None:
            para.line = abs(number) / 240 * 100 if number else 0
        elif word == "s" and number is not None:
            para.style = number
        elif word == "outlinelevel" and number is not None:
            para.outline = number
        elif word == "intbl":
            para.in_table = True
        elif word == "ls" and number is not None:
            para.list_id = number
        elif word == "ilvl" and number is not None:
            para.list_level = number
        elif word == "cell" or word == "nestcell":
            self._paragraph_end(state, cell=True)
            self.row_cells.append(self.cell_paragraphs)
            self.cell_paragraphs = []
        elif word == "row" or word == "nestrow":
            if self.row_cells:
                self.table_rows.append(self.row_cells)
            self.row_cells = []
        elif word in ("paperw", "pgwsxn") and number:
            self.page["width"] = number * TWIP_PX
        elif word in ("paperh", "pghsxn") and number:
            self.page["height"] = number * TWIP_PX
        elif word in ("margl", "marglsxn") and number is not None:
            self.page["left"] = number * TWIP_PX
        elif word in ("margr", "margrsxn") and number is not None:
            self.page["right"] = number * TWIP_PX
        elif word in ("margt", "margtsxn") and number is not None:
            self.page["top"] = number * TWIP_PX
        elif word in ("margb", "margbsxn") and number is not None:
            self.page["bottom"] = number * TWIP_PX

    # --- metin ---------------------------------------------------------------

    def _text(self, state, text):
        destination = state.destination
        if destination == "fonttbl":
            if hasattr(self, "_current_font"):
                name = self.fonts[self._current_font][0] + text
                self.fonts[self._current_font][0] = name
            return
        if destination == "colortbl":
            for ch in text:
                if ch == ";":
                    if not self.colors:
                        self.colors.append([None, 0, 0, 0])
                    self.colors.append([None, 0, 0, 0])
            return
        if destination == "stylesheet":
            if hasattr(self, "_current_style"):
                self.style_names[self._current_style] = (self.style_names.get(self._current_style, "") + text)
            else:
                self.style_names[0] = self.style_names.get(0, "") + text
            return
        if destination == "listtext":
            self.list_marker += text
            return
        if destination:
            return
        if self.runs and self.runs[-1][1] == state.char:
            self.runs[-1] = (self.runs[-1][0] + text, self.runs[-1][1])
        else:
            self.runs.append((text, CharState(**vars(state.char))))

    def _paragraph_end(self, state, final=False, cell=False):
        if state.destination and not final:
            return
        if final and not self.runs and not self.list_marker:
            return
        paragraph = Paragraph(self.runs, ParaState(**vars(state.para)), self.list_marker.strip())
        self.runs, self.list_marker = [], ""
        if state.para.in_table or cell:
            self.cell_paragraphs.append(paragraph)
            return
        self._flush_table()
        self.blocks.append(paragraph)

    def _flush_table(self):
        if self.row_cells:
            self.table_rows.append(self.row_cells)
            self.row_cells = []
        if self.cell_paragraphs:
            self.table_rows.append([self.cell_paragraphs])
            self.cell_paragraphs = []
        if self.table_rows:
            self.blocks.append(("table", self.table_rows))
            self.table_rows = []

    def _finish_pict(self, state):
        pict, self.pict = self.pict, None
        if pict["type"] not in ("pngblip", "jpegblip"):
            if pict["type"]:
                self.skipped.add("WMF/EMF biçimindeki resimler")
            return
        try:
            data = bytes.fromhex("".join(pict["hex"]).replace(" ", ""))
        except ValueError:
            self.skipped.add("bozuk resimler")
            return
        image = QImage.fromData(data)
        if image.isNull():
            self.skipped.add("bozuk resimler")
            return
        width = (pict["goalw"] or pict["w"] * 15) * TWIP_PX * pict["sx"] / 100 or image.width()
        height = (pict["goalh"] or pict["h"] * 15) * TWIP_PX * pict["sy"] / 100 or image.height()
        self.runs.append((("image", image, width, height), CharState(**vars(state.char))))


# =============================================================================
# Belgeye aktarma
# =============================================================================

class Builder:
    def __init__(self, parser, document):
        self.parser = parser
        self.document = document
        self.available_fonts = set(QFontDatabase.families())
        self.lists = {}

    def color(self, index):
        colors = self.parser.colors
        if 0 < index < len(colors) and colors[index][0]:
            _, r, g, b = colors[index]
            return QColor(r, g, b)
        return None

    def char_format(self, char, heading):
        fmt = styles.heading_char_format(heading) if heading else styles.body_char_format()
        if not heading:
            fmt.setFontWeight(QFont.Bold if char.bold else QFont.Normal)
        elif char.bold:
            fmt.setFontWeight(QFont.Bold)
        fmt.setFontItalic(char.italic)
        fmt.setFontUnderline(char.underline)
        fmt.setFontStrikeOut(char.strike)
        font = self.parser.fonts.get(char.font if char.font >= 0 else self.parser.default_font)
        if font:
            name = font[0].strip().rstrip(";").strip()
            fmt.setFontFamilies([name if name in self.available_fonts else styles.DEFAULT_FAMILY])
        if char.size and not heading:
            fmt.setFontPointSize(char.size)
        color = self.color(char.color)
        if color is not None:
            fmt.setForeground(color)
        background = self.color(char.highlight) or self.color(char.background)
        if background is not None:
            fmt.setBackground(background)
        if char.valign:
            fmt.setVerticalAlignment(QTextCharFormat.AlignSuperScript if char.valign == 1 else QTextCharFormat.AlignSubScript)
        return fmt

    def heading_level(self, para):
        name = self.parser.style_names.get(para.style, "").strip().rstrip(";").strip().lower()
        if name in HEADING_NAMES:
            return HEADING_NAMES[name]
        if 0 <= para.outline <= 1:
            return para.outline + 1
        return 0

    def paragraph(self, builder, paragraph, in_table=False):
        para = paragraph.para
        level = self.heading_level(para)
        block = styles.heading_block_format(level)
        if para.align is not None:
            block.setAlignment(para.align)
        is_list = bool(paragraph.list_marker) and not in_table
        block.setLeftMargin(0 if is_list else para.left)
        block.setRightMargin(para.right)
        block.setTextIndent(0 if is_list else para.first)
        if para.before:
            block.setTopMargin(para.before)
        if para.after or para.before:
            block.setBottomMargin(para.after)
        if para.line:
            block.setLineHeight(para.line, QTextBlockFormat.ProportionalHeight.value)
        first_char = paragraph.runs[0][1] if paragraph.runs else CharState()
        builder.paragraph(block, self.char_format(first_char, level))
        if is_list:
            bullet = not re.match(r"^\(?[0-9a-zA-Z]{1,4}[.)]", paragraph.list_marker)
            depth = para.list_level + 1
            key = ("rtf", para.list_id or ("b" if bullet else "n"), depth)
            builder.list_item(key, styles.list_style_for(bullet, depth), depth)
        for content, char in paragraph.runs:
            if isinstance(content, tuple):
                _, image, width, height = content
                max_width = styles.text_width(self.document)
                if width > max_width:
                    height, width = height * max_width / width, max_width
                builder.image(image, width, height)
            else:
                builder.text(content, self.char_format(char, level))

    def build(self, blocks):
        builder = DocumentBuilder(self.document)
        for block in blocks:
            if isinstance(block, Paragraph):
                self.paragraph(builder, block)
            else:
                rows = block[1]
                columns = max(1, min(63, max(len(row) for row in rows)))
                table = builder.table(len(rows), columns)
                for r, row in enumerate(rows):
                    for c, cell in enumerate(row[:columns]):
                        cell_builder = builder.cell(table, r, c)
                        for paragraph in cell or [Paragraph([], ParaState())]:
                            self.paragraph(cell_builder, paragraph, in_table=True)


def prepare(path):
    """Dosyayı çözümler (hatalı dosya burada hata verir, belgeye dokunmadan); build(document) döndürür."""
    parser = Parser(Path(path).read_bytes())
    blocks = parser.parse()

    def build(document):
        if parser.page:
            styles.set_page_setup(document, **parser.page)
        Builder(parser, document).build(blocks)
        return (["Desteklenmeyen öğeler atlandı: " + ", ".join(sorted(parser.skipped)) + "."] if parser.skipped else [])
    return build


def load(path, document):
    return prepare(path)(document)
