"""Sekmeli şerit (Tabcel `ui/serit.py`'den uyarlandı; tasarım: Tabcel `faz5j_tasarim.md` §3): sekme satırı + sayfalar, sayfalarda gruplar.

Şerit yalnız yerleşimdir: düğmeler `QAction`'ı `setDefaultAction` ile kullanır (metin/ikon/ipucu/
etkinlik/işaret durumu eylemden gelir); komut mantığı pencerede kalır. Tüm düğmeler `Qt.NoFocus`:
düzenleme/formül çubuğu odağı çalınmaz.

Dar pencerede gruplar öncelik sırasıyla küçülür (`daralma_plani`, Qt'siz): durum 0 tam, durum 1
küçük düğmeler yazısız, durum 2 grup tek açılır düğmeye iner (içerik açılır çerçeveye taşınır).
"""
from typing import Callable, Iterable, List, Optional, Sequence

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLayout, QMenu, QStackedWidget, QTabBar, QToolButton, QVBoxLayout, QWidget,
    QWidgetAction,
)

from . import icons, theme

SAYFA_YUKSEKLIGI = 92
BUYUK_IKON = 32
KUCUK_IKON = 20


# ---------------------------------------------------------------------- daralma planı (Qt'siz)
def daralma_plani(genislikler: Sequence[Sequence[Optional[int]]], oncelikler: Sequence[int],
                  kullanilabilir: int) -> List[int]:
    """Her grubun durumunu (0 tam, 1 yazısız küçük düğmeler, 2 tek açılır düğme) belirler.

    `genislikler[i]` = grubun [durum 0, durum 1, durum 2] genişliği; durum 1 yoksa (yazılı küçük
    düğmesi yok) `None`. Aşamalıdır: önce, sığana dek, durum 1'i olan gruplar EN DÜŞÜK öncelikliden
    başlayarak durum 1'e iner (az kayıp); durum 1 yapacak grup kalmadıysa gruplar yine en düşük
    öncelikliden durum 2'ye iner. Eşit öncelikte SAĞDAKİ önce (Excel sağdan sola daraltır). Hepsi 2
    iken de sığmazsa olduğu gibi döner (sayfa kırpılır)."""
    n = len(genislikler)
    durum = [0] * n

    def toplam() -> int:
        return sum(genislikler[i][durum[i]] for i in range(n))

    while toplam() > kullanilabilir:
        adaylar = [i for i in range(n) if durum[i] == 0 and genislikler[i][1] is not None]
        if adaylar:
            i = min(adaylar, key=lambda k: (oncelikler[k], -k))
            durum[i] = 1
            continue
        adaylar = [i for i in range(n) if durum[i] < 2]
        if not adaylar:
            break
        i = min(adaylar, key=lambda k: (oncelikler[k], -k))
        durum[i] = 2
    return durum


# ---------------------------------------------------------------------- düğme yardımcıları
def dugme(eylem: Optional[QAction], buyuk: bool, menu: Optional[QMenu] = None,
           ikon: Optional[str] = None, metin: Optional[str] = None,
           ana_islem: bool = False) -> QToolButton:
    d = QToolButton()
    d.setObjectName("seritDugme")
    d.setFocusPolicy(Qt.NoFocus)
    if eylem is not None:
        d.setDefaultAction(eylem)
    if ikon is not None:
        d.setIcon(icons.icon(ikon))
        d.setProperty("ikonAdi", ikon)                     # Hızlı Erişim'e eklenirken beyaz simge için
    if metin is not None:
        d.setText(metin)
    d.setAutoRaise(True)
    if buyuk:
        d.setIconSize(QSize(BUYUK_IKON, BUYUK_IKON))
        d.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    else:
        d.setIconSize(QSize(KUCUK_IKON, KUCUK_IKON))
        d.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if menu is not None:
        d.setMenu(menu)
        d.setPopupMode(QToolButton.MenuButtonPopup if ana_islem else QToolButton.InstantPopup)
    return d


def ikon_dugmesi(eylem: QAction) -> QToolButton:
    """Yalnız ikonlu küçük düğme (satır içi kullanım: kalın, italik…)."""
    d = dugme(eylem, False)
    d.setToolButtonStyle(Qt.ToolButtonIconOnly)
    return d


