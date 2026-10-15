"""Sekmeli şerit (Word/Excel gibi): daralma planı, sekmeler, eylem kataloğu, Hızlı Erişim, kısayollar.

Çalıştırma (proje klasöründe):
    .venv\\Scripts\\python.exe -m unittest testler.test_serit -v

Pencere testleri ekransız (offscreen) çalışır; Hızlı Erişim dosyası geçici klasöre yönlendirilir.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SOZCUK_LOG", "0")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from sozcuk import hizli_erisim, theme  # noqa: E402
from sozcuk.serit import SeritSayfasi, daralma_plani  # noqa: E402
from sozcuk.window import MainWindow  # noqa: E402

_app = QApplication.instance() or QApplication([])
theme.apply(_app)

SEKMELER = ["Dosya", "Giriş", "Ekle", "Sayfa Düzeni", "Gözden Geçir", "Görünüm", "Yardım"]


class DaralmaPlani(unittest.TestCase):
    def test_siyiyorsa_hepsi_tam(self):
        self.assertEqual(daralma_plani([[100, 60, 30], [80, None, 30]], [5, 5], 500), [0, 0])

    def test_once_yazisiz_sonra_acilir(self):
        genislik = [[100, 60, 30], [100, 60, 30], [100, None, 30]]
        self.assertEqual(daralma_plani(genislik, [1, 2, 3], 290), [1, 0, 0])
        self.assertEqual(daralma_plani(genislik, [1, 2, 3], 250), [1, 1, 0])
        self.assertEqual(daralma_plani(genislik, [1, 2, 3], 200), [2, 1, 0])
        self.assertEqual(daralma_plani(genislik, [1, 2, 3], 150), [2, 2, 2])

    def test_esit_oncelikte_sagdaki_once(self):
        genislik = [[100, 60, 30], [100, 60, 30]]
        self.assertEqual(daralma_plani(genislik, [5, 5], 170), [0, 1])

    def test_hic_sigmazsa_hepsi_acilir(self):
        self.assertEqual(daralma_plani([[100, 60, 30], [100, 60, 30]], [1, 2], 10), [2, 2])


class SeritPenceresi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls._yama = mock.patch.object(hizli_erisim, "dosya_yolu", lambda: Path(cls._dir.name) / "hizli.json")
        cls._yama.start()

    @classmethod
    def tearDownClass(cls):
        cls._yama.stop()
        cls._dir.cleanup()

    def setUp(self):
        self.w = MainWindow()
        self.w.resize(1200, 700)
        self.w.show()
        _app.processEvents()

    def tearDown(self):
        self.w.editor.document().setModified(False)
        self.w.close()
        _app.processEvents()

    def test_sekmeler_ve_eski_arayuz_kalkti(self):
        self.assertEqual(self.w.ribbon.sekme_adlari(), SEKMELER)
        self.assertFalse(hasattr(self.w, "menu_row"))
        self.assertFalse(hasattr(self.w, "command_bar"))

    def test_dosya_sekmesi_menu_acar_sayfa_degistirmez(self):
        self.w.ribbon.sec("Ekle")
        self.assertIs(self.w.ribbon._dosya_menusu, self.w.file_menu)
        sekmeler = self.w.ribbon.sekmeler
        self.assertEqual(sekmeler.tabText(sekmeler.currentIndex()), "Ekle")

    def test_dosya_sekmesine_tiklayinca_menu_acilir(self):
        self.w.ribbon.sec("Ekle")
        acilan = []
        self.w.file_menu.popup = lambda konum, *a: acilan.append(konum)
        sekmeler = self.w.ribbon.sekmeler
        QTest.mouseClick(sekmeler, Qt.LeftButton, Qt.NoModifier, sekmeler.tabRect(0).center())
        self.assertEqual(len(acilan), 1)
        self.assertEqual(sekmeler.tabText(sekmeler.currentIndex()), "Ekle")

    def test_dar_pencerede_grup_acilir_dugmeye_iner_ve_geri_gelir(self):
        r = self.w.ribbon
        r.sec("Giriş")
        sayfa = r.sayfa("Giriş")
        self.w.resize(760, 700)
        for _ in range(3):
            _app.processEvents()
        self.assertIn(2, [g.durum for g in sayfa.gruplar])
        self.w.resize(1700, 700)  # ekransız ortamda yazı tipi yok, metinler geniş çıkar: bol yer ver
        for _ in range(3):
            _app.processEvents()
        self.assertEqual([g.durum for g in sayfa.gruplar], [0] * len(sayfa.gruplar))

    def test_her_sekme_sayfasi_gruplu(self):
        for ad in SEKMELER[1:]:
            sayfa = self.w.ribbon.sayfa(ad)
            self.assertIsInstance(sayfa, SeritSayfasi)
            self.assertTrue(sayfa.gruplar, ad)

    def test_tum_komutlar_seritten_erisilir(self):
        eylemler = set(self.w.ribbon.eylemler())
        for ad in ("bold", "italic", "underline", "strike", "bullets", "numbers", "outdent", "indent",
                   "align_left", "align_center", "align_right", "align_justify", "grow_font", "shrink_font",
                   "clear_format", "add_font", "cut", "copy", "paste", "paste_text", "find", "replace",
                   "link", "translate", "language_packs", "spell_next", "spell_live", "dictation_vocabulary",
                   "ruler", "zoom_in", "zoom_out", "zoom_100", "fit_width", "fit_page", "help", "shortcuts",
                   "about", "open_log"):
            if ad == "help":
                continue  # Yardım sekmesinde de var ama başlıktaki düğme aynı eylemi kullanır
            self.assertIn(self.w.eylemler[ad], eylemler, ad)
        self.assertIn(self.w.eylemler["help"], eylemler)
        # mikrofon / sesli oku / renk / tablo / resim / simge / sayfa menüleri hazır bileşen olarak şeritte
        butonlar = set(self.w.ribbon.findChildren(QToolButton))
        for bilesen in (self.w.mic_button, self.w.read_button, self.w.color_button, self.w.highlight_button,
                        self.w.spacing_button):
            self.assertIn(bilesen, butonlar)
        menuler = {b.menu() for b in butonlar if b.menu() is not None}
        for menu in (self.w.table_menu, self.w.image_menu, self.w.symbol_menu, self.w.page_menu.margins_menu,
                     self.w.page_menu.orientation_menu, self.w.page_menu.size_menu, self.w.page_menu.number_menu):
            self.assertIn(menu, menuler)

    def test_ctrl_f1_daraltir_ve_acar(self):
        r = self.w.ribbon
        self.assertFalse(r.daraltilmis())
        r.daralt(True)
        self.assertTrue(r.daraltilmis())
        self.assertFalse(r.yigin.isVisible())
        r.daralt(False)
        self.assertFalse(r.daraltilmis())
        self.assertTrue(r.yigin.isVisible())

    def test_dugme_odagi_calmaz(self):
        for d in self.w.ribbon.findChildren(QToolButton):
            if d.objectName() in ("ScrollLeftButton", "ScrollRightButton"):
                continue  # sekme çubuğunun kendi kaydırma okları
            self.assertEqual(d.focusPolicy(), Qt.NoFocus, d.text() or d.toolTip())

    def test_kisayollar_her_sekmede_calisir(self):
        ed = self.w.editor
        ed.setFocus()
        ed.textCursor().insertText("deneme")
        ed.select_all()
        for tus, eylem in ((Qt.Key_B, "bold"), (Qt.Key_I, "italic"), (Qt.Key_U, "underline")):
            onceki = self.w.eylemler[eylem].isChecked()
            QTest.keyClick(self.w, tus, Qt.ControlModifier)
            self.assertNotEqual(self.w.eylemler[eylem].isChecked(), onceki, eylem)
        self.w.ribbon.sec("Görünüm")
        onceki = self.w.eylemler["bold"].isChecked()
        QTest.keyClick(self.w, Qt.Key_B, Qt.ControlModifier)
        self.assertNotEqual(self.w.eylemler["bold"].isChecked(), onceki)

    def test_kes_kopyala_secime_gore_etkin(self):
        ed = self.w.editor
        ed.textCursor().insertText("merhaba")
        cursor = ed.textCursor()
        cursor.clearSelection()
        ed.setTextCursor(cursor)
        _app.processEvents()
        self.assertFalse(self.w.act_cut.isEnabled())
        ed.select_all()
        _app.processEvents()
        self.assertTrue(self.w.act_cut.isEnabled())
        self.assertTrue(self.w.act_copy.isEnabled())

    def test_cetvel_eylemi_durum_cubuguyla_esli(self):
        e = self.w.eylemler["ruler"]
        self.assertEqual(e.isChecked(), self.w.ruler_button.isChecked())
        e.trigger()
        self.assertEqual(e.isChecked(), self.w.ruler_button.isChecked())
        e.trigger()
        self.assertEqual(e.isChecked(), self.w.ruler_button.isChecked())

    def test_hizli_erisim_ekle_kaldir_ve_kalicilik(self):
        w = self.w
        self.assertFalse(w.hizli_var_mi("bold"))
        self.assertTrue(w.hizli_ekle("bold", "bold"))
        self.assertFalse(w.hizli_ekle("bold", "bold"))        # ikinci kez eklenmez
        self.assertTrue(w.hizli_var_mi("bold"))
        self.assertEqual(w._hizli_kutu.layout().count(), 1)
        self.assertEqual([o["eylem"] for o in hizli_erisim.oku()], ["bold"])
        d = w._hizli_kutu.layout().itemAt(0).widget()
        gorulen = []
        w._hizli_menu_goster = lambda menu, konum: gorulen.append([a.text() for a in menu.actions()])
        self.assertTrue(w.hizli_erisim_menusu(d, None))
        self.assertEqual(gorulen[-1], [hizli_erisim.KALDIR])
        self.assertTrue(w.hizli_kaldir("bold"))
        self.assertEqual(w._hizli_kutu.layout().count(), 0)
        self.assertEqual(hizli_erisim.oku(), [])
        sdugme = next(b for b in w.ribbon.findChildren(QToolButton)
                      if b.objectName() == "seritDugme" and b.defaultAction() is w.eylemler["italic"])
        self.assertTrue(w.hizli_erisim_menusu(sdugme, None))
        self.assertEqual(gorulen[-1], [hizli_erisim.EKLE])

    def test_giris_sekmesi_dar_pencerede_tasmaz(self):
        for genislik in (1100, 800):
            self.w.resize(genislik, 700)
            self.w.ribbon.sec("Giriş")
            for _ in range(3):
                _app.processEvents()
            sayfa = self.w.ribbon.sayfa("Giriş")
            son = max(g.geometry().right() for g in sayfa.gruplar if g.isVisible())
            self.assertLessEqual(son, sayfa.width() + 2, f"{genislik}: gruplar sayfa dışına taşıyor")
            if genislik >= 1100:
                self.assertNotIn(2, [g.durum for g in sayfa.gruplar], "1100 px'te grup açılır düğmeye inmemeli")


if __name__ == "__main__":
    unittest.main()
