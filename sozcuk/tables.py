"""Tablo işlemleri: ekleme, satır/sütun ekleme-silme, hücre birleştirme/bölme ve panodan tablo yapıştırma."""

import csv
import io

from PySide6.QtGui import (
    QBrush,
    QColor,
    QTextCursor,
    QTextDocument,
    QTextFrameFormat,
    QTextLength,
    QTextTable,
    QTextTableFormat,
)

BORDER_COLOR = "#808080"


def table_format():
    """Word'ün 'Tablo Kılavuzu' görünümüne yakın: ince tek çizgi, tam genişlik, eşit sütunlar."""
    fmt = QTextTableFormat()
    fmt.setBorder(1)
    fmt.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
    fmt.setBorderBrush(QBrush(QColor(BORDER_COLOR)))
    fmt.setBorderCollapse(True)
    fmt.setCellPadding(5)
    fmt.setCellSpacing(0)
    fmt.setWidth(QTextLength(QTextLength.PercentageLength, 100))
    return fmt


def insert_table(cursor, rows, cols):
    cursor.beginEditBlock()
    if cursor.hasSelection():
        cursor.removeSelectedText()
    table = cursor.insertTable(rows, cols, table_format())
    cursor.endEditBlock()
    return table


def all_tables(frame):
    for child in frame.childFrames():
        if isinstance(child, QTextTable):
            yield child
        yield from all_tables(child)


# --- hücre seçimi ------------------------------------------------------------

def selection_range(cursor):
    """(tablo, ilk satır, satır sayısı, ilk sütun, sütun sayısı) — imleç tabloda değilse None."""
    table = cursor.currentTable()
    if table is None:
        return None
    if cursor.hasComplexSelection():
        row, rows, col, cols = cursor.selectedTableCells()
        return table, row, rows, col, cols
    cell = table.cellAt(cursor)
    return table, cell.row(), cell.rowSpan(), cell.column(), cell.columnSpan()


def insert_rows(cursor, above):
    table, row, rows, _, _ = selection_range(cursor)
    table.insertRows(row if above else row + rows, rows)


def insert_columns(cursor, left):
    table, _, _, col, cols = selection_range(cursor)
    table.insertColumns(col if left else col + cols, cols)


def delete_rows(cursor):
    table, row, rows, _, _ = selection_range(cursor)
    if rows >= table.rows():
        delete_table(cursor)
    else:
        table.removeRows(row, rows)


def delete_columns(cursor):
    table, _, _, col, cols = selection_range(cursor)
    if cols >= table.columns():
        delete_table(cursor)
    else:
        table.removeColumns(col, cols)


def delete_table(cursor):
    table = cursor.currentTable()
    doc = cursor.document()
    remover = QTextCursor(doc)
    remover.setPosition(table.firstPosition() - 1)
    remover.setPosition(table.lastPosition() + 1, QTextCursor.KeepAnchor)
    remover.removeSelectedText()


def can_merge(cursor):
    return cursor.currentTable() is not None and cursor.hasComplexSelection()


def merge_cells(cursor):
    cursor.currentTable().mergeCells(cursor)


def can_split(cursor):
    info = selection_range(cursor)
    return info is not None and not cursor.hasComplexSelection() and (info[2] > 1 or info[4] > 1)


def split_cell(cursor):
    table, row, _, col, _ = selection_range(cursor)
    table.splitCell(row, col, 1, 1)


def select_cell(cell):
    cursor = cell.firstCursorPosition()
    cursor.setPosition(cell.lastCursorPosition().position(), QTextCursor.KeepAnchor)
    return cursor


def next_cell_cursor(cursor, backwards=False):
    """Tab/Shift+Tab: sonraki/önceki hücrenin içeriğini seçer. Son hücrede Tab yeni satır ekler (Word gibi)."""
    table = cursor.currentTable()
    cell = table.cellAt(cursor)
    row, col = cell.row(), cell.column()
    if backwards:
        col -= 1
        if col < 0:
            row, col = row - 1, table.columns() - 1
        if row < 0:
            return select_cell(table.cellAt(0, 0))
        target = table.cellAt(row, col)
    else:
        col += cell.columnSpan()
        if col >= table.columns():
            row, col = row + cell.rowSpan(), 0
        if row >= table.rows():
            table.appendRows(1)
        target = table.cellAt(row, col)
    return select_cell(target)


# --- pano --------------------------------------------------------------------

def grid_from_mime(mime):
    """Panodaki tablo verisini satır/sütun listesine çevirir (Excel, Word, web, sekmeli metin)."""
    if mime.hasHtml() and "<table" in mime.html().lower():
        doc = QTextDocument()
        doc.setHtml(mime.html())
        table = next(all_tables(doc.rootFrame()), None)
        if table is not None:
            grid = []
            for r in range(table.rows()):
                row = []
                for c in range(table.columns()):
                    text = select_cell(table.cellAt(r, c)).selectedText()
                    row.append(text.replace("\u2029", "\n").strip())
                grid.append(row)
            return grid
    if mime.hasText():
        text = mime.text().replace("\r\n", "\n").rstrip("\n")
        if "\t" in text:
            return [row for row in csv.reader(io.StringIO(text), delimiter="\t")]
    return None


def fill_cells(cursor, grid):
    """Tablodaki imleçten başlayarak hücrelerin üzerine yazar; gerekirse satır/sütun ekler."""
    table = cursor.currentTable()
    cell = table.cellAt(cursor)
    row0, col0 = cell.row(), cell.column()
    need_rows = row0 + len(grid) - table.rows()
    need_cols = col0 + max(len(r) for r in grid) - table.columns()
    if need_rows > 0:
        table.appendRows(need_rows)
    if need_cols > 0:
        table.appendColumns(need_cols)
    for i, values in enumerate(grid):
        for j, value in enumerate(values):
            select_cell(table.cellAt(row0 + i, col0 + j)).insertText(value)


def insert_grid(cursor, grid):
    cols = max(len(r) for r in grid)
    table = cursor.insertTable(len(grid), cols, table_format())
    for i, values in enumerate(grid):
        for j, value in enumerate(values):
            table.cellAt(i, j).firstCursorPosition().insertText(value)
    return table


def style_pasted_tables(document, start, end):
    """HTML'den gelen kenarlıksız tablolara (ör. Excel) görünür kenarlık verir."""
    for table in all_tables(document.rootFrame()):
        if start <= table.firstPosition() <= end:
            fmt = table.format()
            if fmt.border() == 0 or fmt.borderStyle() == QTextFrameFormat.BorderStyle_None:
                base = table_format()
                fmt.setBorder(base.border())
                fmt.setBorderStyle(base.borderStyle())
                fmt.setBorderBrush(base.borderBrush())
                fmt.setBorderCollapse(True)
                fmt.setCellSpacing(0)
                if fmt.cellPadding() < 2:
                    fmt.setCellPadding(base.cellPadding())
                table.setFormat(fmt)
