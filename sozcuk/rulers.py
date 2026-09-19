"""Word tarzı yatay ve dikey cetvel.

Yatay cetvel imlecin bulunduğu paragrafın girintilerini gösterir; işaretçiler sürüklenince
sayfada kılavuz çizgi çıkar, bırakınca seçili paragraflara uygulanır (0,25 cm'ye yapışır, Alt ile serbest).
"""

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QGridLayout, QToolTip, QWidget

from .styles import MIN_TEXT_HEIGHT, PX_PER_CM

SIZE = 24
BAND_MARGIN = 4
MIN_TEXT_WIDTH = PX_PER_CM          # sol ve sağ girinti arasında en az 1 cm
SNAP = PX_PER_CM / 4

BACKGROUND = "#e9e9e9"
MARGIN_FILL = "#d4d4d4"
TEXT_FILL = "#ffffff"
BAND_BORDER = "#c6c6c6"
TICK = "#6b6b6b"
MARKER_FILL = "#ffffff"
MARKER_HOVER = "#dde8f8"
MARKER_PEN = "#5f5f5f"

MARKER_TIPS = {
    "first": "İlk Satır Girintisi",
    "hanging": "Asılı Girinti",
    "left": "Sol Girinti",
    "right": "Sağ Girinti",
}


def _cm(pixels):
    return f"{pixels / PX_PER_CM:.2f} cm".replace(".", ",")


def _label_font():
    font = QFont("Segoe UI")
    font.setPixelSize(10)
    return font


class _Ruler(QWidget):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        editor.viewChanged.connect(self.update)
        editor.document().contentsChanged.connect(self.update)

    def _viewport_offset(self):
        return self.mapFromGlobal(self.editor.viewport().mapToGlobal(QPoint(0, 0)))

    def _to_widget(self, scene_point):
        mapped = self.editor.viewportTransform().map(scene_point)
        return mapped + QPointF(self._viewport_offset())

    def _to_scene_x(self, x):
        transform = self.editor.viewportTransform()
        return (x - self._viewport_offset().x() - transform.dx()) / transform.m11()