class _Acilir(QFrame):
    """Durum 2'de grup içeriğinin açıldığı çerçeve; kapanınca içeriği gruba geri verir."""

    def __init__(self, geri_ver: Callable[[], None]):
        super().__init__(None, Qt.Popup)
        self.setObjectName("seritAcilir")
        self.setStyleSheet(theme.serit_stil())      # Qt.Popup üst pencerenin stil sayfasını almaz
        self._geri_ver = geri_ver
        self._d = QHBoxLayout(self)
        self._d.setContentsMargins(6, 6, 6, 6)

    def doldur(self, w: QWidget) -> None:
        self._d.addWidget(w)
        w.show()

    def hideEvent(self, olay):
        super().hideEvent(olay)
        self._geri_ver()


class SeritGrubu(QWidget):
    """Başlıklı düğme grubu. `buyuk` / `kucukler` / `satirlar` içerik ekler (soldan sağa sütunlar)."""

    def __init__(self, ad: str, oncelik: int = 5, ikon: Optional[str] = None):
        super().__init__()
        self.ad = ad
        self.oncelik = oncelik
        self._ikon = ikon
        self._durum = 0
        self._kucuk: List[QToolButton] = []
        self._kolonlar: List = []                 # iç düzenler: ölçü almadan önce elle geçersiz kılınır
        self._yazili_kucuk = False
        self._genislik: Optional[List[Optional[int]]] = None
        self._acilir: Optional[_Acilir] = None
        self.setObjectName("seritGrubu")

        ana = QVBoxLayout(self)
        ana.setContentsMargins(3, 2, 3, 0)
        ana.setSpacing(0)
        self._icerik = QWidget()
        self._d = QHBoxLayout(self._icerik)
        self._d.setContentsMargins(0, 0, 0, 0)
        self._d.setSpacing(2)
        self._ana = ana
        ana.addWidget(self._icerik, 1)
        self._ozet = dugme(None, True, ikon=ikon or "chevron_down", metin=ad)
        self._ozet.setObjectName("seritOzet")
        g = icons.ICONS.get(ikon or "chevron_down", {}).get("grid", icons.GRID)
        self._ozet.setIconSize(QSize(g, g))             # 20'lik ikon 32'ye büyütülmez (bulanır)
        self._ozet.clicked.connect(self._acilirda_ac)
        self._ozet.hide()
        ana.addWidget(self._ozet, 1)

        alt = QHBoxLayout()
        alt.setContentsMargins(0, 0, 0, 0)
        self.baslik = QLabel(ad)
        self.baslik.setObjectName("seritGrupAdi")
        self.baslik.setAlignment(Qt.AlignCenter)
        alt.addWidget(self.baslik, 1)
        self.baslatici: Optional[QToolButton] = None
        self._alt = alt
        ana.addLayout(alt)

    # ------------------------------------------------------------------ içerik
    def buyuk(self, eylem: Optional[QAction] = None, menu: Optional[QMenu] = None,
              ikon: Optional[str] = None, metin: Optional[str] = None,
              ana_islem: bool = False) -> QToolButton:
        d = dugme(eylem, True, menu, ikon, metin, ana_islem)
        self._d.addWidget(d)
        self._genislik = None
        return d

    def kucukler(self, ogeler: Iterable) -> List[QToolButton]:
        """Üst üste küçük düğmeler (bir sütun). Öğe: `QAction` ya da (eylem, menü) çifti."""
        s = QVBoxLayout()
        s.setSpacing(0)
        s.setContentsMargins(0, 0, 0, 0)
        liste = []
        for o in ogeler:
            if isinstance(o, QToolButton):               # hazır düğme (ör. biçim boyacısı): yazılı küçük düğme gibi davranır
                d = o
                d.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            else:
                eylem, menu = o if isinstance(o, tuple) else (o, None)
                d = dugme(eylem, False, menu)
            s.addWidget(d)
            self._kucuk.append(d)
            liste.append(d)
        s.addStretch(1)
        self._d.addLayout(s)
        self._kolonlar.append(s)
        self._yazili_kucuk = True
        self._genislik = None
        return liste

    def satirlar(self, satirlar: Iterable[Iterable[QWidget]]) -> None:
        """Serbest widget'lı satırlar (yazı tipi kutusu gibi): bir sütun, her satır yatay dizilir."""
        s = QVBoxLayout()
        s.setSpacing(2)
        s.setContentsMargins(0, 0, 0, 0)
        for satir in satirlar:
            h = QHBoxLayout()
            h.setSpacing(2)
            h.setContentsMargins(0, 0, 0, 0)
            for w in satir:
                h.addWidget(w)
            h.addStretch(1)
            s.addLayout(h)
        s.addStretch(1)
        self._d.addLayout(s)
        self._kolonlar.append(s)
        self._genislik = None

    def baslatici_ekle(self, eylem_ya_da_islev, ipucu: str = "") -> QToolButton:
        """Sağ alttaki ↘ pencere başlatıcı."""
        d = QToolButton()
        d.setObjectName("seritBaslatici")
        d.setFocusPolicy(Qt.NoFocus)
        d.setAutoRaise(True)
        d.setIcon(icons.icon("dialog_launcher"))
        d.setIconSize(QSize(12, 12))
        d.setFixedSize(16, 16)
        d.setToolTip(ipucu)
        d.clicked.connect(lambda _=False: eylem_ya_da_islev())
        self._alt.addWidget(d)
        self.baslatici = d
        return d

    # ------------------------------------------------------------------ durum / ölçü
    @property
    def durum(self) -> int:
        return self._durum

    def durum_ayarla(self, durum: int) -> None:
        if durum == 1 and not self._yazili_kucuk:
            durum = 2
        if durum == self._durum:
            return
        if self._durum == 2:
            self._icerigi_geri_al()
        self._durum = durum
        stil = Qt.ToolButtonIconOnly if durum == 1 else Qt.ToolButtonTextBesideIcon
        for d in self._kucuk:
            d.setToolButtonStyle(stil)
        self._icerik.setVisible(durum != 2)
        self._ozet.setVisible(durum == 2)
        self.updateGeometry()

    def genislikler(self) -> List[Optional[int]]:
        """[durum 0, durum 1, durum 2] genişlikleri (önbellekli; içerik eklenince/yazı tipi değişince
        `genislik_sifirla`)."""
        if self._genislik is None:
            self.ensurePolished()                  # stil sayfası uygulanmadan ölçülürse genişlikler eksik çıkar
            for w in self.findChildren(QWidget):
                w.ensurePolished()
            eski = self._durum
            olc: List[Optional[int]] = []
            for d in (0, 1, 2):
                if d == 1 and not self._yazili_kucuk:
                    olc.append(None)
                    continue
                self.durum_ayarla(d)
                for k in self._kolonlar:
                    k.invalidate()
                self._d.invalidate()
                self._icerik.updateGeometry()          # ana düzendeki öğe önbelleği (olay beklenmeden)
                self.layout().invalidate()
                self.layout().activate()
                olc.append(self.sizeHint().width())
            self.durum_ayarla(eski)
            self._genislik = olc
        return self._genislik

    def genislik_sifirla(self) -> None:
        self._genislik = None

    # ------------------------------------------------------------------ durum 2: açılır çerçeve
    def _acilirda_ac(self) -> None:
        if self._acilir is not None:
            return
        self._acilir = _Acilir(self._icerigi_geri_al)
        self._ana.removeWidget(self._icerik)
        self._acilir.doldur(self._icerik)
        self._acilir.move(self._ozet.mapToGlobal(QPoint(0, self._ozet.height())))
        self._acilir.show()

    def _icerigi_geri_al(self) -> None:
        a, self._acilir = self._acilir, None
        if a is None:
            return
        a._d.removeWidget(self._icerik)
        self._ana.insertWidget(0, self._icerik, 1)
        self._icerik.setVisible(self._durum != 2)
        a.deleteLater()


