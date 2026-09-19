"""PDF'i düzenlenebilir metne dönüştürme.

PDF'ler sabit konumlu çizim komutlarıdır; burada metin blokları paragraflara birleştirilir,
yazı tipi/boyut/kalın/italik korunur, başlıklar ve listeler tahmin edilir. Karmaşık düzenler
(çok sütun, tablolar, görseller) birebir korunmaz.

extract() Qt'ye dokunmaz ve arka plan iş parçacığında çalışabilir; build() ana iş parçacığında çağrılır.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QTextCharFormat

from . import styles
from .builder import DocumentBuilder

BULLET_RE = re.compile(r"^\s*[•●▪◦‣∙·■□➢►\-–*]\s+")
NUMBER_RE = re.compile(r"^\s*(\d{1,3}|[a-zA-Z])[.)]\s+")
PAGE_NUMBER_RE = re.compile(r"^\s*(sayfa\s*)?\d{1,4}(\s*/\s*\d{1,4})?\s*$", re.IGNORECASE)
FAMILY_SUFFIXES = ("PSMT", "PS", "MT")
STYLE_WORDS = ("bold", "italic", "oblique", "regular", "semibold", "light", "medium", "black", "heavy", "demi")


class PdfError(Exception):
    pass


@dataclass
class Run:
    text: str
    family: str
    size: float
    bold: bool
    italic: bool


@dataclass
class Paragraph:
    runs: list = field(default_factory=list)
    kind: str = "p"          # p | h1 | h2 | bullet | number
    centered: bool = False
    lines: int = 0

    @property
    def text(self):
        return "".join(r.text for r in self.runs)


def _font_info(fontname):
    name = fontname.split("+", 1)[-1]
    lower = name.lower()
    bold = any(word in lower for word in ("bold", "black", "heavy", "semibold", "demi"))
    italic = "italic" in lower or "oblique" in lower
    family = re.split(r"[-,]", name)[0]
    for suffix in FAMILY_SUFFIXES:
        if family.endswith(suffix) and len(family) > len(suffix):
            family = family[: -len(suffix)]
            break
    for word in STYLE_WORDS:
        if family.lower().endswith(word) and len(family) > len(word):
            family = family[: -len(word)]
    family = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", family).strip()
    return family, bold, italic


def _line_runs(line):
    from pdfminer.layout import LTChar

    runs = []
    for obj in line:
        text = obj.get_text()
        if text in ("\n", "\r"):
            continue
        if isinstance(obj, LTChar):
            family, bold, italic = _font_info(obj.fontname)
            size = round(obj.size * 2) / 2
            key = (family, size, bold, italic)
        elif runs:
            key = (runs[-1].family, runs[-1].size, runs[-1].bold, runs[-1].italic)
        else:
            continue
        if runs and (runs[-1].family, runs[-1].size, runs[-1].bold, runs[-1].italic) == key:
            runs[-1].text += text
        else:
            runs.append(Run(text, *key))
    return runs


def _append_line(paragraph, runs):
    if paragraph.runs and runs:
        last = paragraph.runs[-1]
        if last.text.endswith("-") and runs[0].text[:1].islower():
            last.text = last.text[:-1]           # satır sonu tirelemesini birleştir
        elif not last.text.endswith(" "):
            last.text += " "
    for run in runs:
        prev = paragraph.runs[-1] if paragraph.runs else None
        if prev and (prev.family, prev.size, prev.bold, prev.italic) == (run.family, run.size, run.bold, run.italic):
            prev.text += run.text
        else:
            paragraph.runs.append(run)
    paragraph.lines += 1


def extract(path):
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LAParams, LTTextContainer, LTTextLine
    from pdfminer.pdfparser import PDFSyntaxError

    paragraphs = []
    try:
        pages = list(extract_pages(str(path), laparams=LAParams(line_margin=0.5)))
    except PDFSyntaxError as exc:
        raise PdfError("Dosya geçerli bir PDF değil.") from exc
    except Exception as exc:  # şifreli vb.
        raise PdfError(f"PDF okunamadı: {exc}") from exc

    for page in pages:
        page_width = page.width
        boxes = [el for el in page if isinstance(el, LTTextContainer)]
        for box in boxes:
            lines = [ln for ln in box if isinstance(ln, LTTextLine)]
            current = None
            for line in lines:
                raw = line.get_text()
                if not raw.strip():
                    continue
                runs = _line_runs(line)
                if not runs:
                    continue
                marker = BULLET_RE.match(raw) or NUMBER_RE.match(raw)
                if current is None or marker:
                    current = Paragraph()
                    paragraphs.append(current)
                    if marker:
                        current.kind = "bullet" if BULLET_RE.match(raw) else "number"
                        _strip_prefix(runs, len(marker.group(0)))
                    center = (line.x0 + line.x1) / 2
                    current.centered = (
                        abs(center - page_width / 2) < page_width * 0.04
                        and line.width < page_width * 0.6
                        and line.x0 > page_width * 0.2
                    )
                _append_line(current, runs)

    paragraphs = [p for p in paragraphs if p.text.strip() and not PAGE_NUMBER_RE.match(p.text)]
    if not paragraphs:
        raise PdfError("PDF'te seçilebilir metin bulunamadı (taranmış bir belge olabilir).")
    _classify(paragraphs)
    return paragraphs


def _strip_prefix(runs, count):
    while count and runs:
        take = min(count, len(runs[0].text))
        runs[0].text = runs[0].text[take:]
        count -= take
        if not runs[0].text:
            runs.pop(0)


def _classify(paragraphs):
    sizes = Counter()
    for p in paragraphs:
        for r in p.runs:
            sizes[r.size] += len(r.text)
    body = sizes.most_common(1)[0][0] if sizes else styles.DEFAULT_SIZE
    for p in paragraphs:
        if p.kind != "p":
            continue
        weight = sum(len(r.text) for r in p.runs) or 1
        avg = sum(r.size * len(r.text) for r in p.runs) / weight
        text = p.text.strip()
        all_bold = all(r.bold for r in p.runs if r.text.strip())
        if avg >= body * 1.45 and len(text) < 150:
            p.kind = "h1"
        elif (avg >= body * 1.15 or (all_bold and p.lines == 1 and len(text) <= 70
                                     and not text.endswith((".", ",", ":", ";")))) and len(text) < 150:
            p.kind = "h2"


def build(paragraphs, document):
    builder = DocumentBuilder(document)
    available = set(QFontDatabase.families())
    list_counter = 0
    previous_kind = None

    for p in paragraphs:
        level = {"h1": 1, "h2": 2}.get(p.kind, 0)
        block = styles.heading_block_format(level)
        if p.centered:
            block.setAlignment(Qt.AlignHCenter)
        base = QTextCharFormat()
        builder.paragraph(block, base)

        if p.kind in ("bullet", "number"):
            if p.kind != previous_kind:
                list_counter += 1
            bullet = p.kind == "bullet"
            builder.list_item(("pdf", list_counter), styles.list_style_for(bullet, 1), 1)
        previous_kind = p.kind

        for run in p.runs:
            fmt = QTextCharFormat()
            fmt.setFontFamilies([run.family if run.family in available else styles.DEFAULT_FAMILY])
            fmt.setFontPointSize(run.size if run.size > 0 else styles.DEFAULT_SIZE)
            fmt.setFontWeight(QFont.Bold if run.bold or level else QFont.Normal)
            fmt.setFontItalic(run.italic)
            builder.text(run.text.replace("\t", " "), fmt)


def load(path, document):
    build(extract(path), document)