class HorizontalRuler(_Ruler):
    def __init__(self, editor, parent=None):
        super().__init__(editor, parent)
        self.setFixedHeight(SIZE)
        self.setMouseTracking(True)
        self._drag = None       # sürüklenen işaretçi adı
        self._values = None     # sürükleme sırasında (sol, ilk, sağ)
        self._hover = None

    def _x(self, doc_x):
        return self._to_widget(QPointF(doc_x, 0)).x()

    def _indents(self):
        return self._values if self._values is not None else self.editor.paragraph_indents()

    # --- çizim -------------------------------------------------------------

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(BACKGROUND))
        page_width = self.editor.page_size()[0]
        margin_left, margin_right = self.editor.side_margins()
        page_left, page_right = self._x(0), self._x(page_width)
        text_left, text_right = self._x(margin_left), self._x(page_width - margin_right)
        top, bottom = BAND_MARGIN, self.height() - BAND_MARGIN
        band = QRectF(page_left, top, page_right - page_left, bottom - top)

        p.fillRect(band, QColor(MARGIN_FILL))
        p.fillRect(QRectF(text_left, top, text_right - text_left, bottom - top), QColor(TEXT_FILL))
        p.setPen(QColor(BAND_BORDER))
        p.drawRect(band.adjusted(0, 0, -1, -1))

        self._draw_ticks(p, page_left, page_right, text_left, top, bottom)
        indents = self._indents()
        if indents is not None:
            self._draw_markers(p, indents, top, bottom)

    def _draw_ticks(self, p, page_left, page_right, origin, top, bottom):
        unit = PX_PER_CM * self.editor.zoom()
        middle = (top + bottom) / 2
        p.setFont(_label_font())
        quarter = unit / 4
        show_quarters = quarter >= 4
        first = math.floor((page_left - origin) / quarter)
        last = math.ceil((page_right - origin) / quarter)
        label_every = 1 if unit >= 22 else 2
        for k in range(first, last + 1):
            x = math.floor(origin + k * quarter) + 0.5
            if x < page_left + 2 or x > page_right - 2:
                continue
            if k % 4 == 0:
                cm = abs(k // 4)
                if cm and cm % label_every == 0:
                    p.setPen(QColor(TICK))
                    p.drawText(QRectF(x - 10, top, 20, bottom - top), Qt.AlignCenter, str(cm))
            elif k % 2 == 0:
                p.setPen(QColor(TICK))
                p.drawLine(QPointF(x, middle - 2.5), QPointF(x, middle + 2.5))
            elif show_quarters:
                p.setPen(QColor(TICK))
                p.drawLine(QPointF(x, middle - 1), QPointF(x, middle + 1))

    def _shapes(self, indents, top, bottom):
        left, first, right = (round(self._x(v)) + 0.5 for v in indents)
        mid = (top + bottom) / 2
        return {
            "first": QPolygonF([QPointF(first - 4, top), QPointF(first + 4, top), QPointF(first + 4, top + 3),
                                QPointF(first, mid - 0.5), QPointF(first - 4, top + 3)]),
            "hanging": QPolygonF([QPointF(left, mid + 0.5), QPointF(left + 4, bottom - 7), QPointF(left + 4, bottom - 4),
                                  QPointF(left - 4, bottom - 4), QPointF(left - 4, bottom - 7)]),
            "left": QPolygonF([QPointF(left - 4, bottom - 4), QPointF(left + 4, bottom - 4),
                               QPointF(left + 4, bottom), QPointF(left - 4, bottom)]),
            "right": QPolygonF([QPointF(right, mid + 0.5), QPointF(right + 4, bottom - 7), QPointF(right + 4, bottom - 1),
                                QPointF(right - 4, bottom - 1), QPointF(right - 4, bottom - 7)]),
        }

    def _draw_markers(self, p, indents, top, bottom):
        p.setRenderHint(QPainter.Antialiasing)
        for name, shape in self._shapes(indents, top, bottom).items():
            active = name in (self._drag, self._hover)
            p.setPen(QPen(QColor(MARKER_PEN), 1))
            p.setBrush(QColor(MARKER_HOVER if active else MARKER_FILL))
            p.drawPolygon(shape)

    # --- fare --------------------------------------------------------------

    def _hit(self, pos):
        indents = self.editor.paragraph_indents()
        if indents is None:
            return None
        shapes = self._shapes(indents, BAND_MARGIN, self.height() - BAND_MARGIN)
        for name in ("left", "hanging", "first", "right"):
            if shapes[name].boundingRect().adjusted(-2, -1, 2, 1).contains(QPointF(pos)):
                return name
        return None

    def mousePressEvent(self, event):
        name = self._hit(event.position().toPoint())
        if event.button() != Qt.LeftButton or name is None:
            return
        self._drag = name
        self._values = list(self.editor.paragraph_indents())
        self._start_values = list(self._values)
        self._move(event)

    def mouseMoveEvent(self, event):
        if self._drag is None:
            hover = self._hit(event.position().toPoint())
            if hover != self._hover:
                self._hover = hover
                self.setCursor(Qt.SizeHorCursor if hover else Qt.ArrowCursor)
                self.update()
            if hover:
                QToolTip.showText(event.globalPosition().toPoint(), MARKER_TIPS[hover], self)
            else:
                QToolTip.hideText()
            return
        self._move(event)

    def _move(self, event):
        x = self._to_scene_x(event.position().x())
        if not event.modifiers() & Qt.AltModifier:
            origin = self.editor.side_margins()[0]
            x = origin + round((x - origin) / SNAP) * SNAP
        left, first, right = self._start_values
        x = max(0.0, min(float(self.editor.page_size()[0]), x))
        if self._drag == "first":
            first = min(x, right - MIN_TEXT_WIDTH)
            guide = first
        elif self._drag == "hanging":
            left = min(x, right - MIN_TEXT_WIDTH)
            guide = left
        elif self._drag == "left":
            delta = min(x, right - MIN_TEXT_WIDTH) - left
            delta = max(delta, -left, -first)
            left, first = left + delta, first + delta
            guide = left
        else:
            right = max(x, max(left, first) + MIN_TEXT_WIDTH)
            guide = right
        self._values = [left, first, right]
        self.editor.set_guide(guide)
        self.update()

    def mouseReleaseEvent(self, event):
        if self._drag is None:
            return
        values, self._values, self._drag = self._values, None, None
        self.editor.set_guide(None)
        if values != self._start_values:
            self.editor.set_paragraph_indents(*values)
        self.editor.setFocus()
        self.update()

    def leaveEvent(self, _):
        if self._hover:
            self._hover = None
            self.update()


class VerticalRuler(_Ruler):
    """İmlecin bulunduğu sayfanın üst/alt kenar boşluklarını gösterir; gri/beyaz sınırlar sürüklenerek
    belgenin üst ve alt kenar boşlukları ayarlanır (Word gibi). 0,25 cm'ye yapışır, Alt ile serbest."""

    GRAB_PX = 4  # sınırın bu kadar yakınında sürükleme başlar

    def __init__(self, editor, parent=None):
        super().__init__(editor, parent)
        self.setFixedWidth(SIZE)
        self.setMouseTracking(True)
        self._drag = None        # "top" | "bottom"
        self._drag_page = None   # sürükleme boyunca sabit sayfa (düzen bırakılınca değişir)
        self._values = None      # sürüklerken (üst, alt) önizlemesi
        self._hover = None

    def _page_top_scene(self):
        page = self._drag_page if self._drag_page is not None else self.editor.current_page()
        return self.editor.page_top(page)

    def _page_height(self):
        return self.editor.page_size()[1]

    def _margins(self):
        return self._values if self._values is not None else self.editor.page_margins()

    def _to_scene_y(self, y):
        transform = self.editor.viewportTransform()
        return (y - self._viewport_offset().y() - transform.dy()) / transform.m22()

    def _boundaries(self):
        top, bottom = self._margins()
        page_top = self._page_top_scene()
        return (self._to_widget(QPointF(0, page_top + top)).y(),
                self._to_widget(QPointF(0, page_top + self._page_height() - bottom)).y())

    def _hit(self, y):
        text_top, text_bottom = self._boundaries()
        if abs(y - text_top) <= self.GRAB_PX:
            return "top"
        if abs(y - text_bottom) <= self.GRAB_PX:
            return "bottom"
        return None

    def mouseMoveEvent(self, event):
        y = event.position().y()
        if self._drag is None:
            hover = self._hit(y)
            if hover != self._hover:
                self._hover = hover
                self.setCursor(Qt.SizeVerCursor if hover else Qt.ArrowCursor)
            if hover:
                label = "Üst Kenar Boşluğu" if hover == "top" else "Alt Kenar Boşluğu"
                value = self.editor.page_margins()[0 if hover == "top" else 1]
                QToolTip.showText(event.globalPosition().toPoint(), f"{label}: {_cm(value)}", self)
            else:
                QToolTip.hideText()
            return
        self._move(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        name = self._hit(event.position().y())
        if name is None:
            return
        self._drag = name
        self._drag_page = self.editor.current_page()
        self._values = self.editor.page_margins()
        self._move(event)

    def _move(self, event):
        page_top = self._page_top_scene()
        offset = self._to_scene_y(event.position().y()) - page_top  # sayfa üstünden uzaklık
        top, bottom = self.editor.page_margins()
        if self._drag == "top":
            value = offset
        else:
            value = self._page_height() - offset
        if not event.modifiers() & Qt.AltModifier:
            value = round(value / SNAP) * SNAP
        limit = self._page_height() - MIN_TEXT_HEIGHT
        if self._drag == "top":
            top = max(0.0, min(value, limit - bottom))
            guide, label = page_top + top, "Üst kenar boşluğu"
        else:
            bottom = max(0.0, min(value, limit - top))
            guide, label = page_top + self._page_height() - bottom, "Alt kenar boşluğu"
        self._values = (top, bottom)
        self.editor.set_horizontal_guide(guide)
        QToolTip.showText(event.globalPosition().toPoint(), f"{label}: {_cm(top if self._drag == 'top' else bottom)}", self)
        self.update()

    def mouseReleaseEvent(self, event):
        if self._drag is None:
            return
        values = self._values
        self._drag = self._drag_page = self._values = None
        self.editor.set_horizontal_guide(None)
        QToolTip.hideText()
        if values is not None:
            self.editor.set_page_margins(*values)
        self.editor.setFocus()
        self.update()

    def leaveEvent(self, _):
        if self._hover and self._drag is None:
            self._hover = None
            self.setCursor(Qt.ArrowCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(BACKGROUND))
        top_margin, bottom_margin = self._margins()
        page_top_scene = self._page_top_scene()
        page_top = self._to_widget(QPointF(0, page_top_scene)).y()
        page_bottom = self._to_widget(QPointF(0, page_top_scene + self._page_height())).y()
        text_top = self._to_widget(QPointF(0, page_top_scene + top_margin)).y()
        text_bottom = self._to_widget(QPointF(0, page_top_scene + self._page_height() - bottom_margin)).y()
        left, right = BAND_MARGIN, self.width() - BAND_MARGIN
        band = QRectF(left, page_top, right - left, page_bottom - page_top)

        p.fillRect(band, QColor(MARGIN_FILL))
        p.fillRect(QRectF(left, text_top, right - left, text_bottom - text_top), QColor(TEXT_FILL))
        p.setPen(QColor(BAND_BORDER))
        p.drawRect(band.adjusted(0, 0, -1, -1))

        unit = PX_PER_CM * self.editor.zoom()
        quarter = unit / 4
        middle = (left + right) / 2
        label_every = 1 if unit >= 22 else 2
        p.setFont(_label_font())
        p.setPen(QColor(TICK))
        first = math.floor((page_top - text_top) / quarter)
        last = math.ceil((page_bottom - text_top) / quarter)
        for k in range(first, last + 1):
            y = math.floor(text_top + k * quarter) + 0.5
            if y < max(page_top + 2, 0) or y > min(page_bottom - 2, self.height()):
                continue
            if k % 4 == 0:
                cm = abs(k // 4)
                if cm and cm % label_every == 0:
                    p.drawText(QRectF(left, y - 8, right - left, 16), Qt.AlignCenter, str(cm))
            elif k % 2 == 0:
                p.drawLine(QPointF(middle - 2.5, y), QPointF(middle + 2.5, y))
            elif quarter >= 4:
                p.drawLine(QPointF(middle - 1, y), QPointF(middle + 1, y))


class DocumentArea(QWidget):
    """Cetvelleri ve editörü Word düzeninde bir araya getirir."""

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(BACKGROUND))
        self.setPalette(palette)

        self.editor = editor
        self.corner = QWidget()
        self.corner.setFixedSize(SIZE, SIZE)
        self.horizontal = HorizontalRuler(editor)
        self.vertical = VerticalRuler(editor)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        grid.addWidget(self.corner, 0, 0)
        grid.addWidget(self.horizontal, 0, 1)
        grid.addWidget(self.vertical, 1, 0)
        grid.addWidget(editor, 1, 1)

    def set_rulers_visible(self, visible):
        for widget in (self.corner, self.horizontal, self.vertical):
            widget.setVisible(visible)
