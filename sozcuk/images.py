"""Belgedeki görseller: ekleme (dosya, pano, sürükle-bırak), seçme, tutamaklarla boyutlandırma, kırpma ve döndürme.

Görsel, belgede satır içi tek bir karakterdir (U+FFFC, QTextImageFormat). Seçildiğinde metin imleci o tek
karakteri seçer; böylece Sil, Kes, Kopyala, üzerine yazma ve Geri Al Qt'nin normal metin işlemleriyle çalışır.
Boyutlandırma, kırpma ve döndürme de karakter biçimini değiştirir, bu yüzden tek adımda geri alınabilir.

Word gibi hiçbir işlem özgün görseli bozmaz. Biçimde saklananlar:
    özgün görsel (ORIGINAL_NAME) → döndürme açısı (ROTATION) → döndürülmüş hal üzerinde kırpma (CROP_RECT)
Ekranda görünen görsel bu zincirden üretilir; bu yüzden döndürülmüş görsel yeniden kırpılabilir, kırpma
geri alınabilir, açı değiştirilebilir. (QTextDocument görsel döndüremez; döndürme piksellere uygulanır.)

Ölçüldü: görselin sahnedeki dikdörtgeni satırın taban çizgisine oturan (ascent = yükseklik) konumdur;
tahmin edilen dikdörtgen çizilen piksellerle birebir aynı çıktı.
"""

import math
import uuid

from PySide6.QtCore import QPointF, QRectF, QSizeF, QUrl, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QPen,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextImageFormat,
    QTransform,
)

from . import styles

ORIGINAL_NAME = QTextFormat.UserProperty + 10   # dokunulmamış özgün görselin kaynak adı
CROP_RECT = QTextFormat.UserProperty + 11       # döndürülmüş görsel üzerinde kırpma dikdörtgeni (piksel)
ROTATION = QTextFormat.UserProperty + 12        # derece, saat yönünde

MAX_SOURCE_SIDE = 2400   # eklenen görselin en uzun kenarı (baskıda ~200 dpi); belge dosyası şişmesin
MIN_SIZE = 16
HANDLE = 8               # tutamak boyutu (ekran pikseli)
ROTATE_OFFSET = 24       # döndürme tutamağının görselin üstüne uzaklığı (ekran pikseli)
ROTATE_SNAP = 15         # Shift ile döndürme adımı (derece)
IMAGE_FILTER = "Görseller (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff)"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff")

# tutamak adı -> (x, y) çarpanları: 0 sol/üst, 0.5 orta, 1 sağ/alt
HANDLES = {
    "tl": (0, 0), "t": (0.5, 0), "tr": (1, 0), "r": (1, 0.5),
    "br": (1, 1), "b": (0.5, 1), "bl": (0, 1), "l": (0, 0.5),
}
CURSORS = {
    "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor, "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor,
    "t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor, "l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor,
    "rotate": Qt.PointingHandCursor,
}


# =============================================================================
# Görsel hesapları
# =============================================================================

