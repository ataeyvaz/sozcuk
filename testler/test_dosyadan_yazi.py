"""Ses/video dosyasından yazıya dökme testleri.

Çalıştırma:  .venv\\Scripts\\python -m unittest testler.test_dosyadan_yazi -v
Gerçek konuşma gerektiren uçtan uca deneme (model + örnek ses) otomatik teste konmadı; elle denenir.
"""

import math
import os
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QCoreApplication  # noqa: E402

from sozcuk import transcribe_file as tf  # noqa: E402


class SaflYardimcilar(unittest.TestCase):
    SEGMENTS = [(0, 4.7, "Merhaba."), (5.8, 9.5, "İkinci cümle."), (9.7, 11.8, "Üçüncü."),
                (15.0, 17.0, "Uzun duraktan sonra yeni paragraf."), (3725.2, 3727, "Bir saat sonra.")]

    def test_paragraflar_duraklamada_bolunur(self):
        paras = tf.build_paragraphs(self.SEGMENTS)
        self.assertEqual([p[1] for p in paras],
                         ["Merhaba. İkinci cümle. Üçüncü.", "Uzun duraktan sonra yeni paragraf.", "Bir saat sonra."])

    def test_zaman_damgasi(self):
        text = tf.render_text(self.SEGMENTS, timestamps=True)
        self.assertIn("[00:00:00] Merhaba.", text)
        self.assertIn("[00:00:15] Uzun duraktan", text)
        self.assertIn("[01:02:05] Bir saat sonra.", text)
        self.assertNotIn("[", tf.render_text(self.SEGMENTS))

    def test_uzun_kesintisiz_konusma_cumle_sonunda_bolunur(self):
        long = [(i * 3.0, i * 3.0 + 2.9, "Bu bir deneme cümlesidir ve oldukça uzundur.") for i in range(40)]
        self.assertGreater(len(tf.build_paragraphs(long)), 1)

    def test_bos_metinler_atlanir(self):
        self.assertEqual(tf.render_text([(0, 1, "  "), (1, 2, "")]), "")
        self.assertEqual(tf.render_srt([(0, 1, " ")]), "")

    def test_srt_biçimi(self):
        srt = tf.render_srt([(0, 4.7, "Birinci"), (3725.25, 3727.5, "İkinci")])
        self.assertEqual(srt.splitlines()[:3], ["1", "00:00:00,000 --> 00:00:04,700", "Birinci"])
        self.assertIn("2\n01:02:05,250 --> 01:02:07,500\nİkinci", srt)

    def test_sure_bicimi(self):
        self.assertEqual(tf.fmt_duration(75), "01:15")
        self.assertEqual(tf.fmt_duration(3725), "1:02:05")

    def test_desteklenen_uzantilar(self):
        self.assertEqual(set(tf.EXTENSIONS), {"mp3", "wav", "opus", "ogg", "flac"})


