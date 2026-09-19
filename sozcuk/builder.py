"""İçe aktarıcıların (docx, PDF) QTextDocument'i adım adım doldurmak için kullandığı yardımcı."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QTextCursor, QTextDocument, QTextImageFormat, QTextListFormat

from . import tables


class DocumentBuilder:
    def __init__(self, document, cursor=None, shared=None):
        self.doc = document
        self.cursor = cursor or QTextCursor(document)
        self._fresh = True  # imlecin bulunduğu blok henüz kullanılmadı
        self._shared = shared if shared is not None else {"lists": {}, "images": 0}

    def paragraph(self, block_format, char_format):
        if self._fresh:
            self.cursor.setBlockFormat(block_format)
            self.cursor.setBlockCharFormat(char_format)
            self._fresh = False
        else:
            self.cursor.insertBlock(block_format, char_format)
        self.cursor.setCharFormat(char_format)

    def text(self, text, char_format):
        if text:
            self.cursor.insertText(text, char_format)

    def image(self, image, width, height):
        self._shared["images"] += 1
        name = f"sozcuk-image-{self._shared['images']}"
        self.doc.addResource(QTextDocument.ImageResource, QUrl(name), image)
        fmt = QTextImageFormat()
        fmt.setName(name)
        fmt.setWidth(width)
        fmt.setHeight(height)
        self.cursor.insertImage(fmt)

    def list_item(self, key, style, indent):
        """Geçerli bloğu key ile tanımlanan listeye ekler (yoksa oluşturur)."""
        lists = self._shared["lists"]
        block = self.cursor.block()
        if key in lists:
            lists[key].add(block)
        else:
            fmt = QTextListFormat()
            fmt.setStyle(style)
            fmt.setIndent(indent)
            lists[key] = self.cursor.createList(fmt)

    def table(self, rows, cols):
        table = self.cursor.insertTable(rows, cols, tables.table_format())
        # tablodan sonraki boş blok, sonraki paragraf için kullanılır
        self.cursor.setPosition(table.lastPosition() + 1)
        self._fresh = True
        return table

    def cell(self, table, row, col):
        cursor = table.cellAt(row, col).firstCursorPosition()
        return DocumentBuilder(self.doc, cursor, self._shared)