def prepare_image(image):
    """Çok büyük görselleri makul boyuta indirir (fotoğraflar belgeyi onlarca MB yapmasın)."""
    if image.isNull():
        return image
    if max(image.width(), image.height()) > MAX_SOURCE_SIDE:
        image = image.scaled(MAX_SOURCE_SIDE, MAX_SOURCE_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return image


def local_image_files(mime):
    """Panodaki/sürüklenen verideki yerel görsel dosyalarının yolları."""
    if mime is None or not mime.hasUrls():
        return []
    return [url.toLocalFile() for url in mime.urls()
            if url.isLocalFile() and url.toLocalFile().lower().endswith(IMAGE_SUFFIXES)]


def normalize_angle(angle):
    angle = round(float(angle), 2) % 360
    return 0.0 if abs(angle) < 0.01 or abs(angle - 360) < 0.01 else angle


_rotation_cache = {}


def rotated(image, angle, key=None):
    """Görseli saat yönünde döndürür; 90'ın katlarında kayıpsız, diğer açılarda köşeler saydam."""
    angle = normalize_angle(angle)
    if angle == 0 or image.isNull():
        return image
    cache_key = (key, angle) if key else None
    if cache_key in _rotation_cache:
        return _rotation_cache[cache_key]
    transform = QTransform().rotate(angle)
    if angle in (90.0, 180.0, 270.0):
        result = image.transformed(transform)
    else:
        result = image.convertToFormat(QImage.Format_ARGB32_Premultiplied).transformed(
            transform, Qt.SmoothTransformation)
    if cache_key:
        if len(_rotation_cache) > 16:
            _rotation_cache.pop(next(iter(_rotation_cache)))
        _rotation_cache[cache_key] = result
    return result


def rotate_rect(rect, from_size, to_size, delta):
    """Bir görsel üzerindeki dikdörtgenin, görsel delta derece döndürüldükten sonraki kapsayan dikdörtgeni."""
    transform = QTransform().rotate(delta)
    from_center = QPointF(from_size.width() / 2, from_size.height() / 2)
    to_center = QPointF(to_size.width() / 2, to_size.height() / 2)
    corners = [transform.map(corner - from_center) + to_center
               for corner in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight())]
    xs, ys = [p.x() for p in corners], [p.y() for p in corners]
    result = QRectF(QPointF(min(xs), min(ys)), QPointF(max(xs), max(ys)))
    return result.intersected(QRectF(QPointF(0, 0), to_size))


def text_area(document):
    """Sayfadaki yazı alanının genişlik ve yüksekliği (px)."""
    top, bottom = styles.page_margins(document)
    return styles.text_width(document), styles.page_size(document)[1] - top - bottom


def fit_size(width, height, document, limit_height=1.0):
    max_width, max_height = text_area(document)
    scale = min(1.0, max_width / width, max_height * limit_height / height)
    return width * scale, height * scale


# =============================================================================
# Belge yardımcıları
# =============================================================================

def add_resource(document, image):
    name = f"sozcuk-img-{uuid.uuid4().hex}"
    document.addResource(QTextDocument.ImageResource, QUrl(name), image)
    return name


def resource_image(document, name):
    resource = document.resource(QTextDocument.ImageResource, QUrl(name))
    if isinstance(resource, QImage):
        return resource
    return QImage(resource) if resource is not None else QImage()


def insert_image(cursor, image):
    """Görseli imleç konumuna ekler; yazı alanına sığacak şekilde gösterim boyutu ayarlanır."""
    image = prepare_image(image)
    if image.isNull():
        return False
    document = cursor.document()
    name = add_resource(document, image)
    width, height = fit_size(image.width(), image.height(), document, limit_height=0.9)
    fmt = QTextImageFormat()
    fmt.setName(name)
    fmt.setWidth(round(width, 2))
    fmt.setHeight(round(height, 2))
    fmt.setProperty(ORIGINAL_NAME, name)
    fmt.setProperty(ROTATION, 0.0)
    fmt.setProperty(CROP_RECT, QRectF(0, 0, image.width(), image.height()))
    cursor.insertImage(fmt)
    return True


def image_format_at(document, position):
    if position < 0 or position >= document.characterCount() - 1:
        return None
    cursor = QTextCursor(document)
    cursor.setPosition(position)
    cursor.setPosition(position + 1, QTextCursor.KeepAnchor)
    fmt = cursor.charFormat()
    return fmt.toImageFormat() if fmt.isImageFormat() else None


def image_rect(document, position, fmt):
    """Görselin sahnedeki dikdörtgeni (satır içi görsel taban çizgisine oturur)."""
    block = document.findBlock(position)
    layout = block.layout()
    if layout is None or layout.lineCount() == 0:
        return QRectF()
    relative = position - block.position()
    line = layout.lineForTextPosition(relative)
    if not line.isValid():
        return QRectF()
    x = line.cursorToX(relative)
    x = x[0] if isinstance(x, tuple) else x
    origin = document.documentLayout().blockBoundingRect(block).topLeft()
    width, height = fmt.width(), fmt.height()
    return QRectF(origin.x() + x, origin.y() + line.y() + line.ascent() - height, width, height)


