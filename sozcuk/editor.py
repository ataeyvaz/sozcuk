"""Sayfalı ve yakınlaştırılabilir metin editörü.

Belge bir QGraphicsTextItem içinde, sayfa arka planları ayrı bir öğede çizilir; QGraphicsView
yakınlaştırmayı gerçek vektörel ölçekleme olarak uygular (metin yerleşimi değişmez, Word gibi).
Dışarıya QTextEdit'e benzer bir arayüz sunar (textCursor, currentCharFormat, setAlignment…).
"""

import re

from PySide6.QtCore import QEvent, QPointF, QRectF, QSizeF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QKeyEvent,
    QKeySequence,
    QPainter,
    QPen,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocumentFragment,
    QTextListFormat,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QMenu,
    QStyle,
)

from . import icons, images, links, page_numbers, styles, tables
from .styles import PAGE_GAP

WORD_RE = re.compile(r"\w+(?:['’-]\w+)*", re.UNICODE)
SIDE = 24                       # sayfanın iki yanındaki gri boşluk
CANVAS = "#e9e9e9"
MIN_ZOOM, MAX_ZOOM = 0.1, 5.0


class PageBackground(QGraphicsItem):
    """Beyaz A4 sayfaları, gölgeleri ve (açıksa) sayfa numaralarını çizer."""

    def __init__(self, editor=None):
        super().__init__()
        self.editor = editor
        self._pages = 1
        self._width, self._height = 794.0, 1123.0
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption)

    def set_pages(self, count, width, height):
        if (count, width, height) != (self._pages, self._width, self._height):
            self.prepareGeometryChange()
            self._pages, self._width, self._height = count, width, height
            self.update()

    def boundingRect(self):
        return QRectF(-4, 0, self._width + 8, self._pages * (self._height + PAGE_GAP) + 4)

    def paint(self, painter, option, widget=None):
        exposed = option.exposedRect
        painter.setPen(Qt.NoPen)
        for page in range(self._pages):
            rect = QRectF(0, page * (self._height + PAGE_GAP) + PAGE_GAP, self._width, self._height)
            if not rect.adjusted(-4, -4, 4, 4).intersects(exposed):
                continue
            for spread, alpha in ((3, 6), (2, 10), (1, 18)):
                painter.setBrush(QColor(0, 0, 0, alpha))
                painter.drawRect(rect.adjusted(-spread, -spread + 1, spread, spread + 1))
            painter.setBrush(QColor("#ffffff"))
            painter.drawRect(rect)
            if self.editor is not None:
                # sayfa numarası belgenin metni değildir: kenar boşluğuna çizilir (bkz. page_numbers.py)
                page_numbers.draw(painter, self.editor.document(), rect, page + 1, self._pages)
                painter.setPen(Qt.NoPen)


class TextItem(QGraphicsTextItem):
    """Düzenlenebilir belge. Olaylardan sonra editöre imleç değişimini bildirir."""

    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption)  # yalnızca görünen kısmı çiz
        self.setCursor(Qt.IBeamCursor)

    def paint(self, painter, option, widget=None):
        # Qt odaklı metin öğesinin çevresine kesik çizgili çerçeve çizer; sayfada istemiyoruz
        option.state &= ~(QStyle.State_HasFocus | QStyle.State_Selected)
        self.editor.paint_highlights(painter, option.exposedRect)   # metnin altında kalsın
        super().paint(painter, option, widget)
        self.editor.image_tool.paint_unhighlighted(painter)
        self.editor.paint_issues(painter, option.exposedRect)

    def native_key(self, event):
        super().keyPressEvent(event)

    def sceneEvent(self, event):
        # QGraphicsTextItem Tab/Shift+Tab'ı keyPressEvent'e uğratmadan metne gönderir;
        # tablo ve liste davranışları için önce bizim işleyicimizden geçir.
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            self.keyPressEvent(event)
            return True
        return super().sceneEvent(event)

    def keyPressEvent(self, event):
        if not self.editor.handle_key(event):
            super().keyPressEvent(event)
            self.editor.auto_link(event)
        self.editor.notify()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.editor.notify()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.editor.notify()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.editor.notify()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.editor.notify()

    def inputMethodEvent(self, event):
        super().inputMethodEvent(event)
        self.editor.notify()

    def _image_drop(self, mime):
        return mime.hasImage() or bool(images.local_image_files(mime))

    def dragEnterEvent(self, event):
        if self._image_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._image_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        mime = event.mimeData()
        if self._image_drop(mime):
            # dosya gezgininden ya da tarayıcıdan sürüklenen görsel: bırakılan yere ekle
            position = self.document().documentLayout().hitTest(event.pos(), Qt.FuzzyHit)
            cursor = self.textCursor()
            if position >= 0:
                cursor.setPosition(position)
            self.editor.insert_images_from_mime(mime, cursor)
            event.acceptProposedAction()
            self.editor.setFocus()
            return
        super().dropEvent(event)
        self.editor.notify()

    def contextMenuEvent(self, event):
        # sağ tık imleci seçimin dışındaysa oraya taşı (Word gibi)
        pos = self.document().documentLayout().hitTest(event.pos(), Qt.FuzzyHit)
        cursor = self.textCursor()
        if pos >= 0 and not (cursor.selectionStart() <= pos <= cursor.selectionEnd() and cursor.hasSelection()):
            cursor.setPosition(pos)
            self.setTextCursor(cursor)
            self.editor.notify()
        self.editor.show_context_menu(event.screenPos())


class Issue:
    """Belgede kırmızı dalgalı çizgiyle işaretlenen bir bulgu. İmleç, düzenlemelerle birlikte kayar.

    suggestions: öneri listesi ya da onu üreten işlev — öneriler pahalı olabildiği için (Windows yazım
    denetiminde kelime başına ~60 ms) yalnızca sağ tıklanınca hesaplanır. "" önerisi ifadeyi silmek demektir.
    """

    def __init__(self, cursor, original, suggestions=(), explanation="", kind="yazım"):
        self.cursor = cursor
        self.original = original
        self._suggestions = suggestions
        self.explanation = explanation
        self.kind = kind

    @property
    def start(self):
        return self.cursor.selectionStart()

    @property
    def end(self):
        return self.cursor.selectionEnd()

    def suggestions(self):
        if callable(self._suggestions):
            self._suggestions = list(self._suggestions())
        return list(self._suggestions)

    def is_valid(self):
        return self.cursor.hasSelection() and self.cursor.selectedText() == self.original


