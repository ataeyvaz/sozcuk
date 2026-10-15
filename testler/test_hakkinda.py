"""Hakkında penceresi, Eagle Office paket adı ve iletişim bağlantısı.

Çalıştırma (proje klasöründe):
    .venv\Scripts\python.exe -m unittest testler.test_hakkinda -v
"""

import os
import re
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SOZCUK_LOG", "0")

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from sozcuk import (  # noqa: E402
    APP_NAME, DEVELOPERS, ILETISIM_EPOSTA, PAKET_ADI, PAKET_URUNLERI, __version__,
)
from sozcuk.hakkinda import CREDITS, AboutDialog, hakkinda_metni, paket_metni  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
_app = QApplication.instance() or QApplication([])


class HakkindaTesti(unittest.TestCase):
    def test_sabitler(self):
        self.assertEqual(__version__, "1.5")
        self.assertEqual(PAKET_ADI, "Eagle Office")
        self.assertEqual(ILETISIM_EPOSTA, "ataeyvaz@gmail.com")
        self.assertEqual(DEVELOPERS, "Developed By Usta ve Ata")
        self.assertEqual(PAKET_URUNLERI, (("Sözcük", "kelime işlemci"), ("Tabcel", "hesap tablosu")))

    def test_paket_metni(self):
        self.assertEqual(paket_metni(),
                         "Eagle Office paketi: Sözcük (kelime işlemci)  ·  Tabcel (hesap tablosu)")

    def test_duz_metin(self):
        m = hakkinda_metni()
        self.assertEqual(m.splitlines()[0], "Eagle Office")
        for parca in (APP_NAME, __version__, DEVELOPERS, paket_metni(), f"İletişim: {ILETISIM_EPOSTA}",
                      "sunucuya gönderilmez"):
            self.assertIn(parca, m)
        for ad, _, lisans in CREDITS:
            self.assertIn(ad, m)
            self.assertIn(lisans, m)

    def test_pencere(self):
        d = AboutDialog()
        self.assertEqual(d.windowTitle(), "Sözcük Hakkında")
        etiketler = d.findChildren(QLabel)
        metin = " ".join(e.text() for e in etiketler)
        for parca in ("Eagle Office", "Sözcük", DEVELOPERS, "PySide6", "sunucuya gönderilmez", "Tabcel"):
            self.assertIn(parca, metin)
        baglanti = next(e for e in etiketler if "mailto:" in e.text())
        self.assertIn(f"mailto:{ILETISIM_EPOSTA}", baglanti.text())
        self.assertTrue(baglanti.openExternalLinks())

    def test_menu_eylemi_pencereyi_acar(self):
        from sozcuk.window import MainWindow
        acilan = []
        with mock.patch.object(AboutDialog, "exec", lambda self: acilan.append(self.windowTitle()) or 0):
            w = MainWindow()
            w.show_about()
        self.assertEqual(acilan, ["Sözcük Hakkında"])

    def test_kurulum_betigi_ve_readme(self):
        iss = (KOK / "kurulum" / "sozcuk.iss").read_text(encoding="utf-8-sig")
        self.assertIn('#define AppPublisher "Eagle Office"', iss)
        self.assertIn(f'#define AppContact "mailto:{ILETISIM_EPOSTA}"', iss)
        self.assertIn('#define AppVersion "1.5"', iss)
        self.assertRegex(iss, r"AppContact=\{#AppContact\}")
        self.assertIn("**Eagle Office** paketi", (KOK / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