class Source:
    """Görselin işlem zinciri: özgün → döndürülmüş (base) → kırpılmış (ekranda görünen)."""

    def __init__(self, document, fmt):
        self.original_name = fmt.property(ORIGINAL_NAME) or fmt.name()
        self.original = resource_image(document, self.original_name)
        if self.original.isNull():  # eski/içe aktarılmış görsel: mevcut görsel özgündür
            self.original_name = fmt.name()
            self.original = resource_image(document, fmt.name())
        rotation = fmt.property(ROTATION)
        self.angle = normalize_angle(rotation) if isinstance(rotation, (int, float)) else 0.0
        self.base = rotated(self.original, self.angle, self.original_name)
        crop = fmt.property(CROP_RECT)
        full = QRectF(0, 0, self.base.width(), self.base.height())
        self.crop = crop.intersected(full) if isinstance(crop, QRectF) and not crop.isEmpty() else full
        self.full = full

    @property
    def is_cropped(self):
        return self.crop.toAlignedRect() != self.full.toAlignedRect()

    def display_scale(self, fmt):
        """Ekran pikseli / kırpılmış görsel pikseli."""
        return fmt.width() / self.crop.width() if self.crop.width() else 1.0

    def render(self, document):
        """Kırpılmış (ve döndürülmüş) görseli belge kaynağı olarak ekler; kaynak adını döndürür."""
        if self.angle == 0 and not self.is_cropped:
            return self.original_name
        pixels = self.crop.toAlignedRect().intersected(self.base.rect())
        return add_resource(document, self.base.copy(pixels))

    def apply_to(self, fmt, document, width, height):
        fmt.setName(self.render(document))
        fmt.setProperty(ORIGINAL_NAME, self.original_name)
        fmt.setProperty(ROTATION, self.angle)
        fmt.setProperty(CROP_RECT, QRectF(self.crop))
        fmt.setWidth(round(width, 2))
        fmt.setHeight(round(height, 2))
        return fmt


# =============================================================================
# Etkileşim
# =============================================================================

