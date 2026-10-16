"""PDF'ten metin çıkarma: Calibri bitişik harfleri (ToUnicode'da U+FFFD) ve ligatür karakterleri.

Çalıştırma:  .venv\Scripts\python.exe -m unittest testler.test_pdf_io -v
"""

import os
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SOZCUK_LOG", "0")

from pdfminer.pdffont import PDFCIDFont  # noqa: E402

from sozcuk import pdf_io  # noqa: E402

ORNEK = Path(__file__).resolve().parent.parent / "FuelErpTeknikEgitimDokumani.pdf"


def _font(ad, cikti):
    return SimpleNamespace(basefont=ad, unicode_map=SimpleNamespace(get_unichr=lambda cid: cikti))


class CalibriBitisikHarf(unittest.TestCase):
    def setUp(self):
        pdf_io._patch_calibri_ligatures()

    def test_calibri_ligaturleri_cozulur(self):
        font = _font("/'GNOBER+Calibri'", "�")
        for cid, metin in ((0x19F, "ti"), (0x1A8, "tı"), (0x14C, "ft"), (0x137, "fı"), (0x1B4, "ttı")):
            self.assertEqual(PDFCIDFont.to_unichr(font, cid), metin)

    def test_baska_yazi_tipi_ve_bilinmeyen_glif_degismez(self):
        self.assertEqual(PDFCIDFont.to_unichr(_font("/'X+SegoeUIEmoji'", "�"), 0x19F), "�")
        self.assertEqual(PDFCIDFont.to_unichr(_font("/'X+Calibri'", "�"), 0x999), "�")
        self.assertEqual(PDFCIDFont.to_unichr(_font("/'X+Calibri'", "a"), 0x19F), "a")

    def test_yama_iki_kez_uygulanmaz(self):
        pdf_io._patch_calibri_ligatures()
        pdf_io._patch_calibri_ligatures()
        self.assertEqual(PDFCIDFont.to_unichr(_font("Calibri", "�"), 0x19F), "ti")


@unittest.skipUnless(ORNEK.exists(), "örnek PDF yok")
class OrnekPdf(unittest.TestCase):
    def test_bozuk_karakter_kalmaz(self):
        metin = "\n".join(p.text for p in pdf_io.extract(ORNEK))
        self.assertNotIn("�", metin)
        for bozuk in ("Eği�m", "sa�ş", "ﬁ", "ﬂ"):
            self.assertNotIn(bozuk, metin)
        self.assertIn("Eğitim ve Kullanım Kitapçığı", metin)
        self.assertIn("hazırlanmıştır", metin)


if __name__ == "__main__":
    unittest.main()
