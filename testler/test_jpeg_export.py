"""Sayfaları JPEG olarak kaydetme: sayfa aralığı, dosya adı, sayfa görüntüleri.

Çalıştırma:  .venv\\Scripts\\python.exe -m unittest testler.test_jpeg_export -v
"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SOZCUK_LOG", "0")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sozcuk import jpeg_export, theme  # noqa: E402
from sozcuk.window import MainWindow  # noqa: E402

_app = QApplication.instance() or QApplication([])
theme.apply(_app)


class Aralik(unittest.TestCase):
    def test_aralik_ve_tekli(self):
        self.assertEqual(jpeg_export.parse_pages("1-3, 5", 10), [1, 2, 3, 5])
        self.assertEqual(jpeg_export.parse_pages("8-", 10), [8, 9, 10])
        self.assertEqual(jpeg_export.parse_pages("-2", 10), [1, 2])
        self.assertEqual(jpeg_export.parse_pages("3 3 2", 10), [2, 3])

    def test_hatali(self):
        for metin in ("", "abc", "0", "11", "5-3", "1-99"):
            with self.assertRaises(jpeg_export.RangeError, msg=metin):
                jpeg_export.parse_pages(metin, 10)

    def test_dosya_adi(self):
        self.assertEqual(jpeg_export.file_name("ornek", 1, 30), "ornek01.jpeg")
        self.assertEqual(jpeg_export.file_name("ornek", 12, 30), "ornek12.jpeg")
        self.assertEqual(jpeg_export.file_name("ornek", 7, 120), "ornek007.jpeg")


class Sayfalar(unittest.TestCase):
    def test_sayfa_goruntuleri(self):
        w = MainWindow()
        try:
            w.editor.text.setPlainText("\n".join(f"Satır {i}" for i in range(300)))
            _app.processEvents()
            toplam = w.editor.page_total()
            self.assertGreater(toplam, 1)
            sonuc = list(w.editor.page_images([1, 2], 96))
            self.assertEqual([s[0] for s in sonuc], [1, 2])
            self.assertEqual(sonuc[0][1], toplam)
            en, boy = w.editor.page_size()
            self.assertEqual(sonuc[0][2].width(), round(en))
            self.assertEqual(sonuc[0][2].height(), round(boy))
            self.assertEqual(len(list(w.editor.page_images(None, 48))), toplam)
            # yazdırınca gerçek kâğıt boyutunda çıkması için çözünürlük bilgisi dosyaya yazılır (A4: 210×297 mm)
            _, _, a4 = next(w.editor.page_images([1], 150))
            self.assertEqual(round(a4.dotsPerMeterX() * 0.0254), 150)
            self.assertAlmostEqual(a4.width() / 150 * 25.4, 210, delta=1)
            self.assertAlmostEqual(a4.height() / 150 * 25.4, 297, delta=1)
        finally:
            w.editor.document().setModified(False)
            w.close()


if __name__ == "__main__":
    unittest.main()