class ImageTool:
    """Editörün görsel seçme/boyutlandırma/kırpma/döndürme davranışı. Editor fare ve klavye olaylarını iletir."""

    def __init__(self, editor):
        self.editor = editor
        self.position = None     # seçili görselin belge konumu (izleyen imleç)
        self.crop_mode = False
        self._drag = None        # sürüklenen tutamak
        self._drag_start = None  # (sahne noktası, başlangıç dikdörtgeni)
        self._preview = None     # sürüklerken yeni dikdörtgen (sahne)
        self._full_rect = None   # kırpma modunda döndürülmüş görselin tamamının sahnedeki yeri
        self._rotation = None    # fareyle döndürürken önizleme açısı (derece)

    @property
    def document(self):
        return self.editor.document()

    # --- seçim ---------------------------------------------------------------

    def selected(self):
        """(konum, biçim) — seçili görsel yoksa None."""
        if self.position is None:
            return None
        position = self.position.position()
        fmt = image_format_at(self.document, position)
        if fmt is None:
            self.deselect()
            return None
        return position, fmt

    def select(self, position):
        cursor = QTextCursor(self.document)
        cursor.setPosition(position)
        self.position = cursor
        # metin imleci görsel karakterini seçer: Sil / Kes / Kopyala / üzerine yazma kendiliğinden çalışır
        selection = QTextCursor(self.document)
        selection.setPosition(position)
        selection.setPosition(position + 1, QTextCursor.KeepAnchor)
        self.editor.text.setTextCursor(selection)
        self.editor.notify()
        self.crop_mode = False
        self._preview = self._full_rect = self._rotation = None
        self._update()

    def deselect(self):
        if self.position is None and not self.crop_mode:
            return
        self.position = None
        self.crop_mode = False
        self._drag = self._preview = self._full_rect = self._rotation = None
        self.editor.text.setCursor(Qt.IBeamCursor)
        self._update()

    def sync_with_cursor(self):
        """Metin imleci görseli seçmekten çıktıysa (klavye, tıklama) görsel seçimini bırak."""
        current = self.selected()
        if current is None:
            return
        cursor = self.editor.textCursor()
        position = current[0]
        if not (cursor.selectionStart() == position and cursor.selectionEnd() == position + 1):
            if self.crop_mode:
                self.apply_crop()
            self.deselect()

    def image_under(self, scene_point):
        """Sahne noktasındaki görselin konumu (yoksa None)."""
        hit = self.document.documentLayout().hitTest(scene_point, Qt.FuzzyHit)
        for position in (hit, hit - 1):
            fmt = image_format_at(self.document, position)
            if fmt is not None and image_rect(self.document, position, fmt).contains(scene_point):
                return position
        return None

    def current_rect(self):
        current = self.selected()
        return image_rect(self.document, *current) if current else QRectF()

    # --- tutamaklar ------------------------------------------------------------

    def _zoom(self):
        return max(self.editor.zoom(), 0.01)

    def _handle_rects(self, rect):
        size = HANDLE / self._zoom()  # ekranda sabit boyut
        return {name: QRectF(rect.x() + fx * rect.width() - size / 2, rect.y() + fy * rect.height() - size / 2,
                             size, size)
                for name, (fx, fy) in HANDLES.items()}

    def _rotate_handle_center(self, rect):
        return QPointF(rect.center().x(), rect.top() - ROTATE_OFFSET / self._zoom())

    def handle_at(self, scene_point):
        rect = self._preview or self.current_rect()
        if rect.isEmpty():
            return None
        grow = HANDLE / self._zoom() * 0.5
        if not self.crop_mode:
            center = self._rotate_handle_center(rect)
            if math.hypot(scene_point.x() - center.x(), scene_point.y() - center.y()) <= HANDLE / self._zoom():
                return "rotate"
        for name, handle in self._handle_rects(rect).items():
            if handle.adjusted(-grow, -grow, grow, grow).contains(scene_point):
                return name
        return None

    # --- fare ----------------------------------------------------------------

    def mouse_press(self, scene_point, button, modifiers):
        """Olay işlendiyse True (metin öğesine iletilmez)."""
        if button != Qt.LeftButton:
            under = self.image_under(scene_point)
            if under is not None and (self.selected() is None or self.selected()[0] != under):
                self.select(under)  # sağ tık: önce görseli seç, menü görsele göre açılsın
            return False
        if self.selected() is not None:
            handle = self.handle_at(scene_point)
            if handle is not None:
                rect = self._preview if (self.crop_mode and self._preview) else self.current_rect()
                self._drag = handle
                self._drag_start = (scene_point, QRectF(rect))
                return True
            if self.crop_mode and self._full_rect is not None and self._full_rect.contains(scene_point):
                return True  # kırpma modunda görselin üzerine tıklamak modu bozmasın
        under = self.image_under(scene_point)
        if under is not None:
            if self.crop_mode:
                self.apply_crop()
            self.select(under)
            return True
        if self.crop_mode:
            self.apply_crop()
        self.deselect()
        return False

    def mouse_move(self, scene_point, modifiers):
        if self._drag is None:
            handle = self.handle_at(scene_point) if self.selected() is not None else None
            self.editor.text.setCursor(CURSORS[handle] if handle else Qt.IBeamCursor)
            return False
        start_point, start = self._drag_start
        if self._drag == "rotate":
            center = start.center()
            angle = math.degrees(math.atan2(scene_point.y() - center.y(), scene_point.x() - center.x())
                                 - math.atan2(start_point.y() - center.y(), start_point.x() - center.x()))
            if modifiers & Qt.ShiftModifier:
                angle = round(angle / ROTATE_SNAP) * ROTATE_SNAP
            self._rotation = normalize_angle(angle)
            self._update()
            return True

        dx, dy = scene_point.x() - start_point.x(), scene_point.y() - start_point.y()
        rect = QRectF(start)
        if "l" in self._drag:
            rect.setLeft(min(start.left() + dx, start.right() - MIN_SIZE))
        if "r" in self._drag:
            rect.setRight(max(start.right() + dx, start.left() + MIN_SIZE))
        if "t" in self._drag:
            rect.setTop(min(start.top() + dy, start.bottom() - MIN_SIZE))
        if "b" in self._drag:
            rect.setBottom(max(start.bottom() + dy, start.top() + MIN_SIZE))

        if self.crop_mode:
            rect = rect.intersected(self._full_rect)  # kırpma görselin dışına taşamaz
        else:
            if len(self._drag) == 2 and not modifiers & Qt.ShiftModifier:
                rect = self._keep_aspect(rect, start)
            max_width, max_height = text_area(self.document)
            rect.setWidth(min(rect.width(), max_width))
            rect.setHeight(min(rect.height(), max_height))
        self._preview = rect
        self._update()
        return True

    def _keep_aspect(self, rect, start):
        """Köşeden boyutlandırmada en-boy oranını koru (Word gibi; Shift ile serbest)."""
        # fare konumunun köşegen üzerindeki izdüşümü: yatay ve dikey hareket birlikte hesaba katılır
        scale = ((rect.width() * start.width() + rect.height() * start.height())
                 / (start.width() ** 2 + start.height() ** 2))
        width = max(MIN_SIZE, start.width() * scale)
        height = width * start.height() / start.width()
        result = QRectF(rect)
        if "l" in self._drag:
            result.setLeft(start.right() - width)
        else:
            result.setRight(start.left() + width)
        if "t" in self._drag:
            result.setTop(start.bottom() - height)
        else:
            result.setBottom(start.top() + height)
        return result

    def mouse_release(self):
        if self._drag is None:
            return False
        drag, self._drag = self._drag, None
        if drag == "rotate":
            angle, self._rotation = self._rotation, None
            if angle:
                self.rotate_by(angle)
            self._update()
            return True
        if self.crop_mode:
            return True  # kırpma, mod kapatılınca uygulanır (Enter, dışarı tıklama, "Kırp")
        if self._preview is not None:
            preview, self._preview = self._preview, None
            self.resize(preview.width(), preview.height())
        self._update()
        return True

    # --- işlemler ------------------------------------------------------------

    def _set_format(self, position, fmt):
        cursor = QTextCursor(self.document)
        cursor.setPosition(position)
        cursor.setPosition(position + 1, QTextCursor.KeepAnchor)
        cursor.setCharFormat(fmt)  # geri alınabilir tek adım
        self.select(position)

    def resize(self, width, height):
        current = self.selected()
        if current is None:
            return
        position, fmt = current
        fmt.setWidth(round(width, 2))
        fmt.setHeight(round(height, 2))
        self._set_format(position, fmt)

    def reset_size(self):
        """Görseli kendi piksel boyutuna (yazı alanına sığacak kadar) döndürür."""
        current = self.selected()
        if current is None:
            return
        position, fmt = current
        source = Source(self.document, fmt)
        self.resize(*fit_size(source.crop.width(), source.crop.height(), self.document))

    def rotate_by(self, delta):
        """Görseli saat yönünde delta derece döndürür (eksi: saat yönünün tersine)."""
        current = self.selected()
        if current is None:
            return
        position, fmt = current
        source = Source(self.document, fmt)
        scale = source.display_scale(fmt)
        old_size = QSizeF(source.base.width(), source.base.height())
        source.angle = normalize_angle(source.angle + delta)
        source.base = rotated(source.original, source.angle, source.original_name)
        new_size = QSizeF(source.base.width(), source.base.height())
        source.crop = rotate_rect(source.crop, old_size, new_size, delta)
        source.full = QRectF(QPointF(0, 0), new_size)
        width, height = source.crop.width() * scale, source.crop.height() * scale
        max_width, max_height = text_area(self.document)
        shrink = min(1.0, max_width / width, max_height / height)
        self._set_format(position, source.apply_to(fmt, self.document, width * shrink, height * shrink))

    def reset_rotation(self):
        current = self.selected()
        if current is None:
            return
        angle = Source(self.document, current[1]).angle
        if angle:
            self.rotate_by(-angle)

    def rotation(self):
        current = self.selected()
        return Source(self.document, current[1]).angle if current else 0.0

    def is_cropped(self):
        current = self.selected()
        return bool(current) and Source(self.document, current[1]).is_cropped

    def start_crop(self):
        current = self.selected()
        if current is None:
            return
        position, fmt = current
        source = Source(self.document, fmt)
        rect = image_rect(self.document, position, fmt)
        scale_x, scale_y = rect.width() / source.crop.width(), rect.height() / source.crop.height()
        self._full_rect = QRectF(rect.x() - source.crop.x() * scale_x, rect.y() - source.crop.y() * scale_y,
                                 source.base.width() * scale_x, source.base.height() * scale_y)
        self._preview = QRectF(rect)
        self.crop_mode = True
        self._update()

    def cancel_crop(self):
        self.crop_mode = False
        self._preview = self._full_rect = None
        self._update()

    def apply_crop(self):
        if not self.crop_mode:
            return
        current = self.selected()
        box, full = self._preview, self._full_rect
        self.crop_mode = False
        self._preview = self._full_rect = None
        if current is None or box is None or full is None:
            self._update()
            return
        position, fmt = current
        source = Source(self.document, fmt)
        scale_x, scale_y = full.width() / source.base.width(), full.height() / source.base.height()
        crop = QRectF((box.x() - full.x()) / scale_x, (box.y() - full.y()) / scale_y,
                      box.width() / scale_x, box.height() / scale_y).intersected(source.full)
        if crop.toAlignedRect().isEmpty():
            self._update()
            return
        source.crop = QRectF(crop.toAlignedRect())
        self._set_format(position, source.apply_to(fmt, self.document, box.width(), box.height()))

    def reset_crop(self):
        current = self.selected()
        if current is None:
            return
        position, fmt = current
        source = Source(self.document, fmt)
        scale = source.display_scale(fmt)
        source.crop = QRectF(source.full)
        width, height = fit_size(source.full.width() * scale, source.full.height() * scale, self.document)
        self._set_format(position, source.apply_to(fmt, self.document, width, height))

    # --- klavye --------------------------------------------------------------

    def key_press(self, event):
        if self.crop_mode:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.apply_crop()
                return True
            if event.key() == Qt.Key_Escape:
                self.cancel_crop()
                return True
        elif self.selected() is not None and event.key() == Qt.Key_Escape:
            cursor = self.editor.textCursor()
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)
            self.deselect()
            return True
        return False

    # --- çizim ---------------------------------------------------------------

    def _update(self):
        self.editor.viewport().update()

    def paint_unhighlighted(self, painter):
        """Seçili görseli metin seçimi renginin üstüne yeniden çizer (Word'de seçili görsel mavileşmez).
        Görsel seçimi aslında metin imlecinin seçtiği U+FFFC karakteridir; Qt onu seçim rengiyle boyar."""
        current = self.selected()
        if current is None or self.crop_mode:
            return
        position, fmt = current
        rect = image_rect(self.document, position, fmt)
        block = self.document.findBlock(position)
        line = block.layout().lineForTextPosition(position - block.position())
        top = self.document.documentLayout().blockBoundingRect(block).y() + line.y()
        cover = QRectF(rect.x(), min(rect.y(), top), rect.width(), max(rect.bottom(), top + line.height()) - min(rect.y(), top))
        painter.fillRect(cover, QColor("#ffffff"))
        painter.drawImage(rect, resource_image(self.document, fmt.name()))

    def paint(self, painter):
        current = self.selected()
        if current is None:
            return
        position, fmt = current
        rect = self._preview or image_rect(self.document, position, fmt)
        zoom = self._zoom()
        painter.save()
        if self.crop_mode and self._full_rect is not None:
            self._paint_crop(painter, Source(self.document, fmt), rect, zoom)
        elif self._rotation is not None:
            self._paint_rotation(painter, fmt, rect, zoom)
        else:
            if self._preview is not None:
                painter.setOpacity(0.55)
                painter.drawImage(rect, resource_image(self.document, fmt.name()))
                painter.setOpacity(1.0)
            accent = QColor("#185abd")
            painter.setPen(QPen(accent, 1 / zoom))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
            # döndürme tutamağı: görselin üstünde, çizgiyle bağlı yuvarlak
            center = self._rotate_handle_center(rect)
            painter.drawLine(QPointF(rect.center().x(), rect.top()), center)
            # dairesel ok: yarıçapı r olan 280°'lik yay ve ucunda küçük ok başı
            radius = HANDLE / zoom * 0.8
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, radius + 2 / zoom, radius + 2 / zoom)
            painter.setPen(QPen(accent, 1.5 / zoom))
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius), 60 * 16, 280 * 16)
            tip = QPointF(center.x() + radius * math.cos(math.radians(60)), center.y() - radius * math.sin(math.radians(60)))
            arrow = 3.5 / zoom
            painter.setPen(Qt.NoPen)
            painter.setBrush(accent)
            painter.drawPolygon([tip + QPointF(-arrow, -arrow * 0.6), tip + QPointF(arrow * 0.7, -arrow * 0.9),
                                 tip + QPointF(0, arrow)])
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(QPen(accent, 1 / zoom))
            for handle in self._handle_rects(rect).values():
                painter.drawRect(handle)
        painter.restore()

    def _paint_rotation(self, painter, fmt, rect, zoom):
        center = rect.center()
        painter.translate(center)
        painter.rotate(self._rotation)
        local = QRectF(-rect.width() / 2, -rect.height() / 2, rect.width(), rect.height())
        painter.setOpacity(0.6)
        painter.drawImage(local, resource_image(self.document, fmt.name()))
        painter.setOpacity(1.0)
        painter.setPen(QPen(QColor("#185abd"), 1 / zoom, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(local)
        painter.resetTransform()

    def _paint_crop(self, painter, source, rect, zoom):
        full = self._full_rect
        base = source.base
        painter.setOpacity(0.35)  # kırpılan alan soluk
        painter.drawImage(full, base)
        painter.setOpacity(1.0)
        piece = QRectF((rect.x() - full.x()) * base.width() / full.width(),
                       (rect.y() - full.y()) * base.height() / full.height(),
                       rect.width() * base.width() / full.width(),
                       rect.height() * base.height() / full.height())
        painter.fillRect(rect, QColor("#ffffff"))
        painter.drawImage(rect, base, piece)
        painter.setPen(QPen(QColor("#1f1f1f"), 1.5 / zoom))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)
        # Word'deki gibi kalın siyah L ve çizgi biçimli kırpma tutamakları
        length, width = 14 / zoom, 4 / zoom
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1f1f1f"))
        x0, y0, x1, y1 = rect.left(), rect.top(), rect.right(), rect.bottom()
        cx, cy = rect.center().x(), rect.center().y()
        for x, y, w, h in [
            (x0, y0, length, width), (x0, y0, width, length),
            (x1 - length, y0, length, width), (x1 - width, y0, width, length),
            (x0, y1 - width, length, width), (x0, y1 - length, width, length),
            (x1 - length, y1 - width, length, width), (x1 - width, y1 - length, width, length),
            (cx - length / 2, y0, length, width), (cx - length / 2, y1 - width, length, width),
            (x0, cy - length / 2, width, length), (x1 - width, cy - length / 2, width, length),
        ]:
            painter.drawRect(QRectF(x, y, w, h))