class SeritSayfasi(QWidget):
    """Bir sekmenin sayfası: gruplar yatay dizilir, aralarda 1 px dikey çizgi."""

    def __init__(self):
        super().__init__()
        self.setObjectName("seritSayfasi")
        self.gruplar: List[SeritGrubu] = []
        self._ayirac: List[QFrame] = []
        self._d = QHBoxLayout(self)
        self._d.setContentsMargins(4, 2, 4, 2)
        self._d.setSpacing(0)
        self._d.setSizeConstraint(QLayout.SetNoConstraint)     # pencere gruplara değil, gruplar pencereye uyar
        self._d.addStretch(1)
        self._duzenleniyor = False
        self.setFixedHeight(SAYFA_YUKSEKLIGI)

    def grup_ekle(self, grup: SeritGrubu, konum: Optional[int] = None) -> SeritGrubu:
        konum = len(self.gruplar) if konum is None else konum
        if self.gruplar:
            ay = QFrame()
            ay.setFrameShape(QFrame.VLine)
            ay.setObjectName("seritAyirac")
            self._ayirac.append(ay)
            self._d.insertWidget(self._d.count() - 1, ay)
        self.gruplar.insert(konum, grup)
        # düzen sırası = grup listesi sırası (ayırıcılar araya yeniden dizilir)
        self._yeniden_diz()
        self._duzenle()
        return grup

    def _yeniden_diz(self) -> None:
        for w in [*self.gruplar, *self._ayirac]:
            self._d.removeWidget(w)
        i = 0
        for k, g in enumerate(self.gruplar):
            self._d.insertWidget(i, g)
            i += 1
            if k < len(self.gruplar) - 1:
                self._d.insertWidget(i, self._ayirac[k])
                i += 1

    def _kullanilabilir(self) -> int:
        m = self._d.contentsMargins()
        return self.width() - m.left() - m.right() - len(self._ayirac) * 1

    def _duzenle(self) -> None:
        if self._duzenleniyor or not self.gruplar:
            return
        self._duzenleniyor = True
        try:
            plan = daralma_plani([g.genislikler() for g in self.gruplar],
                                 [g.oncelik for g in self.gruplar], self._kullanilabilir())
            for g, d in zip(self.gruplar, plan):
                g.durum_ayarla(d)
        finally:
            self._duzenleniyor = False

    def resizeEvent(self, olay):
        super().resizeEvent(olay)
        self._duzenle()

    def _olculeri_sifirla(self) -> None:
        for g in self.gruplar:
            g.genislik_sifirla()

    def showEvent(self, olay):
        super().showEvent(olay)
        self._olculeri_sifirla()               # ilk ölçüm stil/yazı tipi uygulanmadan yapılmış olabilir
        self._duzenle()

    def event(self, olay):
        if olay.type() in (QEvent.FontChange, QEvent.StyleChange, QEvent.PolishRequest) and self.isVisible():
            self._olculeri_sifirla()
            self._duzenle()
        return super().event(olay)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, SAYFA_YUKSEKLIGI)

    def guncelle(self) -> None:
        """Alt sınıflar düğme durumlarını eşitler (yalnız görünen sayfa için çağrılır)."""


