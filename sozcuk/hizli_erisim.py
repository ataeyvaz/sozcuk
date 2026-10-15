"""Özelleştirilebilir Hızlı Erişim çubuğu (Tabcel'deki `hizli_erisim.py`'den uyarlandı): başlık şeridindeki Kaydet / Geri Al / Yinele düğmelerinin
yanına, şerit düğmesine sağ tıklayıp "Hızlı Erişim Araç Çubuğuna Ekle" ile komut eklenir; eklenen düğmeye sağ tık
→ "Hızlı Erişimden Kaldır". Liste `%APPDATA%/Sözcük/hizli_erisim.json`'da saklanır (tüm pencerelerde ortak)."""
import json
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QEvent, QObject, QSize, QStandardPaths, Qt
from PySide6.QtWidgets import QApplication, QMenu, QToolButton

from . import icons

DOSYA_ADI = "hizli_erisim.json"
EKLE = "Hızlı Erişim Araç Çubuğuna Ekle"
KALDIR = "Hızlı Erişim Araç Çubuğundan Kaldır"
SINIR = 12                                                   # başlık şeridini taşırmamak için


def dosya_yolu() -> Path:
    return Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / DOSYA_ADI


def oku() -> List[Dict]:
    """[{eylem, ikon}] — bozuk/yok dosyada boş liste."""
    try:
        veri = json.loads(dosya_yolu().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(veri, list):
        return []
    return [{"eylem": o["eylem"], "ikon": o.get("ikon")} for o in veri
            if isinstance(o, dict) and isinstance(o.get("eylem"), str)][:SINIR]


def yaz(liste: List[Dict]) -> None:
    """Geçici dosyaya yaz → yerine koy ; hata sessiz (ayar kaybı kullanıcıyı bölmez)."""
    try:
        yol = dosya_yolu()
        yol.parent.mkdir(parents=True, exist_ok=True)
        gecici = yol.with_suffix(".tmp")
        gecici.write_text(json.dumps(liste, ensure_ascii=False, indent=1), encoding="utf-8")
        gecici.replace(yol)
    except OSError:
        pass


class _SagTikSuzgeci(QObject):
    """Uygulama düzeyinde TEK süzgeç: şerit düğmeleri açılır pencerelere taşınabildiği için (daralma) düğmelere tek tek
    değil, olaya bakılır; yalnız `HizliErisim` karışımı olan pencerenin düğmeleri ilgilenir."""

    def eventFilter(self, nesne, olay):
        if olay.type() != QEvent.ContextMenu or not isinstance(nesne, QToolButton):
            return False
        try:
            pencere = nesne.window()
        except RuntimeError:                                  # C++ nesnesi silinmiş
            return False
        islev = getattr(pencere, "hizli_erisim_menusu", None)
        return bool(islev and islev(nesne, olay.globalPos()))


_suzgec: Optional[_SagTikSuzgeci] = None


class HizliErisim:
    """`Pencere` karışımı. Gerektirir: `eylemler` (anahtar → QAction), `_hizli_kutu` (düğmelerin konacağı widget)."""

    def _hizli_kur(self) -> None:
        global _suzgec
        if _suzgec is None:
            _suzgec = _SagTikSuzgeci()
            uygulama = QApplication.instance()
            uygulama.installEventFilter(_suzgec)
            uygulama.aboutToQuit.connect(lambda: uygulama.removeEventFilter(_suzgec))   # çıkışta yarı yıkılmış nesnelere dokunma
        self._hizli_liste = [o for o in oku() if o["eylem"] in self.eylemler]
        self._hizli_diz()

    def _hizli_diz(self) -> None:
        d = self._hizli_kutu.layout()
        while d.count():
            oge = d.takeAt(0).widget()
            if oge is not None:
                oge.setParent(None)
                oge.deleteLater()
        for o in self._hizli_liste:
            d.addWidget(self._hizli_dugme(o))

    def _hizli_dugme(self, o: Dict) -> QToolButton:
        a = self.eylemler[o["eylem"]]
        b = QToolButton()
        b.setObjectName("hizliDugme")
        b.setProperty("hizliEylem", o["eylem"])
        b.setDefaultAction(a)
        b.setFocusPolicy(Qt.NoFocus)
        b.setIconSize(QSize(20, 20))
        if o.get("ikon"):
            b.setIcon(icons.icon(o["ikon"], "#ffffff"))
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
        else:                                                # simgesiz komut: kısa metin
            b.setToolButtonStyle(Qt.ToolButtonTextOnly)
            b.setStyleSheet("color: #ffffff;")
        b.setToolTip(a.toolTip())
        return b

    # ------------------------------------------------------------------ düzenleme
    def hizli_anahtar(self, dugme: QToolButton) -> Optional[str]:
        """Düğmenin eylem kataloğundaki anahtarı (yoksa None)."""
        k = dugme.property("hizliEylem")
        if k in self.eylemler:
            return k
        a = dugme.defaultAction()
        if a is None:
            return None
        return next((anahtar for anahtar, e in self.eylemler.items() if e is a), None)

    def hizli_var_mi(self, anahtar: str) -> bool:
        return any(o["eylem"] == anahtar for o in self._hizli_liste)

    def hizli_ekle(self, anahtar: str, ikon: Optional[str] = None) -> bool:
        if anahtar not in self.eylemler or self.hizli_var_mi(anahtar) or len(self._hizli_liste) >= SINIR:
            return False
        self._hizli_liste.append({"eylem": anahtar, "ikon": ikon})
        self._hizli_degisti()
        return True

    def hizli_kaldir(self, anahtar: str) -> bool:
        yeni = [o for o in self._hizli_liste if o["eylem"] != anahtar]
        if len(yeni) == len(self._hizli_liste):
            return False
        self._hizli_liste = yeni
        self._hizli_degisti()
        return True

    def _hizli_degisti(self) -> None:
        yaz(self._hizli_liste)
        self._hizli_diz()

    def hizli_erisim_menusu(self, dugme: QToolButton, konum) -> bool:
        """Sağ tık menüsü; ilgilenilen bir düğmeyse True (olay tüketilir). Testlerde `menu_goster` yamalanır."""
        anahtar = self.hizli_anahtar(dugme)
        if anahtar is None or dugme.objectName() not in ("seritDugme", "hizliDugme"):
            return False
        m = QMenu(self)
        if dugme.objectName() == "hizliDugme" or self.hizli_var_mi(anahtar):
            m.addAction(KALDIR, lambda: self.hizli_kaldir(anahtar))
        else:
            ikon = dugme.property("ikonAdi") or self.eylemler[anahtar].property("ikonAdi")
            m.addAction(EKLE, lambda: self.hizli_ekle(anahtar, ikon))
        self._hizli_menu_goster(m, konum)
        return True

    def _hizli_menu_goster(self, menu: QMenu, konum) -> None:
        menu.exec(konum)