class SesCozmeTesti(unittest.TestCase):
    """soundfile ile çözme: her biçimde 16 kHz mono ve doğru süre (parça sınırlarında kayma olmamalı)."""

    @staticmethod
    def _write(path, subtype_format, rate, channels, seconds):
        import numpy as np
        import soundfile as sf
        t = np.arange(int(rate * seconds)) / rate
        wave_ = 0.3 * np.sin(2 * np.pi * 440 * t)
        data = np.stack([wave_] * channels, axis=1) if channels > 1 else wave_
        sf.write(path, data, rate, format=subtype_format)

    def test_biçimler_16k_mono_ve_sure(self):
        folder = tempfile.mkdtemp()
        cases = [("a.wav", "WAV", 44100, 2), ("b.flac", "FLAC", 48000, 1), ("c.ogg", "OGG", 22050, 2),
                 ("d.opus", "OGG", 48000, 1), ("e.mp3", "MP3", 44100, 2), ("f.wav", "WAV", 16000, 1)]
        for name, fmt, rate, channels in cases:
            path = os.path.join(folder, name)
            if name.endswith(".opus"):
                import numpy as np
                import soundfile as sf
                t = np.arange(48000 * 3) / 48000
                sf.write(path, 0.3 * np.sin(2 * np.pi * 440 * t), 48000, format="OGG", subtype="OPUS")
            else:
                self._write(path, fmt, rate, channels, 3.0)
            audio = tf.decode_audio(path)
            self.assertEqual(audio.dtype.name, "float32", name)
            self.assertEqual(audio.ndim, 1, name)
            self.assertAlmostEqual(len(audio) / 16000, 3.0, delta=0.12, msg=name)
            self.assertGreater(float(abs(audio).max()), 0.1, name)         # sessizlik değil

    def test_uzun_dosya_parca_sinirlarinda_kaymaz(self):
        import numpy as np
        path = os.path.join(tempfile.mkdtemp(), "uzun.wav")
        self._write(path, "WAV", 44100, 2, 65.0)                           # 30 sn'lik parçalar: 3 parça
        audio = tf.decode_audio(path)
        self.assertAlmostEqual(len(audio) / 16000, 65.0, delta=0.05)
        # parça sınırlarında (30 ve 60 sn) süreklilik: ardışık örnekler arasında sıçrama olmamalı
        for second in (30, 60):
            i = second * 16000
            self.assertLess(float(np.abs(np.diff(audio[i - 5:i + 5])).max()), 0.2)

    def test_desteklenmeyen_bicim_anlasilir_hata(self):
        path = os.path.join(tempfile.mkdtemp(), "video.mp4")
        Path(path).write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200)
        from sozcuk import dictation
        with self.assertRaises(dictation.DictationError) as ctx:
            tf.decode_audio(path)
        self.assertIn("desteklenmiyor", str(ctx.exception))

    def test_cozme_iptal_edilebilir(self):
        import threading
        path = os.path.join(tempfile.mkdtemp(), "x.wav")
        self._write(path, "WAV", 16000, 1, 3.0)
        flag = threading.Event()
        flag.set()
        with self.assertRaises(tf.Cancelled):
            tf.decode_audio(path, flag)


class IsciTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def _tone(self, seconds=2.0):
        """Konuşma içermeyen (sinüs) kısa wav: işçi çökmeden 'metin yok' ile bitmeli."""
        path = os.path.join(tempfile.mkdtemp(), "ton.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 440 * i / 16000)))
                                   for i in range(int(16000 * seconds))))
        return path

    def _run(self, worker, timeout_ms=180000):
        results = []
        worker.finished_state.connect(lambda state, message: results.append((state, message)))
        worker.start()
        deadline = timeout_ms / 1000
        import time
        t0 = time.time()
        while not results and time.time() - t0 < deadline:
            self.app.processEvents()
            time.sleep(0.02)
        worker.wait(5000)
        self.app.processEvents()
        return results

    def test_olmayan_dosya_hata_verir(self):
        worker = tf.FileTranscribeWorker(r"C:\yok\yok.mp3", "tr", "Dengeli")
        state, message = self._run(worker)[0]
        self.assertEqual(state, "error")
        self.assertTrue(message)

    def test_konusmasiz_ses_cokmeden_biter(self):
        worker = tf.FileTranscribeWorker(self._tone(), "tr", "Dengeli")
        segments = []
        worker.segment.connect(lambda s, e, t: segments.append(t))
        state, _ = self._run(worker)[0]
        self.assertEqual(state, "done")

    def test_iptal_erken_biter(self):
        worker = tf.FileTranscribeWorker(self._tone(), "tr", "Dengeli")
        worker.cancel()                      # başlamadan iptal: model yüklendikten sonra hemen çıkmalı
        state, _ = self._run(worker)[0]
        self.assertEqual(state, "cancelled")


if __name__ == "__main__":
    unittest.main()