class Editor(QGraphicsView):
    cursorPositionChanged = Signal()
    currentCharFormatChanged = Signal(QTextCharFormat)
    zoomChanged = Signal(float)
    viewChanged = Signal()  # kaydırma, yakınlaştırma, boyut — cetveller için
    issuesChanged = Signal()
    pageSetupChanged = Signal()  # sayfa boyutu, yönlendirme ya da kenar boşlukları değişti

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.setFrameShape(QFrame.NoFrame)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor(CANVAS))
        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)

        scene = QGraphicsScene(self)
        self.setScene(scene)
        self.pages = PageBackground(self)
        self.text = TextItem(self)
        self.image_tool = images.ImageTool(self)
        scene.addItem(self.pages)
        scene.addItem(self.text)

        self._zoom = 1.0
        self._guide = None
        self._hguide = None
        self.issues = []              # başlangıç konumuna göre sıralı
        self.highlights = []          # Bul ve Değiştir eşleşmeleri: (başlangıç, bitiş)
        self.highlight_current = -1
        self.reading_range = None     # sesli okunan cümle: (başlangıç, bitiş)
        self.bulk_loading = False     # belge yüklenirken: paragraf paragraf değişiklik işlenmesin
        self.context_menu_hooks = []  # hook(menu, cursor): sağ tık menüsüne öğe ekler
        self.issue_menu_hooks = []    # hook(menu, issue): altı çizili bulgunun önerilerinin altına öğe ekler
        self._last_position = None
        self._last_format = None
        self._notify_timer = QTimer(self, singleShot=True, interval=0)
        self._notify_timer.timeout.connect(self.notify)

        doc = self.document()
        doc.documentLayout().documentSizeChanged.connect(self._update_scene_rect)
        doc.contentsChanged.connect(self._notify_timer.start)
        doc.contentsChange.connect(self._prune_issues)
        self.cursorPositionChanged.connect(self.image_tool.sync_with_cursor)
        self.cursorPositionChanged.connect(self._drop_link_format)
        self.horizontalScrollBar().valueChanged.connect(self.viewChanged)
        self.verticalScrollBar().valueChanged.connect(self.viewChanged)
        self.reset()

    # =========================================================================
    # QTextEdit benzeri arayüz
    # =========================================================================

    def document(self):
        return self.text.document()

    def textCursor(self):
        return self.text.textCursor()

    def setTextCursor(self, cursor):
        self.text.setTextCursor(cursor)
        self.notify()
        self.ensure_cursor_visible()

    def currentCharFormat(self):
        return self.textCursor().charFormat()

    def mergeCurrentCharFormat(self, fmt):
        cursor = self.textCursor()
        cursor.mergeCharFormat(fmt)
        if not cursor.hasSelection() and not cursor.block().text():
            cursor.mergeBlockCharFormat(fmt)
        self.text.setTextCursor(cursor)
        self.notify()

    def setCurrentCharFormat(self, fmt):
        cursor = self.textCursor()
        cursor.setCharFormat(fmt)
        self.text.setTextCursor(cursor)
        self.notify()

    def paragraph_alignment(self):
        return self.textCursor().blockFormat().alignment()

    def set_paragraph_alignment(self, alignment):
        cursor = self.textCursor()
        fmt = QTextBlockFormat()
        fmt.setAlignment(alignment)
        cursor.mergeBlockFormat(fmt)
        self.notify()

    def undo(self):
        cursor = self.textCursor()
        self.document().undo(cursor)
        self.setTextCursor(cursor)

    def redo(self):
        cursor = self.textCursor()
        self.document().redo(cursor)
        self.setTextCursor(cursor)

    def toPlainText(self):
        return self.document().toPlainText()

    def setFocus(self, reason=Qt.OtherFocusReason):
        super().setFocus(reason)
        self.scene().setFocusItem(self.text, reason)

    def notify(self):
        cursor = self.textCursor()
        position = (cursor.position(), cursor.anchor())
        fmt = cursor.charFormat()
        if position != self._last_position:
            self._last_position = position
            self.cursorPositionChanged.emit()
            self.viewChanged.emit()
        if fmt != self._last_format:
            self._last_format = fmt
            self.currentCharFormatChanged.emit(fmt)

    # =========================================================================
    # Sayfa düzeni
    # =========================================================================
    #
    # Sayfa boyutu ve kenar boşlukları belgeye aittir (styles.page_size / all_margins).
    # Belge, her sayfa SLOT (sayfa yüksekliği + PAGE_GAP) yüksekliğinde olacak şekilde sayfalanır. Her sayfanın üst kenar
    # boşluğuna PAGE_GAP eklenir; PageBackground bu şeridi gri bırakıp kalanını beyaz sayfa
    # olarak çizer. Böylece metin hiçbir zaman sayfalar arasındaki boşluğa taşmaz.

    def apply_page_layout(self):
        doc = self.document()
        doc.setIndentWidth(styles.INDENT_WIDTH)
        top, bottom, left, right = styles.all_margins(doc)
        width, height = styles.page_size(doc)
        root = doc.rootFrame()
        fmt = root.frameFormat()
        if (fmt.topMargin(), fmt.bottomMargin(), fmt.leftMargin(), fmt.rightMargin()) != (
            top + PAGE_GAP, bottom, left, right
        ):
            fmt.setMargin(0)
            fmt.setTopMargin(top + PAGE_GAP)
            fmt.setBottomMargin(bottom)
            fmt.setLeftMargin(left)
            fmt.setRightMargin(right)
            root.setFrameFormat(fmt)
        if doc.pageSize() != QSizeF(width, height + PAGE_GAP):
            doc.setPageSize(QSizeF(width, height + PAGE_GAP))
        self._update_scene_rect()

    def _update_scene_rect(self, *_):
        pages = self.page_count()
        width, height = self.page_size()
        self.pages.set_pages(pages, width, height)
        self.scene().setSceneRect(QRectF(-SIDE, 0, width + 2 * SIDE, pages * self.slot() + PAGE_GAP))
        self.viewChanged.emit()

    def page_size(self):
        """Sayfanın genişliği ve yüksekliği (px)."""
        return styles.page_size(self.document())

    def slot(self):
        """Sahnede bir sayfanın kapladığı dikey alan (sayfa + aradaki boşluk)."""
        return self.page_size()[1] + PAGE_GAP

    def page_count(self):
        return max(1, self.document().pageCount())

    def current_page(self):
        y = self.cursor_rect().center().y()
        return min(self.page_count(), max(1, int(y // self.slot()) + 1))

    def page_top(self, page):
        """1'den başlayan sayfa numarasının sahnedeki üst kenarı."""
        return (page - 1) * self.slot() + PAGE_GAP

    def cursor_rect(self, position=None):
        """İmlecin (ya da verilen konumun) belge (sahne) koordinatlarındaki dikdörtgeni."""
        cursor = self.textCursor()
        if position is not None:
            cursor = QTextCursor(self.document())
            cursor.setPosition(min(position, self.document().characterCount() - 1))
        block = cursor.block()
        doc_layout = self.document().documentLayout()
        block_rect = doc_layout.blockBoundingRect(block)
        layout = block.layout()
        if layout is None or layout.lineCount() == 0:
            return QRectF(block_rect.x(), block_rect.y(), 1, max(block_rect.height(), 14))
        relative = cursor.position() - block.position()
        line = layout.lineForTextPosition(relative)
        if not line.isValid():
            line = layout.lineAt(layout.lineCount() - 1)
        x = line.cursorToX(relative)
        if isinstance(x, tuple):
            x = x[0]
        return QRectF(self._layout_origin(block_rect, layout) + QPointF(x, line.y()), QSizeF(1, line.height()))

    @staticmethod
    def _layout_origin(block_rect, layout):
        """Satır koordinatlarının (QTextLine.x/y, cursorToX) belgedeki başlangıç noktası.
        Qt, blockBoundingRect'in sol üstünü düzenin konumuna (çerçeve kaymaları dahil) taşır;
        sayfa sonu kaymaları ise satırların kendi y değerindedir."""
        return block_rect.topLeft()

    def ensure_cursor_visible(self):
        self.ensureVisible(self.cursor_rect(), 20, 40)

    def ensure_position_visible(self, position):
        """Sesli okunan cümle görünür kalsın (imleç yerinden oynamaz)."""
        self.ensureVisible(self.cursor_rect(position), 20, 80)

    # =========================================================================
    # Yazım / dilbilgisi bulguları (kırmızı dalgalı çizgi)
    # =========================================================================

    def _issue_index(self, position):
        """Başlangıcı position'dan küçük olmayan ilk bulgunun sırası (ikili arama).
        Konum listesi her seferinde toplanmaz: uzun belgede binlerce bulgu olabilir."""
        low, high = 0, len(self.issues)
        while low < high:
            middle = (low + high) // 2
            if self.issues[middle].start < position:
                low = middle + 1
            else:
                high = middle
        return low

    def replace_issues(self, range_start, range_end, new_issues):
        """[range_start, range_end] aralığındaki bulguları yenileriyle değiştirir (paragraf yeniden denetlenince).
        new_issues: (başlangıç, uzunluk, öneriler, açıklama, tür) listesi, sıralı; konumlar belge içindedir.
        Liste sıralı tutulduğu için yalnızca ilgili dilim değiştirilir (tüm liste filtrelenip sıralanmaz)."""
        first = self._issue_index(range_start)
        last = first
        while last < len(self.issues) and self.issues[last].start <= range_end:
            last += 1
        if first == last and not new_issues:
            return
        created = []
        for start, length, suggestions, explanation, kind in new_issues:
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(start + length, QTextCursor.KeepAnchor)
            created.append(Issue(cursor, cursor.selectedText(), suggestions, explanation, kind))
        self.issues[first:last] = created
        self._repaint_issues()

    def remove_issues(self, predicate):
        kept = [i for i in self.issues if not predicate(i)]
        if len(kept) != len(self.issues):
            self.issues = kept
            self._repaint_issues()

    def clear_issues(self):
        if self.issues:
            self.issues = []
            self._repaint_issues()

    def issue_at(self, position):
        index = self._issue_index(position + 1) - 1
        for issue in self.issues[max(0, index - 1): index + 2]:
            if issue.start <= position <= issue.end:
                return issue
        return None

    def next_issue(self, position):
        """Konumdan sonraki ilk bulgu (sona gelince baştan)."""
        if not self.issues:
            return None
        index = self._issue_index(position + 1)
        return self.issues[index] if index < len(self.issues) else self.issues[0]

    def apply_issue(self, issue, replacement):
        if issue not in self.issues:
            return
        self.issues.remove(issue)
        if issue.is_valid():
            start = issue.start
            if replacement == "" and start > 0 and self.document().characterAt(start - 1).isspace():
                start -= 1  # tekrarlanan kelimeyi silerken önündeki boşluğu da sil
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(issue.end, QTextCursor.KeepAnchor)
            cursor.insertText(replacement)
        self._repaint_issues()

    def ignore_issue(self, issue):
        if issue in self.issues:
            self.issues.remove(issue)
            self._repaint_issues()

    def select_issue(self, issue):
        self.setTextCursor(QTextCursor(issue.cursor))
        self.setFocus()

    def _prune_issues(self, position, removed, added):
        """Düzenlenen yerdeki geçersizleşmiş bulguları atar (her tuşta tüm listeyi taramadan)."""
        if not self.issues or self.bulk_loading:
            return
        low, high = position - 1, position + max(removed, added) + 1
        first = max(0, self._issue_index(low) - 1)
        last = self._issue_index(high + 1)
        window = self.issues[first:last]
        valid = [i for i in window if not (i.end >= low and i.start <= high) or i.is_valid()]
        if len(valid) != len(window):
            self.issues[first:last] = valid
            self._repaint_issues()

    def _repaint_issues(self):
        self.text.update()
        self.issuesChanged.emit()

    def set_highlights(self, ranges, current=-1):
        """Bul ve Değiştir'in bulduğu yerler; current numaralı olan seçili renkle çizilir."""
        self.highlights = list(ranges)
        self.highlight_current = current
        self.viewport().update()

    def _range_rects(self, start, end, exposed):
        """Belge konum aralığının satır satır dikdörtgenleri (yalnızca görünen bölümde)."""
        document = self.document()
        doc_layout = document.documentLayout()
        block = document.findBlock(start)
        rects = []
        while block.isValid() and block.position() < end:
            layout = block.layout()
            block_rect = doc_layout.blockBoundingRect(block)
            if layout is not None and block_rect.intersects(exposed):
                origin = self._layout_origin(block_rect, layout)
                rel_start = max(0, start - block.position())
                rel_end = min(block.length() - 1, end - block.position())
                for i in range(layout.lineCount()):
                    line = layout.lineAt(i)
                    line_start, line_end = line.textStart(), line.textStart() + line.textLength()
                    if line_end <= rel_start or line_start >= rel_end:
                        continue
                    x1 = line.cursorToX(max(rel_start, line_start))
                    x2 = line.cursorToX(min(rel_end, line_end))
                    x1 = x1[0] if isinstance(x1, tuple) else x1
                    x2 = x2[0] if isinstance(x2, tuple) else x2
                    rects.append(QRectF(origin.x() + x1, origin.y() + line.y(), max(2.0, x2 - x1), line.height()))
            block = block.next()
        return rects

    def set_reading_range(self, span):
        """Sesli okunan cümleyi açık maviyle işaretler (None: işareti kaldırır)."""
        self.reading_range = span
        self.viewport().update()

    def paint_highlights(self, painter, exposed):
        if self.reading_range:
            painter.save()
            for rect in self._range_rects(*self.reading_range, exposed):
                painter.fillRect(rect, QColor("#cde4fa"))
            painter.restore()
        if not self.highlights:
            return
        painter.save()
        for index, (start, end) in enumerate(self.highlights):
            current = index == self.highlight_current
            color = QColor("#ff9632") if current else QColor("#ffe27a")
            for rect in self._range_rects(start, end, exposed):
                painter.fillRect(rect, color)
        painter.restore()

    def paint_issues(self, painter, exposed):
        if not self.issues:
            return
        doc_layout = self.document().documentLayout()
        # yalnızca görünen bölümdeki bulguları çiz (uzun belgede binlerce bulgu olabilir)
        first = doc_layout.hitTest(QPointF(0, exposed.top()), Qt.FuzzyHit)
        last = doc_layout.hitTest(QPointF(self.page_size()[0], exposed.bottom()), Qt.FuzzyHit)
        if first >= 0 and last >= 0:
            low = self.document().findBlock(first).position()
            last_block = self.document().findBlock(last)
            high = last_block.position() + last_block.length()
            visible = self.issues[self._issue_index(low): self._issue_index(high + 1)]
        else:
            visible = self.issues
        pen = QPen(QColor("#e81123"), 1)
        pen.setCosmetic(True)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        for issue in visible:
            start, end = issue.start, issue.end
            block = self.document().findBlock(start)
            layout = block.layout()
            block_rect = doc_layout.blockBoundingRect(block)
            if layout is None or not block_rect.intersects(exposed):
                continue
            origin = self._layout_origin(block_rect, layout)
            rel_start, rel_end = start - block.position(), end - block.position()
            for i in range(layout.lineCount()):
                line = layout.lineAt(i)
                line_start, line_end = line.textStart(), line.textStart() + line.textLength()
                if line_end <= rel_start or line_start >= rel_end:
                    continue
                x1 = line.cursorToX(max(rel_start, line_start))
                x2 = line.cursorToX(min(rel_end, line_end))
                x1 = x1[0] if isinstance(x1, tuple) else x1
                x2 = x2[0] if isinstance(x2, tuple) else x2
                y = origin.y() + line.y() + line.ascent() + 2
                self._draw_wave(painter, origin.x() + x1, origin.x() + x2, y)
        painter.restore()

    @staticmethod
    def _draw_wave(painter, x1, x2, y):
        step = 2.0
        points = []
        x, up = x1, True
        while x <= x2:
            points.append(QPointF(x, y - 1 if up else y + 1))
            x += step
            up = not up
        if len(points) > 1:
            painter.drawPolyline(points)

    # =========================================================================
    # Yakınlaştırma
    # =========================================================================

    def zoom(self):
        return self._zoom

    def set_zoom(self, zoom, anchor=None):
        zoom = round(min(MAX_ZOOM, max(MIN_ZOOM, zoom)), 2)
        if abs(zoom - self._zoom) < 0.001:
            return
        if anchor is not None:
            scene_point = self.mapToScene(anchor)
        else:
            scene_point = self.mapToScene(self.viewport().rect().center())
        self._zoom = zoom
        self.setTransform(QTransform.fromScale(zoom, zoom))
        if anchor is not None:
            delta = self.mapFromScene(scene_point) - anchor
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())
        else:
            self.centerOn(scene_point)
        self.zoomChanged.emit(zoom)
        self.viewChanged.emit()

    def fit_width(self):
        scrollbar = self.verticalScrollBar().sizeHint().width()
        self.set_zoom((self.width() - scrollbar - 2 * SIDE) / self.page_size()[0])

    def fit_page(self):
        width, height = self.page_size()
        width_zoom = (self.viewport().width() - 2 * SIDE) / width
        height_zoom = (self.viewport().height() - 2 * PAGE_GAP) / height
        self.set_zoom(min(width_zoom, height_zoom))
        top = self.page_top(self.current_page()) - PAGE_GAP / 2
        self.verticalScrollBar().setValue(round(top * self._zoom))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            steps = event.angleDelta().y() / 120
            if steps:
                self.set_zoom(self._zoom * (1.1 ** steps), anchor=event.position().toPoint())
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewChanged.emit()

    def mousePressEvent(self, event):
        point = self.mapToScene(event.position().toPoint())
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier:
            link = links.cursor_over_link(self, point)
            if link is not None:
                links.open_link(self, link[0])   # Word gibi: Ctrl + tıklama bağlantıyı açar
                event.accept()
                return
        if self.image_tool.mouse_press(point, event.button(), event.modifiers()):
            self.setFocus()
            event.accept()
            return
        # sayfanın dışındaki gri alana tıklanınca imleci en yakın konuma koy, odağı kaybetme
        if self.itemAt(event.position().toPoint()) is not self.text and event.button() == Qt.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            size = self.document().documentLayout().documentSize()
            point = QPointF(min(max(point.x(), 0), self.page_size()[0] - 1), min(max(point.y(), 0), size.height() - 1))
            position = self.document().documentLayout().hitTest(point, Qt.FuzzyHit)
            if position >= 0:
                cursor = self.textCursor()
                cursor.setPosition(position)
                self.text.setTextCursor(cursor)
                self.notify()
            self.setFocus()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        point = self.mapToScene(event.position().toPoint())
        link = links.cursor_over_link(self, point)
        if link is not None:
            self.text.setCursor(Qt.PointingHandCursor if event.modifiers() & Qt.ControlModifier else Qt.IBeamCursor)
            self.setToolTip(f"{links.describe(link[0])}\nAçmak için Ctrl ile tıklayın")
        elif self.toolTip():
            self.setToolTip("")
        if self.image_tool.mouse_move(point, event.modifiers()):
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.image_tool.mouse_release():
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # görselin üzerine çift tık: metinde kelime seçimi yerine görsel seçili kalsın
        point = self.mapToScene(event.position().toPoint())
        if event.button() == Qt.LeftButton and self.image_tool.image_under(point) is not None:
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # --- cetvel kılavuz çizgisi --------------------------------------------

    def set_guide(self, x):
        """Yatay cetvelden sürüklerken sayfa boyunca dikey kılavuz çizgi (None: gizle)."""
        self._guide = x
        self.viewport().update()

    def set_horizontal_guide(self, y):
        """Dikey cetvelden sürüklerken sayfa genişliğince yatay kılavuz çizgi (None: gizle)."""
        self._hguide = y
        self.viewport().update()

    def drawForeground(self, painter, rect):
        self.image_tool.paint(painter)
        if self._guide is None and self._hguide is None:
            return
        pen = QPen(QColor(0, 0, 0, 150), 0, Qt.DotLine)
        pen.setCosmetic(True)
        painter.setPen(pen)
        if self._guide is not None:
            painter.drawLine(QPointF(self._guide, rect.top()), QPointF(self._guide, rect.bottom()))
        if self._hguide is not None:
            painter.drawLine(QPointF(0, self._hguide), QPointF(self.page_size()[0], self._hguide))

    # --- sayfa kenar boşlukları (dikey cetvel) -----------------------------

    def page_margins(self):
        return styles.page_margins(self.document())

    def set_page_margins(self, top, bottom):
        """Üst/alt kenar boşluklarını değiştirir; belge yeniden sayfalanır ve kaydedilmemiş sayılır."""
        return self.set_page_setup(top=top, bottom=bottom)[2:4]

    def side_margins(self):
        return styles.side_margins(self.document())

    def set_page_setup(self, **values):
        """Sayfa boyutu/kenar boşlukları (styles.set_page_setup anahtarları); belge yeniden sayfalanır,
        kaydedilmemiş sayılır. Uygulanan (genişlik, yükseklik, üst, alt, sol, sağ) döner."""
        doc = self.document()
        old = styles.page_size(doc) + styles.all_margins(doc)
        applied = styles.set_page_setup(doc, **values)
        if applied == old:
            return applied
        self.image_tool.deselect()
        self.apply_page_layout()
        doc.setModified(True)
        self.viewChanged.emit()
        self.pageSetupChanged.emit()
        self.ensure_cursor_visible()
        return applied

    # --- sayfa numarası -----------------------------------------------------

    def page_numbers(self):
        return page_numbers.settings(self.document())

    def set_page_numbers(self, **values):
        """Sayfa numarası ayarlarını değiştirir (enabled, position, format, start); uygulanan ayarı döndürür."""
        doc = self.document()
        old = page_numbers.settings(doc)
        applied = page_numbers.set_settings(doc, **values)
        if applied != old:
            doc.setModified(True)
            self.pages.update()
            self.viewport().update()
            self.pageSetupChanged.emit()
        return applied

    def set_orientation(self, landscape):
        width, height = self.page_size()
        if (width > height) != landscape:
            top, bottom, left, right = styles.all_margins(self.document())
            # Word gibi: kenar boşlukları da sayfayla birlikte döner
            self.set_page_setup(width=height, height=width, top=left, bottom=right, left=bottom, right=top)

    def set_paper(self, name):
        for key, _, width, height in styles.PAPER_SIZES:
            if key == name:
                width, height = width * styles.PX_PER_CM, height * styles.PX_PER_CM
                if styles.is_landscape(self.document()):
                    width, height = height, width
                self.set_page_setup(width=width, height=height)
                return

    # =========================================================================
    # Belge
    # =========================================================================

    def reset(self):
        doc = self.document()
        self.clear_issues()
        self.image_tool.deselect()
        loading, self.bulk_loading = self.bulk_loading, True
        doc.setUndoRedoEnabled(False)
        doc.clear()
        styles.reset_page_setup(doc)  # A4, dikey, 2,5 cm (Word TR)
        page_numbers.reset(doc)
        font = QFont(styles.DEFAULT_FAMILY)
        font.setPointSizeF(styles.DEFAULT_SIZE)
        doc.setDefaultFont(font)
        self.apply_page_layout()
        cursor = QTextCursor(doc)
        cursor.setBlockFormat(styles.body_block_format())
        cursor.setBlockCharFormat(styles.body_char_format())
        cursor.setCharFormat(styles.body_char_format())
        self.text.setTextCursor(cursor)
        doc.setUndoRedoEnabled(True)
        doc.setModified(False)
        self.bulk_loading = loading
        self.notify()

    def load(self, build):
        """Belgeyi temizler ve build(document) ile yeniden doldurur.
        Yükleme boyunca bulk_loading açıktır: yazım denetimi paragraf paragraf değil, sonra tek taramayla çalışır."""
        doc = self.document()
        self.bulk_loading = True
        try:
            self.reset()
            doc.setUndoRedoEnabled(False)
            build(doc)
            self.apply_page_layout()
        finally:
            self.bulk_loading = False
        doc.setUndoRedoEnabled(True)
        doc.setModified(False)
        self.text.setTextCursor(QTextCursor(doc))
        self.verticalScrollBar().setValue(0)
        self.notify()

    def print_document(self, printer):
        """Belgeyi ekrandaki sayfa boşlukları olmadan gerçek kâğıt ölçüleriyle yazdırır (PDF dışa aktarma da buradan)."""
        clone = self.document().clone()
        top, bottom = self.page_margins()
        fmt = clone.rootFrame().frameFormat()
        fmt.setTopMargin(top)
        fmt.setBottomMargin(bottom)
        clone.rootFrame().setFrameFormat(fmt)
        width, height = self.page_size()
        clone.setPageSize(QSizeF(width, height))
        config = page_numbers.settings(self.document())
        if not config.enabled:
            clone.print_(printer)
            return
        # sayfa numarası belgenin dışında çizildiği için sayfalar tek tek basılır
        total = max(1, clone.pageCount())
        first = max(1, printer.fromPage() or 1)
        last = min(total, printer.toPage() or total)
        painter = QPainter(printer)
        try:
            painter.scale(printer.resolution() / 96.0, printer.resolution() / 96.0)
            for index, page in enumerate(range(first, last + 1)):
                if index:
                    printer.newPage()
                painter.save()
                painter.translate(0, -(page - 1) * height)
                clone.drawContents(painter, QRectF(0, (page - 1) * height, width, height))
                painter.restore()
                page_numbers.draw(painter, self.document(), QRectF(0, 0, width, height), page, total, config)
        finally:
            painter.end()

    # =========================================================================
    # Seçili bloklar
    # =========================================================================

    def _selected_blocks(self):
        cursor = self.textCursor()
        block = self.document().findBlock(cursor.selectionStart())
        end = cursor.selectionEnd()
        while block.isValid() and block.position() <= end:
            yield block
            if cursor.hasSelection() and block.position() + block.length() > end:
                break
            block = block.next()

    def _edit_blocks(self, change):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for block in list(self._selected_blocks()):
            fmt = block.blockFormat()
            change(fmt, block)
            QTextCursor(block).setBlockFormat(fmt)
        cursor.endEditBlock()
        self.notify()
        self.viewChanged.emit()

    # --- başlık stilleri -----------------------------------------------------

    def heading_level(self):
        return self.textCursor().blockFormat().headingLevel()

    def set_heading(self, level):
        char_format = styles.heading_char_format(level)
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for block in list(self._selected_blocks()):
            old_level = block.blockFormat().headingLevel()
            block_cursor = QTextCursor(block)
            block_cursor.setBlockFormat(styles.heading_block_format(level, block.blockFormat()))
            if old_level != level or level:
                # Normal'e dönerken yalnızca başlıktan gelen boyut/kalınlık sıfırlanır
                block_cursor.mergeBlockCharFormat(char_format)
                block_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                block_cursor.mergeCharFormat(char_format)
        cursor.endEditBlock()
        self.mergeCurrentCharFormat(char_format)

    # --- karakter biçimleri --------------------------------------------------

    def _merge(self, fmt):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            word = QTextCursor(cursor)
            word.select(QTextCursor.WordUnderCursor)
            # imleç bir kelimenin içindeyse (Word gibi) kelimenin tamamına uygula
            if word.hasSelection() and word.selectionStart() < cursor.position() < word.selectionEnd():
                word.mergeCharFormat(fmt)
        else:
            cursor.mergeCharFormat(fmt)
        self.mergeCurrentCharFormat(fmt)

    def set_bold(self, on):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if on else QFont.Normal)
        self._merge(fmt)

    def set_italic(self, on):
        fmt = QTextCharFormat()
        fmt.setFontItalic(on)
        self._merge(fmt)

    def set_underline(self, on):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(on)
        self._merge(fmt)

    def set_strike(self, on):
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(on)
        self._merge(fmt)

    def set_family(self, family):
        fmt = QTextCharFormat()
        fmt.setFontFamilies([family])
        self._merge(fmt)

    def set_size(self, size):
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self._merge(fmt)

    def step_size(self, direction):
        current = self.currentCharFormat().fontPointSize() or styles.DEFAULT_SIZE
        sizes = styles.FONT_SIZES
        if direction > 0:
            size = next((s for s in sizes if s > current), current + 10)
        else:
            size = next((s for s in reversed(sizes) if s < current), max(1, current - 1))
        self.set_size(size)

    def set_text_color(self, color):
        fmt = QTextCharFormat()
        fmt.setForeground(QBrush(color) if color else QBrush(Qt.NoBrush))
        self._merge(fmt)

    def set_highlight(self, color):
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(color) if color else QBrush(Qt.NoBrush))
        self._merge(fmt)

    def clear_formatting(self):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if not cursor.hasSelection():
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.setCharFormat(styles.body_char_format())
        for block in list(self._selected_blocks()):
            fmt = styles.body_block_format()
            if block.textList():
                fmt.setObjectIndex(block.blockFormat().objectIndex())
            QTextCursor(block).setBlockFormat(fmt)
            QTextCursor(block).setBlockCharFormat(styles.body_char_format())
        cursor.endEditBlock()
        self.setCurrentCharFormat(styles.body_char_format())

    # --- paragraf biçimleri --------------------------------------------------

    def set_line_spacing(self, factor):
        self._edit_blocks(
            lambda fmt, _: fmt.setLineHeight(factor * 100, QTextBlockFormat.ProportionalHeight.value)
        )

    def line_spacing(self):
        fmt = self.textCursor().blockFormat()
        if fmt.lineHeightType() == QTextBlockFormat.ProportionalHeight.value:
            return fmt.lineHeight() / 100
        return 1.0

    def _indent_base(self, block):
        """Paragrafın girinti düzeyi ve liste girintisinden gelen sol kayma (px)."""
        fmt = block.blockFormat()
        base = fmt.indent() * self.document().indentWidth()
        if block.textList():
            base += block.textList().format().indent() * self.document().indentWidth()
        return base

    def paragraph_indents(self):
        """Cetvel için (sol, ilk satır, sağ) — sayfanın sol kenarından piksel. Tablo içindeyse None."""
        cursor = self.textCursor()
        if cursor.currentTable() is not None:
            return None
        block = cursor.block()
        fmt = block.blockFormat()
        margin_left, margin_right = self.side_margins()
        left = margin_left + self._indent_base(block) + fmt.leftMargin()
        return left, left + fmt.textIndent(), self.page_size()[0] - margin_right - fmt.rightMargin()

    def set_paragraph_indents(self, left, first, right):
        margin_left, margin_right = self.side_margins()
        page_width = self.page_size()[0]

        def change(fmt, block):
            fmt.setLeftMargin(left - margin_left - self._indent_base(block))
            fmt.setTextIndent(first - left)
            fmt.setRightMargin(page_width - margin_right - right)
        self._edit_blocks(change)

    # --- listeler ------------------------------------------------------------

    def toggle_list(self, bullet):
        cursor = self.textCursor()
        current = cursor.currentList()
        cursor.beginEditBlock()
        if current and styles.is_bullet(current.format().style()) == bullet:
            for block in list(self._selected_blocks()):
                if block.textList():
                    block.textList().remove(block)
                    fmt = block.blockFormat()
                    fmt.setIndent(0)
                    QTextCursor(block).setBlockFormat(fmt)
        elif current:
            fmt = current.format()
            fmt.setStyle(styles.list_style_for(bullet, fmt.indent()))
            current.setFormat(fmt)
        else:
            fmt = QTextListFormat()
            fmt.setIndent(1)
            fmt.setStyle(styles.list_style_for(bullet, 1))
            cursor.createList(fmt)
        cursor.endEditBlock()
        self.notify()
        self.viewChanged.emit()

    def change_indent(self, delta):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for block in list(self._selected_blocks()):
            lst = block.textList()
            if not lst:
                fmt = block.blockFormat()
                fmt.setIndent(max(0, fmt.indent() + delta))
                QTextCursor(block).setBlockFormat(fmt)
                continue
            old = lst.format()
            indent = max(1, old.indent() + delta)
            if indent == old.indent():
                continue
            bullet = styles.is_bullet(old.style())
            lst.remove(block)
            # remove() listenin girintisini paragrafa aktarır; sıfırlamazsak girinti birikir
            fmt = block.blockFormat()
            fmt.setIndent(0)
            QTextCursor(block).setBlockFormat(fmt)
            target = self._neighbour_list(block, indent, bullet)
            if target:
                target.add(block)
            else:
                fmt = QTextListFormat()
                fmt.setIndent(indent)
                fmt.setStyle(styles.list_style_for(bullet, indent))
                QTextCursor(block).createList(fmt)
        cursor.endEditBlock()
        self.notify()
        self.viewChanged.emit()

    @staticmethod
    def _neighbour_list(block, indent, bullet):
        """Yukarıda aynı seviyedeki listeyi bulur ki numaralandırma devam etsin."""
        prev = block.previous()
        while prev.isValid() and prev.textList():
            fmt = prev.textList().format()
            if fmt.indent() == indent:
                return prev.textList() if styles.is_bullet(fmt.style()) == bullet else None
            if fmt.indent() < indent:
                return None
            prev = prev.previous()
        return None

    # --- tablolar ------------------------------------------------------------

    def insert_table(self, rows, cols):
        cursor = self.textCursor()
        table = tables.insert_table(cursor, rows, cols)
        self.setTextCursor(table.cellAt(0, 0).firstCursorPosition())

    def table_action(self, action, *args):
        cursor = self.textCursor()
        if cursor.currentTable() is None:
            return
        cursor.beginEditBlock()
        action(cursor, *args)
        cursor.endEditBlock()
        self.notify()

    # --- pano ----------------------------------------------------------------

    def _native_shortcut(self, sequence):
        key = QKeySequence(sequence)[0]
        event = QKeyEvent(QEvent.KeyPress, key.key(), key.keyboardModifiers())
        self.text.native_key(event)
        self.notify()

    def cut(self):
        self._native_shortcut(QKeySequence.Cut)

    def copy(self):
        self._native_shortcut(QKeySequence.Copy)

    def select_all(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.Document)
        self.setTextCursor(cursor)
        self.setFocus()

    def paste(self, plain=False):
        mime = QApplication.clipboard().mimeData()
        if mime is None:
            return
        cursor = self.textCursor()
        doc = self.document()
        html_range = None
        cursor.beginEditBlock()
        grid = tables.grid_from_mime(mime)
        if not plain and grid and cursor.currentTable() is not None:
            tables.fill_cells(cursor, grid)
        elif plain:
            cursor.insertText(mime.text().replace("\r\n", "\n"))
        elif images.local_image_files(mime) or (mime.hasImage() and not mime.text().strip()):
            # ekran görüntüsü, kopyalanan görsel ya da Gezgin'den kopyalanan görsel dosyaları
            cursor.endEditBlock()
            self.insert_images_from_mime(mime, cursor)  # eklenen görseli seçer
            return
        elif mime.hasHtml():
            start = cursor.selectionStart()
            cursor.insertFragment(QTextDocumentFragment.fromHtml(mime.html(), doc))
            html_range = (start, cursor.position())
        elif grid:
            tables.insert_grid(cursor, grid)
        elif mime.hasText():
            cursor.insertText(mime.text().replace("\r\n", "\n"))
        cursor.endEditBlock()
        if html_range:
            # yeni tablo çerçeveleri ancak düzenleme bloğu kapanınca oluşur; aynı geri-al adımına ekle
            cursor.joinPreviousEditBlock()
            tables.style_pasted_tables(doc, *html_range)
            cursor.endEditBlock()
        self.setTextCursor(cursor)

    # --- görseller -----------------------------------------------------------

    def insert_image(self, image, cursor=None):
        """Görseli imlece ekler ve seçer (Word gibi eklenen görsel hemen boyutlandırılabilir)."""
        cursor = QTextCursor(cursor) if cursor is not None else self.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        position = cursor.position()
        if not images.insert_image(cursor, image):
            return False
        self.image_tool.select(position)
        self.ensure_cursor_visible()
        return True

    def insert_image_files(self, paths, cursor=None):
        """Dosyalardan görsel ekler; açılamayan dosyaların adlarını döndürür."""
        cursor = QTextCursor(cursor) if cursor is not None else self.textCursor()
        failed, inserted = [], None
        cursor.beginEditBlock()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        for path in paths:
            image = QImage(path)
            if image.isNull():
                failed.append(path)
                continue
            inserted = cursor.position()
            images.insert_image(cursor, image)
        cursor.endEditBlock()
        if inserted is not None:
            self.image_tool.select(inserted)
            self.ensure_cursor_visible()
        return failed

    def insert_images_from_mime(self, mime, cursor=None):
        files = images.local_image_files(mime)
        if files:
            return not self.insert_image_files(files, cursor)
        if mime.hasImage():
            return self.insert_image(QImage(mime.imageData()), cursor)
        return False

    def can_paste(self):
        mime = QApplication.clipboard().mimeData()
        return mime is not None and (mime.hasText() or mime.hasHtml() or mime.hasImage() or mime.hasUrls())

    def add_image_menu(self, menu):
        """Seçili görselin işlemleri (sağ tık menüsü ve araç çubuğu için ortak)."""
        tool = self.image_tool
        selected = tool.selected() is not None
        entries = [
            ("rotate_right", "Sağa 90° Döndür", lambda: tool.rotate_by(90), selected),
            ("rotate_left", "Sola 90° Döndür", lambda: tool.rotate_by(-90), selected),
            ("flip", "Döndürmeyi Sıfırla", tool.reset_rotation, selected and tool.rotation() != 0),
            None,
            ("crop", "Kırp", tool.start_crop, selected and not tool.crop_mode),
            ("crop_reset", "Kırpmayı Sıfırla", tool.reset_crop, selected and tool.is_cropped()),
            ("image_size", "Özgün Boyut", tool.reset_size, selected),
        ]
        actions = []
        for entry in entries:
            if entry is None:
                menu.addSeparator()
                continue
            icon_name, text, slot, enabled = entry
            action = menu.addAction(icons.icon(icon_name), text)
            action.setEnabled(enabled)
            action.triggered.connect(slot)
            actions.append(action)
        return actions

    # --- sağ tık menüsü ------------------------------------------------------

    def show_context_menu(self, global_pos):
        cursor = self.textCursor()
        menu = QMenu(self)

        # Word gibi: altı çizili hatanın önerileri menünün en üstünde, kalın
        issue = self.issue_at(cursor.position()) if not cursor.hasSelection() else None
        if issue is not None:
            suggestions = issue.suggestions()
            for suggestion in suggestions:
                label = suggestion if suggestion else "Tekrarlanan Kelimeyi Sil"
                action = menu.addAction(label)
                font = action.font()
                font.setBold(True)
                action.setFont(font)
                action.triggered.connect(lambda _=False, s=suggestion: self.apply_issue(issue, s))
            if not suggestions:
                menu.addAction("(Yazım önerisi yok)").setEnabled(False)
            if issue.explanation:
                menu.addAction(issue.explanation).setEnabled(False)
            if self.issue_menu_hooks:
                for hook in self.issue_menu_hooks:
                    hook(menu, issue)
            else:
                menu.addAction("Yoksay", lambda: self.ignore_issue(issue))
            menu.addSeparator()

        def add(menu_, icon_name, text, slot, enabled=True, shortcut=None):
            action = menu_.addAction(text)
            if icon_name:
                action.setIcon(icons.icon(icon_name))
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
                action.setShortcutVisibleInContextMenu(True)
            action.setEnabled(enabled)
            action.triggered.connect(slot)
            return action

        add(menu, "cut", "Kes", self.cut, cursor.hasSelection(), QKeySequence.Cut)
        add(menu, "copy", "Kopyala", self.copy, cursor.hasSelection(), QKeySequence.Copy)
        add(menu, "paste", "Yapıştır", self.paste, self.can_paste(), QKeySequence.Paste)
        add(menu, "paste_text", "Yalnızca Metni Koru", lambda: self.paste(plain=True), self.can_paste(), "Ctrl+Shift+V")

        if self.image_tool.selected() is not None:
            menu.addSeparator()
            if self.image_tool.crop_mode:
                add(menu, "crop", "Kırpmayı Uygula", self.image_tool.apply_crop, shortcut="Return")
                add(menu, None, "Kırpmadan Vazgeç", self.image_tool.cancel_crop, shortcut="Esc")
            else:
                self.add_image_menu(menu)

        if cursor.currentTable() is not None:
            menu.addSeparator()
            insert = menu.addMenu(icons.icon("table"), "Ekle")
            add(insert, "row_above", "Üste Satır Ekle", lambda: self.table_action(tables.insert_rows, True))
            add(insert, "row_below", "Alta Satır Ekle", lambda: self.table_action(tables.insert_rows, False))
            add(insert, "col_left", "Sola Sütun Ekle", lambda: self.table_action(tables.insert_columns, True))
            add(insert, "col_right", "Sağa Sütun Ekle", lambda: self.table_action(tables.insert_columns, False))
            delete = menu.addMenu(icons.icon("delete"), "Sil")
            add(delete, None, "Satırları Sil", lambda: self.table_action(tables.delete_rows))
            add(delete, None, "Sütunları Sil", lambda: self.table_action(tables.delete_columns))
            add(delete, None, "Tabloyu Sil", lambda: self.table_action(tables.delete_table))
            add(menu, "merge", "Hücreleri Birleştir", lambda: self.table_action(tables.merge_cells),
                tables.can_merge(cursor))
            add(menu, "split", "Hücreyi Böl", lambda: self.table_action(tables.split_cell),
                tables.can_split(cursor))
        for hook in self.context_menu_hooks:
            hook(menu, cursor)
        menu.exec(global_pos)

    # --- klavye --------------------------------------------------------------

    def handle_key(self, event):
        """Word davranışları. Olayı işlediyse True döner."""
        key, mods = event.key(), event.modifiers()
        cursor = self.textCursor()

        if self.image_tool.key_press(event):
            return True

        if event.matches(QKeySequence.Paste):
            self.paste()
            return True
        if key == Qt.Key_V and mods == (Qt.ControlModifier | Qt.ShiftModifier):
            self.paste(plain=True)
            return True

        if key in (Qt.Key_Tab, Qt.Key_Backtab):
            backwards = key == Qt.Key_Backtab or bool(mods & Qt.ShiftModifier)
            if cursor.currentTable() is not None:
                cursor.beginEditBlock()
                target = tables.next_cell_cursor(cursor, backwards)
                cursor.endEditBlock()
                self.setTextCursor(target)
                return True
            if cursor.currentList() is not None and cursor.atBlockStart():
                self.change_indent(-1 if backwards else 1)
                return True
            if backwards:
                return True

        if key in (Qt.Key_Return, Qt.Key_Enter) and not mods & Qt.ShiftModifier:
            block = cursor.block()
            in_list = cursor.currentList() is not None
            if in_list and not block.text():
                # Word: boş madde üzerinde Enter önce seviye düşürür, sonra listeden çıkar
                if cursor.currentList().format().indent() > 1:
                    self.change_indent(-1)
                else:
                    self.toggle_list(styles.is_bullet(cursor.currentList().format().style()))
                return True
            if block.blockFormat().headingLevel() and cursor.atBlockEnd() and not cursor.hasSelection():
                self.text.native_key(event)
                self.set_heading(0)
                return True
        return False

    # --- sayaç ---------------------------------------------------------------

    # --- köprüler -------------------------------------------------------------

    def link_at_cursor(self):
        return links.link_at(self.document(), self.textCursor().position())

    def open_link(self, href):
        return links.open_link(self, href)

    def apply_link(self, href, text=None, span=None):
        """Seçime (ya da verilen aralığa) köprü uygular."""
        cursor = self.textCursor()
        if span is not None:
            cursor.setPosition(span[0])
            cursor.setPosition(span[1], QTextCursor.KeepAnchor)
        links.apply(cursor, href, text)
        self.setTextCursor(cursor)
        self.setFocus()

    def remove_link(self, span=None):
        span = span or (self.link_at_cursor() or (None, None, None))[1:]
        if span[0] is None:
            return
        links.remove(self.document(), span[0], span[1])
        self.setFocus()

    def _drop_link_format(self):
        """Köprünün hemen başında/sonunda yazmaya başlayınca yazılan metin köprüye katılmasın (Word gibi)."""
        cursor = self.textCursor()
        if cursor.hasSelection() or self.bulk_loading:
            return
        fmt = cursor.charFormat()
        if not fmt.anchorHref():
            return
        link = links.link_at(self.document(), cursor.position())
        if link is not None and link[1] < cursor.position() < link[2]:
            return
        clean = QTextCharFormat(fmt)
        clean.setAnchor(False)
        clean.setAnchorHref("")
        clean.setFontUnderline(False)
        clean.setForeground(QColor("#000000"))
        self.setCurrentCharFormat(clean)

    def auto_link(self, event):
        """Word gibi: adresin arkasına boşluk ya da Enter gelince kendiliğinden köprü olur."""
        if event.text() not in (" ", "\r", "\n") or self.bulk_loading:
            return
        cursor = self.textCursor()
        position = cursor.position() - 1
        if event.text() != " ":
            position = self.document().findBlock(cursor.position()).previous().position() \
                + len(self.document().findBlock(cursor.position()).previous().text())
        found = links.auto_link_at(self.document(), max(0, position))
        if found is None:
            return
        start, end, href = found
        edit = QTextCursor(self.document())
        edit.setPosition(start)
        edit.setPosition(end, QTextCursor.KeepAnchor)
        edit.joinPreviousEditBlock()
        links.apply(edit, href)
        edit.endEditBlock()

    def counts(self):
        text = self.toPlainText()
        words = len(WORD_RE.findall(text))
        # karakterleri tek tek dolaşmak uzun belgede çok yavaştı (ölçüldü: 300 paragrafta sürenin %97'si);
        # satır/paragraf ayırıcıları ve nesne yer tutucuları C düzeyinde sayılıp çıkarılır
        chars = len(text) - sum(text.count(mark) for mark in ("\n", "\u2029", "\u2028", "\ufffc"))
        return words, chars