class _SekmeCubugu(QTabBar):
    ciftTik = Signal(int)

    def mouseDoubleClickEvent(self, olay):
        i = self.tabAt(olay.position().toPoint())
        if i >= 0:
            self.ciftTik.emit(i)
        else:
            super().mouseDoubleClickEvent(olay)


class Serit(QWidget):
    """Sekme satırı + sayfalar. `Dosya` sekmesi sayfa değil açılır menüdür."""

    def __init__(self):
        super().__init__()
        self.setObjectName("serit")
        self._dosya_indeksi: Optional[int] = None
        self._dosya_menusu: Optional[QMenu] = None
        self._onceki = 0
        self._daraltilmis = False
        self._yigin_acik: Optional[QWidget] = None

        self._d = QVBoxLayout(self)
        self._d.setContentsMargins(0, 0, 0, 0)
        self._d.setSpacing(0)
        self.sekmeler = _SekmeCubugu()
        self.sekmeler.setObjectName("seritSekmeleri")
        self.sekmeler.setDrawBase(False)
        self.sekmeler.setExpanding(False)
        self.sekmeler.setFocusPolicy(Qt.NoFocus)
        self.sekmeler.currentChanged.connect(self._sekme_degisti)
        self.sekmeler.tabBarClicked.connect(self._sekme_tiklandi)
        self.sekmeler.ciftTik.connect(lambda _i: self.daralt(not self._daraltilmis))
        self._d.addWidget(self.sekmeler)
        self.yigin = QStackedWidget()
        self.yigin.setObjectName("seritYigin")
        self._d.addWidget(self.yigin)
        QShortcut(QKeySequence("Ctrl+F1"), self, activated=lambda: self.daralt(not self._daraltilmis),
                  context=Qt.WindowShortcut)

    # ------------------------------------------------------------------ sekmeler
    def sekme_ekle(self, ad: str, sayfa: QWidget) -> int:
        self.yigin.addWidget(sayfa)
        i = self.sekmeler.addTab(ad)
        return i

    def dosya_sekmesi_ekle(self, menu: QMenu, ad: str = "Dosya") -> int:
        """Başa sayfasız sekme: tıklayınca `menu` açılır, seçili sekme değişmez."""
        self.yigin.insertWidget(0, QWidget())
        self.sekmeler.blockSignals(True)
        i = self.sekmeler.insertTab(0, ad)
        self.sekmeler.blockSignals(False)
        self._dosya_indeksi, self._dosya_menusu = i, menu
        self._onceki = 1 if self.sekmeler.count() > 1 else 0
        return i

    def sekme_adlari(self) -> List[str]:
        return [self.sekmeler.tabText(i) for i in range(self.sekmeler.count())]

    def sayfa(self, ad: str) -> Optional[QWidget]:
        for i, a in enumerate(self.sekme_adlari()):
            if a == ad:
                return self.yigin.widget(i)
        return None

    def sec(self, ad: str) -> None:
        self.sekmeler.setCurrentIndex(self.sekme_adlari().index(ad))

    def _dosya_menusunu_ac(self) -> None:
        if self._dosya_menusu is not None:
            r = self.sekmeler.tabRect(self._dosya_indeksi)
            self._dosya_menusu.popup(self.sekmeler.mapToGlobal(r.bottomLeft()))

    def _sekme_degisti(self, i: int) -> None:
        if i == self._dosya_indeksi:
            self.sekmeler.blockSignals(True)
            self.sekmeler.setCurrentIndex(self._onceki)
            self.sekmeler.blockSignals(False)
            self._dosya_menusunu_ac()
            return
        self._onceki = i
        self.yigin.setCurrentIndex(i)
        self.guncelle()

    def _sekme_tiklandi(self, i: int) -> None:
        if i == self._dosya_indeksi:
            return
        if self._daraltilmis:
            self._yigin_ac()

    # ------------------------------------------------------------------ daraltma (Ctrl+F1)
    def daraltilmis(self) -> bool:
        return self._daraltilmis

    def daralt(self, evet: bool) -> None:
        if evet == self._daraltilmis:
            return
        self._daraltilmis = evet
        if evet:
            self.yigin.hide()
        else:
            self._yigin_kapat()
            self.yigin.show()

    def _yigin_ac(self) -> None:
        """Daraltılmışken sekmeye tık: sayfa ızgaranın üstünde açılır çerçeve olarak görünür."""
        if self._yigin_acik is not None:
            return
        self._d.removeWidget(self.yigin)
        self.yigin.setParent(None, Qt.Popup)
        self.yigin.setStyleSheet(theme.serit_stil())
        self.yigin.setFixedWidth(self.width())
        self.yigin.move(self.mapToGlobal(QPoint(0, self.sekmeler.height())))
        self.yigin.show()
        self._yigin_acik = self.yigin

    def _yigin_kapat(self) -> None:
        if self._yigin_acik is None:
            return
        self._yigin_acik = None
        self.yigin.hide()
        self.yigin.setParent(self, Qt.Widget)
        self.yigin.setStyleSheet("")
        self.yigin.setMinimumWidth(0)
        self.yigin.setMaximumWidth(16777215)
        self._d.addWidget(self.yigin)

    # ------------------------------------------------------------------ durum / sorgu
    def guncelle(self) -> None:
        """Yalnız görünen sayfayı eşitler (her seçim değişiminde 7 sayfa gezilmez)."""
        s = self.yigin.currentWidget()
        if isinstance(s, SeritSayfasi):
            s.guncelle()

    def eylemler(self) -> List[QAction]:
        """Şeritteki tüm düğmelerin eylemleri ve menülerindeki (alt menüler dahil) eylemler."""
        bulunan: List[QAction] = []

        def menu_gez(m: QMenu):
            for e in m.actions():
                if e.menu() is not None:
                    menu_gez(e.menu())
                elif not e.isSeparator() and not isinstance(e, QWidgetAction):    # renk seçici gibi menü içi widget'lar komut değil
                    bulunan.append(e)
        for d in self.findChildren(QToolButton):
            if d.defaultAction() is not None:
                bulunan.append(d.defaultAction())
            if d.menu() is not None:
                menu_gez(d.menu())
        if self._dosya_menusu is not None:
            menu_gez(self._dosya_menusu)
        return bulunan
